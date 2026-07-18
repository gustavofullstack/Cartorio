"""G8.20.T2 — valida workflow template-orcamento-escritura.json (estrutura + LGPD).

Cobre:
1. test_template_json_is_valid_n8n_workflow: passa n8n_wf_inventory strict
2. test_template_nodes_count: >=5 nodes (template declara 6)
3. test_template_draft_flag_present: Format Response marca draft=true
4. test_template_audit_node_present: LGPD Art. 37 com endpoint /audit
5. test_template_no_pii_in_static_json: regex LGPD anti-PII em todo JSON

Nao chama N8N live. Garante que o template importado segue o schema strict.

Modified by Gustavo Almeida — Wave 49 (G8.20.T2 cartorio-n8n).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / "infra" / "n8n-workflows" / "template-orcamento-escritura.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def payload() -> dict[str, object]:
    """Carrega o JSON do template-orcamento-escritura."""
    return json.loads(WF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_text() -> str:
    """Texto cru do JSON para grep de PII."""
    return WF.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def nodes(payload: dict[str, object]) -> list[dict[str, object]]:
    return list(payload.get("nodes") or [])


# ---------------------------------------------------------------------------
# 1. Schema strict (Pydantic v2 via app.schemas.n8n_workflow)
# ---------------------------------------------------------------------------


def test_template_json_is_valid_n8n_workflow(payload: dict[str, object]) -> None:
    """Template passa schema strict N8nWorkflow do Pydantic v2."""
    try:
        from app.schemas.n8n_workflow import N8nWorkflow
    except ImportError:  # pragma: no cover — schema em backend/app
        pytest.skip("app.schemas.n8n_workflow nao disponivel neste contexto")

    wf = N8nWorkflow.model_validate(payload)
    assert wf.name == "WF-TEMPLATE Orcamento Escritura"
    assert wf.active is False  # template exportado inativo ate revisao
    assert "emolumento" in wf.tags or any(
        isinstance(t, dict) and t.get("name") == "emolumento" for t in wf.tags
    )


# ---------------------------------------------------------------------------
# 2. Count de nodes (>=5; template declara 6)
# ---------------------------------------------------------------------------


def test_template_nodes_count(nodes: list[dict[str, object]]) -> None:
    """Workflow tem >=5 nodes (otimizacao G8.20.T2 mantem 6 nodes)."""
    assert len(nodes) >= 5, f"template deve ter >=5 nodes (atual: {len(nodes)})"


def test_template_node_names_distinct(nodes: list[dict[str, object]]) -> None:
    """Nomes de nodes sao unicos (evita routing ambíguo)."""
    names = [n["name"] for n in nodes]
    assert len(names) == len(set(names)), f"nodes duplicados: {names}"


# ---------------------------------------------------------------------------
# 3. Flag draft=true no Format Response (HITL by design)
# ---------------------------------------------------------------------------


def test_template_draft_flag_present(payload: dict[str, object]) -> None:
    """Node Format Response DRAFT produz { draft: true } — HITL escrevente valida."""
    nodes = list(payload.get("nodes") or [])
    format_node = next(
        (n for n in nodes if n.get("name") == "Format Response DRAFT"),
        None,
    )
    assert format_node is not None, "node 'Format Response DRAFT' ausente"
    js_code = str(format_node["parameters"]["jsCode"])
    assert "draft: true" in js_code or "draft:true" in js_code, (
        f"Format Response deve setar draft:true para HITL (got: {js_code[:200]!r})"
    )
    assert "HITL" in js_code, "comentario HITL obrigatorio no codigo"


def test_template_returns_draft_to_bot_layer(payload: dict[str, object]) -> None:
    """Format Response expoe campos `total`, `validade_ate`, `referencia`."""
    nodes = list(payload.get("nodes") or [])
    format_node = next(n for n in nodes if n.get("name") == "Format Response DRAFT")
    js_code = str(format_node["parameters"]["jsCode"])
    for must in ("total", "validade_ate", "referencia"):
        assert must in js_code, f"campo {must!r} faltando no Format Response"


# ---------------------------------------------------------------------------
# 4. Node Audit LGPD Art. 37 com endpoint /audit
# ---------------------------------------------------------------------------


def test_template_audit_node_present(nodes: list[dict[str, object]]) -> None:
    """Workflow inclui node 'Audit LGPD Art.37' apontando para /audit."""
    audit = next(
        (n for n in nodes if n.get("name") == "Audit LGPD Art.37"),
        None,
    )
    assert audit is not None, "node 'Audit LGPD Art.37' ausente"
    params = audit.get("parameters") or {}
    url = str(params.get("url") or "")
    assert "/api/v1/audit" in url, f"audit node URL deve apontar /api/v1/audit (got: {url})"
    assert str(params.get("method") or "").upper() == "POST"


def test_template_audit_sends_protocolo_draft(nodes: list[dict[str, object]]) -> None:
    """Audit payload inclui protocolo=DRAFT (HITL placeholder)."""
    audit = next(n for n in nodes if n.get("name") == "Audit LGPD Art.37")
    body_params = (audit["parameters"].get("bodyParameters") or {}).get("parameters") or []
    names = {p["name"]: p["value"] for p in body_params}
    assert names.get("action") == "orcamento_draft"
    assert names.get("entity") == "emolumento"
    assert names.get("protocolo") == "DRAFT"


def test_template_connections_chain_linear(payload: dict[str, object]) -> None:
    """Conexoes formam chain linear: Webhook→Validar→Calc→Format→Audit."""
    conn = payload.get("connections") or {}
    expected = [
        ("Webhook", "Validar"),
        ("Validar", "Calc Emolumento"),
        ("Calc Emolumento", "Format Response DRAFT"),
        ("Format Response DRAFT", "Audit LGPD Art.37"),
    ]
    for src, dst in expected:
        assert src in conn, f"{src!r} nao tem conexao definida"
        next_nodes = []
        for branch in conn[src].get("main") or []:
            for hop in branch:
                next_nodes.append(hop.get("node"))
        assert dst in next_nodes, f"{src!r} nao conecta em {dst!r} (got: {next_nodes})"


# ---------------------------------------------------------------------------
# 5. No PII in static JSON (LGPD Art. 46)
# ---------------------------------------------------------------------------


_PII_PATTERNS = (
    # CPF: 11 digitos pontuado ou nao
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    # CNPJ
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b"),
    # Email
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
)


@pytest.mark.parametrize("pat", _PII_PATTERNS)
def test_template_no_pii_in_static_json(raw_text: str, pat: re.Pattern[str]) -> None:
    """Nenhum CPF/CNPJ/email presente no JSON estatico (LGPD Art. 46)."""
    matches = pat.findall(raw_text)
    assert not matches, f"PII detectada no template: {matches}"


def test_template_no_personal_names_in_node_names(nodes: list[dict[str, object]]) -> None:
    """Node names nao carregam nomes pessoais — apenas identificadores semanticos."""
    personal_keywords = {"cliente", "paciente", "usuario", "senha", "cpf", "rg"}
    for n in nodes:
        name = str(n.get("name") or "").lower()
        for kw in personal_keywords:
            assert kw not in name, f"node {name!r} parece carregar dado pessoal ({kw})"
