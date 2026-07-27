"""Ciclo de vida do catalogo versionado de emolumentos (Fase 1).

Spec: docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md.

Regras P0:
- O agente so le itens PUBLISHED cuja vigencia contenha a data da consulta.
  Ausencia ou expiracao retornam None -> caller responde HITL, NUNCA preco
  inventado.
- Uma versao anterior NUNCA e sobrescrita: ao promover uma nova captura, a
  PUBLISHED anterior (e seus itens) vira SUPERSEDED.
- Toda promocao grava entrada no audit log append-only (AuditService.log).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, NotRequired, TypedDict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.emolumento_catalogo import EmolumentoItem, EstadoEmolumento, FonteCaptura
from app.services.audit import AuditService


class CatalogoNaoEncontradoError(ValueError):
    """Captura inexistente no catalogo."""


class EstadoInvalidoError(ValueError):
    """Transicao de estado invalida no ciclo de vida do dado."""


class ItemExtraido(TypedDict):
    """Item extraido da fonte oficial, entrada de ``registrar_extracao``."""

    tipo_ato: str
    item_portaria: str
    ato: str
    emolumentos: Decimal
    tfj: Decimal
    valor_final: Decimal
    componentes: NotRequired[dict[str, Any] | None]
    escopo: NotRequired[str | None]
    vigencia_inicio: NotRequired[date]
    vigencia_fim: NotRequired[date | None]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def consultar_preco(
    db: Session, tipo_ato: str, *, hoje: date | None = None
) -> EmolumentoItem | None:
    """Retorna o item PUBLISHED vigente para ``tipo_ato`` ou None.

    Nunca inventa preco: slug inexistente, item nao publicado ou vigencia
    expirada/futura retornam None (caller encaminha ao HITL).
    """
    ref = hoje or date.today()
    stmt = (
        select(EmolumentoItem)
        .where(
            EmolumentoItem.tipo_ato == tipo_ato,
            EmolumentoItem.estado == EstadoEmolumento.PUBLISHED,
            EmolumentoItem.vigencia_inicio <= ref,
            or_(
                EmolumentoItem.vigencia_fim.is_(None),
                EmolumentoItem.vigencia_fim >= ref,
            ),
        )
        .order_by(EmolumentoItem.vigencia_inicio.desc(), EmolumentoItem.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def registrar_extracao(
    db: Session,
    *,
    url: str,
    sha256: str,
    capturado_em: date,
    itens: list[ItemExtraido],
    vigencia_inicio: date | None = None,
) -> FonteCaptura:
    """Cria FonteCaptura EXTRACTED + itens EXTRACTED (idempotente por sha256).

    Se ja existir captura com o mesmo sha256, retorna a existente sem
    duplicar — capturas anteriores NUNCA sao sobrescritas.
    """
    existente = (
        db.execute(select(FonteCaptura).where(FonteCaptura.sha256 == sha256)).scalars().first()
    )
    if existente is not None:
        return existente

    vigencia = vigencia_inicio or capturado_em
    captura = FonteCaptura(
        url=url,
        sha256=sha256,
        capturado_em=capturado_em,
        vigencia_inicio=vigencia,
        vigencia_fim=None,
        estado=EstadoEmolumento.EXTRACTED,
    )
    db.add(captura)
    db.flush()
    for item in itens:
        db.add(
            EmolumentoItem(
                captura_id=captura.id,
                tipo_ato=item["tipo_ato"],
                item_portaria=item["item_portaria"],
                ato=item["ato"],
                emolumentos=item["emolumentos"],
                tfj=item["tfj"],
                valor_final=item["valor_final"],
                componentes=item.get("componentes"),
                escopo=item.get("escopo"),
                estado=EstadoEmolumento.EXTRACTED,
                vigencia_inicio=item.get("vigencia_inicio", vigencia),
                vigencia_fim=item.get("vigencia_fim"),
            )
        )
    db.commit()
    db.refresh(captura)
    return captura


def marcar_revisao_humana(db: Session, captura_id: int, revisor: str) -> FonteCaptura:
    """Transicao EXTRACTED -> HUMAN_REVIEWED (validacao do escrevente)."""
    captura = db.get(FonteCaptura, captura_id)
    if captura is None:
        raise CatalogoNaoEncontradoError(f"captura {captura_id} nao encontrada")
    if captura.estado != EstadoEmolumento.EXTRACTED:
        raise EstadoInvalidoError(
            f"captura {captura_id} em estado {captura.estado}; "
            f"revisao humana exige {EstadoEmolumento.EXTRACTED}"
        )
    captura.estado = EstadoEmolumento.HUMAN_REVIEWED
    captura.revisado_por = revisor
    captura.revisado_em = _utcnow()
    for item in captura.itens:
        item.estado = EstadoEmolumento.HUMAN_REVIEWED
    db.commit()
    db.refresh(captura)
    return captura


def promover(db: Session, captura_id: int, revisor: str) -> FonteCaptura:
    """Transicao HUMAN_REVIEWED -> PUBLISHED, com supersede da versao anterior.

    Capturas PUBLISHED anteriores (e seus itens) viram SUPERSEDED — nunca sao
    sobrescritas nem deletadas. Grava entrada no audit log append-only.
    """
    captura = db.get(FonteCaptura, captura_id)
    if captura is None:
        raise CatalogoNaoEncontradoError(f"captura {captura_id} nao encontrada")
    if captura.estado != EstadoEmolumento.HUMAN_REVIEWED:
        raise EstadoInvalidoError(
            f"captura {captura_id} em estado {captura.estado}; "
            f"promocao exige {EstadoEmolumento.HUMAN_REVIEWED}"
        )

    anteriores = (
        db.execute(
            select(FonteCaptura).where(
                FonteCaptura.estado == EstadoEmolumento.PUBLISHED,
                FonteCaptura.id != captura.id,
            )
        )
        .scalars()
        .all()
    )
    superseded_ids: list[int] = []
    for anterior in anteriores:
        anterior.estado = EstadoEmolumento.SUPERSEDED
        superseded_ids.append(anterior.id)
        for item in anterior.itens:
            item.estado = EstadoEmolumento.SUPERSEDED

    captura.estado = EstadoEmolumento.PUBLISHED
    captura.revisado_por = revisor
    captura.revisado_em = _utcnow()
    for item in captura.itens:
        item.estado = EstadoEmolumento.PUBLISHED
    db.flush()

    # AuditService.log faz o commit (append-only hash chain + HMAC).
    AuditService.log(
        db,
        actor_id=revisor,
        actor_type="user",
        action="emolumento_catalogo.promover",
        resource=f"fonte_captura:{captura.id}",
        payload={
            "captura_id": captura.id,
            "sha256": captura.sha256,
            "itens_publicados": len(captura.itens),
            "capturas_superseded": superseded_ids,
        },
    )
    db.refresh(captura)
    return captura


__all__ = [
    "CatalogoNaoEncontradoError",
    "EstadoInvalidoError",
    "ItemExtraido",
    "consultar_preco",
    "marcar_revisao_humana",
    "promover",
    "registrar_extracao",
]
