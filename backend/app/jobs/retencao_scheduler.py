"""Scheduler in-process para job de retenção LGPD (Sprint 3 G4.3 + Sprint 4 D29-G3).

Roda `run_retencao()` automaticamente no horario configurado (default 03:00 BRT = 06:00 UTC).
Segue o mesmo padrao de `app.jobs.cron_dead_mans_switch.py` (3-level check).

Duas fases:
- Fase 1 (soft delete): anonimiza PII de clientes ATIVOS inativos (5y/2y).
- Fase 2 (hard delete / purge): remove definitivamente clientes JA soft-deleted
  por REVOGACAO_CONSENTIMENTO ou OUTROS apos 5y do deleted_at.
  EXERCICIO_DIREITO_TITULAR (correcoes art. 18 III) sao PRESERVADOS.

LGPD:
- Art. 16: dados pessoais podem ser eliminados apos cessada a finalidade.
- Art. 18 III: correcao de dados — NAO vai para purge automatico.
- Art. 18 VI: titular pode pedir eliminacao. Job automatiza soft+hard delete.
- Art. 37: toda execucao do job gera audit log com batch_id + per-client detail.

Configuracao (env vars):
- RETENCAO_ENABLED (default true)
- RETENCAO_HOUR_BRAZIL (default 3 = 03:00 BRT)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


# BRT = UTC-3 (sem DST em 2026 — Lei 11.622/2007 revogou horario de verao no NE/SE).
_BRAZIL_UTC_OFFSET_HOURS = 3


def _local_to_utc(hour_brazil: int, base_date_utc: datetime) -> datetime:
    """Calcula o datetime UTC correspondente a `hour_brazil` (00-23) de amanha.

    Args:
        hour_brazil: hora no fuso BRT (0-23).
        base_date_utc: datetime UTC de referencia.

    Returns:
        datetime UTC do proximo slot `hour_brazil` BRT >= base_date_utc.
    """
    # base_date_utc em UTC → converter para BRT
    brazil_now = base_date_utc.astimezone(timezone(timedelta(hours=-_BRAZIL_UTC_OFFSET_HOURS)))
    target_brazil = brazil_now.replace(hour=hour_brazil, minute=0, second=0, microsecond=0)
    # Se ja passou, avanca 1 dia
    if target_brazil <= brazil_now:
        target_brazil = target_brazil + timedelta(days=1)
    # Converter de volta para UTC
    return target_brazil.astimezone(timezone.utc)


def compute_next_run_utc(
    now: datetime,
    retencao_hour_brazil: int = 3,
) -> datetime:
    """Calcula o proximo datetime UTC em que `run_retencao` deve rodar.

    Args:
        now: datetime UTC de referencia.
        retencao_hour_brazil: hora alvo no fuso BRT (0-23, default 3 = 03:00 BRT).

    Returns:
        datetime UTC do proximo slot >= now.

    Examples:
        >>> # now=05:00 UTC (02:00 BRT 2026-06-29), hour=3 → next=06:00 UTC (03:00 BRT)
        >>> from datetime import datetime, timezone, timedelta
        >>> now = datetime(2026, 6, 29, 5, 0, tzinfo=timezone.utc)
        >>> compute_next_run_utc(now).hour
        6
    """
    if not (0 <= retencao_hour_brazil <= 23):
        raise ValueError(
            f"retencao_hour_brazil deve estar em [0, 23]; recebido={retencao_hour_brazil!r}"
        )
    return _local_to_utc(retencao_hour_brazil, now)


def should_run_retencao_now(
    now: datetime,
    retencao_enabled: bool,
    retencao_hour_brazil: int = 3,
) -> bool:
    """Decide se o scheduler deve rodar `run_retencao` AGORA.

    Regras:
    1. Se retencao_enabled=False → False.
    2. Compara now (em BRT) com retencao_hour_brazil:00:00 do MESMO DIA.
       Match exato de hora (minuto/segundo/microsegundo 0).
       Granularidade de 1 min suficiente pra scheduler que checa a cada 60s.

    Args:
        now: datetime UTC.
        retencao_enabled: settings.retencao_enabled.
        retencao_hour_brazil: hora alvo no fuso BRT.

    Returns:
        True se deve rodar agora; False caso contrario.

    Examples:
        >>> from datetime import datetime, timezone
        >>> # 06:00 UTC = 03:00 BRT → True
        >>> now = datetime(2026, 6, 29, 6, 0, tzinfo=timezone.utc)
        >>> should_run_retencao_now(now, True, 3)
        True
        >>> # 10:00 UTC = 07:00 BRT → False
        >>> now2 = datetime(2026, 6, 29, 10, 0, tzinfo=timezone.utc)
        >>> should_run_retencao_now(now2, True, 3)
        False
    """
    if not retencao_enabled:
        return False
    # Converter now para BRT
    brazil_now = now.astimezone(timezone(timedelta(hours=-_BRAZIL_UTC_OFFSET_HOURS)))
    return brazil_now.hour == retencao_hour_brazil and brazil_now.minute == 0


async def retencao_scheduler_loop(
    *,
    interval_seconds: int = 60,
    retencao_enabled: bool = True,
    retencao_hour_brazil: int = 3,
) -> None:
    """Loop in-process que executa `run_retencao()` no horario configurado.

    Roda para SEMPRE ate ser cancelado via task.cancel() (shutdown).
    Checagem a cada `interval_seconds` (default 60s) — comparacao simples
    contra `now` em BRT, custo desprezivel.

    Args:
        interval_seconds: intervalo entre checagens (default 60s).
        retencao_enabled: liga/desliga.
        retencao_hour_brazil: hora alvo BRT (default 3).

    Pattern: copia de `main.py:_dead_mans_switch_loop` (A13) — mesmo cancel-safe,
    best-effort, error-swallowing.
    """
    from sqlalchemy import text

    from app.db import session_scope
    from app.jobs.retencao import run_retencao
    from app.services.audit import AuditService

    last_run_date: str | None = None  # "YYYY-MM-DD" BRT para evitar rodar 2x/dia

    while True:
        try:
            now = datetime.now(timezone.utc)
            if not retencao_enabled:
                await asyncio.sleep(interval_seconds)
                continue

            # Determinar "hoje" em BRT (date string)
            brazil_today = (
                now.astimezone(timezone(timedelta(hours=-_BRAZIL_UTC_OFFSET_HOURS)))
                .date()
                .isoformat()
            )

            should_run = should_run_retencao_now(
                now=now,
                retencao_enabled=retencao_enabled,
                retencao_hour_brazil=retencao_hour_brazil,
            )

            # Idempotencia: 1 execucao por dia BRT
            if should_run and last_run_date != brazil_today:
                logger.info(
                    "RETENCAO_TICK_START: now_utc=%s brazil_today=%s",
                    now.isoformat(),
                    brazil_today,
                )
                with session_scope() as db:
                    # Smoke test DB
                    db.execute(text("SELECT 1"))
                    result = run_retencao(db)
                    # Audit log da execucao (LGPD art. 37)
                    # IDs internos mascarados para log externo: f"C{id:04d}"
                    audit_payload = {
                        "batch_id": result.batch_id,
                        "scanned": result.scanned,
                        "soft_deleted_5y": result.soft_deleted_5y,
                        "soft_deleted_inativo": result.soft_deleted_inativo,
                        "hard_deleted_ids": [f"C{id:04d}" for id in result.hard_deleted_ids],
                        "hard_deleted_count": len(result.hard_deleted_ids),
                        "skipped_exercicio_direito": result.skipped_exercicio_direito,
                        "errors_count": len(result.errors),
                        "duration_ms": result.duration_ms,
                        "trigger": "scheduler",
                        "brazil_today": brazil_today,
                        "cutoff_5y": (result.cutoff_5y.isoformat() if result.cutoff_5y else None),
                    }
                    AuditService.log_system_action(
                        action="retencao.run.scheduled",
                        payload=audit_payload,
                    )
                last_run_date = brazil_today
                logger.info(
                    "RETENCAO_TICK_END: batch=%s scanned=%s d5y=%s d_inativo=%s hard_deleted=%s skipped_exercicio=%s errors=%s",
                    result.batch_id[:8],
                    result.scanned,
                    len(result.soft_deleted_5y),
                    len(result.soft_deleted_inativo),
                    len(result.hard_deleted_ids),
                    result.skipped_exercicio_direito,
                    len(result.errors),
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — best-effort
            logger.error(
                "RETENCAO_LOOP_ERROR type=%s msg=%s",
                type(exc).__name__,
                str(exc)[:200],
                exc_info=True,
            )
        await asyncio.sleep(interval_seconds)


__all__ = [
    "compute_next_run_utc",
    "should_run_retencao_now",
    "retencao_scheduler_loop",
]
