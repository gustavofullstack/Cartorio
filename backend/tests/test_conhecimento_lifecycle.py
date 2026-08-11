"""Contrato da máquina de estados ConhecimentoInstitucional (fail-closed)."""

from __future__ import annotations

import pytest

from app.models.conhecimento_institucional import EstadoConhecimento
from app.services.conhecimento_lifecycle import (
    TransicaoConhecimentoInvalidaError,
    destinos_permitidos,
    e_consumivel,
    e_terminal,
    exigir_publicacao_para_consumo,
    pode_transicionar,
    transicionar,
)


def test_somente_published_e_consumivel() -> None:
    assert e_consumivel(EstadoConhecimento.PUBLISHED) is True
    assert e_consumivel(EstadoConhecimento.APPROVED) is False
    assert e_consumivel(EstadoConhecimento.CLASSIFIED) is False


def test_fluxo_feliz_ate_published() -> None:
    estado = EstadoConhecimento.INGESTED
    for destino in (
        EstadoConhecimento.EXTRACTED,
        EstadoConhecimento.CLASSIFIED,
        EstadoConhecimento.PENDING_HUMAN_VALIDATION,
        EstadoConhecimento.APPROVED,
        EstadoConhecimento.PUBLISHED,
    ):
        tr = transicionar(estado, destino, actor_id="human:escrevente", reason="avanco controlado")
        assert tr.to_state == destino
        estado = destino
    assert e_consumivel(estado) is True


def test_proibe_pular_hitl() -> None:
    with pytest.raises(TransicaoConhecimentoInvalidaError):
        transicionar(
            EstadoConhecimento.CLASSIFIED,
            EstadoConhecimento.PUBLISHED,
            actor_id="pipeline",
            reason="tentativa ilegal",
        )


def test_proibe_reabrir_terminal() -> None:
    assert e_terminal(EstadoConhecimento.REJECTED) is True
    assert destinos_permitidos(EstadoConhecimento.REJECTED) == frozenset()
    with pytest.raises(TransicaoConhecimentoInvalidaError):
        transicionar(
            EstadoConhecimento.REJECTED,
            EstadoConhecimento.APPROVED,
            actor_id="human",
            reason="reabrir",
        )


def test_revogacao_remove_consumo() -> None:
    tr = transicionar(
        EstadoConhecimento.PUBLISHED,
        EstadoConhecimento.REVOKED,
        actor_id="human:dpo",
        reason="conteudo desatualizado",
    )
    assert tr.to_state == EstadoConhecimento.REVOKED
    assert e_consumivel(tr.to_state) is False
    with pytest.raises(TransicaoConhecimentoInvalidaError):
        exigir_publicacao_para_consumo(tr.to_state)


def test_exige_actor_e_reason() -> None:
    with pytest.raises(TransicaoConhecimentoInvalidaError):
        transicionar(
            EstadoConhecimento.INGESTED,
            EstadoConhecimento.EXTRACTED,
            actor_id="",
            reason="ok",
        )
    with pytest.raises(TransicaoConhecimentoInvalidaError):
        transicionar(
            EstadoConhecimento.INGESTED,
            EstadoConhecimento.EXTRACTED,
            actor_id="a",
            reason="",
        )


def test_pode_transicionar_matriz() -> None:
    assert pode_transicionar(EstadoConhecimento.APPROVED, EstadoConhecimento.PUBLISHED)
    assert not pode_transicionar(EstadoConhecimento.INGESTED, EstadoConhecimento.PUBLISHED)
