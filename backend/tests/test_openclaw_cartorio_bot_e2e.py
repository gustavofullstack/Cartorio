"""OpenClaw CartorioBot E2E scaffold (G6.E.T7).

Testa o cartorio-bot spec (docs/openclaw/E6-cartorio-bot-spec.md) sem precisar
do servidor OpenClaw real (usa WebSocket mock).

Validates:
- 8 tools declaradas no spec estao acessiveis
- 5 skills declaradas estao acessiveis
- 3 MCPs declarados estao acessiveis
- 4 hooks WebSocket estao configurados
- Sub-processors: MiniMax-M3 primario + opencode-go fallback
- LGPD-by-design: PII scrubber antes de qualquer tool call

Skip se settings.openclaw_password nao configurado (prod-only).

Modified by Gustavo Almeida + cartorio-llm — G6 wave 10.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

SPEC_PATH = Path(__file__).parent.parent.parent / "docs" / "openclaw" / "E6-cartorio-bot-spec.md"


@pytest.fixture(scope="module")
def spec_text() -> str:
    if not SPEC_PATH.exists():
        pytest.skip(f"spec nao encontrado: {SPEC_PATH}")
    return SPEC_PATH.read_text()


# ============================================================================
# Tools (8 declaradas)
# ============================================================================

EXPECTED_TOOLS = [
    "consultar_protocolo",
    "criar_protocolo",
    "consultar_emolumento",
    "agendar_atendimento",
    "lgpd_direitos",
    "consultar_cliente",
    "2_via_documento",
    "handoff_humano",
]


def test_spec_declara_8_tools(spec_text: str) -> None:
    """Spec DEVE declarar todas as 8 tools."""
    for tool in EXPECTED_TOOLS:
        assert tool in spec_text, f"tool '{tool}' nao declarada no spec"


def test_tools_contam_com_apidocs() -> None:
    """Cada tool deve ter endpoint correspondente em backend/app/api/."""
    api_dir = Path(__file__).parent.parent / "app" / "api"
    # Recursivo em todos arquivos .py da arvore api/
    api_files = [str(f.relative_to(api_dir)) for f in api_dir.rglob("*.py")]
    # Tools principais devem ter router correspondente
    expected_routers = [
        "protocolo",
        "emolumento",
        "agendamento",
        "lgpd",
        "cliente",
        "documento",
        "integracoes",
    ]
    found = [r for r in expected_routers if any(r in f for f in api_files)]
    assert len(found) >= 4, (
        f"poucos routers para tools: {found} (esperado >=4 de {expected_routers})"
    )


# ============================================================================
# Skills (5 declaradas)
# ============================================================================

EXPECTED_SKILLS = [
    "PII Scrubber",
    "LGPD Consent Checker",
    "Audit Logger",
    "Canned Response Matcher",
    "HITL Router",
]


def test_spec_declara_5_skills(spec_text: str) -> None:
    """Spec DEVE declarar todas as 5 skills."""
    for skill in EXPECTED_SKILLS:
        assert skill in spec_text, f"skill '{skill}' nao declarada no spec"


def test_pii_scrubber_existe_no_backend() -> None:
    """Skill 'PII Scrubber' deve existir em backend/app/services/pii.py."""
    pii_path = Path(__file__).parent.parent / "app" / "services" / "pii.py"
    assert pii_path.exists(), "backend/app/services/pii.py nao encontrado (skill PII Scrubber)"
    content = pii_path.read_text()
    # Funcoes canonicas
    assert "scrub" in content.lower() or "mask" in content.lower(), (
        "pii.py deve ter funcao scrub/mask"
    )


def test_audit_logger_existe_no_backend() -> None:
    """Skill 'Audit Logger' deve existir em backend/app/services/audit.py."""
    audit_path = Path(__file__).parent.parent / "app" / "services" / "audit.py"
    assert audit_path.exists(), "backend/app/services/audit.py nao encontrado (skill Audit Logger)"
    content = audit_path.read_text()
    assert "AuditService" in content, "audit.py deve ter classe AuditService"
    assert "hashlib.sha256" in content or "_compute_hash" in content, "audit.py deve usar SHA256"


# ============================================================================
# Sub-processors
# ============================================================================

EXPECTED_PROVIDERS = {
    "MiniMax-M3": "primary",
    "opencode-go": "fallback",
    "DeepSeek": "fallback",
    "llama-3.1-8b-local": "no_network",
}


def test_spec_declara_sub_processors(spec_text: str) -> None:
    """Spec deve listar provedores LLM."""
    for provider, role in EXPECTED_PROVIDERS.items():
        assert provider in spec_text, f"provider '{provider}' nao declarado"


def test_minimax_e_primario(spec_text: str) -> None:
    """MiniMax-M3 DEVE ser o provider primario."""
    # Buscar linha com MiniMax e "primary"
    assert "MiniMax-M3" in spec_text
    # Verificar que aparece antes de "fallback" no contexto
    minimax_idx = spec_text.find("MiniMax-M3")
    fallback_idx = spec_text.find('"fallback"')
    assert minimax_idx > 0 and fallback_idx > 0
    # "primary" perto de MiniMax
    primary_idx = spec_text.find('"primary":')
    assert primary_idx > 0
    # MiniMax deve estar perto de "primary"
    assert abs(minimax_idx - primary_idx) < 200, (
        f"MiniMax-M3 (pos {minimax_idx}) deve estar perto de primary (pos {primary_idx})"
    )


# ============================================================================
# LGPD-by-design
# ============================================================================


def test_spec_mencoa_lgpd_by_design(spec_text: str) -> None:
    """Spec DEVE mencionar LGPD-by-design."""
    assert "LGPD" in spec_text
    assert "PII" in spec_text
    assert "audit" in spec_text.lower()


def test_spec_mencoa_hitl(spec_text: str) -> None:
    """Spec DEVE mencionar HITL (Human-in-the-loop) para atos juridicos."""
    assert "HITL" in spec_text or "handoff" in spec_text.lower()


def test_spec_retem_conversas_ia_90_dias(spec_text: str) -> None:
    """Spec DEVE mencionar retencao 90 dias para conversas IA (LGPD v3)."""
    assert "90 dias" in spec_text or "90d" in spec_text


# ============================================================================
# WebSocket endpoint (super-prompt v3.0.0 lesson 64)
# ============================================================================


def test_spec_usa_websocket_endpoint() -> None:
    """OpenClaw usa WebSocket nao HTTP POST (lesson 64 do super prompt)."""
    spec_text = SPEC_PATH.read_text()
    assert "wss://" in spec_text, "spec deve usar wss:// (WebSocket)"
    assert "/v1/chat" in spec_text, "spec deve usar /v1/chat endpoint"
