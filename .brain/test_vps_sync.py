"""Testes do VPS Sync Catalog (BRAIN4)."""
from __future__ import annotations

import pytest  # noqa: E402

from brain.vps_sync import (  # noqa: E402
    BACKUP_PATHS,
    CONTAINERS,
    DNS_RECORDS,
    DEPLOY_COMMANDS,
    ENV_FILES,
    VOLUMES,
    VPS_DEPLOY,
    get_all_health_urls,
    get_critical_containers,
    get_total_health_urls,
)


# ============================================================================
# Tests: VPS Info
# ============================================================================


def test_vps_deploy_tem_ip_public_e_tailscale() -> None:
    """VPS tem IP publico e Tailscale para acesso redundante."""
    assert VPS_DEPLOY.vps_ip_public == "187.77.236.77"
    assert VPS_DEPLOY.vps_ip_tailscale == "100.99.172.84"


def test_vps_deploy_paths_canonicos() -> None:
    """Paths canonicos de filesystem."""
    assert VPS_DEPLOY.project_path == "/home/easypanel/projects/cartorio"
    assert VPS_DEPLOY.volumes_path.startswith("/home/easypanel/volumes")
    assert VPS_DEPLOY.backups_path.startswith("/home/easypanel/backups")


def test_vps_tailnet_definido() -> None:
    """Tailnet para MagicDNS."""
    assert VPS_DEPLOY.tailnet == "tail2fe279.ts.net"


# ============================================================================
# Tests: Containers
# ============================================================================


def test_total_containers_cobre_servicos_principais() -> None:
    """Containers cobrem os 11+ servicos canonicos."""
    services = {c.service for c in CONTAINERS}
    essenciais = {"api", "chatwoot", "evolution-api", "n8n", "openclaw-gateway", "redis"}
    for s in essenciais:
        assert s in services, f"Falta container: {s}"


def test_container_names_unicos() -> None:
    """Nomes de containers Docker Swarm sao unicos."""
    names = [c.name for c in CONTAINERS]
    assert len(names) == len(set(names))


def test_container_api_tem_healthcheck() -> None:
    """API tem healthcheck configurado."""
    api = next(c for c in CONTAINERS if c.service == "api")
    assert api.healthcheck_url is not None
    assert "api.2notasudi.com.br" in api.healthcheck_url


def test_container_chatwoot_tem_dependency() -> None:
    """Chatwoot sidekiq depende de chatwoot + redis."""
    sidekiq = next(c for c in CONTAINERS if c.service == "chatwoot-sidekiq")
    assert "cartorio_chatwoot" in sidekiq.depends_on
    assert "cartorio_redis" in sidekiq.depends_on


def test_container_n8n_runner_depende_n8n() -> None:
    """n8n-runner depende de n8n principal."""
    runner = next(c for c in CONTAINERS if c.service == "n8n-runner")
    assert "cartorio_n8n" in runner.depends_on


def test_container_redis_sem_dependency() -> None:
    """Redis eh container base (sem dependencies)."""
    redis = next(c for c in CONTAINERS if c.service == "redis")
    assert redis.depends_on == ()


# ============================================================================
# Tests: Volumes
# ============================================================================


def test_volumes_cobrem_servicos() -> None:
    """Volumes cobrem os principais servicos com persistent storage."""
    esperados = ["api_secrets", "chatwoot_storage", "n8n_data", "redis_data"]
    for v in esperados:
        assert v in VOLUMES, f"Falta volume: {v}"


def test_volumes_em_path_canonico() -> None:
    """Todos volumes em /home/easypanel/volumes/cartorio/."""
    for path in VOLUMES.values():
        assert path.startswith("/home/easypanel/volumes/cartorio/")


# ============================================================================
# Tests: ENV files
# ============================================================================


def test_env_files_para_servicos_principais() -> None:
    """ENV files separados por servico (LGPD art. 37 segregation)."""
    esperados = ["api", "chatwoot", "evolution", "n8n", "redis", "openclaw"]
    for s in esperados:
        assert s in ENV_FILES, f"Falta .env: {s}"


def test_env_files_em_volumes_secrets() -> None:
    """ENV files em /secrets/ para permissao 600."""
    for path in ENV_FILES.values():
        assert "/secrets/" in path or "/volumes/cartorio/" in path


# ============================================================================
# Tests: Backups
# ============================================================================


def test_backups_cobrem_pg_basebackup() -> None:
    """Backup diario de pg_basebackup configurado."""
    assert "pg_basebackup_daily" in BACKUP_PATHS


def test_backups_cobrem_supabase_storage() -> None:
    """Backup do Supabase Storage."""
    assert "supabase_storage" in BACKUP_PATHS


def test_backups_cobrem_n8n_workflows() -> None:
    """Backup dos workflows N8N em JSON."""
    assert "n8n_workflows_json" in BACKUP_PATHS


# ============================================================================
# Tests: DNS Records
# ============================================================================


def test_dns_records_dominios_principais_configurados() -> None:
    """6 dominios principais configurados."""
    dominios_config = [d for d, info in DNS_RECORDS.items() if "Configurado" in info["status"]]
    assert len(dominios_config) >= 6


def test_dns_records_pendentes_documentados() -> None:
    """Dominios pendentes estao documentados."""
    pendentes = [d for d, info in DNS_RECORDS.items() if "PENDENTE" in info["status"]]
    # n8n + supabase = 2 pendentes
    assert len(pendentes) >= 2


# ============================================================================
# Tests: Deploy commands
# ============================================================================


def test_deploy_commands_presentes() -> None:
    """Comandos de deploy/rollback/logs presentes."""
    assert "deploy_api" in DEPLOY_COMMANDS
    assert "restart_api" in DEPLOY_COMMANDS
    assert "tail_logs_api" in DEPLOY_COMMANDS
    assert "deploy_via_ssh" in DEPLOY_COMMANDS


def test_deploy_via_ssh_usa_tailscale() -> None:
    """Deploy via SSH usa Tailscale IP (rede privada)."""
    cmd = DEPLOY_COMMANDS["deploy_via_ssh"]
    assert "100.99.172.84" in cmd  # Tailscale IP


# ============================================================================
# Tests: Helpers
# ============================================================================


def test_get_all_health_urls_retorna_apenas_com_healthcheck() -> None:
    """Helper retorna apenas containers com healthcheck_url."""
    urls = get_all_health_urls()
    assert len(urls) >= 5  # api, chatwoot, evolution, n8n, openclaw


def test_get_critical_containers_sao_fundamentals() -> None:
    """Critical containers sao os essenciais sem dependency."""
    critical = get_critical_containers()
    assert "api" in critical
    assert "redis" in critical


def test_get_total_health_urls() -> None:
    """Total de healthcheck URLs >= 5."""
    total = get_total_health_urls()
    assert total >= 5