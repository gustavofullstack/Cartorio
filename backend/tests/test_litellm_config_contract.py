"""Contratos estáticos entre LiteLLM e a configuração segura do backend."""

from pathlib import Path


def test_litellm_uses_independent_zen_secret_slots() -> None:
    """O proxy usa os três slots Zen sem aliases legados de segredo."""
    config = (Path(__file__).resolve().parents[2] / "infra/litellm/config.yaml").read_text()

    assert "os.environ/OPENCODE_ZEN_ACCOUNT_1_API_KEY" in config
    assert "os.environ/OPENCODE_ZEN_ACCOUNT_2_API_KEY" in config
    assert "os.environ/OPENCODE_ZEN_ACCOUNT_3_API_KEY" in config
    assert "os.environ/OPENCODE_FREE_" not in config


def test_litellm_uses_canonical_external_provider_secret_names() -> None:
    """Nomes de env do proxy acompanham os nomes expostos pelo backend."""
    config = (Path(__file__).resolve().parents[2] / "infra/litellm/config.yaml").read_text()

    assert "os.environ/MISTRAL_API_KEY" in config
    assert "os.environ/GOOGLE_AI_STUDIO_API_KEY" in config
    assert "MISTRAL_FREE_API_KEY" not in config
    assert "os.environ/GOOGLE_API_KEY" not in config
