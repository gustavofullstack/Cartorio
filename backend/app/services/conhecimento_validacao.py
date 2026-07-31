"""Validação humana (HITL) e publicação do ConhecimentoInstitucional.

Nenhuma decisão é implícita. Publicação exige APPROVED prévio. Revogação e
supersede preservam histórico (append-only no nível de aplicação).
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from app.models.conhecimento_institucional import DecisaoValidacao, EstadoConhecimento
from app.services.conhecimento_lifecycle import (
    TransicaoConhecimentoInvalidaError,
    transicionar,
)

_TARGET_KINDS: Final[frozenset[str]] = frozenset(
    {
        "VERSION",
        "UNIT",
        "FACT",
        "CALCULATION_RULE",
        "DOCUMENT_TYPE",
        "CLASSIFICATION_RESULT",
    }
)


@dataclass(frozen=True)
class DecisaoHitl:
    """Decisão humana rastreável, pronta para persistência/audit."""

    target_kind: str
    target_id: int
    decision: str
    reviewer_id: str
    rationale: str
    resulting_state: str
    idempotency_key: str

    def as_dict(self) -> dict[str, object]:
        return {
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "decision": self.decision,
            "reviewer_id": self.reviewer_id,
            "rationale": self.rationale,
            "resulting_state": self.resulting_state,
            "idempotency_key": self.idempotency_key,
        }


@dataclass(frozen=True)
class PublicacaoResultado:
    """Resultado de promoção/revogação/supersede."""

    action: str
    from_state: str
    to_state: str
    actor_id: str
    publication_reference: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor_id": self.actor_id,
            "publication_reference": self.publication_reference,
            "reason": self.reason,
        }


class ValidacaoConhecimentoError(ValueError):
    """Falha fail-closed em validação ou publicação."""


def registrar_decisao_humana(
    *,
    estado_atual: str,
    target_kind: str,
    target_id: int,
    decision: str,
    reviewer_id: str,
    rationale: str,
) -> DecisaoHitl:
    """Registra APPROVED/REJECTED a partir de PENDING_HUMAN_VALIDATION."""
    if target_kind not in _TARGET_KINDS:
        raise ValidacaoConhecimentoError(f"target_kind inválido: {target_kind}")
    if target_id <= 0:
        raise ValidacaoConhecimentoError("target_id deve ser positivo")
    if decision not in {DecisaoValidacao.APPROVED, DecisaoValidacao.REJECTED}:
        raise ValidacaoConhecimentoError("decision deve ser APPROVED ou REJECTED")
    if not reviewer_id or not reviewer_id.strip():
        raise ValidacaoConhecimentoError("reviewer_id obrigatório")
    if not rationale or len(rationale.strip()) < 5:
        raise ValidacaoConhecimentoError("rationale mínimo de 5 caracteres")

    destino = (
        EstadoConhecimento.APPROVED
        if decision == DecisaoValidacao.APPROVED
        else EstadoConhecimento.REJECTED
    )
    try:
        transicao = transicionar(
            estado_atual,
            destino,
            actor_id=reviewer_id,
            reason=rationale,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    idem = sha256(
        f"{target_kind}:{target_id}:{decision}:{reviewer_id.strip()}:{rationale.strip()}".encode()
    ).hexdigest()
    return DecisaoHitl(
        target_kind=target_kind,
        target_id=target_id,
        decision=decision,
        reviewer_id=reviewer_id.strip(),
        rationale=rationale.strip(),
        resulting_state=transicao.to_state,
        idempotency_key=idem,
    )


def publicar_versao(
    *,
    estado_atual: str,
    version_id: int,
    actor_id: str,
    reason: str,
) -> PublicacaoResultado:
    """Promove APPROVED → PUBLISHED. Única via de elegibilidade no BRAIN."""
    if version_id <= 0:
        raise ValidacaoConhecimentoError("version_id deve ser positivo")
    try:
        transicao = transicionar(
            estado_atual,
            EstadoConhecimento.PUBLISHED,
            actor_id=actor_id,
            reason=reason,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    reference = sha256(
        f"publish:{version_id}:{actor_id.strip()}:{reason.strip()}".encode()
    ).hexdigest()[:32]
    return PublicacaoResultado(
        action="PUBLISH",
        from_state=transicao.from_state,
        to_state=transicao.to_state,
        actor_id=actor_id.strip(),
        publication_reference=f"pub_{reference}",
        reason=reason.strip(),
    )


def revogar_publicacao(
    *,
    estado_atual: str,
    version_id: int,
    actor_id: str,
    reason: str,
) -> PublicacaoResultado:
    """Marca PUBLISHED/APPROVED → REVOKED, removendo elegibilidade imediata."""
    if version_id <= 0:
        raise ValidacaoConhecimentoError("version_id deve ser positivo")
    try:
        transicao = transicionar(
            estado_atual,
            EstadoConhecimento.REVOKED,
            actor_id=actor_id,
            reason=reason,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    reference = sha256(
        f"revoke:{version_id}:{actor_id.strip()}:{reason.strip()}".encode()
    ).hexdigest()[:32]
    return PublicacaoResultado(
        action="REVOKE",
        from_state=transicao.from_state,
        to_state=transicao.to_state,
        actor_id=actor_id.strip(),
        publication_reference=f"rev_{reference}",
        reason=reason.strip(),
    )


def superseder_publicacao(
    *,
    estado_atual: str,
    version_id: int,
    actor_id: str,
    reason: str,
) -> PublicacaoResultado:
    """PUBLISHED → SUPERSEDED quando nova versão aprovada a substitui."""
    if version_id <= 0:
        raise ValidacaoConhecimentoError("version_id deve ser positivo")
    try:
        transicao = transicionar(
            estado_atual,
            EstadoConhecimento.SUPERSEDED,
            actor_id=actor_id,
            reason=reason,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    reference = sha256(
        f"supersede:{version_id}:{actor_id.strip()}:{reason.strip()}".encode()
    ).hexdigest()[:32]
    return PublicacaoResultado(
        action="SUPERSEDE",
        from_state=transicao.from_state,
        to_state=transicao.to_state,
        actor_id=actor_id.strip(),
        publication_reference=f"sup_{reference}",
        reason=reason.strip(),
    )


__all__ = [
    "DecisaoHitl",
    "PublicacaoResultado",
    "ValidacaoConhecimentoError",
    "publicar_versao",
    "registrar_decisao_humana",
    "revogar_publicacao",
    "superseder_publicacao",
]
