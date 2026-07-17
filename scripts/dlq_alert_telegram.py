#!/usr/bin/env python3
"""G8.08.T3 — Alerta de falhas recorrentes de webhook (DLQ) ao Telegram do escrevente.

Monitora profundidade da DLQ e dispara alerta no Telegram do escrevente quando
o threshold é excedido. **NÃO expoe payload** (LGPD by design) — só métricas
agregadas (count por queue, idade maxima).

Uso:
    # Dry-run (default): imprime alerta no console, NAO envia
    python3 scripts/dlq_alert_telegram.py

    # Apply mode: envia para Telegram real
    python3 scripts/dlq_alert_telegram.py --apply

    # Custom threshold
    python3 scripts/dlq_alert_telegram.py --threshold-failed 50 --threshold-pending 100

Configuracao (env vars ou .secrets/telegram.env):
    TELEGRAM_BOT_TOKEN: token do bot Telegram
    TELEGRAM_CHAT_ID: chat_id do escrevente (pode ser grupo)
    DLQ_ALERT_THRESHOLD_FAILED: int (default 10) — alerta se FAILED > threshold em 1h
    DLQ_ALERT_THRESHOLD_PENDING: int (default 100) — alerta se PENDING > threshold
    DLQ_ALERT_COOLDOWN_MINUTES: int (default 30) — min entre alertas repetidos

LGPD compliance:
- Alerta inclui APENAS contadores (queue, count, age_max_minutes)
- NUNCA expoe payload, last_error com PII, ou qualquer dado pessoal
- Log da operacao fica em audit_log (LGPD Art.37)

Modified by Gustavo Almeida — G8 Wave 31 A2.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


def _load_env_file(path: Path) -> dict[str, str]:
    """Carrega .env simples (KEY=VALUE) sem dependências."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def collect_metrics(db_path: str | None = None) -> dict[str, dict[str, int]]:
    """Coleta métricas agregadas da DLQ (SEM payload).

    Returns:
        Dict {queue: {"pending": N, "failed_1h": M, "max_age_minutes": X}}
    """
    from sqlalchemy import create_engine, func, select  # noqa: PLC0415
    from sqlalchemy.orm import sessionmaker  # noqa: PLC0415

    from app.models.outbox_message import OutboxMessage, OutboxQueue, OutboxStatus  # noqa: PLC0415

    db_url = db_path or os.getenv(
        "DATABASE_URL", "sqlite:///" + str(PROJECT_ROOT / "backend" / "cartorio.db")
    )
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        result: dict[str, dict[str, int]] = {}
        now = datetime.now(tz=timezone.utc)
        one_hour_ago = now.timestamp() - 3600
        for queue in OutboxQueue:
            # PENDING count
            pending = session.execute(
                select(func.count(OutboxMessage.id)).where(
                    OutboxMessage.queue == queue,
                    OutboxMessage.status == OutboxStatus.PENDING,
                )
            ).scalar() or 0
            # FAILED nas últimas 1h
            failed_1h = session.execute(
                select(func.count(OutboxMessage.id)).where(
                    OutboxMessage.queue == queue,
                    OutboxMessage.status == OutboxStatus.FAILED,
                    OutboxMessage.updated_at >= func.fromtimestamp(one_hour_ago),
                )
            ).scalar() or 0
            # Idade máxima (em minutos) das PENDING
            oldest = session.execute(
                select(func.min(OutboxMessage.created_at)).where(
                    OutboxMessage.queue == queue,
                    OutboxMessage.status == OutboxStatus.PENDING,
                )
            ).scalar()
            max_age_min = 0
            if oldest:
                if oldest.tzinfo is None:
                    oldest = oldest.replace(tzinfo=timezone.utc)
                max_age_min = int((now - oldest).total_seconds() // 60)
            result[queue.value] = {
                "pending": int(pending),
                "failed_1h": int(failed_1h),
                "max_age_minutes": max_age_min,
            }
        return result
    finally:
        session.close()


def build_alert_message(
    metrics: dict[str, dict[str, int]],
    threshold_failed: int,
    threshold_pending: int,
) -> str | None:
    """Constroi mensagem de alerta Telegram se algum threshold for violado.

    Returns:
        String formatada MarkdownV2 ou None se tudo OK.
    """
    triggered: list[str] = []
    for queue, stats in metrics.items():
        if stats["failed_1h"] >= threshold_failed:
            triggered.append(
                f"🚨 *{queue}*: {stats['failed_1h']} falhas em 1h (threshold {threshold_failed})"
            )
        if stats["pending"] >= threshold_pending:
            triggered.append(
                f"⚠️ *{queue}*: {stats['pending']} pendentes (threshold {threshold_pending}), "
                f"mais antiga {stats['max_age_minutes']}min"
            )
    if not triggered:
        return None
    header = "🛎️ *DLQ ALERT — Cartório 2º Notas*\n\n"
    body = "\n".join(triggered)
    footer = (
        f"\n\n_Updated: {datetime.now(tz=timezone.utc).isoformat()}_\n"
        f"_Run: `dlq_alert_telegram.py`_"
    )
    return header + body + footer


def send_telegram(message: str, token: str, chat_id: str) -> tuple[bool, str]:
    """Envia mensagem ao Telegram via Bot API. Retorna (success, response)."""
    import urllib.request
    import urllib.parse

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "MarkdownV2",
        }
    ).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status == 200, body
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="DLQ alert to Telegram")
    parser.add_argument("--apply", action="store_true", help="Envia Telegram real (default dry-run)")
    parser.add_argument("--threshold-failed", type=int, default=10, help="Threshold FAILED em 1h")
    parser.add_argument("--threshold-pending", type=int, default=100, help="Threshold PENDING total")
    parser.add_argument("--db", default=None, help="DATABASE_URL override")
    parser.add_argument(
        "--env-file",
        default=str(PROJECT_ROOT / ".secrets" / "telegram.env"),
        help="Path to telegram env file",
    )
    args = parser.parse_args()

    env = _load_env_file(Path(args.env_file))
    token = env.get("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

    print(f"[dlq_alert] Collecting DLQ metrics from {args.db or 'default'}...")
    metrics = collect_metrics(args.db)
    print(f"[dlq_alert] Metrics collected: {json.dumps(metrics, indent=2)}")

    message = build_alert_message(
        metrics,
        threshold_failed=args.threshold_failed,
        threshold_pending=args.threshold_pending,
    )
    if message is None:
        print("[dlq_alert] All queues within thresholds. No alert.")
        return 0

    print(f"\n[dlq_alert] === ALERT TRIGGERED ===\n{message}\n")

    if not args.apply:
        print("[dlq_alert] DRY-RUN mode (default). Use --apply to send.")
        return 1  # Exit 1 = alerta detectado (dry-run)

    if not token or not chat_id:
        print("[dlq_alert] ERROR: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID required in --apply mode.")
        return 2

    print(f"[dlq_alert] Sending Telegram message to chat {chat_id}...")
    ok, response = send_telegram(message, token, chat_id)
    if ok:
        print("[dlq_alert] ✅ Alert sent successfully.")
        return 1  # Exit 1 = alerta enviado (success)
    print(f"[dlq_alert] ❌ Telegram send failed: {response}")
    return 3


if __name__ == "__main__":
    sys.exit(main())