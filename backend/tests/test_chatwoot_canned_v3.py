"""Tests para chatwoot_canned_responses_v3 (G6.B.T2 - 10 respostas adicionais)."""

from __future__ import annotations

from app.services.chatwoot_canned_responses_v3 import (
    V3_CANNED_RESPONSES,
    get_v3_short_codes,
)


def test_v3_tem_exatamente_10_respostas() -> None:
    """v3 adiciona exatamente 10 respostas."""
    assert len(V3_CANNED_RESPONSES) == 10


def test_v3_short_codes_unicos() -> None:
    """Todos short codes v3 sao unicos entre si."""
    codes = [r.short_code for r in V3_CANNED_RESPONSES]
    assert len(codes) == len(set(codes))


def test_v3_short_codes_distintos_v2() -> None:
    """Nenhum short code v3 colide com v2 (ja existentes)."""
    from app.services.chatwoot_canned_responses import get_all_short_codes

    v2_codes = set(get_all_short_codes())
    v3_codes = set(get_v3_short_codes())
    overlap = v2_codes & v3_codes
    assert len(overlap) == 0, f"Colisao v2 vs v3: {overlap}"


def test_v3_tags_presentes() -> None:
    """Cada resposta tem pelo menos 1 tag."""
    for r in V3_CANNED_RESPONSES:
        assert len(r.tags) >= 1, f"{r.short_code} sem tags"


def test_v3_content_nao_vazio() -> None:
    """Cada resposta tem content (>= 30 chars)."""
    for r in V3_CANNED_RESPONSES:
        assert len(r.content) >= 30, f"{r.short_code} content muito curto: {len(r.content)}"


def test_v3_categorias_presentes() -> None:
    """Categorias principais estao presentes."""
    short_codes = set(get_v3_short_codes())
    expected_categories = {
        "2via_instrucoes",
        "2via_pronta",
        "2via_docs",
        "protesto_consulta",
        "protesto_baixa",
        "protesto_cancel",
        "divorcio_consensual",
        "inventario_extra",
        "averbacao_emancipacao",
        "averbacao_casamento",
    }
    assert short_codes == expected_categories


def test_v3_handoff_marcado_quando_requer_humano() -> None:
    """Canned que requer handoff humano tem tag 'handoff'."""
    handoff_codes = {"protesto_cancel", "inventario_extra"}
    for r in V3_CANNED_RESPONSES:
        if r.short_code in handoff_codes:
            assert "handoff" in r.tags, f"{r.short_code} requer humano mas nao tem tag 'handoff'"


def test_v3_protesto_cancel_avisa_handoff() -> None:
    """Canned protesto_cancel EXPLICITAMENTE avisa que NAO pode ser feito pelo bot."""
    cancel = next(r for r in V3_CANNED_RESPONSES if r.short_code == "protesto_cancel")
    assert "bot" in cancel.content.lower()
    assert "humano" in cancel.content.lower() or "escrevente" in cancel.content.lower()
