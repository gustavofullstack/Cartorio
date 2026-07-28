"""Contratos dos scripts operacionais instalados na VPS do Cartório."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DAILY_BACKUP = ROOT / "infra" / "backup" / "cartorio-backup.sh"
PG_BASEBACKUP = ROOT / "infra" / "backup" / "pg_basebackup_4x.sh"
READINESS = ROOT / "infra" / "scripts" / "cartorio-vps-readiness.sh"


def test_backups_resolve_the_canonical_postgres_service() -> None:
    """Renomear o serviço no EasyPanel não pode parar silenciosamente os backups."""
    for script_path in (DAILY_BACKUP, PG_BASEBACKUP):
        script = script_path.read_text(encoding="utf-8")
        assert 'PG_SERVICE_NAME="${PG_SERVICE_NAME:-cartorio_banco_de_dados}"' in script
        assert "label=com.docker.swarm.service.name=${PG_SERVICE_NAME}" in script


def test_daily_backup_preserves_n8n_without_an_api_key() -> None:
    """A cópia dos workflows usa o CLI interno quando a API key de auditoria falha."""
    script = DAILY_BACKUP.read_text(encoding="utf-8")

    assert "docker service inspect cartorio_system-api" in script
    assert "n8n export:workflow --all" in script
    assert "docker cp" in script
    assert "bancos foram preservados no backup" in script


def test_readiness_uses_live_service_names_and_fail_closed_channel_gates() -> None:
    """O gate não pode produzir falso DOWN consultando os serviços aposentados."""
    script = READINESS.read_text(encoding="utf-8")

    for service_name in (
        "cartorio_system-api",
        "cartorio_memory-cache",
        "cartorio_banco_de_dados",
        "cartorio_whatsapp-api",
        "cartorio_hermes",
    ):
        assert service_name in script
    assert "hermes-feishu-pairing" in script
    assert "whatsapp-session" in script
    assert "n8n-workflow-database" in script
    assert "select count(*) from workflow_entity" in script
    assert "cartorio_api --format" not in script
    assert "cartorio_supabase cartorio_n8n" not in script
