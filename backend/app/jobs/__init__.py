"""Jobs agendados (cron / scheduler externo) do Cartorio.

Cada modulo aqui expoe uma funcao `run_*` que serve como entry point
para scheduler externo (N8N Cron / k8s CronJob / systemd timer). Jobs NAO
devem assumir contexto de request HTTP — recebem `db: Session` direto.

Convencoes:
- Funcao retorna dataclass (frozen) com resultado + contadores.
- Erros em 1 item NAO derrubam o job inteiro (best-effort + log).
- NAO gravam audit log internamente (chamador eh quem sabe o canal/request_id).
"""

from __future__ import annotations

from app.jobs.cron_dead_mans_switch import CronRunResult, run_dead_mans_switch_check
from app.jobs.dead_mans_switch import (
    DEFAULT_THRESHOLD_MINUTES,
    AuditHealth,
    HealthStatus,
    check_audit_log_freshness,
)
from app.jobs.retencao import RetencaoConfig, RetencaoResult, run_retencao

__all__ = [
    # A13 — dead man's switch audit_log
    "AuditHealth",
    "CronRunResult",
    "DEFAULT_THRESHOLD_MINUTES",
    "HealthStatus",
    "check_audit_log_freshness",
    "run_dead_mans_switch_check",
    # Retencao
    "RetencaoConfig",
    "RetencaoResult",
    "run_retencao",
]
