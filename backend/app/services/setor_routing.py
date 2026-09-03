"""Serviço de roteamento de setores para HITL.

Responsável por determinar o setor correto baseado no tipo de ato,
consultando a configuração no banco de dados (com fallback para defaults).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setor import SETOR_POR_TIPO_ATO_DEFAULT, ProtocoloSetor, Setor

if TYPE_CHECKING:
    from app.models.protocolo import Protocolo

logger = logging.getLogger(__name__)


def get_setor_por_slug(db: Session, slug: str) -> Setor | None:
    """Busca setor ativo pelo slug."""
    return db.execute(
        select(Setor).where(Setor.slug == slug, Setor.ativo.is_(True))
    ).scalar_one_or_none()


def get_setor_por_tipo_ato(db: Session, tipo_ato: str) -> Setor | None:
    """Determina o setor responsável por um tipo de ato.

    Ordem de prioridade:
    1. Configuração no banco (tabela setores + mapeamento protocolo_setores)
    2. Default hardcoded (SETOR_POR_TIPO_ATO_DEFAULT)
    3. None (sem setor definido)
    """
    slug = SETOR_POR_TIPO_ATO_DEFAULT.get(tipo_ato)
    if not slug:
        logger.warning("setor_routing: tipo_ato sem mapeamento default: %s", tipo_ato)
        return None

    setor = get_setor_por_slug(db, slug)
    if setor:
        return setor

    # Fallback: criar setor on-demand se não existir (modo desenvolvimento)
    logger.info("setor_routing: setor %s não encontrado no DB, retornando None", slug)
    return None


def get_setores_ativos(db: Session) -> list[Setor]:
    """Lista todos os setores ativos ordenados por ordem_exibicao."""
    return list(
        db.execute(
            select(Setor)
            .where(Setor.ativo.is_(True))
            .order_by(Setor.ordem_exibicao)
        ).scalars().all()
    )


def get_setor_para_handoff(db: Session, tipo_ato: str) -> dict | None:
    """Retorna informações do setor para handoff HITL (Chatwoot).

    Retorna dict com: slug, nome, responsavel, email, telefone_interno
    """
    setor = get_setor_por_tipo_ato(db, tipo_ato)
    if not setor:
        return None

    return {
        "slug": setor.slug,
        "nome": setor.nome,
        "responsavel": setor.responsavel,
        "email": setor.email,
        "telefone_interno": setor.telefone_interno,
    }


def associar_protocolo_setor(
    db: Session,
    protocolo: Protocolo,
    tipo_ato: str,
    *,
    principal: bool = True,
) -> bool:
    """Associa um protocolo ao setor correspondente ao tipo de ato."""
    slug = SETOR_POR_TIPO_ATO_DEFAULT.get(tipo_ato)
    if not slug:
        return False

    setor = get_setor_por_slug(db, slug)
    if not setor:
        return False

    # Verificar se já existe associação
    existe = db.execute(
        select(ProtocoloSetor).where(
            ProtocoloSetor.protocolo_id == protocolo.id,
            ProtocoloSetor.setor_id == setor.id,
        )
    ).scalar_one_or_none()

    if not existe:
        associacao = ProtocoloSetor(
            protocolo_id=protocolo.id,
            setor_id=setor.id,
            principal=principal,
            criado_em=datetime.now(datetime.UTC).isoformat(),
        )
        db.add(associacao)
        return True

    return False


def inicializar_setores_padrao(db: Session) -> int:
    """Inicializa os setores padrão no banco se não existirem.

    Retorna número de setores criados.
    """
    from app.models.setor import SETORES_PADRAO

    criados = 0
    for data in SETORES_PADRAO:
        slug = data["slug"]
        existente = get_setor_por_slug(db, slug)
        if not existente:
            setor = Setor(**data)  # type: ignore[arg-type]
            db.add(setor)
            criados += 1
            logger.info("setor_routing: criado setor padrão %s", slug)

    if criados > 0:
        db.commit()
        logger.info("setor_routing: %d setores padrão inicializados", criados)

    return criados