"""Service backup_v2 — health check do backup pg_basebackup 4x/dia (A14).

Diferencas de `/health/backup` (existente, v0.4.0):
- backup (v1): checa `.tar.gz` no diretorio raiz /var/backups/cartorio (cron diario
  as 03:00 — freq. 1/dia, threshold 26h).
- backup-v2 (A14): checa diretorios timestamped `YYYYMMDD_HH/.complete` em
  /var/backups/cartorio/pgbase (cron 0 */6 — freq. 4/dia, threshold 6h = 360min).

Classificacao 4-niveis:
- healthy: ultimo backup completo com idade <= 360 min (6h, = cron freq)
- stale: 360 < idade <= 720 min (6h-12h, alerta amarelo)
- critical: idade > 720 min (12h+, alerta vermelho, RPO estourado)
- empty: nenhum backup com marker .complete (cron nunca rodou OK)

LGPD: este service NAO expoe dados de cliente — apenas timestamps + paths.
Resposta JSON do endpoint /health/backup-v2 inclui apenas metadados de saude.

v1.0.0 (2026-06-25): A14 — backup DB 4x/dia pg_basebackup + WAL.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Diretorio default dos backups pg_basebackup.
# Pode ser sobrescrito via parametro `backup_dir` (usado em testes).
DEFAULT_BACKUP_DIR = "/var/backups/cartorio/pgbase"

# Threshold default (cron roda 4x/dia = cada 6h). 360 min = janela esperada.
DEFAULT_HEALTHY_THRESHOLD_MINUTES = 360

# 2x threshold = 720 min. A partir daqui, CRITICAL.
DEFAULT_CRITICAL_THRESHOLD_MINUTES = DEFAULT_HEALTHY_THRESHOLD_MINUTES * 2

# Marker file que o script pg_basebackup_4x.sh cria quando termina OK.
COMPLETE_MARKER = ".complete"


class BackupHealthStatus(str, Enum):
    """4 niveis de saude do backup (espelha `HealthStatus` em dead_mans_switch)."""

    HEALTHY = "healthy"  # ultimo backup <= 360min (6h)
    STALE = "stale"  # 360 < idade <= 720min (6h-12h)
    CRITICAL = "critical"  # idade > 720min (12h+)
    EMPTY = "empty"  # nenhum backup com marker .complete


class BackupHealth(BaseModel):
    """Saida tipada de `check_backup_v2_freshness`.

    Attributes:
        status: classificacao 4-niveis (healthy/stale/critical/empty).
        last_backup_at: timestamp (UTC) do ultimo backup com marker .complete,
            ou None se empty.
        last_backup_age_minutes: idade em minutos desde o ultimo backup OK
            (None se empty).
        last_backup_dir: nome do diretorio do ultimo backup (YYYYMMDD_HH)
            ou None.
        backup_count: numero de backups com marker .complete no diretorio.
        threshold_minutes: janela healthy em minutos (default 360).
        backup_dir: diretorio-base que foi escaneado.
        error: mensagem de erro se leitura falhou (None em caso normal).
        alert: mensagem de alerta formatada (None se healthy).
    """

    status: BackupHealthStatus
    last_backup_at: datetime | None = None
    last_backup_age_minutes: int | None = None
    last_backup_dir: str | None = None
    backup_count: int = 0
    threshold_minutes: int = Field(default=DEFAULT_HEALTHY_THRESHOLD_MINUTES, ge=1)
    backup_dir: str = DEFAULT_BACKUP_DIR
    error: str | None = None
    alert: str | None = None

    model_config = {"frozen": True}


def _list_complete_backups(backup_dir: str) -> list[tuple[str, float]]:
    """Lista diretorios com marker `.complete`, retorna [(dirname, mtime), ...].

    Apenas diretorios com marker `.complete` sao considerados backups OK.
    Diretorios orfaos (sem marker) sao ignorados — backup em andamento.

    Args:
        backup_dir: diretorio-base onde pg_basebackup_4x.sh grava YYYYMMDD_HH/.

    Returns:
        Lista de tuplas (dirname, mtime) ordenada por mtime DESC. Vazia se
        diretorio nao existe ou nao tem backups completos.
    """
    if not os.path.isdir(backup_dir):
        return []

    results: list[tuple[str, float]] = []
    for entry in os.listdir(backup_dir):
        full = os.path.join(backup_dir, entry)
        if not os.path.isdir(full):
            continue
        marker = os.path.join(full, COMPLETE_MARKER)
        if not os.path.isfile(marker):
            continue
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue
        results.append((entry, mtime))

    # Ordena do mais recente para o mais antigo
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _classify(
    backups: list[tuple[str, float]],
    backup_dir: str,
    threshold_minutes: int,
    *,
    now: datetime | None = None,
) -> BackupHealth:
    """Classifica saude do backup com base nos diretorios completos.

    Args:
        backups: lista [(dirname, mtime)] do mais recente ao mais antigo.
        backup_dir: diretorio-base escaneado.
        threshold_minutes: janela healthy em minutos (default 360).
        now: override do "agora" para testes deterministicos.

    Returns:
        BackupHealth com status + alert (None se healthy).
    """
    if not backups:
        return BackupHealth(
            status=BackupHealthStatus.EMPTY,
            last_backup_at=None,
            last_backup_age_minutes=None,
            last_backup_dir=None,
            backup_count=0,
            threshold_minutes=threshold_minutes,
            backup_dir=backup_dir,
            error=None,
            alert=(
                "backup_v2 VAZIO: nenhum backup com marker .complete encontrado. "
                "Cron pg_basebackup 4x/dia nunca rodou com sucesso, ou script nao "
                "foi instalado em /usr/local/bin/pg_basebackup_4x.sh."
            ),
        )

    last_dir, last_mtime = backups[0]
    last_dt = datetime.fromtimestamp(last_mtime, tz=timezone.utc)
    now = now or datetime.now(tz=timezone.utc)
    age_minutes = int((now - last_dt).total_seconds() // 60)

    if age_minutes <= threshold_minutes:
        status = BackupHealthStatus.HEALTHY
        alert = None
    elif age_minutes <= threshold_minutes * 2:
        status = BackupHealthStatus.STALE
        alert = (
            f"backup_v2 STALE: ultimo backup ha {age_minutes}min "
            f"(threshold={threshold_minutes}min, cron freq=6h). "
            f"Verificar se cron 0 */6 esta rodando + script executavel."
        )
    else:
        status = BackupHealthStatus.CRITICAL
        alert = (
            f"backup_v2 CRITICAL: ultimo backup ha {age_minutes}min "
            f"(threshold={threshold_minutes}min, 2x={threshold_minutes * 2}min). "
            f"RPO estourado (>12h sem backup). ACAO IMEDIATA: "
            f"verificar container {os.environ.get('PG_CONTAINER', 'cartorio_supabase-db-1')}, "
            f"volume mount /var/backups/cartorio/pgbase, e logs do cron."
        )

    return BackupHealth(
        status=status,
        last_backup_at=last_dt,
        last_backup_age_minutes=age_minutes,
        last_backup_dir=last_dir,
        backup_count=len(backups),
        threshold_minutes=threshold_minutes,
        backup_dir=backup_dir,
        error=None,
        alert=alert,
    )


def check_backup_v2_freshness(
    backup_dir: str | None = None,
    threshold_minutes: int = DEFAULT_HEALTHY_THRESHOLD_MINUTES,
    *,
    now: datetime | None = None,
) -> BackupHealth:
    """Verifica freshness do backup pg_basebackup 4x/dia (A14).

    Escaneia `backup_dir` (default /var/backups/cartorio/pgbase), busca
    diretorios `YYYYMMDD_HH/.complete` e classifica em 4 niveis baseado na
    idade do mais recente.

    Args:
        backup_dir: diretorio-base para escanear (default DEFAULT_BACKUP_DIR).
            Em testes, passar tmp_path ou diretorio mockado.
        threshold_minutes: janela healthy em minutos (default 360 = 6h).
        now: override do "agora" para testes deterministicos.

    Returns:
        BackupHealth com classificacao + alerta (None se healthy).

    Raises:
        ValueError: se threshold_minutes < 1.
    """
    if threshold_minutes < 1:
        raise ValueError(f"threshold_minutes deve ser >= 1, recebeu {threshold_minutes}")

    target_dir = backup_dir or DEFAULT_BACKUP_DIR

    try:
        backups = _list_complete_backups(target_dir)
    except Exception as e:
        # Diretorio nao acessivel (permissoes, mount nao montado) etc.
        # Retorna EMPTY com error explicito.
        logger.error("backup_v2 scan failed: dir=%s err=%s", target_dir, e)
        return BackupHealth(
            status=BackupHealthStatus.EMPTY,
            last_backup_at=None,
            last_backup_age_minutes=None,
            last_backup_dir=None,
            backup_count=0,
            threshold_minutes=threshold_minutes,
            backup_dir=target_dir,
            error=f"{type(e).__name__}: {e}",
            alert=(
                f"backup_v2 VAZIO + erro de leitura em {target_dir}. "
                f"Verificar volume mount do diretorio de backup no container."
            ),
        )

    health = _classify(backups, target_dir, threshold_minutes, now=now)

    if health.status == BackupHealthStatus.HEALTHY:
        logger.info(
            "BACKUP_V2_OK: last_backup_age=%dmin threshold=%dmin count=%d",
            health.last_backup_age_minutes,
            threshold_minutes,
            health.backup_count,
        )
    else:
        logger.error(
            "BACKUP_V2_%s: %s",
            health.status.value.upper(),
            health.alert,
        )

    return health


__all__ = [
    "BackupHealth",
    "BackupHealthStatus",
    "DEFAULT_BACKUP_DIR",
    "DEFAULT_HEALTHY_THRESHOLD_MINUTES",
    "check_backup_v2_freshness",
]
