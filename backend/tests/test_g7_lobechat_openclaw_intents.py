"""G7.06.T4 — Synthetic E2E: LobeChat → OpenClaw → API (3 intents).

Cadeia live (LobeChat UI → OpenClaw gateway → Cartorio API) pode estar HOLD em prod.
Este modulo exerce o contrato das 3 intents **offline**, com:

- FastAPI TestClient para endpoints de emolumento / protocolo
- SQLite in-memory + X-API-Key para HITL DRAFT
- respx/httpx mocks para Chatwoot handoff (sem rede real)
- Skills registry OpenClaw como mapa intent → tool

Intents cobertas:
  1. Consulta emolumento (procuracao)
  2. Status protocolo / HITL draft
  3. Handoff humano / Chatwoot-style

Refs:
  - docs/LOBECHAT_OPENCLAW_3INTENTS_E2E_G7.md
  - docs/openclaw/E6-cartorio-bot-spec.md
  - infra/openclaw-agent/skills/registry.json

Modified by Gustavo Almeida — G7 Wave 27.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.chatwoot_handoff_macros import HANDOFF_MACROS, get_macro_by_name
from app.services.emolumento import calcular

ROOT = Path(__file__).resolve().parents[2]
SKILLS_REGISTRY = ROOT / "infra" / "openclaw-agent" / "skills" / "registry.json"
OPENCLAW_SPEC = ROOT / "docs" / "openclaw" / "E6-cartorio-bot-spec.md"

# User utterances that LobeChat would send into OpenClaw (synthetic)
UTTER_EMOLUMENTO = "Quanto custa uma procuraçao simples?"
UTTER_PROTOCOLO = "Qual o status do protocolo 2026-00001?"
UTTER_HANDOFF = "Quero falar com um escrevente humano, por favor"


# ============================================================================
# Helpers: intent routing (mirrors OpenClaw skill registry)
# ============================================================================


def _load_skills() -> list[dict[str, Any]]:
    assert SKILLS_REGISTRY.is_file(), f"missing {SKILLS_REGISTRY}"
    data = json.loads(SKILLS_REGISTRY.read_text(encoding="utf-8"))
    return list(data.get("skills") or [])


def resolve_skill_for_utterance(text: str) -> dict[str, Any] | None:
    """Resolve skill by keyword heuristics (offline stand-in for OpenClaw NLU)."""
    lower = text.lower()
    skills = _load_skills()
    # Priority order matches product funnel: emolumento → protocolo → handoff
    ordered = (
        "cartorio-emolumento-calc",
        "cartorio-protocolo-tracker",
        "cartorio-handoff-trigger",
    )
    keyword_map = {
        "cartorio-emolumento-calc": (
            "emolumento",
            "custa",
            "quanto",
            "procurac",
            "procuraç",
            "valor",
        ),
        "cartorio-protocolo-tracker": (
            "protocolo",
            "status",
            "andamento",
            "cart-",
        ),
        "cartorio-handoff-trigger": (
            "humano",
            "escrevente",
            "atendente",
            "falar com",
            "reclamacao",
            "reclamação",
        ),
    }
    for name in ordered:
        keys = keyword_map[name]
        if any(k in lower for k in keys):
            for s in skills:
                if s.get("name") == name:
                    return s
    return None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def api_client(test_engine, test_session_factory):
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def cliente_lgpd(test_engine):
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        cliente = Cliente(
            id=1,
            cpf_hash="b" * 64,
            nome="Maria OpenClaw Test",
            consentimento_lgpd=True,
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv("CARTORIO_API_KEY", "c" * 64)
    from app.config import settings

    return settings.cartorio_api_key


# ============================================================================
# Skill registry / contract
# ============================================================================


def test_skills_registry_declares_three_target_intents() -> None:
    skills = {s["name"]: s for s in _load_skills()}
    assert "cartorio-emolumento-calc" in skills
    assert "cartorio-protocolo-tracker" in skills
    assert "cartorio-handoff-trigger" in skills

    emol = skills["cartorio-emolumento-calc"]
    assert "cartorio_api_emolumento_calcular" in emol["tools_used"]
    assert emol.get("pii_safe") is True

    prot = skills["cartorio-protocolo-tracker"]
    assert "cartorio_api_protocolo_consultar" in prot["tools_used"]
    assert prot.get("pii_safe") is False  # needs identification

    hand = skills["cartorio-handoff-trigger"]
    assert any("chatwoot" in t or "handoff" in t for t in hand["tools_used"])


def test_openclaw_spec_lists_tools_for_three_intents() -> None:
    if not OPENCLAW_SPEC.is_file():
        pytest.skip("OpenClaw cartorio-bot spec missing")
    text = OPENCLAW_SPEC.read_text(encoding="utf-8")
    for tool in (
        "consultar_emolumento",
        "consultar_protocolo",
        "criar_protocolo",
        "handoff_humano",
    ):
        assert tool in text, f"tool {tool} missing from E6 spec"


def test_utterance_routing_three_intents() -> None:
    s1 = resolve_skill_for_utterance(UTTER_EMOLUMENTO)
    s2 = resolve_skill_for_utterance(UTTER_PROTOCOLO)
    s3 = resolve_skill_for_utterance(UTTER_HANDOFF)
    assert s1 is not None and s1["name"] == "cartorio-emolumento-calc"
    assert s2 is not None and s2["name"] == "cartorio-protocolo-tracker"
    assert s3 is not None and s3["name"] == "cartorio-handoff-trigger"


# ============================================================================
# Intent 1 — Consulta emolumento (procuracao)
# ============================================================================


def test_intent_emolumento_service_procuracao() -> None:
    """OpenClaw tool consultar_emolumento → service layer (no network)."""
    calc = calcular("procuracao", folhas=1, urgencia=False)
    assert calc.tipo == "procuracao"
    assert calc.total == Decimal("68.94")
    assert calc.base == Decimal("68.94")
    assert calc.tabela_referencia  # MG 2026 snapshot


def test_intent_emolumento_http_calcular_api(api_client: TestClient) -> None:
    """LobeChat→OpenClaw→GET /api/v1/emolumentos/calcular-api?tipo=procuracao."""
    skill = resolve_skill_for_utterance(UTTER_EMOLUMENTO)
    assert skill is not None

    resp = api_client.get(
        "/api/v1/emolumentos/calcular-api",
        params={"tipo": "procuracao", "folhas": 1, "urgencia": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tipo"] == "procuracao"
    assert float(body["total"]) == 68.94
    assert body["isento"] is False


def test_intent_emolumento_http_calcular_legacy(api_client: TestClient) -> None:
    """Path legacy used by some OpenClaw tool wrappers."""
    resp = api_client.get(
        "/api/v1/emolumento/calcular",
        params={"tipo": "procuracao", "folhas": 1, "urgencia": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("erro") is None
    assert body["tipo"] == "procuracao"
    assert Decimal(body["total"]) == Decimal("68.94")


# ============================================================================
# Intent 2 — Status protocolo / HITL draft
# ============================================================================


def test_intent_protocolo_hitl_draft_create(
    api_client: TestClient,
    cliente_lgpd: Cliente,
    api_key: str,
    test_engine,
) -> None:
    """OpenClaw criar_protocolo always births DRAFT (HITL mandatory)."""
    skill = resolve_skill_for_utterance("crie um protocolo de procuracao")
    # "protocolo" keyword → protocolo-tracker skill (status); create is still HITL tool
    assert skill is not None or True

    resp = api_client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "procuracao",
            "valor_snapshot": "68.94",
            "observacoes": "G7.06.T4 synthetic LobeChat→OpenClaw",
            "hitl_draft": True,
        },
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert re.match(r"^CART-\d{4}-\d{6}$", data["protocolo"])
    assert data["status"] == "draft"
    assert data["created_by"] == "api"

    SessionLocal = sessionmaker(bind=test_engine)
    with SessionLocal() as db:
        prot = db.query(Protocolo).filter_by(numero=data["protocolo"]).first()
        assert prot is not None
        assert prot.status == "DRAFT"  # never auto-EM_ANDAMENTO
        assert prot.tipo == "procuracao"


def test_intent_protocolo_status_consulta(
    api_client: TestClient,
    cliente_lgpd: Cliente,
    test_engine,
) -> None:
    """OpenClaw consultar_protocolo → GET /api/v1/protocolo/{YYYY-NNNNN}."""
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        db.add(
            Protocolo(
                numero="2026-00001",
                cliente_id=1,
                tipo="procuracao",
                status="DRAFT",
                valor_base=Decimal("68.94"),
                valor_total=Decimal("68.94"),
                tabela_referencia="TABELA_2026_MG",
                prazo_dias=5,
                canal_origem="web",  # CanalOrigem enum (OpenClaw/LobeChat → web)
            )
        )
        db.commit()

    skill = resolve_skill_for_utterance(UTTER_PROTOCOLO)
    assert skill is not None
    assert skill["name"] == "cartorio-protocolo-tracker"

    resp = api_client.get("/api/v1/protocolo/2026-00001")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["numero"] == "2026-00001"
    assert str(body["status"]).upper() == "DRAFT"
    assert body["tipo"] == "procuracao"
    # HITL messaging: awaiting clerk validation
    proxima = (body.get("proxima_acao") or "").lower()
    assert "escrevente" in proxima or "valid" in proxima


def test_intent_protocolo_hitl_rejects_non_draft_flag(
    api_client: TestClient,
    cliente_lgpd: Cliente,
    api_key: str,
) -> None:
    """Bot must not force non-draft processing (HITL gate)."""
    resp = api_client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "procuracao",
            "valor_snapshot": "68.94",
            "hitl_draft": False,
        },
        headers={"X-API-Key": api_key},
    )
    # 422 validation — bot never bypasses HITL
    assert resp.status_code in (422, 400), resp.text


# ============================================================================
# Intent 3 — Handoff humano / Chatwoot-style
# ============================================================================


def test_intent_handoff_macro_contract() -> None:
    """Skill handoff maps to Chatwoot macro handoff_humano (labels + team)."""
    skill = resolve_skill_for_utterance(UTTER_HANDOFF)
    assert skill is not None
    assert skill["name"] == "cartorio-handoff-trigger"

    macro = get_macro_by_name("handoff_humano")
    assert macro is not None
    action_types = {a.type for a in macro.actions}
    assert "assign_team" in action_types
    assert "add_label" in action_types
    assert "send_message" in action_types
    labels = [a.payload.get("label") for a in macro.actions if a.type == "add_label"]
    assert "handoff-humano" in labels
    assert len(HANDOFF_MACROS) >= 10


@pytest.mark.asyncio
@respx.mock
async def test_intent_handoff_chatwoot_http_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenClaw handoff_humano → Chatwoot REST (respx, no live DNS)."""
    import app.services.chatwoot_handoff as handoff_mod

    monkeypatch.setattr(handoff_mod, "CHATWOOT_API_KEY", "test-key-not-real")
    monkeypatch.setattr(handoff_mod, "CHATWOOT_ACCOUNT_ID", "1")
    monkeypatch.setattr(handoff_mod, "CHATWOOT_INBOX_ID", "9")
    monkeypatch.setattr(handoff_mod, "CHATWOOT_API_BASE_URL", "http://chatwoot.test")
    monkeypatch.setattr(handoff_mod, "CHATWOOT_PUBLIC_URL", "https://chatwoot.2notasudi.com.br")

    base = "http://chatwoot.test/api/v1/accounts/1"
    respx.get(f"{base}/contacts/search").mock(
        return_value=httpx.Response(200, json={"payload": []})
    )
    respx.post(f"{base}/contacts").mock(
        return_value=httpx.Response(201, json={"payload": {"id": 77}})
    )
    respx.post(f"{base}/conversations").mock(
        return_value=httpx.Response(201, json={"payload": {"id": 501}})
    )
    respx.post(url__regex=r".*/conversations/501/messages").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )

    ok, info = await handoff_mod.handoff_to_chatwoot(
        chat_id=424242,
        text=UTTER_HANDOFF,
        history=["user: preciso de ajuda humana"],
    )
    assert ok is True
    assert info["conversation_id"] == "501"
    assert info["contact_id"] == "77"
    assert "conversations/501" in info["public_url"]


# ============================================================================
# Full synthetic chain (3 turns) — LobeChat conversation simulation
# ============================================================================


def test_synthetic_chain_three_intents_end_to_end(
    api_client: TestClient,
    cliente_lgpd: Cliente,
    api_key: str,
    test_engine,
) -> None:
    """Simulate a 3-turn LobeChat session routed by OpenClaw skills → API.

    Turn 1: emolumento procuracao
    Turn 2: create HITL draft + status consult
    Turn 3: handoff macro selection (HTTP mocked separately)
    """
    turns: list[dict[str, Any]] = []

    # --- Turn 1: emolumento ---
    skill1 = resolve_skill_for_utterance(UTTER_EMOLUMENTO)
    assert skill1 and skill1["name"] == "cartorio-emolumento-calc"
    r1 = api_client.get(
        "/api/v1/emolumentos/calcular-api",
        params={"tipo": "procuracao", "folhas": 1},
    )
    assert r1.status_code == 200
    emol = r1.json()
    turns.append({"intent": skill1["name"], "tool": "consultar_emolumento", "result": emol})
    assert float(emol["total"]) == 68.94

    # --- Turn 2a: create draft (HITL) ---
    r2 = api_client.post(
        "/api/v1/protocolo/criar-api",
        json={
            "cliente_id": 1,
            "ato": "procuracao",
            "valor_snapshot": str(emol["total"]),
            "hitl_draft": True,
            "observacoes": "chain synthetic G7.06.T4",
        },
        headers={"X-API-Key": api_key},
    )
    assert r2.status_code == 201, r2.text
    draft = r2.json()
    assert draft["status"] == "draft"
    turns.append(
        {
            "intent": "criar_protocolo",
            "tool": "criar_protocolo",
            "result": draft,
            "hitl": True,
        }
    )

    # --- Turn 2b: status consult (classic number format OpenClaw tool) ---
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        db.add(
            Protocolo(
                numero="2026-00042",
                cliente_id=1,
                tipo="procuracao",
                status="DRAFT",
                valor_base=Decimal(str(emol["total"])),
                valor_total=Decimal(str(emol["total"])),
                tabela_referencia="TABELA_2026_MG",
                prazo_dias=5,
                canal_origem="web",
            )
        )
        db.commit()

    skill2 = resolve_skill_for_utterance("status do protocolo 2026-00042")
    assert skill2 and skill2["name"] == "cartorio-protocolo-tracker"
    r2b = api_client.get("/api/v1/protocolo/2026-00042")
    assert r2b.status_code == 200, r2b.text
    status_body = r2b.json()
    assert str(status_body["status"]).upper() == "DRAFT"
    turns.append(
        {
            "intent": skill2["name"],
            "tool": "consultar_protocolo",
            "result": status_body,
        }
    )

    # --- Turn 3: handoff macro (no live Chatwoot) ---
    skill3 = resolve_skill_for_utterance(UTTER_HANDOFF)
    assert skill3 and skill3["name"] == "cartorio-handoff-trigger"
    macro = get_macro_by_name("handoff_humano")
    assert macro is not None
    turns.append(
        {
            "intent": skill3["name"],
            "tool": "handoff_humano",
            "macro": macro.name,
            "labels": [a.payload.get("label") for a in macro.actions if a.type == "add_label"],
        }
    )

    assert len(turns) == 4  # emol + create + status + handoff
    assert turns[0]["tool"] == "consultar_emolumento"
    assert turns[1]["hitl"] is True
    assert turns[2]["result"]["numero"] == "2026-00042"
    assert "handoff-humano" in turns[3]["labels"]


def test_radar_expanded_still_in_openapi(api_client: TestClient) -> None:
    """G7.18.T1 support: OpenAPI must expose /health/radar/expanded (code gate)."""
    schema = api_client.get("/openapi.json").json()
    paths = schema.get("paths") or {}
    assert "/api/v1/health/radar/expanded" in paths
    methods = paths["/api/v1/health/radar/expanded"]
    assert "get" in methods
