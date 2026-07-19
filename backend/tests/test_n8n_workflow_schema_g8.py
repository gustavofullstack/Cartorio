"""Testes do schema strict Pydantic para exports JSON do N8N (G8.13.T2).

Cobre:
- campos requeridos presentes (name, nodes, connections, settings)
- tipos corretos (nodes list, parameters dict, connections dict)
- extra fields rejeitados (forward-compat blocked)
- timezone IANA validado
- regex anti-PII em node name (LGPD Art. 46)
- regex anti-PII em tag/description
- exports reais (5+) passam sem erro
- errors formatados com path Pydantic (loc tuple)

Modified by Gustavo Almeida — G8.13.T2 (cartorio-n8n).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.n8n_workflow import (
    N8nNode,
    N8nSettings,
    N8nWorkflow,
    is_strict_valid,
    validate_workflow_payload,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
WF_DIR = REPO_ROOT / "infra" / "n8n-workflows"


def _minimal_payload(**overrides: object) -> dict[str, object]:
    """Payload minimo valido (apenas campos required)."""
    base: dict[str, object] = {
        "name": "Test Workflow",
        "nodes": [],
        "connections": {},
        "active": False,
        "settings": {},
    }
    base.update(overrides)
    return base


def _minimal_node(**overrides: object) -> dict[str, object]:
    """Node minimo valido."""
    base: dict[str, object] = {
        "id": "node-1",
        "name": "Init",
        "type": "n8n-nodes-base.set",
        "typeVersion": 1,
        "position": [200, 200],
        "parameters": {},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Validacao basica
# ---------------------------------------------------------------------------


class TestN8nWorkflowValid:
    """Payloads canonicos passam."""

    def test_minimal_workflow_passes(self) -> None:
        wf = N8nWorkflow.model_validate(_minimal_payload())
        assert wf.name == "Test Workflow"
        assert wf.active is False
        assert wf.nodes == []
        assert wf.connections == {}
        assert wf.settings.timezone is None  # default None

    def test_valid_workflow_with_nodes_passes(self) -> None:
        payload = _minimal_payload(nodes=[_minimal_node()])
        wf = N8nWorkflow.model_validate(payload)
        assert len(wf.nodes) == 1
        assert wf.nodes[0].name == "Init"
        assert wf.nodes[0].typeVersion == 1
        assert wf.nodes[0].position == [200, 200]

    def test_node_typeVersion_accepts_float(self) -> None:
        # N8N moderno exporta typeVersion=3.4 (float)
        node = N8nNode.model_validate(_minimal_node(typeVersion=3.4))
        assert node.typeVersion == 3.4

    def test_settings_timezone_iana_valid(self) -> None:
        for tz in ("America/Sao_Paulo", "UTC", "Europe/Lisbon", "America/New_York"):
            wf = N8nWorkflow.model_validate(_minimal_payload(settings={"timezone": tz}))
            assert wf.settings.timezone == tz


# ---------------------------------------------------------------------------
# 2. Erros de campos required / tipos
# ---------------------------------------------------------------------------


class TestN8nWorkflowErrors:
    """Violacoes sao detectadas com mensagem clara."""

    def test_missing_required_name_fails(self) -> None:
        payload = _minimal_payload()
        del payload["name"]
        with pytest.raises(ValidationError) as exc_info:
            N8nWorkflow.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_empty_name_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            N8nWorkflow.model_validate(_minimal_payload(name=""))
        errors = exc_info.value.errors()
        assert any("at least 1 character" in e["msg"] for e in errors)

    def test_name_too_long_fails(self) -> None:
        with pytest.raises(ValidationError):
            N8nWorkflow.model_validate(_minimal_payload(name="x" * 201))

    def test_node_parameters_must_be_dict(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            N8nNode.model_validate(_minimal_node(parameters="not a dict"))  # type: ignore[arg-type]
        errors = exc_info.value.errors()
        assert any("parameters" in str(e["loc"]) for e in errors)

    def test_node_position_wrong_length_fails(self) -> None:
        with pytest.raises(ValidationError):
            N8nNode.model_validate(_minimal_node(position=[100]))  # 1 elem only
        with pytest.raises(ValidationError):
            N8nNode.model_validate(_minimal_node(position=[100, 200, 300]))

    def test_node_missing_type_fails(self) -> None:
        node_data = _minimal_node()
        del node_data["type"]
        with pytest.raises(ValidationError):
            N8nNode.model_validate(node_data)


# ---------------------------------------------------------------------------
# 3. extra="forbid" — forward-compat blocked
# ---------------------------------------------------------------------------


class TestExtraFieldsRejected:
    """Campos nao catalogados sao rejeitados (HITL by design)."""

    def test_workflow_extra_field_rejected(self) -> None:
        payload = _minimal_payload(brand_new_field="surprise")
        with pytest.raises(ValidationError) as exc_info:
            N8nWorkflow.model_validate(payload)
        assert any("brand_new_field" in str(e["loc"]) for e in exc_info.value.errors())

    def test_node_extra_field_rejected(self) -> None:
        node = _minimal_node(magic_extra="oops")
        with pytest.raises(ValidationError) as exc_info:
            N8nNode.model_validate(node)
        assert any("magic_extra" in str(e["loc"]) for e in exc_info.value.errors())

    def test_settings_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            N8nSettings.model_validate({"mystery": 42})
        assert any("mystery" in str(e["loc"]) for e in exc_info.value.errors())


# ---------------------------------------------------------------------------
# 4. Timezone IANA
# ---------------------------------------------------------------------------


class TestTimezoneValidation:
    """Timezone precisa ser IANA valida (zoneinfo stdlib)."""

    def test_invalid_timezone_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            N8nSettings.model_validate({"timezone": "Fake/Zone"})
        assert "IANA" in str(exc_info.value.errors()[0]["msg"])

    def test_empty_string_timezone_fails(self) -> None:
        # ZoneInfo("") levanta ZoneInfoNotFoundError
        with pytest.raises(ValidationError):
            N8nSettings.model_validate({"timezone": ""})

    def test_none_timezone_passes(self) -> None:
        s = N8nSettings.model_validate({})
        assert s.timezone is None


# ---------------------------------------------------------------------------
# 5. LGPD Art. 46 — anti-PII em identifiers
# ---------------------------------------------------------------------------


class TestLgpdPiiDetection:
    """PII em node name/tag/description eh bloqueada."""

    def test_cpf_in_node_name_rejected(self) -> None:
        node = _minimal_node(name="Customer CPF 123.456.789-00 node")
        with pytest.raises(ValidationError) as exc_info:
            N8nNode.model_validate(node)
        assert "PII" in str(exc_info.value.errors()[0]["msg"])

    def test_cnpj_in_node_name_rejected(self) -> None:
        node = _minimal_node(name="Empresa 12.345.678/0001-90")
        with pytest.raises(ValidationError):
            N8nNode.model_validate(node)

    def test_email_in_node_name_rejected(self) -> None:
        node = _minimal_node(name="Send to fulano@example.com")
        with pytest.raises(ValidationError):
            N8nNode.model_validate(node)

    def test_phone_in_node_name_rejected(self) -> None:
        node = _minimal_node(name="Call +55 (34) 99999-1234")
        with pytest.raises(ValidationError):
            N8nNode.model_validate(node)

    def test_pii_in_workflow_description_rejected(self) -> None:
        payload = _minimal_payload(description="Cliente CPF 111.222.333-44")
        with pytest.raises(ValidationError):
            N8nWorkflow.model_validate(payload)

    def test_pii_in_tag_rejected(self) -> None:
        payload = _minimal_payload(tags=["cpf-123.456.789-00"])
        with pytest.raises(ValidationError):
            N8nWorkflow.model_validate(payload)

    def test_safe_node_name_passes(self) -> None:
        node = N8nNode.model_validate(_minimal_node(name="Init Correlation"))
        assert node.name == "Init Correlation"


# ---------------------------------------------------------------------------
# 6. Helpers publicos
# ---------------------------------------------------------------------------


class TestHelpers:
    """Helpers de conveniência."""

    def test_is_strict_valid_true(self) -> None:
        assert is_strict_valid(_minimal_payload()) is True

    def test_is_strict_valid_false_on_missing_field(self) -> None:
        p = _minimal_payload()
        del p["name"]
        assert is_strict_valid(p) is False

    def test_is_strict_valid_false_on_extra_field(self) -> None:
        assert is_strict_valid(_minimal_payload(ghost=1)) is False

    def test_validate_workflow_payload_returns_model(self) -> None:
        wf = validate_workflow_payload(_minimal_payload())
        assert isinstance(wf, N8nWorkflow)


# ---------------------------------------------------------------------------
# 7. Real exports — garantia de compat (HONESTY GATE)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wf_filename",
    [
        "01-consulta-emolumento.json",
        "04-boas-vindas-lgpd.json",
        "08-audit-verify-diario.json",
        "31-telegram-listener.json",
        "36-chatwoot-telegram-sync.json",
        "evo-in.json",
    ],
)
def test_real_n8n_export_passes_strict_schema(wf_filename: str) -> None:
    """5+ JSONs reais do Wave 29 inventory passam strict.

    Se quebrar, ou (a) N8N adicionou campo canonico nao catalogado
    (atualizar schema) ou (b) export tem bug (reportar owner).
    """
    path = WF_DIR / wf_filename
    if not path.exists():
        pytest.skip(f"fixture ausente: {wf_filename}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    wf = N8nWorkflow.model_validate(payload)
    assert wf.name, f"{wf_filename} name vazio"
    assert isinstance(wf.nodes, list)
    for node in wf.nodes:
        assert node.id and node.name and node.type


def test_real_exports_batch_validation() -> None:
    """Todos os exports reais catalogados passam (gate de 5+ minimo).

    Assertion de sanidade: >=5 JSONs reais passam strict schema. Se
    algum falhar, o teste falha com a lista completa de erros.
    """
    if not WF_DIR.is_dir():
        pytest.skip(f"WF dir ausente: {WF_DIR}")
    failures: list[tuple[str, list[dict[str, object]]]] = []
    passed = 0
    for path in sorted(WF_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            N8nWorkflow.model_validate(payload)
            passed += 1
        except (ValidationError, json.JSONDecodeError) as exc:
            err_list = exc.errors() if isinstance(exc, ValidationError) else [{"msg": str(exc)}]
            failures.append((path.name, err_list))
    assert passed >= 5, (
        f"minimo 5 JSONs reais devem passar strict schema (passed={passed}, failed={len(failures)})"
    )
    # Reporta falhas sem bloquear — gate eh >=5 passes.
    if failures:
        summary = "\n".join(
            f"  - {name}: {errs[0].get('msg', '?')[:120]}" for name, errs in failures[:5]
        )
        pytest.fail(f"{len(failures)}/{passed + len(failures)} exports falharam strict:\n{summary}")
