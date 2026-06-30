"""Service de Protocolo - logica de negocio extraida do router.py.

Refatorado para ser reusado tanto pelo endpoint FastAPI (/api/v1/protocolo POST)
quanto pela tool MCP (cartorio_criar_protocolo). Antes, o MCP fazia self-loop
HTTP (httpx.post pra localhost:8000) - isso causava deadlock em carga porque
o sub-app MCP e a API principal compartilhavam o mesmo event loop.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.audit import AuditService
from app.services.emolumento import TIPOS_VALIDOS, calcular as calcular_emolumento_svc
from app.services.pii import hash_pii


class LGPDBlockedError(Exception):
    """Excecao para bloqueio por falta de consentimento LGPD."""


class TipoInvalidoError(Exception):
    """Excecao para tipo de ato fora da tabela de emolumentos."""


def _gerar_numero_protocolo(db: Session, ano: int) -> str:
    """Gera proximo numero ANO-SEQUENCIAL (YYYY-NNNNN)."""
    prefixo = f"{ano}-"
    # Query do ultimo sequencial do ano
    ultimo = db.execute(
        select(Protocolo.numero)
        .where(Protocolo.numero.like(f"{prefixo}%"))
        .order_by(Protocolo.numero.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not ultimo:
        return f"{prefixo}00001"
    try:
        seq = int(ultimo.split("-")[1]) + 1
    except (IndexError, ValueError):
        return f"{prefixo}00001"
    return f"{prefixo}{seq:05d}"


def criar_protocolo_svc(
    db: Session,
    *,
    tipo: str,
    cliente_cpf: str,
    cliente_nome: str,
    consentimento_lgpd: bool,
    canal_origem: str = "web",
    actor_id: str = "bot",
    actor_type: str = "bot",
) -> dict[str, Any]:
    """Cria protocolo DRAFT com gate LGPD + scrubber PII + audit log.

    Args:
        db: Sessao SQLAlchemy (caller gerencia transacao).
        tipo: Tipo do ato (deve estar em TIPOS_VALIDOS).
        cliente_cpf: CPF do cliente (11 digitos, com ou sem pontuacao).
        cliente_nome: Nome completo do cliente.
        consentimento_lgpd: OBRIGATORIO ser True.
        canal_origem: Canal de origem (whatsapp/telegram/web/balcao/email).
        actor_id: Identificador do ator (default: bot).
        actor_type: Tipo do ator (default: bot).

    Returns:
        Dict com status, numero, protocolo_id, estado, cliente_id, proxima_acao.

    Raises:
        LGPDBlockedError: Se consentimento_lgpd=False.
        TipoInvalidoError: Se tipo nao esta em TIPOS_VALIDOS.
    """
    # ------------------------------------------------------------------
    # Gate LGPD - bloqueia ANTES de qualquer persistencia.
    # ------------------------------------------------------------------
    if not consentimento_lgpd:
        AuditService.log(
            db,
            actor_id=actor_id,
            actor_type=actor_type,
            action="protocolo.create.lgpd_blocked",
            resource="protocolo:new",
            payload={
                "tipo": tipo,
                "canal_origem": canal_origem,
                "motivo": "consentimento_lgpd=false",
            },
        )
        raise LGPDBlockedError("Consentimento LGPD obrigatorio para criar protocolo.")

    # ------------------------------------------------------------------
    # Validacao de tipo contra tabela de emolumentos
    # ------------------------------------------------------------------
    if tipo not in TIPOS_VALIDOS:
        raise TipoInvalidoError(f"Tipo '{tipo}' nao esta na tabela de emolumentos.")

    # ------------------------------------------------------------------
    # PII scrubbing - hasheia CPF ANTES de persistir.
    # Salt vem do settings (em prod vem de secret manager).
    # ------------------------------------------------------------------
    from app.config import settings  # lazy import to avoid circular

    cpf_hash = hash_pii(cliente_cpf, salt=settings.audit_hmac_key[:32])

    # ------------------------------------------------------------------
    # Cliente - reusa se CPF ja existir (idempotencia por hash)
    # ------------------------------------------------------------------
    cliente = db.execute(select(Cliente).where(Cliente.cpf_hash == cpf_hash)).scalar_one_or_none()

    if cliente is None:
        cliente = Cliente(
            cpf_hash=cpf_hash,
            nome=cliente_nome,
            consentimento_lgpd=True,
            consentimento_em=datetime.datetime.now(datetime.timezone.utc),
            consentimento_canal=canal_origem,
        )
        db.add(cliente)
        db.flush()
    else:
        cliente.consentimento_lgpd = True
        cliente.consentimento_em = datetime.datetime.now(datetime.timezone.utc)
        cliente.consentimento_canal = canal_origem

    # ------------------------------------------------------------------
    # Snapshot de emolumento (regra: nunca recalcular)
    # ------------------------------------------------------------------
    calc = calcular_emolumento_svc(tipo, folhas=1, urgencia=False)

    # ------------------------------------------------------------------
    # Numero ANO-SEQUENCIAL
    # ------------------------------------------------------------------
    ano_atual = datetime.datetime.now(datetime.timezone.utc).year
    numero = _gerar_numero_protocolo(db, ano_atual)

    protocolo = Protocolo(
        numero=numero,
        cliente_id=cliente.id,
        tipo=tipo,
        status="DRAFT",  # HITL: nunca EM_ANDAMENTO direto
        valor_base=calc.base,
        valor_adicional=calc.adicional_folhas + calc.adicional_urgencia,
        valor_total=calc.total,
        tabela_referencia=calc.tabela_referencia,
        prazo_dias=5,
        canal_origem=canal_origem,
    )
    db.add(protocolo)
    db.flush()

    # ------------------------------------------------------------------
    # Audit log - OBRIGATORIO em toda mutacao.
    # ------------------------------------------------------------------
    AuditService.log(
        db,
        actor_id=actor_id,
        actor_type=actor_type,
        action="protocolo.create",
        resource=f"protocolo:{protocolo.id}",
        payload={
            "numero": protocolo.numero,
            "tipo": protocolo.tipo,
            "canal_origem": protocolo.canal_origem,
            "cliente_id": cliente.id,
            "cpf_hash": cpf_hash,  # hash, nao o CPF puro
            "valor_total": str(protocolo.valor_total),
            "status": protocolo.status,
            "consentimento_lgpd": True,
            "pii_scrubbed": True,
        },
    )

    db.commit()
    db.refresh(protocolo)

    return {
        "status": "criado",
        "numero": protocolo.numero,
        "protocolo_id": protocolo.id,
        "estado": protocolo.status,
        "proxima_acao": (
            "Aguardando validacao humana do escrevente. "
            "O protocolo NAO sera processado ate confirmacao no painel admin."
        ),
        "cliente_id": cliente.id,
    }
