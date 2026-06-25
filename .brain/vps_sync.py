"""VPS Production Sync Catalog (BRAIN4).

Catalogo de TODOS os paths canonicos em producao (VPS Hostinger).
Sincroniza local dev <-> VPS prod.

Informacoes:
- Containers Docker Swarm (12 servicos Easypanel)
- Paths filesystem VPS
- Config files locations
- Environment vars locations
- Backup paths
- Deploy commands

Uso:
    from brain.vps_sync import VPS_DEPLOY, CONTAINERS, BACKUP_PATHS
    print(VPS_DEPLOY.vps_ip_public)
    print([c.name for c in CONTAINERS])
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================================
# VPS Info
# ============================================================================


@dataclass(frozen=True)
class VpsInfo:
    """Metadata da VPS Hostinger."""

    provider: str
    vps_ip_public: str
    vps_ip_tailscale: str
    ssh_user: str
    os: str
    project_path: str  # /home/easypanel/projects/cartorio
    volumes_path: str  # /home/easypanel/volumes
    backups_path: str  # /home/easypanel/backups
    tailnet: str
    docker_swarm_manager: bool = True


VPS_DEPLOY = VpsInfo(
    provider="Hostinger",
    vps_ip_public="187.77.236.77",
    vps_ip_tailscale="100.99.172.84",
    ssh_user="root",  # ou 'easypanel' dependendo do contexto
    os="Ubuntu 22.04 LTS",
    project_path="/home/easypanel/projects/cartorio",
    volumes_path="/home/easypanel/volumes",
    backups_path="/home/easypanel/backups",
    tailnet="tail2fe279.ts.net",
    docker_swarm_manager=True,
)


# ============================================================================
# Containers (Easypanel Swarm)
# ============================================================================


@dataclass(frozen=True)
class Container:
    """Container Docker Swarm."""

    name: str  # cartorio_api, cartorio_chatwoot, etc
    service: str  # api, chatwoot, evolution-api, etc
    image: str  # ex: cartorio-backend:v0.6.0
    port_internal: int | None
    port_external: int | None
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    healthcheck_url: str | None = None


CONTAINERS: tuple[Container, ...] = (
    Container(
        name="cartorio_api",
        service="api",
        image="cartorio-backend:v0.6.0",
        port_internal=8000,
        port_external=None,  # Traefik route
        healthcheck_url="https://api.2notasudi.com.br/api/v1/health/radar",
    ),
    Container(
        name="cartorio_chatwoot",
        service="chatwoot",
        image="chatwoot/chatwoot:v3.x",
        port_internal=3000,
        port_external=None,
        healthcheck_url="https://cartorio-chatwoot.dfgdxq.easypanel.host/api/v1/accounts",
    ),
    Container(
        name="cartorio_chatwoot-sidekiq",
        service="chatwoot-sidekiq",
        image="chatwoot/chatwoot:v3.x",
        port_internal=None,
        port_external=None,
        depends_on=("cartorio_chatwoot", "cartorio_redis"),
    ),
    Container(
        name="cartorio_evolution-api",
        service="evolution-api",
        image="evolutionapi/evolution-api:2.3.7",
        port_internal=8080,
        port_external=None,
        healthcheck_url="https://whatsapp.2notasudi.com.br/",
    ),
    Container(
        name="cartorio_n8n",
        service="n8n",
        image="n8nio/n8n:1.94.x",
        port_internal=5678,
        port_external=None,
        healthcheck_url="https://flow.2notasudi.com.br/healthz",
    ),
    Container(
        name="cartorio_n8n-runner",
        service="n8n-runner",
        image="n8nio/n8n:1.94.x",
        port_internal=None,
        port_external=None,
        depends_on=("cartorio_n8n",),
    ),
    Container(
        name="cartorio_openclaw-gateway",
        service="openclaw-gateway",
        image="openclaw/gateway:0.4.x",
        port_internal=18790,
        port_external=None,
        healthcheck_url="https://agent.2notasudi.com.br/health",
    ),
    Container(
        name="cartorio_redis",
        service="redis",
        image="redis:7-alpine",
        port_internal=6379,
        port_external=None,
        depends_on=(),
    ),
    Container(
        name="cartorio_redis_dbgate",
        service="redis-dbgate",
        image="dbgate/dbgate:latest",
        port_internal=3000,
        port_external=3001,
    ),
    Container(
        name="cartorio_redis_rediscommander",
        service="redis-commander",
        image="rediscommander/redis-commander:latest",
        port_internal=8081,
        port_external=8081,
    ),
    Container(
        name="cartorio_easypanel",
        service="easypanel",
        image="easypanel/easypanel:latest",
        port_internal=3000,
        port_external=3000,
    ),
    Container(
        name="cartorio_easypanel-traefik",
        service="easypanel-traefik",
        image="traefik:v3.x",
        port_internal=80,
        port_external=80,
    ),
    # Supabase self-hosted (14 containers separados, gerenciados pelo Supabase)
)


# ============================================================================
# Volumes / Persistent Storage
# ============================================================================


VOLUMES: dict[str, str] = {
    "api_secrets": "/home/easypanel/volumes/cartorio/api/secrets",
    "api_logs": "/home/easypanel/volumes/cartorio/api/logs",
    "chatwoot_storage": "/home/easypanel/volumes/cartorio/chatwoot/storage",
    "evolution_instances": "/home/easypanel/volumes/cartorio/evolution/instances",
    "n8n_data": "/home/easypanel/volumes/cartorio/n8n/data",
    "redis_data": "/home/easypanel/volumes/cartorio/redis/data",
    "supabase_storage": "/home/easypanel/volumes/supabase/storage",
}


# ============================================================================
# Environment vars (.env files)
# ============================================================================


ENV_FILES: dict[str, str] = {
    "api": "/home/easypanel/volumes/cartorio/api/secrets/.env",
    "chatwoot": "/home/easypanel/volumes/cartorio/chatwoot/.env",
    "evolution": "/home/easypanel/volumes/cartorio/evolution/.env",
    "n8n": "/home/easypanel/volumes/cartorio/n8n/.env",
    "redis": "/home/easypanel/volumes/cartorio/redis/.env",
    "openclaw": "/home/easypanel/volumes/cartorio/openclaw/.env",
}


# ============================================================================
# Backup paths
# ============================================================================


BACKUP_PATHS: dict[str, str] = {
    "pg_basebackup_daily": "/home/easypanel/backups/cartorio/pg_basebackup/{YYYY-MM-DD}/",
    "supabase_storage": "/home/easypanel/backups/supabase/storage/{YYYY-MM-DD}.tar.gz",
    "n8n_workflows_json": "/home/easypanel/backups/cartorio/n8n/{YYYY-MM-DD}/workflows/",
    "evolution_session": "/home/easypanel/backups/cartorio/evolution/session-{TIMESTAMP}.json",
    "logs_weekly": "/home/easypanel/backups/cartorio/logs/{YYYY-WW}/",
}


# ============================================================================
# DNS Records (Cloudflare)
# ============================================================================


DNS_RECORDS: dict[str, dict[str, str]] = {
    "api.2notasudi.com.br": {"type": "A", "value": "187.77.236.77", "status": "✅ Configurado"},
    "agent.2notasudi.com.br": {"type": "A", "value": "187.77.236.77", "status": "✅ Configurado"},
    "chat.2notasudi.com.br": {"type": "A", "value": "187.77.236.77", "status": "✅ Configurado"},
    "supbase.2notasudi.com.br": {"type": "A", "value": "187.77.236.77", "status": "✅ Configurado"},
    "easypanel.2notasudi.com.br": {"type": "A", "value": "187.77.236.77", "status": "✅ Configurado"},
    "whatsapp.2notasudi.com.br": {"type": "A", "value": "187.77.236.77", "status": "✅ Configurado"},
    "cartorio-n8n.dfgdxq.easypanel.host": {"type": "CNAME", "value": "easypanel-host", "status": "✅ Configurado"},
    "n8n.2notasudi.com.br": {"type": "A", "value": "PENDENTE", "status": "⚠️ NXDOMAIN"},
    "supabase.2notasudi.com.br": {"type": "A", "value": "PENDENTE", "status": "⚠️ NXDOMAIN"},
    "flow.2notasudi.com.br": {"type": "A", "value": "OPCIONAL", "status": "🟡 Nice-to-have"},
}


# ============================================================================
# Deploy commands
# ============================================================================


DEPLOY_COMMANDS: dict[str, str] = {
    "deploy_api": "easypanel deploy cartorio_api --branch master",
    "restart_api": "docker service update --force cartorio_api",
    "tail_logs_api": "docker logs -f $(docker ps -q -f name=cartorio_api)",
    "exec_into_api": "docker exec -it $(docker ps -q -f name=cartorio_api) bash",
    "deploy_via_ssh": (
        "ssh root@100.99.172.84 'cd /home/easypanel/projects/cartorio && "
        "git pull origin master && easypanel deploy api'"
    ),
}


# ============================================================================
# Health check aggregator
# ============================================================================


def get_all_health_urls() -> dict[str, str]:
    """Mapa service_name -> healthcheck_url (apenas containers com healthcheck)."""
    return {c.service: c.healthcheck_url for c in CONTAINERS if c.healthcheck_url}


def get_critical_containers() -> tuple[str, ...]:
    """Containers criticos (sem dependencia, essenciais)."""
    critical = {"api", "redis", "n8n", "openclaw-gateway", "evolution-api", "supabase"}
    return tuple(c.service for c in CONTAINERS if c.service in critical and not c.depends_on)


def get_total_health_urls() -> int:
    """Total de URLs de health check configuradas."""
    return sum(1 for c in CONTAINERS if c.healthcheck_url is not None)