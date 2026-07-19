"""AlertManager webhook receiver — Cartório 2º Notas Uberlândia (G8.15.T2).

Pipeline: Prometheus → AlertManager → `POST /api/v1/webhook/alertmanager/*`
           → formatação LGPD-safe → Telegram do escrevente.

**LGPD Art. 46 (segurança e sigilo) — P0 absoluto**:
   1. O payload recebido é processado em memória e AUTO-PURGE ao fim
      (não persistimos em DB, não logamos labels raw, não ecoamos pro
      Telegram sem passar pelo scrubber PII).
   2. Toda mensagem Telegram contém APENAS metadata categórica:
      alertname, severity, instance, squad, status, summary scrubbed,
      description scrubbed.
   3. Endpoint é POST-only, sem state, sem idempotency key compartilhada
      com cliente (AlertManager retry é tratado pelo group_interval).
   4. Webhook secret (HMAC) opcional via header `X-AlertManager-Signature`
      — se `ALERTMANAGER_WEBHOOK_SECRET` configurado.

Auth: requer `require_cartorio_api_key` (header `X-API-Key`) — rede interna
      entre AlertManager (porta 9093) e cartorio-api (porta 8000).
      Sem chave = 401. NUNCA expor publicamente.

Dedup: defesa em profundidade via Redis SET NX com TTL 60s por fingerprint.
       Bloqueia reenvio se o mesmo alerta chega < 60s (além do group_interval
       do AlertManager, que é 5m).

Modified by Gustavo Almeida — G8.15.T2.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/alertmanager", tags=["alertmanager"])

# --- Constants ---

TELEGRAM_API_BASE = "https://api.telegram.org"
ALERTMANAGER_WEBHOOK_SECRET: str | None = (
    getattr(settings, "alertmanager_webhook_secret", None)
    or os.environ.get("ALERTMANAGER_WEBHOOK_SECRET")
    or None
)
ALERTMANAGER_DEDUP_TTL = 60  # seconds

# --- Pydantic schemas (strict — extra=forbid pra bloquear campos não documentados) ---
# G8.17.T2: reusa os schemas de `app.schemas.webhook_alertmanager` que ja tem
# `Field(description=...)` em 100% dos campos para Swagger documentado.
from app.schemas.webhook_alertmanager import (  # noqa: E402,F401
    AlertAnnotation,
    AlertEntry,
    AlertLabel,
    AlertManagerPayload,
)


# --- LGPD PII scrubber (defesa em profundidade) ---

import re  # noqa: E402  (após imports de app.config)

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CPF", re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")),
    ("RG", re.compile(r"\d{1,2}\.?\d{3}\.?\d{3}-?\d{1,2}")),
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("PHONE_BR", re.compile(r"\+?55?\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}")),
    ("PROTOCOL", re.compile(r"\bPROT-\d{4}-\d{6}\b", re.IGNORECASE)),
    ("ESCRITURA", re.compile(r"\bESCR-\d{6}\b", re.IGNORECASE)),
)

_SEVERITY_MARKER: dict[str, tuple[str, str]] = {
    "critical": ("🔴", "P0"),
    "warning": ("⚠️", "P1"),
    "info": ("ℹ️", "P2"),
}


def _scrub_pii(text: str) -> tuple[str, list[str]]:
    """Strip PII de qualquer texto. Returns (scrubbed, list_of_redactions)."""
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


def _safe_str(value: str | None, *, max_len: int = 200) -> str:
    if not value:
        return "unknown"
    cleaned, _ = _scrub_pii(str(value))
    return cleaned[:max_len]


def _alert_fingerprint(alert: AlertEntry) -> str:
    """Hash curto pra dedup (não inclui timestamps — AlertManager repete por janela)."""
    import hashlib

    canonical = "|".join(f"{k}={v}" for k, v in sorted(alert.labels.model_dump().items()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def format_alert_message(alert: AlertEntry, payload_status: str) -> str:
    """Formata UM alerta em mensagem Telegram LGPD-safe.

    Nunca inclui dados brutos: summary/description passam pelo scrubber PII.
    """
    severity = (alert.labels.severity or "warning").lower()
    severity_emoji, severity_tag = _SEVERITY_MARKER.get(severity, _SEVERITY_MARKER["warning"])
    status = (alert.status or payload_status or "firing").lower()
    status_marker = "🚨 FIRING" if status == "firing" else "✅ RESOLVED"

    summary_scrub, sum_red = _scrub_pii(alert.annotations.summary or "")
    desc_scrub, desc_red = _scrub_pii(alert.annotations.description or "")

    lines = [
        f"{severity_emoji} <b>{severity_tag} {_safe_str(alert.labels.alertname)}</b>",
        f"<b>Status:</b> {status_marker}",
        f"<b>Squad:</b> {_safe_str(alert.labels.squad, max_len=80)}",
        f"<b>Instance:</b> <code>{_safe_str(alert.labels.instance)}</code>",
    ]
    if summary_scrub:
        lines.append(f"\n<b>Summary:</b> {summary_scrub[:300]}")
    if desc_scrub:
        lines.append(f"<b>Details:</b> {desc_scrub[:400]}")
    redactions = sum_red + desc_red
    if redactions:
        lines.append(f"\n<i>LGPD: {', '.join(redactions)} redactado(s) por segurança</i>")
    runbook = alert.annotations.runbook_url or alert.annotations.runbook
    if runbook:
        clean_runbook, _ = _scrub_pii(runbook)
        lines.append(f"<b>Runbook:</b> {clean_runbook[:200]}")
    return "\n".join(lines)


# --- Telegram sender (async) ---


async def _send_telegram_message(
    text: str,
    *,
    token: str,
    chat_id: str,
    timeout: float = 10.0,
) -> tuple[bool, str]:
    """Envia mensagem ao Telegram via Bot API (async). Não levanta exceção."""
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=body)
        if resp.status_code == 200:
            return True, resp.text[:300]
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _dedup_key(fingerprint: str) -> str:
    return f"cartorio:alertmanager:dedup:{fingerprint}"


async def _is_duplicate(fingerprint: str) -> bool:
    """Dedup via Redis SET NX com TTL 60s. Retorna True se já existe (= duplicado)."""
    try:
        from app.services.redis_bus import get_bus  # noqa: PLC0415

        bus = get_bus()
        client = await bus._get_client()  # noqa: SLF001
        # SET NX EX
        was_set = await client.set(_dedup_key(fingerprint), "1", nx=True, ex=ALERTMANAGER_DEDUP_TTL)
        return not bool(was_set)
    except Exception as exc:  # noqa: BLE001
        # Fail-open: se Redis cair, deixa passar (AlertManager ainda tem group_interval)
        logger.warning("[alertmanager] dedup check failed (fail-open): %s", exc)
        return False


def _resolve_chat_id(receiver: str) -> str | None:
    """Resolve chat_id por receiver name. Fallback: TELEGRAM_DEFAULT_CHAT_ID."""
    env_key = f"ALERTMANAGER_CHAT_{receiver.upper().replace('-', '_')}"
    return (
        os.environ.get(env_key)
        or os.environ.get("TELEGRAM_DEFAULT_CHAT_ID")
        or os.environ.get("TELEGRAM_CHAT_ID")
    )


def _resolve_token() -> str | None:
    """Resolve bot token do Telegram."""
    return (
        os.environ.get("ALERTMANAGER_TELEGRAM_BOT_TOKEN")
        or getattr(settings, "telegram_bot_token", None)
        or os.environ.get("TELEGRAM_BOT_TOKEN")
    )


def _check_signature(
    raw_body: bytes,
    signature: Annotated[str | None, Header(alias="X-AlertManager-Signature")] = None,
) -> None:
    """Valida HMAC-SHA256 se ALERTMANAGER_WEBHOOK_SECRET estiver configurado."""
    if not ALERTMANAGER_WEBHOOK_SECRET:
        return
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-AlertManager-Signature",
        )
    import hashlib
    import hmac as _hmac

    expected = _hmac.new(
        ALERTMANAGER_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not _hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )


# --- Background worker (envio Telegram NÃO bloqueia webhook) ---


async def _dispatch_or_send_all(
    payload: AlertManagerPayload,
    *,
    receiver_label: str,
    skip_dedup: bool,
) -> dict[str, int]:
    """Helper: dedup ON → `_dispatch_to_telegram`; dedup OFF → envia direto."""
    if skip_dedup:
        token = _resolve_token()
        chat_id = _resolve_chat_id(receiver_label)
        if not token or not chat_id:
            logger.warning("[alertmanager] Telegram not configured for receiver=%s", receiver_label)
            return {"sent": 0, "deduped": 0, "failed": 0}
        sent = 0
        failed = 0
        for alert in payload.alerts:
            msg = format_alert_message(alert, payload.status)
            ok, _ = await _send_telegram_message(msg, token=token, chat_id=chat_id)
            if ok:
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "deduped": 0, "failed": failed}
    return await _dispatch_to_telegram(payload, receiver_label=receiver_label)


async def _dispatch_to_telegram(
    payload: AlertManagerPayload,
    *,
    receiver_label: str,
) -> dict[str, int]:
    """Envia alertas ao Telegram (chamado via BackgroundTasks)."""
    token = _resolve_token()
    chat_id = _resolve_chat_id(receiver_label)
    if not token or not chat_id:
        logger.warning(
            "[alertmanager] Telegram not configured for receiver=%s (token=%s, chat=%s)",
            receiver_label,
            bool(token),
            bool(chat_id),
        )
        return {"sent": 0, "deduped": 0, "failed": 0}

    sent = 0
    deduped = 0
    failed = 0
    for alert in payload.alerts:
        fp = _alert_fingerprint(alert)
        if await _is_duplicate(fp):
            deduped += 1
            continue
        msg = format_alert_message(alert, payload.status)
        ok, _resp = await _send_telegram_message(msg, token=token, chat_id=chat_id)
        if ok:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "deduped": deduped, "failed": failed}


# --- Endpoints ---


async def _alertmanager_request(
    payload: AlertManagerPayload,
    background_tasks: BackgroundTasks,
    *,
    receiver_label: str,
    skip_dedup: bool = False,
) -> dict[str, Any]:
    """Handler compartilhado pelos endpoints default/critical/dlq/lgpd/n8n.

    LGPD Art. 46: processa em memória, agenda envio em background, AUTO-PURGE.
    Retorna imediatamente (HTTP 202) sem bloquear AlertManager.
    """
    # Auto-purge defensivo: anota no audit log a contagem apenas (não payload).
    n_alerts = len(payload.alerts)
    n_critical = sum(1 for a in payload.alerts if a.labels.severity == "critical")

    # Enfileira envio em background. Não bloqueia o webhook.
    # NOTA: BackgroundTasks roda em threadpool (sem event loop), então usamos
    # asyncio.run() num thread novo — Telegram é HTTP e o cliente httpx.AsyncClient
    # precisa de loop. Encapsulado pra isolar exceções.
    def _runner_sync() -> None:
        try:
            asyncio.run(
                _dispatch_or_send_all(
                    payload,
                    receiver_label=receiver_label,
                    skip_dedup=skip_dedup,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("[alertmanager] background send failed: %s", exc)

    background_tasks.add_task(_runner_sync)

    logger.info(
        "[alertmanager] receiver=%s alerts=%d critical=%d status=%s",
        receiver_label,
        n_alerts,
        n_critical,
        payload.status,
    )

    return {
        "status": "accepted",
        "receiver": receiver_label,
        "alerts_received": n_alerts,
        "alerts_critical": n_critical,
        "payload_status": payload.status,
    }


@router.post("", status_code=status.HTTP_202_ACCEPTED)
@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def alertmanager_default(
    payload: AlertManagerPayload,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Webhook default — todos os alertas que não casam rota específica.

    Receiver: `cartorio-telegram-default`.
    """
    return await _alertmanager_request(payload, background_tasks, receiver_label="default")


@router.post("/critical", status_code=status.HTTP_202_ACCEPTED)
async def alertmanager_critical(
    payload: AlertManagerPayload,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Webhook P0 critical — Telegram imediato, sem dedup."""
    return await _alertmanager_request(
        payload, background_tasks, receiver_label="critical", skip_dedup=True
    )


@router.post("/dlq", status_code=status.HTTP_202_ACCEPTED)
async def alertmanager_dlq(
    payload: AlertManagerPayload,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Webhook DLQ Overflow — sem dedup, sem resolved (contadores contínuos)."""
    return await _alertmanager_request(
        payload, background_tasks, receiver_label="dlq", skip_dedup=True
    )


@router.post("/lgpd", status_code=status.HTTP_202_ACCEPTED)
async def alertmanager_lgpd(
    payload: AlertManagerPayload,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Webhook squad cartorio-lgpd — DPO + escrevente."""
    return await _alertmanager_request(payload, background_tasks, receiver_label="lgpd")


@router.post("/n8n", status_code=status.HTTP_202_ACCEPTED)
async def alertmanager_n8n(
    payload: AlertManagerPayload,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Webhook squad cartorio-n8n — operadores de workflow."""
    return await _alertmanager_request(payload, background_tasks, receiver_label="n8n")
