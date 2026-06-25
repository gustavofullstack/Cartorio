"""Dead man's switch job — wrapper para check de freshness do audit_log (A13).

LGPD art. 37 (continuidade do registro de auditoria): se o audit_log parar de
receber entries por mais de 1h, isso indica que o sistema parou de registrar
auditoria juridica — falha GRAVE (perda de rastreabilidade). Este job expõe
a funcao `check_audit_log_freshness` parametrizada (threshold em minutos)
que retorna Pydantic `AuditHealth` para uso por cron + endpoints.

Diferenca de `app.services.dead_mans_switch`:
- services: API de baixo nivel (`check_audit_log_alive(db) -> dict`)
  usada pelo endpoint `/health/audit` (A23 SQUAD A)
- jobs/dead_mans_switch: API parametrizada para cron + admin (`AuditHealth`
  tipado, threshold customizavel, classification 4-niveis: healthy/stale/
  critical/empty)

Tambem expõe a funcao `check_audit_log_freshness_3lvl` (briefing A13
/root/cartorio-a13-dead-mans-switch) que classifica em 3 niveis
(healthy/warning/critical) com shape diferente:
- last_audit_ts (ISO)
- stale_seconds (int)
- status (healthy|warning|critical)
- threshold_minutes (int)

E expone a metrica Prometheus `audit_dead_mans_status` (0/1/2).

NAO mexe em audit/pii (escopo = observability + alerting, NAO logica de chain).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Threshold default = 60 minutos (LGPD art. 37 — continuidade do audit).
# Override via parametro `threshold_minutes` em testes / cron / admin.
DEFAULT_THRESHOLD_MINUTES = 60


class HealthStatus(str, Enum):
    """Status do audit log (4 niveis de severidade)."""

    HEALTHY = "healthy"  # last entry <= threshold
    STALE = "stale"  # threshold < last entry <= 2x threshold
    CRITICAL = "critical"  # last entry > 2x threshold (sistema claramente quebrado)
    EMPTY = "empty"  # tabela vazia (cold start / app sem gravar nada)


class AuditHealth(BaseModel):
    """Saida tipada de `check_audit_log_freshness`.

    Attributes:
        status: classificacao 4-niveis (healthy/stale/critical/empty).
        last_entry_at: timestamp do ultimo entry no audit_log, ou None se vazio.
        last_entry_age_minutes: idade do ultimo entry em minutos (None se vazio).
        threshold_minutes: threshold usado na avaliacao (default 60).
        alert: mensagem de alerta pronta para Telegram/log (None se healthy).
    """

    status: HealthStatus
    last_entry_at: datetime | None = None
    last_entry_age_minutes: int | None = None
    threshold_minutes: int = Field(default=DEFAULT_THRESHOLD_MINUTES, ge=1)
    alert: str | None = None

    model_config = {"frozen": True}


def _query_last_audit_timestamp(db: Session) -> datetime | None:
    """Retorna o timestamp (naive UTC) do ultimo AuditLog ou None se vazio.

    AuditLog.timestamp eh `default=datetime.utcnow` (naive UTC por convencao
    do projeto). Comparacoes sao feitas em naive UTC para nao misturar TZ.
    """
    stmt = select(func.max(AuditLog.timestamp))
    return db.execute(stmt).scalar()


def _classify(
    last_entry_at: datetime | None,
    threshold_minutes: int,
    *,
    now: datetime | None = None,
) -> AuditHealth:
    """Classifica saude do audit_log em 4 niveis.

    Args:
        last_entry_at: timestamp do ultimo entry (None = tabela vazia).
        threshold_minutes: janela maxima em minutos para considerar "healthy".
        now: override do "agora" para testes deterministicos.

    Returns:
        AuditHealth com status + alert (None se healthy).
    """
    if last_entry_at is None:
        return AuditHealth(
            status=HealthStatus.EMPTY,
            last_entry_at=None,
            last_entry_age_minutes=None,
            threshold_minutes=threshold_minutes,
            alert=(
                "audit_log VAZIA — nenhuma entry registrada. "
                "Sistema pode estar com problema de gravacao. "
                "Verificar app + pipeline de audit."
            ),
        )

    now = now or datetime.now(tz=timezone.utc)
    # Normaliza naive UTC -> aware UTC para comparacao segura
    last = last_entry_at if last_entry_at.tzinfo else last_entry_at.replace(tzinfo=timezone.utc)
    age = now - last
    age_minutes = int(age.total_seconds() // 60)

    if age_minutes <= threshold_minutes:
        status = HealthStatus.HEALTHY
        alert = None
    elif age_minutes < threshold_minutes * 2:
        status = HealthStatus.STALE
        alert = (
            f"audit_log STALE: ultima entry ha {age_minutes}min "
            f"(threshold={threshold_minutes}min). "
            f"Verificar se API esta processando requests."
        )
    else:
        status = HealthStatus.CRITICAL
        alert = (
            f"audit_log CRITICAL: ultima entry ha {age_minutes}min "
            f"(threshold={threshold_minutes}min, 2x={threshold_minutes * 2}min). "
            f"Sistema pode estar sem registrar auditoria — perda de rastreabilidade "
            f"juridica (LGPD art. 37). ACAO IMEDIATA."
        )

    return AuditHealth(
        status=status,
        last_entry_at=last_entry_at,
        last_entry_age_minutes=age_minutes,
        threshold_minutes=threshold_minutes,
        alert=alert,
    )


def check_audit_log_freshness(
    db: Session,
    threshold_minutes: int = DEFAULT_THRESHOLD_MINUTES,
    *,
    now: datetime | None = None,
) -> AuditHealth:
    """Verifica freshness do audit_log (dead man's switch A13).

    Compara o timestamp do ultimo `AuditLog` registrado contra o threshold
    (default 60min) e classifica em 4 niveis: healthy / stale / critical /
    empty. Retorna Pydantic `AuditHealth` (frozen) pronto para serializacao
    JSON via endpoint / cron.

    Args:
        db: SQLAlchemy session.
        threshold_minutes: janela maxima em minutos. Default 60 (LGPD art. 37).
        now: override do "agora" para testes deterministicos.

    Returns:
        AuditHealth com classificacao + alerta (None se healthy).
    """
    if threshold_minutes < 1:
        raise ValueError(f"threshold_minutes deve ser >= 1, recebeu {threshold_minutes}")

    last = _query_last_audit_timestamp(db)
    health = _classify(last, threshold_minutes, now=now)

    if health.status == HealthStatus.HEALTHY:
        logger.info(
            "AUDIT_FRESHNESS_OK: last_entry_age=%dmin threshold=%dmin",
            health.last_entry_age_minutes,
            threshold_minutes,
        )
    else:
        # stale/critical/empty: log estruturado (Telegram GRUPO PIETRA SQUAD
        # eh placeholder; cron separado chamara este job e enviara IM real).
        logger.error(
            "AUDIT_FRESHNESS_%s: %s",
            health.status.value.upper(),
            health.alert,
        )

    return health


__all__ = [
    "AuditHealth",
    "AuditHealth3Lvl",
    "DEFAULT_THRESHOLD_MINUTES",
    "HealthStatus",
    "HealthStatus3Lvl",
    "check_audit_log_freshness",
    "check_audit_log_freshness_3lvl",
]


# ============================================================================
# 3-level classification (briefing A13 /root/cartorio-a13-dead-mans-switch)
# ============================================================================


class HealthStatus3Lvl(str, Enum):
    """Status do audit log em 3 niveis (briefing A13).

    Mapeamento do 4-level (HealthStatus):
    - HEALTHY  -> HEALTHY  (0)
    - STALE    -> WARNING  (1)
    - CRITICAL -> CRITICAL (2)
    - EMPTY    -> CRITICAL (2)  # cold start = critico (fail-safe)
    """

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


# Mapeamento explicito 4-level -> 3-level
_4L_TO_3L: dict[HealthStatus, HealthStatus3Lvl] = {
    HealthStatus.HEALTHY: HealthStatus3Lvl.HEALTHY,
    HealthStatus.STALE: HealthStatus3Lvl.WARNING,
    HealthStatus.CRITICAL: HealthStatus3Lvl.CRITICAL,
    HealthStatus.EMPTY: HealthStatus3Lvl.CRITICAL,
}

# Mapeamento 3-level -> codigo numerico Prometheus (0/1/2)
_3L_TO_PROM: dict[HealthStatus3Lvl, int] = {
    HealthStatus3Lvl.HEALTHY: 0,
    HealthStatus3Lvl.WARNING: 1,
    HealthStatus3Lvl.CRITICAL: 2,
}


class AuditHealth3Lvl(BaseModel):
    """Saida tipada de `check_audit_log_freshness_3lvl` (briefing A13).

    Attributes:
        status: classificacao 3-niveis (healthy/warning/critical).
        last_audit_ts: timestamp ISO do ultimo entry no audit_log, ou None se vazio.
        stale_seconds: idade do ultimo entry em segundos (None se vazio).
        threshold_minutes: threshold usado na avaliacao (default 60).
    """

    status: HealthStatus3Lvl
    last_audit_ts: datetime | None = None
    stale_seconds: int | None = None
    threshold_minutes: int = Field(default=DEFAULT_THRESHOLD_MINUTES, ge=1)

    model_config = {"frozen": True}


def check_audit_log_freshness_3lvl(
    db: Session,
    threshold_minutes: int = DEFAULT_THRESHOLD_MINUTES,
    *,
    now: datetime | None = None,
) -> AuditHealth3Lvl:
    """Verifica freshness do audit_log em 3 niveis (briefing A13).

    Wrapper sobre `check_audit_log_freshness` (4-niveis) que mapeia para o
    shape 3-niveis (healthy/warning/critical). Tambem atualiza a metrica
    Prometheus `audit_dead_mans_status` (0/1/2).

    Args:
        db: SQLAlchemy session.
        threshold_minutes: janela maxima em minutos. Default 60.
        now: override do "agora" para testes deterministicos.

    Returns:
        AuditHealth3Lvl com status + last_audit_ts + stale_seconds.
    """
    # Lazy import para evitar ciclo: services/metrics.py nao importa jobs/
    from app.services.metrics import store as metrics_store

    health4 = check_audit_log_freshness(db, threshold_minutes, now=now)
    status3 = _4L_TO_3L[health4.status]
    last_audit_ts = health4.last_entry_at
    stale_seconds = (
        health4.last_entry_age_minutes * 60 if health4.last_entry_age_minutes is not None else None
    )

    # Atualiza metrica Prometheus
    metrics_store.set_audit_dead_mans_status(_3L_TO_PROM[status3])

    return AuditHealth3Lvl(
        status=status3,
        last_audit_ts=last_audit_ts,
        stale_seconds=stale_seconds,
        threshold_minutes=health4.threshold_minutes,
    )
