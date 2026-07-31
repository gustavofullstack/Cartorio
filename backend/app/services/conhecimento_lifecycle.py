"""Máquina de estados fail-closed do bounded context ConhecimentoInstitucional.

Transições são explícitas e unidirecionais por padrão. Reprocessamento cria nova
versão (fora deste módulo); este módulo nunca muta histórico nem publica sozinho.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.models.conhecimento_institucional import EstadoConhecimento


class TransicaoConhecimentoInvalidaError(ValueError):
    """Tentativa de pular, reabrir ou reverter estado sem autorização explícita."""


# Grafo permitido. Chaves = estado atual; valores = destinos aceitos.
_TRANSICOES: Final[dict[str, frozenset[str]]] = {
    EstadoConhecimento.INGESTED: frozenset(
        {EstadoConhecimento.EXTRACTED, EstadoConhecimento.REJECTED}
    ),
    EstadoConhecimento.EXTRACTED: frozenset(
        {EstadoConhecimento.CLASSIFIED, EstadoConhecimento.REJECTED}
    ),
    EstadoConhecimento.CLASSIFIED: frozenset(
        {
            EstadoConhecimento.PENDING_HUMAN_VALIDATION,
            EstadoConhecimento.REJECTED,
        }
    ),
    EstadoConhecimento.PENDING_HUMAN_VALIDATION: frozenset(
        {
            EstadoConhecimento.APPROVED,
            EstadoConhecimento.REJECTED,
        }
    ),
    EstadoConhecimento.APPROVED: frozenset(
        {
            EstadoConhecimento.PUBLISHED,
            EstadoConhecimento.REJECTED,
            EstadoConhecimento.REVOKED,
        }
    ),
    EstadoConhecimento.PUBLISHED: frozenset(
        {
            EstadoConhecimento.SUPERSEDED,
            EstadoConhecimento.REVOKED,
        }
    ),
    EstadoConhecimento.SUPERSEDED: frozenset(),
    EstadoConhecimento.REJECTED: frozenset(),
    EstadoConhecimento.REVOKED: frozenset(),
}

# Estados a partir dos quais o BRAIN pode recuperar conteúdo automaticamente.
_CONSUMIVEIS: Final[frozenset[str]] = frozenset({EstadoConhecimento.PUBLISHED})

# Estados terminais — sem saída.
_TERMINAIS: Final[frozenset[str]] = frozenset(
    {
        EstadoConhecimento.SUPERSEDED,
        EstadoConhecimento.REJECTED,
        EstadoConhecimento.REVOKED,
    }
)


@dataclass(frozen=True)
class TransicaoRegistrada:
    """Resultado imutável de uma transição válida (para audit/trace)."""

    from_state: str
    to_state: str
    actor_id: str
    reason: str


def estados_permitidos() -> frozenset[str]:
    """Conjunto fechado de estados reconhecidos pelo contexto."""
    return frozenset(_TRANSICOES)


def e_consumivel(estado: str) -> bool:
    """Somente ``PUBLISHED`` é elegível para recuperação automática no BRAIN."""
    return estado in _CONSUMIVEIS


def e_terminal(estado: str) -> bool:
    """Estados terminais não admitem nova transição."""
    return estado in _TERMINAIS


def destinos_permitidos(estado_atual: str) -> frozenset[str]:
    """Lista destinos válidos a partir do estado atual (vazio se terminal/desconhecido)."""
    if estado_atual not in _TRANSICOES:
        raise TransicaoConhecimentoInvalidaError(f"estado desconhecido: {estado_atual}")
    return _TRANSICOES[estado_atual]


def pode_transicionar(estado_atual: str, estado_destino: str) -> bool:
    """Verifica se a aresta existe no grafo fail-closed."""
    if estado_atual not in _TRANSICOES:
        return False
    return estado_destino in _TRANSICOES[estado_atual]


def transicionar(
    estado_atual: str,
    estado_destino: str,
    *,
    actor_id: str,
    reason: str,
) -> TransicaoRegistrada:
    """Aplica a transição se e somente se for permitida.

    Exige ``actor_id`` e ``reason`` não vazios para rastreabilidade HITL/audit.
    Não persiste nada — o chamador grava o resultado e o evento de audit.
    """
    if not actor_id or not actor_id.strip():
        raise TransicaoConhecimentoInvalidaError("actor_id obrigatório")
    if not reason or not reason.strip():
        raise TransicaoConhecimentoInvalidaError("reason obrigatório")
    if estado_atual not in _TRANSICOES:
        raise TransicaoConhecimentoInvalidaError(f"estado desconhecido: {estado_atual}")
    if estado_destino not in estados_permitidos():
        raise TransicaoConhecimentoInvalidaError(f"destino desconhecido: {estado_destino}")
    if not pode_transicionar(estado_atual, estado_destino):
        raise TransicaoConhecimentoInvalidaError(
            f"transição proibida: {estado_atual} -> {estado_destino}"
        )
    return TransicaoRegistrada(
        from_state=estado_atual,
        to_state=estado_destino,
        actor_id=actor_id.strip(),
        reason=reason.strip(),
    )


def exigir_publicacao_para_consumo(estado: str) -> None:
    """Barreira fail-closed antes de qualquer recuperação no BRAIN."""
    if not e_consumivel(estado):
        raise TransicaoConhecimentoInvalidaError(
            "somente conhecimento PUBLISHED é consumível automaticamente"
        )


__all__ = [
    "TransicaoConhecimentoInvalidaError",
    "TransicaoRegistrada",
    "destinos_permitidos",
    "e_consumivel",
    "e_terminal",
    "estados_permitidos",
    "exigir_publicacao_para_consumo",
    "pode_transicionar",
    "transicionar",
]
