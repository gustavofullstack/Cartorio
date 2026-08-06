"""Validação humana (HITL) e publicação do ConhecimentoInstitucional.

Nenhuma decisão é implícita. Publicação exige APPROVED prévio. Revogação e
supersede preservam histórico (append-only no nível de aplicação).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from app.models.conhecimento_institucional import DecisaoValidacao, EstadoConhecimento
from app.services.pii import detect_only
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
_HUMAN_ACTOR: Final[re.Pattern[str]] = re.compile(
    r"^human:(?:escrevente|tabeliao|dpo|lgpd)(?::[A-Za-z0-9._-]{1,64})?$"
)
_PATH_OR_LINK: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:\b(?:https?|ftp)://|(?:^|\s)(?:/|\.\./|~/)|[A-Za-z]:[\\/])"
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


def _validar_ator_humano(actor_id: str, *, papel_lgpd: bool = False) -> str:
    actor = actor_id.strip()
    if _HUMAN_ACTOR.fullmatch(actor) is None:
        raise ValidacaoConhecimentoError("ator humano autorizado obrigatório")
    if papel_lgpd and not actor.startswith(("human:dpo", "human:lgpd")):
        raise ValidacaoConhecimentoError("sign-off deve ser de DPO/LGPD")
    return actor


def _validar_texto_evidencia(value: str, field_name: str) -> str:
    text = value.strip()
    if len(text) < 5 or len(text) > 500:
        raise ValidacaoConhecimentoError(f"{field_name} deve ter entre 5 e 500 caracteres")
    if detect_only(text) or _PATH_OR_LINK.search(text):
        raise ValidacaoConhecimentoError(f"{field_name} contém dado não permitido")
    return text


def _validar_aprovacao_versionada(
    decisao: DecisaoHitl,
    *,
    version_id: int,
    papel_lgpd: bool = False,
) -> None:
    if (
        decisao.target_kind != "VERSION"
        or decisao.target_id != version_id
        or decisao.decision != DecisaoValidacao.APPROVED
        or decisao.resulting_state != EstadoConhecimento.APPROVED
    ):
        raise ValidacaoConhecimentoError("decisão APPROVED da mesma versão é obrigatória")
    _validar_ator_humano(decisao.reviewer_id, papel_lgpd=papel_lgpd)


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
    reviewer = _validar_ator_humano(reviewer_id)
    rationale_segura = _validar_texto_evidencia(rationale, "rationale")

    destino = (
        EstadoConhecimento.APPROVED
        if decision == DecisaoValidacao.APPROVED
        else EstadoConhecimento.REJECTED
    )
    try:
        transicao = transicionar(
            estado_atual,
            destino,
            actor_id=reviewer,
            reason=rationale_segura,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    idem = sha256(
        f"{target_kind}:{target_id}:{decision}:{reviewer}:{rationale_segura}".encode()
    ).hexdigest()
    return DecisaoHitl(
        target_kind=target_kind,
        target_id=target_id,
        decision=decision,
        reviewer_id=reviewer,
        rationale=rationale_segura,
        resulting_state=transicao.to_state,
        idempotency_key=idem,
    )


def publicar_versao(
    *,
    estado_atual: str,
    version_id: int,
    actor_id: str,
    reason: str,
    approval: DecisaoHitl,
    lgpd_signoff: DecisaoHitl,
    t4_authorized: bool = False,
    environment: str = "disabled",
) -> PublicacaoResultado:
    """Promove somente em integração isolada T4, com dupla decisão humana.

    Produção/canais live não fazem parte deste contrato offline. Um adaptador
    operacional futuro deverá verificar RBAC e persistência antes de chamar.
    """
    if version_id <= 0:
        raise ValidacaoConhecimentoError("version_id deve ser positivo")
    if not t4_authorized or environment != "isolated":
        raise ValidacaoConhecimentoError("publicação bloqueada sem gate T4 isolado")
    actor = _validar_ator_humano(actor_id)
    reason_safe = _validar_texto_evidencia(reason, "reason")
    _validar_aprovacao_versionada(approval, version_id=version_id)
    _validar_aprovacao_versionada(lgpd_signoff, version_id=version_id, papel_lgpd=True)
    try:
        transicao = transicionar(
            estado_atual,
            EstadoConhecimento.PUBLISHED,
            actor_id=actor,
            reason=reason_safe,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    reference = sha256(
        f"publish:{version_id}:{actor}:{reason_safe}:"
        f"{approval.idempotency_key}:{lgpd_signoff.idempotency_key}".encode()
    ).hexdigest()[:32]
    return PublicacaoResultado(
        action="PUBLISH",
        from_state=transicao.from_state,
        to_state=transicao.to_state,
        actor_id=actor,
        publication_reference=f"pub_{reference}",
        reason=reason_safe,
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
    actor = _validar_ator_humano(actor_id)
    reason_safe = _validar_texto_evidencia(reason, "reason")
    try:
        transicao = transicionar(
            estado_atual,
            EstadoConhecimento.REVOKED,
            actor_id=actor,
            reason=reason_safe,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    reference = sha256(
        f"revoke:{version_id}:{actor}:{reason_safe}".encode()
    ).hexdigest()[:32]
    return PublicacaoResultado(
        action="REVOKE",
        from_state=transicao.from_state,
        to_state=transicao.to_state,
        actor_id=actor,
        publication_reference=f"rev_{reference}",
        reason=reason_safe,
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
    actor = _validar_ator_humano(actor_id)
    reason_safe = _validar_texto_evidencia(reason, "reason")
    try:
        transicao = transicionar(
            estado_atual,
            EstadoConhecimento.SUPERSEDED,
            actor_id=actor,
            reason=reason_safe,
        )
    except TransicaoConhecimentoInvalidaError as error:
        raise ValidacaoConhecimentoError(str(error)) from error

    reference = sha256(
        f"supersede:{version_id}:{actor}:{reason_safe}".encode()
    ).hexdigest()[:32]
    return PublicacaoResultado(
        action="SUPERSEDE",
        from_state=transicao.from_state,
        to_state=transicao.to_state,
        actor_id=actor,
        publication_reference=f"sup_{reference}",
        reason=reason_safe,
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
