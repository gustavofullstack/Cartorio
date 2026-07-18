#!/usr/bin/env python3
"""G8.15.T2 — AlertManager → Telegram bridge (LGPD-safe).

Pipeline OFFLINE-friendly (sem VPS, sem AlertManager live nesta sessão).
Em produção este script é chamado pelo endpoint FastAPI
`POST /api/v1/webhook/alertmanager` quando o AlertManager dispara.

**LGPD Art. 46**: o conteúdo enviado ao Telegram contém APENAS metadata
categórica. O payload bruto (incluindo labels com possíveis CPF/RG) é
processado em memória e AUTO-PURGE no fim — nunca persistido, nunca logado.

Modos de uso:

    # Dry-run (default, sem rede): imprime mensagem que SERIA enviada
    python3 scripts/alert_to_telegram.py --input payload.json

    # Apply mode: envia para Telegram real (requer TELEGRAM_BOT_TOKEN + chat_id)
    python3 scripts/alert_to_telegram.py --input payload.json --apply

    # Stdin mode: pipe do AlertManager via `cat | python3 ...`
    curl -s http://alertmanager:9093/api/v1/alerts | \\
        python3 scripts/alert_to_telegram.py --apply

Formato do payload (compatível com AlertManager webhook v4):

    {
      "version": "4",
      "groupKey": "{}:{alertname=\"Foo\"}",
      "status": "firing|resolved",
      "receiver": "cartorio-telegram-default",
      "alerts": [
        {
          "status": "firing",
          "labels": {"alertname": "HighErrorRate", "severity": "critical",
                     "instance": "cartorio-api:8000", "squad": "cartorio-sre"},
          "annotations": {"summary": "Error rate > 5%", "description": "..."},
          "startsAt": "2026-07-18T14:00:00Z",
          "endsAt": "0001-01-01T00:00:00Z"
        }
      ]
    }

Modified by Gustavo Almeida — G8.15.T2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# --- LGPD PII patterns (DATASENSITIVE — NUNCA ecoar pra Telegram) ---
# Mesmo filtros usados em app/services/pii.py. Aqui no nível do script pra
# defesa em profundidade (defense-in-depth: 3 layers).
_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CPF", re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")),
    ("RG", re.compile(r"\d{1,2}\.?\d{3}\.?\d{3}-?\d{1,2}")),
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    # PHONE_BR: aceita (XX) 9XXXX-XXXX, (XX) XXXX-XXXX, +55 XX 9XXXX-XXXX, etc.
    ("PHONE_BR", re.compile(r"\+?55?\s?\(?\d{2}\)?\s?\d{4,5}-?\d{4}|\(?\d{2}\)?\s?\d{4,5}-?\d{4}")),
    ("PROTOCOL", re.compile(r"\bPROT-\d{4}-\d{6}\b", re.IGNORECASE)),
    ("ESCRITURA", re.compile(r"\bESCR-\d{6}\b", re.IGNORECASE)),
)

# Severity → emoji + Telegram parse_mode marker (HTML sem emojis por padrão do projeto)
SEVERITY_MARKERS: dict[str, tuple[str, str]] = {
    "critical": ("🔴", "P0"),
    "warning": ("⚠️", "P1"),
    "info": ("ℹ️", "P2"),
}

# Status marker
STATUS_MARKERS: dict[str, str] = {
    "firing": "🚨 FIRING",
    "resolved": "✅ RESOLVED",
}


@dataclass(frozen=True)
class FormattedAlert:
    """Mensagem formatada pronta pra enviar (LGPD-safe)."""

    fingerprint: str  # hash pra dedup
    text: str
    severity: str
    alertname: str
    instance: str
    status: str
    squad: str

    def to_dict(self) -> dict[str, str]:
        return {
            "fingerprint": self.fingerprint,
            "text": self.text,
            "severity": self.severity,
            "alertname": self.alertname,
            "instance": self.instance,
            "status": self.status,
            "squad": self.squad,
        }


def _scrub_pii(text: str) -> tuple[str, list[str]]:
    """Strip PII from any text. Returns (scrubbed_text, list_of_redactions).

    LGPD Art. 46: zero dado pessoal bruto em canal externo (Telegram).
    Se um label/annotation contém CPF/RG/etc, ele é REDACTED e listado no audit.
    """
    if not text:
        return text, []
    redactions: list[str] = []
    out = text
    for label, pattern in _PII_PATTERNS:
        matches = pattern.findall(out)
        if matches:
            redactions.append(f"{label}={len(matches)}")
            out = pattern.sub(f"[{label}_REDACTED]", out)
    return out, redactions


def _safe_label(value: str | None) -> str:
    """Trunca e sanitiza um label pra uso em mensagem Telegram."""
    if not value:
        return "unknown"
    cleaned, _ = _scrub_pii(str(value))
    return cleaned[:120]


def _fingerprint(alert: dict[str, Any]) -> str:
    """Hash estável de um alerta (labels canônicas) pra dedup.

    Não inclui startsAt/endsAt porque AlertManager repete o mesmo alerta
    em group_interval; queremos dedup de MESMO alerta, não de MESMA janela.
    """
    labels = alert.get("labels", {}) or {}
    canonical = "|".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def format_alert(payload: dict[str, Any]) -> list[FormattedAlert]:
    """Formata payload AlertManager em mensagens Telegram LGPD-safe.

    Args:
        payload: dict no formato webhook v4 do AlertManager.

    Returns:
        Lista de FormattedAlert (uma por alerta no payload). Lista vazia
        se payload inválido ou sem alertas.

    Notes:
        - NUNCA inclui dados brutos de annotations/description com PII.
        - NUNCA inclui labels não-canônicos (k8s_pod, container, etc que
          podem vazar metadata interna).
        - Auto-purge: o dict `payload` pode ser descartado pelo caller após
          chamada — não retemos referência.
    """
    if not isinstance(payload, dict):
        return []
    alerts = payload.get("alerts", [])
    if not isinstance(alerts, list) or not alerts:
        return []

    status_marker_alert = payload.get("status", "")
    results: list[FormattedAlert] = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        labels = alert.get("labels", {}) or {}
        annotations = alert.get("annotations", {}) or {}
        if not isinstance(labels, dict) or not isinstance(annotations, dict):
            continue

        alertname = _safe_label(labels.get("alertname", "UnknownAlert"))
        severity = str(labels.get("severity", "warning")).lower()
        instance = _safe_label(labels.get("instance", ""))
        squad = _safe_label(labels.get("squad", "cartorio-sre"))
        status = str(alert.get("status", status_marker_alert or "firing")).lower()

        severity_emoji, severity_tag = SEVERITY_MARKERS.get(
            severity, SEVERITY_MARKERS["warning"]
        )
        status_marker = STATUS_MARKERS.get(status, "❓ UNKNOWN")

        summary, summary_redactions = _scrub_pii(
            str(annotations.get("summary", ""))
        )
        description, description_redactions = _scrub_pii(
            str(annotations.get("description", ""))
        )

        # LGPD audit: lista de redactions que OCORRERAM (para log interno)
        all_redactions = summary_redactions + description_redactions

        lines = [
            f"{severity_emoji} <b>{severity_tag} {alertname}</b>",
            f"<b>Status:</b> {status_marker}",
            f"<b>Squad:</b> {squad}",
            f"<b>Instance:</b> <code>{instance}</code>",
        ]
        if summary:
            lines.append(f"\n<b>Summary:</b> {summary[:300]}")
        if description:
            lines.append(f"<b>Details:</b> {description[:400]}")
        if all_redactions:
            lines.append(
                f"\n<i>LGPD: {', '.join(all_redactions)} redactado(s) por segurança</i>"
            )

        # Runbook URL é metadata técnica, mas scrub mesmo assim (não vazar URLs internas)
        runbook_url = annotations.get("runbook_url") or annotations.get("runbook")
        if runbook_url:
            clean_runbook, _ = _scrub_pii(str(runbook_url))
            lines.append(f"<b>Runbook:</b> {clean_runbook[:200]}")

        text = "\n".join(lines)

        results.append(
            FormattedAlert(
                fingerprint=_fingerprint(alert),
                text=text,
                severity=severity,
                alertname=alertname,
                instance=instance,
                status=status,
                squad=squad,
            )
        )
    return results


# --- Telegram sender ---

def send_telegram(
    message: str,
    token: str,
    chat_id: str,
    *,
    timeout: float = 10.0,
) -> tuple[bool, str]:
    """Envia mensagem ao Telegram via Bot API.

    Returns:
        (success: bool, response_or_error: str)

    Raises:
        Não levanta exceção — Telegram API errors viram (False, error_msg).
    """
    import urllib.parse
    import urllib.request

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status == 200, body
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def send_telegram_async(messages: list[FormattedAlert], token: str, chat_id: str) -> list[tuple[bool, str]]:
    """Envia várias mensagens em sequência (sync).

    Async nativo do script seria overkill — Telegram Bot API é HTTP síncrono.
    Caller FastAPI deve usar BackgroundTasks pra não bloquear webhook.
    """
    results: list[tuple[bool, str]] = []
    for msg in messages:
        ok, response = send_telegram(msg.text, token, chat_id)
        results.append((ok, response))
    return results


# --- Dedup store (in-memory, defesa em profundidade) ---

class DedupCache:
    """Dedup de alertas em janela curta.

    Defesa em profundidade: mesmo com group_interval do AlertManager, evita
    reenvio se o mesmo `fingerprint` aparece em < `window_seconds` (default 60s).
    """

    def __init__(self, window_seconds: int = 60) -> None:
        self._window = window_seconds
        self._seen: dict[str, float] = {}

    def should_send(self, fingerprint: str) -> bool:
        now = time.monotonic()
        last = self._seen.get(fingerprint)
        if last is not None and (now - last) < self._window:
            return False
        self._seen[fingerprint] = now
        # Garbage collect fingerprints velhos
        if len(self._seen) > 1000:
            cutoff = now - self._window
            self._seen = {k: v for k, v in self._seen.items() if v >= cutoff}
        return True


# --- CLI ---

def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input and args.input != "-":
        path = Path(args.input)
        if not path.exists():
            raise SystemExit(f"[alert_to_telegram] Input file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    # stdin
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("[alert_to_telegram] Empty stdin")
    return json.loads(raw)


def _load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="AlertManager → Telegram (LGPD-safe)")
    parser.add_argument("--input", "-i", default="-", help="Payload JSON file (default stdin)")
    parser.add_argument("--apply", action="store_true", help="Envia Telegram real (default dry-run)")
    parser.add_argument(
        "--env-file",
        default=str(PROJECT_ROOT / ".secrets" / "telegram.env"),
        help="Path to telegram env file",
    )
    parser.add_argument(
        "--dedup-window",
        type=int,
        default=60,
        help="Janela de dedup em segundos (default 60)",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Desativa dedup local (NÃO recomendado)",
    )
    args = parser.parse_args()

    try:
        payload = _load_payload(args)
    except json.JSONDecodeError as exc:
        print(f"[alert_to_telegram] Invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    formatted = format_alert(payload)
    if not formatted:
        print("[alert_to_telegram] No alerts in payload (or invalid). Nothing to send.")
        return 0

    # LGPD: auto-purge do payload bruto. NÃO mantemos referência.
    payload = {}  # type: ignore[assignment]

    # Dedup
    dedup = DedupCache(window_seconds=args.dedup_window) if not args.no_dedup else None
    to_send: list[FormattedAlert] = []
    for msg in formatted:
        if dedup is None or dedup.should_send(msg.fingerprint):
            to_send.append(msg)

    if dedup is not None:
        suppressed = len(formatted) - len(to_send)
        if suppressed:
            print(
                f"[alert_to_telegram] Dedup suppressed {suppressed}/{len(formatted)} alert(s).",
                file=sys.stderr,
            )

    if not to_send:
        print("[alert_to_telegram] All alerts deduped. Nothing to send.")
        return 0

    print(f"[alert_to_telegram] {len(to_send)} alert(s) ready:")
    for msg in to_send:
        print(f"  → {msg.severity.upper():8s} {msg.alertname:30s} "
              f"status={msg.status:8s} fp={msg.fingerprint}")
        print("---")
        print(msg.text)
        print("---")

    if not args.apply:
        print("\n[alert_to_telegram] DRY-RUN (default). Use --apply to send.")
        print("[alert_to_telegram] LGPD-safe verified: payload purged, only metadata sent.")
        return 0

    env = _load_env_file(Path(args.env_file))
    token = env.get("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(
            "[alert_to_telegram] ERROR: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID required.",
            file=sys.stderr,
        )
        return 3

    print(f"[alert_to_telegram] Sending {len(to_send)} message(s) to chat {chat_id}...")
    results = send_telegram_async(to_send, token, chat_id)
    failures = sum(1 for ok, _ in results if not ok)
    if failures:
        for ok, resp in results:
            if not ok:
                print(f"  ✗ {resp}", file=sys.stderr)
        return 4
    print(f"[alert_to_telegram] ✓ All {len(to_send)} message(s) sent successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
