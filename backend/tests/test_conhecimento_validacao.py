"""HITL + publicação fail-closed do ConhecimentoInstitucional."""

from __future__ import annotations

import pytest

from app.models.conhecimento_institucional import DecisaoValidacao, EstadoConhecimento
from app.services.conhecimento_validacao import (
    ValidacaoConhecimentoError,
    publicar_versao,
    registrar_decisao_humana,
    revogar_publicacao,
    superseder_publicacao,
)


def test_hitl_aprova_a_partir_de_pending() -> None:
    decisao = registrar_decisao_humana(
        estado_atual=EstadoConhecimento.PENDING_HUMAN_VALIDATION,
        target_kind="VERSION",
        target_id=1,
        decision=DecisaoValidacao.APPROVED,
        reviewer_id="human:escrevente",
        rationale="conteudo institucional revisado",
    )
    assert decisao.resulting_state == EstadoConhecimento.APPROVED
    assert len(decisao.idempotency_key) == 64


def test_hitl_rejeita() -> None:
    decisao = registrar_decisao_humana(
        estado_atual=EstadoConhecimento.PENDING_HUMAN_VALIDATION,
        target_kind="CLASSIFICATION_RESULT",
        target_id=9,
        decision=DecisaoValidacao.REJECTED,
        reviewer_id="human:dpo",
        rationale="classificacao incorreta",
    )
    assert decisao.resulting_state == EstadoConhecimento.REJECTED


def test_publicacao_exige_approved() -> None:
    with pytest.raises(ValidacaoConhecimentoError):
        publicar_versao(
            estado_atual=EstadoConhecimento.PENDING_HUMAN_VALIDATION,
            version_id=1,
            actor_id="human:escrevente",
            reason="publicar cedo demais",
        )


def test_publicar_e_revogar() -> None:
    pub = publicar_versao(
        estado_atual=EstadoConhecimento.APPROVED,
        version_id=42,
        actor_id="human:tabeliao",
        reason="aprovado para consulta interna",
    )
    assert pub.to_state == EstadoConhecimento.PUBLISHED
    assert pub.publication_reference.startswith("pub_")

    rev = revogar_publicacao(
        estado_atual=EstadoConhecimento.PUBLISHED,
        version_id=42,
        actor_id="human:dpo",
        reason="norma revogada",
    )
    assert rev.to_state == EstadoConhecimento.REVOKED


def test_supersede() -> None:
    result = superseder_publicacao(
        estado_atual=EstadoConhecimento.PUBLISHED,
        version_id=7,
        actor_id="human:tabeliao",
        reason="substituido por versao 2",
    )
    assert result.action == "SUPERSEDE"
    assert result.to_state == EstadoConhecimento.SUPERSEDED


def test_rationale_curto_falha() -> None:
    with pytest.raises(ValidacaoConhecimentoError):
        registrar_decisao_humana(
            estado_atual=EstadoConhecimento.PENDING_HUMAN_VALIDATION,
            target_kind="VERSION",
            target_id=1,
            decision=DecisaoValidacao.APPROVED,
            reviewer_id="human",
            rationale="ok",
        )
