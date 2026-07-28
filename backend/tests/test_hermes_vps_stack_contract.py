"""Contratos de implantação segura do Hermes Cartório na VPS."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
STACK_PATH = ROOT / "infra" / "hermes" / "docker-stack.yml"
CONFIG_PATH = ROOT / "infra" / "hermes" / "config.cartorio.yaml"
SOUL_PATH = ROOT / "infra" / "openclaw-agent" / "workspace" / "SOUL.md"

EXPECTED_SECRETS = {
    "hermes_api_server_key",
    "hermes_minimax_api_key",
    "hermes_mcp_cartorio_api_key",
    "hermes_photon_project_secret",
}


def _stack() -> dict:
    return yaml.safe_load(STACK_PATH.read_text(encoding="utf-8"))


def test_hermes_vps_stack_is_isolated_and_persistent() -> None:
    """Hermes roda como serviço novo, numa réplica e na rede do Cartório."""
    stack = _stack()
    service = stack["services"]["hermes"]

    assert "@sha256:" in service["image"]
    assert service["deploy"]["replicas"] == 1
    assert service["networks"] == ["easypanel-cartorio"]
    assert service["volumes"] == ["hermes_cartorio_data:/opt/data"]
    assert stack["networks"]["easypanel-cartorio"]["external"] is True
    assert service["deploy"]["update_config"]["failure_action"] == "rollback"


def test_hermes_vps_stack_uses_external_secrets_only() -> None:
    """Nenhuma chave pode entrar no manifesto ou no repositório."""
    stack = _stack()
    service = stack["services"]["hermes"]
    declared = set(stack["secrets"])
    mounted = {entry if isinstance(entry, str) else entry["source"] for entry in service["secrets"]}
    command = "\n".join(service["command"])
    entrypoint = (
        ROOT / "infra" / "hermes" / "lark-entrypoint.sh"
    ).read_text(encoding="utf-8")
    secret_readers = f"{command}\n{entrypoint}"

    assert declared == EXPECTED_SECRETS
    assert mounted == EXPECTED_SECRETS
    assert all(stack["secrets"][name]["external"] is True for name in EXPECTED_SECRETS)
    for name in EXPECTED_SECRETS:
        assert (
            f"/run/secrets/{name}" in secret_readers
            or f"read_required_secret {name}" in secret_readers
        )


def test_hermes_uses_mcp_not_direct_database_or_redis_access() -> None:
    """O agente acessa dados do Cartório pelo limite API/MCP, preservando RLS."""
    service = _stack()["services"]["hermes"]
    config = CONFIG_PATH.read_text(encoding="utf-8")

    assert service["environment"]["MCP_CARTORIO_URL"] == "http://cartorio_api:8000/mcp"
    assert "mcp_servers:" in config
    assert "${MCP_CARTORIO_URL}" in config
    assert "${MCP_CARTORIO_API_KEY}" in config
    assert "postgres" not in config.lower()
    assert "redis" not in config.lower()


def test_hermes_uses_native_minimax_with_highspeed_fallback() -> None:
    """O runtime usa providers que existem no Hermes e uma contingência testada."""
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    entrypoint = (
        ROOT / "infra" / "hermes" / "lark-entrypoint.sh"
    ).read_text(encoding="utf-8")

    assert config["model"] == {
        "default": "${HERMES_LLM_MODEL}",
        "provider": "minimax",
        "base_url": "${HERMES_LLM_BASE_URL}",
    }
    assert config["fallback_model"] == {
        "provider": "minimax",
        "model": "MiniMax-M2.7-highspeed",
        "base_url": "${HERMES_LLM_BASE_URL}",
    }
    assert "read_required_secret hermes_minimax_api_key" in entrypoint
    assert "provider: openai" not in CONFIG_PATH.read_text(encoding="utf-8")


def test_hermes_mounts_canonical_pietra_persona() -> None:
    """O gateway não pode voltar à persona genérica após substituir uma task."""
    stack = _stack()
    service = stack["services"]["hermes"]
    entrypoint = (
        ROOT / "infra" / "hermes" / "lark-entrypoint.sh"
    ).read_text(encoding="utf-8")
    soul = SOUL_PATH.read_text(encoding="utf-8")

    mounted_configs = {
        entry["source"]: entry["target"] for entry in service["configs"]
    }
    assert mounted_configs["hermes_cartorio_soul_v1"] == "/run/configs/SOUL.md"
    assert "install -m 0600 /run/configs/SOUL.md" in entrypoint
    assert "Você é a **Pietra" in soul
    assert "NUNCA mencione modelos de IA" in soul
    assert "NUNCA liste ferramentas internas" in soul


def test_photon_starts_fail_closed_with_allowlist() -> None:
    """O canal iMessage não pode ser aberto a qualquer remetente por engano."""
    service = _stack()["services"]["hermes"]
    config = CONFIG_PATH.read_text(encoding="utf-8")

    assert service["environment"]["PHOTON_ALLOW_ALL_USERS"] == "false"
    assert "PHOTON_ALLOWED_USERS" in service["environment"]
    assert "photon:" in config
    assert "sidecar_port: 8793" in config
