"""API router v1 - Cartorio Backend.

Endpoints versionados sob `/api/v1`. Cada endpoint tem tag PT-BR no Swagger
para facilitar discovery. Mutacoes gravam audit log; leituras sensiveis
(cliente/protocolo) tambem registram acesso.

Tags:
- meta      : health, ready
- emolumento: calculo de custas
- protocolo : gestao do ciclo de vida do protocolo
- webhook   : integracao com canais externos (Evolution/WhatsApp)
- audit     : integridade da cadeia de audit log
- health    : health radar multi-servico
- dev       : exports para tooling (Postman)
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import os
import time
from typing import Annotated, Any, cast

import httpx
import redis
from fastapi import APIRouter, Depends, Form, Header, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field  # noqa: F401  (usado nos schemas abaixo)

from app.config import settings
from app.db import get_db, session_scope
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.schemas.protocolo import (
    CanalOrigem,
    ClienteResumo,
    EtapaHistorico,
    HistoricoEtapa,
    LGPDBlockedResponse,
    ProtocoloApiCreateRequest,
    ProtocoloApiCreateResponse,
    ProtocoloCreateRequest,
    ProtocoloCreateResponse,
    ProtocoloNotFoundResponse,
    ProtocoloResponse,
    StatusProtocolo,
)
from app.schemas.audit import AuditLogFilter, AuditLogListResponse, AuditLogResponse
from app.schemas.metrics import MetricsResponse, N8nMetricsIngest, N8nMetricsIngestResponse
from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs
from app.services.audit_query import get_audit_log_by_id, list_audit_logs
from app.services.emolumento import TIPOS_VALIDOS, calcular as calcular_emolumento_svc
from app.services.pii import hash_pii, scrub

# Integrations router (smoke test OpenCode-Go, etc)
from app.api.v1.integrations import integrations_router  # noqa: E402

# ============================================================================
# Router com tags PT-BR para o Swagger/OpenAPI
# ============================================================================

api_router = APIRouter()
api_router.include_router(integrations_router)


# Regex do formato ANO-SEQUENCIAL (YYYY-NNNNN)
_NUMERO_PROTOCOLO_REGEX = r"^\d{4}-\d{5}$"


# ============================================================================
# Emolumento
# ============================================================================


@api_router.get(
    "/emolumento/calcular",
    tags=["emolumento"],
    summary="Calcular emolumento (tabela oficial MG 2026)",
    description=(
        "Calcula emolumento + adicionais por folha (5% a partir da 2a) + "
        "adicional de urgencia (50%). Usa snapshot da tabela de emolumentos "
        "vigente (placeholder - em producao vem de carga oficial do estado). "
        "Nao envolve PII - pode ser consumido publicamente."
    ),
    response_description="Resultado do calculo em JSON com breakdown base/adicional/total.",
)
async def calcular_emolumento(
    tipo: Annotated[
        str,
        Query(
            description="Tipo do ato cartorario.",
            examples=["escritura_compra_venda"],
        ),
    ] = "",
    folhas: Annotated[int, Query(ge=1, le=1000, description="Quantidade de folhas.")] = 1,
    urgencia: Annotated[
        bool,
        Query(description="Se true, aplica adicional de 50% por urgencia."),
    ] = False,
) -> dict:
    """Calcula emolumento. Publico - sem PII envolvida."""
    try:
        resultado = calcular_emolumento_svc(tipo, folhas=folhas, urgencia=urgencia)
    except ValueError as e:
        return {"erro": str(e)}
    return {
        "tipo": resultado.tipo,
        "folhas": resultado.folhas,
        "urgencia": resultado.urgencia,
        "base": str(resultado.base),
        "adicional_folhas": str(resultado.adicional_folhas),
        "adicional_urgencia": str(resultado.adicional_urgencia),
        "total": str(resultado.total),
        "tabela_referencia": resultado.tabela_referencia,
        "valido_ate": resultado.valido_ate,
    }


# ============================================================================
# Protocolo - GET (consulta)
# ============================================================================


@api_router.get(
    "/protocolo/{numero}",
    tags=["protocolo"],
    summary="Consultar protocolo por numero",
    description=(
        "Busca um protocolo pelo numero no formato **ANO-SEQUENCIAL** "
        "(ex: `2026-00001`). Retorna status atual, etapa em que se encontra, "
        "historico completo de etapas, proxima acao esperada e prazo estimado. "
        "Toda consulta e registrada no audit log (LGPD art. 37 - registro de "
        "operacoes de tratamento)."
    ),
    response_model=ProtocoloResponse,
    response_description="Protocolo encontrado, com historico e proxima acao.",
    responses={
        200: {
            "description": "Protocolo encontrado.",
            "content": {
                "application/json": {
                    "example": {
                        "numero": "2026-00001",
                        "status": "DRAFT",
                        "etapa_atual": "criado",
                        "cliente": {"nome": "Joao da Silva", "cpf_hash": "a" * 64},
                        "tipo": "certidao_negativa",
                        "canal_origem": "web",
                        "valor_base": "87.50",
                        "valor_total": "87.50",
                        "tabela_referencia": "TABELA_2026_MG",
                        "prazo_estimado": "5 dias uteis",
                        "proxima_acao": "Aguardando validacao do escrevente.",
                        "historico": [
                            {
                                "etapa": "criado",
                                "timestamp": "2026-06-23T10:00:00.500000",
                                "descricao": "Protocolo criado em DRAFT.",
                                "autor": "bot",
                            }
                        ],
                        "created_at": "2026-06-23T10:00:00.500000",
                        "updated_at": "2026-06-23T10:00:00.500000",
                    }
                }
            },
        },
        404: {
            "model": ProtocoloNotFoundResponse,
            "description": "Protocolo nao encontrado.",
        },
        422: {
            "description": "Formato do numero invalido (esperado YYYY-NNNNN).",
        },
    },
)
def get_protocolo(
    request: Request,
    numero: Annotated[
        str,
        Path(
            pattern=_NUMERO_PROTOCOLO_REGEX,
            description="Numero do protocolo no formato ANO-SEQUENCIAL (YYYY-NNNNN).",
            examples=["2026-00001"],
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> ProtocoloResponse:
    """Consulta publica do protocolo + audit log obrigatorio."""
    protocolo = db.execute(select(Protocolo).where(Protocolo.numero == numero)).scalar_one_or_none()

    if protocolo is None:
        # Loga tentativa de consulta a protocolo inexistente (seguranca).
        # request.state populado por RequestContextMiddleware (request_id,
        # client_ip, user_agent) - LGPD art. 37 exige registro de operacoes.
        AuditService.log(
            db,
            actor_id="anonymous",
            actor_type="user",
            action="protocolo.read.not_found",
            resource=f"protocolo:{numero}",
            payload={"numero": numero, "result": "not_found"},
            request_id=getattr(request.state, "request_id", None),
            ip=getattr(request.state, "client_ip", None),
            user_agent=getattr(request.state, "user_agent", None),
        )
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "PROTOCOLO_NOT_FOUND",
                "mensagem": f"Protocolo {numero} nao encontrado.",
                "detalhes": {"numero_consultado": numero},
            },
        )

    # Audit log da consulta (LGPD art. 37)
    AuditService.log(
        db,
        actor_id="anonymous",
        actor_type="user",
        action="protocolo.read",
        resource=f"protocolo:{protocolo.id}",
        payload={
            "numero": protocolo.numero,
            "status": protocolo.status,
            "tipo": protocolo.tipo,
        },
        **audit_kwargs(request),
    )

    # Constroi historico minimo a partir dos dados do protocolo.
    historico: list[HistoricoEtapa] = [
        HistoricoEtapa(
            etapa=EtapaHistorico.CRIADO,
            timestamp=protocolo.created_at,
            descricao="Protocolo criado em modo DRAFT (HITL obrigatorio).",
            autor="bot",
        ),
    ]
    if protocolo.status == StatusProtocolo.AGUARDANDO_DOC.value:
        historico.append(
            HistoricoEtapa(
                etapa=EtapaHistorico.AGUARDANDO_DOC,
                timestamp=protocolo.updated_at,
                descricao="Aguardando envio de documentos pelo cliente.",
                autor="bot",
            )
        )
    elif protocolo.status == StatusProtocolo.EM_ANDAMENTO.value:
        historico.append(
            HistoricoEtapa(
                etapa=EtapaHistorico.EM_ANALISE,
                timestamp=protocolo.updated_at,
                descricao="Em analise juridica pelo escrevente.",
                autor="escrevente",
            )
        )
    elif protocolo.status == StatusProtocolo.CONCLUIDO.value:
        historico.append(
            HistoricoEtapa(
                etapa=EtapaHistorico.CONCLUIDO,
                timestamp=protocolo.concluido_em or protocolo.updated_at,
                descricao="Protocolo concluido.",
                autor="escrevente",
            )
        )

    etapa_atual = historico[-1].etapa

    proxima_acao = {
        StatusProtocolo.DRAFT.value: (
            "Aguardando validacao humana do escrevente. "
            "Acesse o painel admin ou aguarde contato via WhatsApp."
        ),
        StatusProtocolo.ABERTO.value: "Documentacao sendo conferida pelo escrevente.",
        StatusProtocolo.EM_ANDAMENTO.value: "Em analise juridica.",
        StatusProtocolo.AGUARDANDO_DOC.value: (
            "Envie os documentos solicitados pelo escrevente via WhatsApp."
        ),
        StatusProtocolo.CONCLUIDO.value: "Protocolo concluido. PDF disponivel para download.",
        StatusProtocolo.CANCELADO.value: "Protocolo cancelado. Procure o cartorio para mais detalhes.",
        StatusProtocolo.EXPIRADO.value: "Protocolo expirado. Inicie nova solicitacao se ainda necessario.",
    }.get(protocolo.status, "Consulte o cartorio para atualizacoes.")

    return ProtocoloResponse(
        numero=protocolo.numero,
        status=StatusProtocolo(protocolo.status),
        etapa_atual=etapa_atual,
        cliente=ClienteResumo(nome=protocolo.cliente.nome, cpf_hash=protocolo.cliente.cpf_hash),
        tipo=protocolo.tipo,
        canal_origem=CanalOrigem(protocolo.canal_origem),
        valor_base=protocolo.valor_base,
        valor_total=protocolo.valor_total,
        tabela_referencia=protocolo.tabela_referencia,
        prazo_estimado=(f"{protocolo.prazo_dias} dias uteis" if protocolo.prazo_dias else None),
        proxima_acao=proxima_acao,
        historico=historico,
        created_at=protocolo.created_at,
        updated_at=protocolo.updated_at,
    )


# ============================================================================
# Protocolo - POST (criacao)
# ============================================================================


def _gerar_numero_protocolo(db: Session, ano: int) -> str:
    """Gera o proximo numero ANO-SEQUENCIAL para o ano informado.

    Formato: YYYY-NNNNN onde NNNNN e zero-padded sequencial por ano.
    Estrategia: count + 1 do ano (boa o suficiente pra MVP; em prod usar sequence).
    """
    padrao = f"{ano}-%"
    existentes = (
        db.execute(select(Protocolo.numero).where(Protocolo.numero.like(padrao))).scalars().all()
    )
    proximo = len(existentes) + 1
    return f"{ano}-{proximo:05d}"


@api_router.post(
    "/protocolo",
    tags=["protocolo"],
    summary="Criar protocolo (HITL DRAFT obrigatorio)",
    description=(
        "Cria um novo protocolo em modo **DRAFT** (status inicial). "
        "O bot NUNCA cria protocolo direto em `EM_ANDAMENTO` - o escrevente "
        "sempre valida antes (Human-In-The-Loop, regra do projeto). \n\n"
        "**Gate LGPD obrigatorio**: o campo `consentimento_lgpd` DEVE ser `True`. "
        "Conforme Lei 13.709/2018 (LGPD), art. 7o, I, o tratamento de dados "
        "pessoais exige consentimento explicito. Se ausente, retorna 422 "
        "LGPD_BLOCKED. \n\n"
        "**PII scrubbing**: o CPF recebido e hasheado (SHA256+salt) antes de "
        "persistir. Nenhum dado pessoal em texto puro e salvo no banco."
    ),
    response_model=ProtocoloCreateResponse,
    status_code=201,
    response_description="Protocolo criado em modo DRAFT, aguardando validacao humana.",
    responses={
        201: {
            "description": "Protocolo criado em DRAFT. Proximo passo: escrevente validar.",
        },
        422: {
            "model": LGPDBlockedResponse,
            "description": "Consentimento LGPD nao fornecido ou dados invalidos.",
        },
    },
)
def post_protocolo(
    request: Request,
    payload: ProtocoloCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ProtocoloCreateResponse:
    """Cria protocolo DRAFT com gate LGPD + scrubber PII + audit log."""
    # ------------------------------------------------------------------
    # Gate LGPD - bloqueia ANTES de qualquer persistencia.
    # ------------------------------------------------------------------
    if not payload.consentimento_lgpd:
        # Loga tentativa bloqueada (LGPD art. 37 - registro de tratamento)
        AuditService.log(
            db,
            actor_id="anonymous",
            actor_type="bot",
            action="protocolo.create.lgpd_blocked",
            resource="protocolo:new",
            payload={
                "tipo": payload.tipo,
                "canal_origem": payload.canal_origem.value,
                "motivo": "consentimento_lgpd=false",
            },
            **audit_kwargs(request),
        )
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "LGPD_BLOCKED",
                "mensagem": (
                    "Consentimento obrigatorio. Conforme Lei 13.709/2018 (LGPD), "
                    "o tratamento de dados pessoais exige consentimento explicito."
                ),
                "detalhes": {"consentimento_lgpd_aceito": False},
            },
        )

    # ------------------------------------------------------------------
    # Validacao de tipo contra tabela de emolumentos
    # ------------------------------------------------------------------
    if payload.tipo not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "TIPO_INVALIDO",
                "mensagem": f"Tipo '{payload.tipo}' nao esta na tabela de emolumentos.",
                "detalhes": {"tipos_validos": sorted(TIPOS_VALIDOS)},
            },
        )

    # ------------------------------------------------------------------
    # Logica core extraida para app.services.protocolo.criar_protocolo_svc
    # (refator: reusado tambem pela tool MCP cartorio_criar_protocolo).
    # ------------------------------------------------------------------
    from app.services.protocolo import criar_protocolo_svc

    result = criar_protocolo_svc(
        db,
        tipo=payload.tipo,
        cliente_cpf=payload.cliente_cpf,
        cliente_nome=payload.cliente_nome,
        consentimento_lgpd=payload.consentimento_lgpd,
        canal_origem=payload.canal_origem.value,
    )

    return ProtocoloCreateResponse(
        status=result["status"],
        numero=result["numero"],
        protocolo_id=result["protocolo_id"],
        estado=StatusProtocolo(result["estado"]),
        proxima_acao=result["proxima_acao"],
        cliente_id=result["cliente_id"],
    )


# ============================================================================
# POST /api/v1/protocolo/criar-api (Sprint 3 E1.S3.T1 — M1.8 + LGPD P0 #1)
#
# Endpoint autenticado por X-API-Key, usado por integracoes externas
# (N8N WF #2 criar-protocolo, sistemas do escritorio, etc).
#
# Diferencas vs POST /api/v1/protocolo principal:
# - Auth: X-API-Key header (vs public + LGPD gate)
# - Identifica cliente por ID interno (vs CPF + nome)
# - Recebe valor_snapshot ja calculado pelo caller (vs calcular internamente)
# - Numero do protocolo formato CART-YYYY-XXXXXX (vs YYYY-NNNNN)
# - Audit log action="protocolo.created" (vs "protocolo.create")
# - LGPD: rejeita clientes com motivo_encerramento = REVOGACAO_CONSENTIMENTO
# ============================================================================


def _verify_api_key(x_api_key: str | None) -> None:
    """Valida X-API-Key contra settings.cartorio_api_key.

    Levanta HTTPException 401 se ausente ou incorreta. Constante-time
    comparison via hashlib.compare_digest para evitar timing attacks.
    """
    expected = settings.cartorio_api_key
    if not expected:
        # API key nao configurada no .env - bloqueia por seguranca
        raise HTTPException(
            status_code=503,
            detail={
                "erro": "API_KEY_NOT_CONFIGURED",
                "mensagem": (
                    "Endpoint protegido por X-API-Key mas chave nao configurada no servidor."
                ),
            },
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=401,
            detail={
                "erro": "UNAUTHORIZED",
                "mensagem": "X-API-Key ausente ou invalida.",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )


@api_router.post(
    "/protocolo/criar-api",
    tags=["protocolo"],
    summary="Criar protocolo via API (auth X-API-Key, HITL DRAFT obrigatorio)",
    description=(
        "Cria protocolo em modo **DRAFT** autenticado por **header X-API-Key**. "
        "Diferente do POST /api/v1/protocolo principal (public + LGPD gate), este "
        "endpoint eh usado por integracoes externas autorizadas: N8N WF #2 "
        "criar-protocolo, sistemas do escritorio, etc.\n\n"
        "**Auth**: header `X-API-Key` com mesmo valor de `CARTORIO_API_KEY` no .env.\n\n"
        "**Identificacao**: por `cliente_id` (FK clientes.id). Cliente precisa existir "
        "e NAO pode ter `motivo_encerramento = REVOGACAO_CONSENTIMENTO`.\n\n"
        "**Snapshot**: caller envia `valor_snapshot` ja calculado. Regra do projeto: "
        "nunca recalcular protocolo antigo.\n\n"
        "**HITL**: `hitl_draft` DEVE ser True (default). Backend rejeita "
        "`hitl_draft=False` com 422.\n\n"
        "**Audit log**: action=`protocolo.created`, actor_type=`api`, payload com "
        "`{cliente_id_hash, ato, valor, hitl_draft}`."
    ),
    status_code=201,
    response_model=ProtocoloApiCreateResponse,
    response_description="Protocolo criado em modo DRAFT (CART-YYYY-XXXXXX).",
    responses={
        401: {"description": "X-API-Key ausente ou invalida."},
        404: {"description": "Cliente nao encontrado."},
        422: {"description": "LGPD bloqueado (revogacao) ou payload invalido."},
    },
)
def post_protocolo_criar_api(
    request: Request,
    payload: ProtocoloApiCreateRequest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: Session = Depends(get_db),
) -> ProtocoloApiCreateResponse:
    """Cria protocolo DRAFT via API autenticada.

    Auth: X-API-Key header.
    LGPD: rejeita cliente com motivo_encerramento = REVOGACAO_CONSENTIMENTO.
    HITL: hitl_draft DEVE ser True (rejeitado senao).
    """
    # ------------------------------------------------------------------
    # Auth: X-API-Key
    # ------------------------------------------------------------------
    api_key_header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    _verify_api_key(api_key_header)

    # ------------------------------------------------------------------
    # Validacao cliente existe
    # ------------------------------------------------------------------
    cliente = db.execute(
        select(Cliente).where(Cliente.id == payload.cliente_id)
    ).scalar_one_or_none()

    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "CLIENTE_NOT_FOUND",
                "mensagem": f"Cliente {payload.cliente_id} nao encontrado.",
                "detalhes": {"cliente_id_consultado": payload.cliente_id},
            },
        )

    # ------------------------------------------------------------------
    # LGPD gate: cliente NAO pode ter revogado consentimento
    # ------------------------------------------------------------------
    if (
        cliente.motivo_encerramento
        and cliente.motivo_encerramento.value == "revogacao_consentimento"
    ):
        AuditService.log(
            db,
            actor_id="api_key",
            actor_type="api",
            action="protocolo.created.lgpd_blocked",
            resource=f"cliente:{cliente.id}",
            payload={
                "motivo": "cliente.revogacao_consentimento",
                "ato": payload.ato.value,
                "valor": str(payload.valor_snapshot),
                "cliente_id_hash": hash_pii(str(cliente.id), salt=settings.audit_hmac_key[:32]),
            },
            **audit_kwargs(request),
        )
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "LGPD_BLOCKED",
                "mensagem": (
                    f"Cliente {cliente.id} revogou consentimento LGPD. "
                    "Conforme Lei 13.709/2018, art. 18, VI, novos protocolos "
                    "nao podem ser criados para este cliente."
                ),
                "detalhes": {
                    "cliente_id": cliente.id,
                    "motivo_encerramento": cliente.motivo_encerramento.value,
                    "revogacao_em": (
                        cliente.updated_at.isoformat() if cliente.updated_at else None
                    ),
                    "direitos_titular": (
                        "Cliente pode reabrir atendimento criando novo consentimento. "
                        "DPO: dpo@2notasudi.com.br"
                    ),
                },
            },
        )

    # ------------------------------------------------------------------
    # Gerar numero CART-YYYY-XXXXXX (sequencial por ano)
    # ------------------------------------------------------------------
    ano_atual = datetime.datetime.now(datetime.timezone.utc).year
    prefixo = f"CART-{ano_atual}-"
    ultimo = db.execute(
        select(Protocolo.numero)
        .where(Protocolo.numero.like(f"{prefixo}%"))
        .order_by(Protocolo.numero.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not ultimo:
        seq = 1
    else:
        try:
            seq = int(ultimo.split("-")[2]) + 1
        except (IndexError, ValueError):
            seq = 1
    numero_protocolo = f"{prefixo}{seq:06d}"

    # ------------------------------------------------------------------
    # Persistir protocolo (status SEMPRE DRAFT - HITL obrigatorio)
    # ------------------------------------------------------------------
    protocolo = Protocolo(
        numero=numero_protocolo,
        cliente_id=cliente.id,
        tipo=payload.ato.value,
        status="DRAFT",  # HITL: nunca EM_ANDAMENTO
        valor_base=payload.valor_snapshot,
        valor_total=payload.valor_snapshot,
        tabela_referencia="API_SNAPSHOT",
        prazo_dias=5,
        canal_origem="api",
    )
    db.add(protocolo)
    db.flush()  # obtem protocolo.id para audit log

    # ------------------------------------------------------------------
    # Audit log - LGPD art. 37: registrar CRIACAO (OBRIGATORIO)
    # ------------------------------------------------------------------
    cliente_id_hash = hash_pii(str(cliente.id), salt=settings.audit_hmac_key[:32])
    audit_entry = AuditService.log(
        db,
        actor_id="api_key",
        actor_type="api",
        action="protocolo.created",
        resource=f"protocolo:{protocolo.id}",
        payload={
            "numero": numero_protocolo,
            "ato": payload.ato.value,
            "valor": str(payload.valor_snapshot),
            "hitl_draft": payload.hitl_draft,
            "cliente_id_hash": cliente_id_hash,
            "canal_origem": "api",
            "observacoes_present": payload.observacoes is not None,
        },
        **audit_kwargs(request),
    )
    db.commit()
    db.refresh(protocolo)

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------
    return ProtocoloApiCreateResponse(
        protocolo=numero_protocolo,
        cliente_id=cliente.id,
        status="draft",
        audit_id=str(audit_entry.id).zfill(32),  # hex-like id para compat
        created_at=protocolo.created_at,
        created_by="api",
    )


# ============================================================================
# Webhook Evolution (WhatsApp)
# ============================================================================


@api_router.post(
    "/webhook/evolution",
    tags=["webhook"],
    summary="Webhook WhatsApp (Evolution API)",
    description=(
        "Recebe mensagem do Evolution API, aplica **PII scrubbing em 3 camadas** "
        "(input, pre-LLM, output), detecta intencao via LLM, retorna resposta. "
        "Bloqueia fluxo automaticamente se PII for detectado antes do LLM "
        "(handoff humano obrigatorio). \n\n"
        "Registra **tudo** no audit log (chain SHA256 + HMAC)."
    ),
    response_description="Status do processamento + resposta do bot + texto scrubbed.",
)
async def webhook_evolution(request: Request, payload: dict) -> dict:
    """Webhook do Evolution API (WhatsApp).

    Recebe mensagem, aplica PII scrubbing, detecta intencao via LLM,
    retorna resposta. Audit log de TUDO.

    Sprint 2: idempotencia via evolution_ingest (message_id) - replay nao duplica.
    Mantem a logica inline de PII+LLM para nao quebrar o workflow #12 ativo
    e formato legado (pre-Sprint 1.2) que ainda usa payload {message, sender, instance}.
    """
    # Idempotency check (Sprint 2) - so se payload tem formato novo
    # (data.key.id). Formato legado e ignorado silenciosamente.
    from app.services.evolution_ingest import ingest_evolution_event

    if payload.get("data", {}).get("key", {}).get("id"):
        with session_scope() as db:
            ingest_result = ingest_evolution_event(db, payload)
            if ingest_result["status"] == "idempotent":
                return {
                    "status": "idempotent",
                    "message_id": ingest_result.get("message_id"),
                    "info": "message already processed",
                }
            if ingest_result["status"] == "rejected":
                return ingest_result
            # accepted: continua processamento abaixo

    raw_text = payload.get("message", {}).get("text", "") or ""
    sender = payload.get("sender", "unknown")
    instance = payload.get("instance", "")

    # Calculate raw message hash
    raw_message_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    scrub_result = scrub(raw_text)
    with session_scope() as db:
        # Garante que canal="whatsapp" mesmo se header X-Canal nao veio.
        ctx = audit_kwargs(request)
        if not ctx["canal"]:
            ctx["canal"] = "whatsapp"
        AuditService.log(
            db,
            actor_id=sender,
            actor_type="bot",
            action="conversa.received",
            resource=f"whatsapp:{instance}",
            payload={
                "scrubbed": scrub_result.text,
                "findings": scrub_result.findings,
                "redaction_count": scrub_result.redaction_count,
            },
            **ctx,
        )

    handoff = False
    handoff_reason = None
    intent = "chat"
    bot_response = ""
    llm_tokens_in = None
    llm_tokens_out = None
    llm_latency_ms = None

    if (
        settings.pii_scrub_enabled
        and settings.pii_block_on_detect
        and scrub_result.redaction_count > 0
    ):
        bot_response = (
            "Recebi sua mensagem com dados sensiveis. "
            "Por seguranca, vou transferir para um atendente humano. "
            "Aguarde um instante."
        )
        handoff = True
        handoff_reason = "PII detectada"
        # P0.2 - LGPD art. 37 audit log: registrar o BLOQUEIO alem da
        # deteccao (que ja eh logada em conversa.received na linha 483).
        # Sem isso, compliance review nao distingue "PII detectado mas
        # seguiu" de "PII detectado e bloqueado" - nao conseguimos provar
        # que bloqueamos, so que detectamos.
        try:
            with session_scope() as db_pii:
                ctx_pii = audit_kwargs(request)
                if not ctx_pii["canal"]:
                    ctx_pii["canal"] = "whatsapp"
                AuditService.log(
                    db_pii,
                    actor_id=sender,
                    actor_type="bot",
                    action="conversa.pii_blocked",
                    resource=f"whatsapp:{instance}",
                    payload={
                        "pii_findings": scrub_result.findings,
                        "redaction_count": scrub_result.redaction_count,
                        "handoff_reason": handoff_reason,
                        "blocked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    },
                    **ctx_pii,
                )
        except Exception:
            # Audit log falhou - NAO quebrar o fluxo principal.
            # Conversa com handoff ja foi gravada (try/except la embaixo).
            pass
    else:
        # Chamar LLM via modulo dedicado (SRP + LGPD by design - refator 2026-06-23).
        # opencode_go.chat() faz:
        # - consent gate (LGPD art. 7 I)
        # - rate limit por sessao (cost guard)
        # - PII scrubbing INTERNO (defense-in-depth)
        # - audit log via AuditService (LGPD art. 37)
        from app.integrations.opencode_go import ChatError, chat_with_settings

        # LGPD: consent inferido pelo canal (cliente iniciou conversa via WhatsApp).
        # Em sprint 2 adicionar gate explicito ("digite SIM para autorizar uso de IA").
        # Rate limit 60/min por sender (cost guard contra abuso).
        session_id = f"whatsapp:{sender}:{instance}"
        actor_id_audit = f"whatsapp:{sender}"

        # LGPD-015: request_id + client_ip do request.state (RequestContextMiddleware)
        # Propagados para o wrapper opencode_go para audit log de output scrub.
        ctx_llm = audit_kwargs(request)

        try:
            with session_scope() as db_llm:
                llm_resp = await chat_with_settings(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Voce e a Pietra, assistente de IA do Cartorio do 2o Oficio de "
                                "Notas de Uberlandia. Ajude os clientes de forma prestativa, clara "
                                "e objetiva. Se o cliente solicitar falar com um humano, ou se for "
                                "necessario um especialista, inclua a palavra [HUMANO] na sua "
                                "resposta para fazermos o redirecionamento. Nunca cometa erros "
                                "legais nem invente regras; se nao souber ou for complexo, "
                                "encaminhe para o humano com [HUMANO]."
                            ),
                        },
                        {"role": "user", "content": scrub_result.text},
                    ],
                    consent_granted=True,  # inferido pelo canal WhatsApp
                    actor_id=actor_id_audit,
                    db=db_llm,
                    session_id=session_id,
                    rate_limit_per_minute=settings.opencode_go_rate_limit_per_minute,
                    request_id=ctx_llm.get("request_id"),
                    client_ip=ctx_llm.get("client_ip"),
                )
            bot_response = llm_resp.content
            llm_tokens_in = llm_resp.tokens_in
            llm_tokens_out = llm_resp.tokens_out
            llm_latency_ms = llm_resp.latency_ms
        except ChatError as e:
            if e.kind == "RATE_LIMITED":
                bot_response = (
                    "Voce atingiu o limite de mensagens por minuto. "
                    "Aguarde um instante antes de enviar outra. [HUMANO]"
                )
            elif e.kind == "LGPD_BLOCKED":
                bot_response = (
                    "Preciso confirmar seu consentimento para usar IA. "
                    "Digite SIM para autorizar o atendimento automatizado. [HUMANO]"
                )
            else:
                bot_response = (
                    "Desculpe, tive um problema de comunicacao com o meu cerebro de IA. "
                    "Vou chamar um atendente humano para te ajudar. [HUMANO]"
                )
            handoff = True
            handoff_reason = f"LLM {e.kind}" + (f" status {e.status_code}" if e.status_code else "")
            llm_latency_ms = 0

        if "[HUMANO]" in bot_response:
            handoff = True
            handoff_reason = "Solicitado pelo bot/cliente"
            bot_response = bot_response.replace("[HUMANO]", "").strip()

    # Save to conversas table (best-effort, nao bloqueia webhook se DB falhar)
    try:
        with session_scope() as db:
            from app.models.conversa import Conversa

            conversa = Conversa(
                canal="whatsapp",
                external_id=sender,
                raw_message_hash=raw_message_hash,
                raw_message_scrubbed=scrub_result.text,
                intent_detected=intent,
                confidence_score=1.0 if not handoff else 0.0,
                bot_response=bot_response,
                handoff_to_human=handoff,
                handoff_at=datetime.datetime.now(datetime.timezone.utc) if handoff else None,
                handoff_reason=handoff_reason,
                llm_model=settings.opencode_go_model,
                llm_tokens_in=llm_tokens_in,
                llm_tokens_out=llm_tokens_out,
                llm_latency_ms=llm_latency_ms,
            )
            db.add(conversa)
    except Exception:
        pass

    # Save to Redis active session cache (ADR-014 - multi-tenant)
    try:
        import json

        r_client = redis.from_url(settings.redis_url, socket_timeout=2.0)
        redis_key = f"cartorio:sess:{sender}"
        user_msg = json.dumps(
            {
                "role": "user",
                "content": scrub_result.text,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )
        r_client.rpush(redis_key, user_msg)
        if bot_response:
            bot_msg = json.dumps(
                {
                    "role": "assistant",
                    "content": bot_response,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
            )
            r_client.rpush(redis_key, bot_msg)
        r_client.expire(redis_key, settings.redis_session_ttl_seconds)
        r_client.close()
    except Exception:
        pass

    return {
        "status": "ok",
        "response": bot_response,
        "scrubbed": scrub_result.text[:200],
        # P0.1 - LGPD response shape (cartorio-lgpd audit 2026-06-23):
        # explicit flags para o cliente (e para integradores como
        # cartorio-n8n) saberem se PII foi detectado e se handoff
        # humano foi acionado. Substitui o "status: ok" generico que
        # escondia o signal de bloqueio. Valores:
        # - pii_blocked: True se scrub() redatou >= 1 PII
        # - needs_human_handoff: True se handoff foi acionado (PII
        #   detectada, LLM error, ou [HUMANO] na resposta)
        # - handoff_reason: motivo do handoff ("PII detectada",
        #   "LLM RATE_LIMITED", "Solicitado pelo bot/cliente")
        "pii_blocked": scrub_result.redaction_count > 0,
        "needs_human_handoff": handoff,
        "handoff_reason": handoff_reason,
    }


# ============================================================================
# Audit
# ============================================================================


@api_router.post(
    "/audit/verify",
    tags=["audit"],
    summary="Verificar integridade da cadeia de audit log",
    description=(
        "Recalcula hash SHA256 + HMAC de todas as entradas do audit log e "
        "compara com o valor armazenado. Retorna `chain_ok=True` se a cadeia "
        "esta integra, ou `chain_ok=False` com `last_valid_position` indicando "
        "onde a quebra foi detectada. Recomendado rodar diariamente via cron."
    ),
    response_description="Status da cadeia + posicao da ultima entrada valida.",
)
async def audit_verify() -> dict:
    """Verifica integridade da cadeia de audit log."""
    with session_scope() as db:
        ok, last_valid = AuditService.verify_chain(db)
    return {"chain_ok": ok, "last_valid_position": last_valid}


# ============================================================================
# Health Radar
# ============================================================================


@api_router.get(
    "/health/live",
    tags=["health"],
    summary="Liveness probe (sem dependencias externas)",
    description=(
        "Liveness probe padrao Kubernetes/Portainer. Retorna 200 se o processo "
        "esta vivo. NAO consulta DB/Redis/LLM (sem deps = sem falso negativo). "
        "Usado pelo container orchestrator pra decidir restart."
    ),
    response_description="200 com {status: alive}.",
)
async def health_live() -> dict:
    """Liveness probe: processo Python vivo?"""
    from app import __version__  # type: ignore[attr-defined]

    return {"status": "alive", "service": "cartorio-api", "version": __version__}


@api_router.get(
    "/health/ready",
    tags=["health"],
    summary="Readiness probe (verifica dependencias criticas)",
    description=(
        "Readiness probe padrao Kubernetes/Portainer. Retorna 200 se todas as "
        "dependencias criticas (DB, Redis) estao saudaveis. Retorna 503 com "
        "detalhes se alguma dep cair. Usado pelo load balancer pra decidir roteamento."
    ),
    response_description="200 ready / 503 not_ready.",
)
async def health_ready() -> JSONResponse:
    """Readiness probe: DB + Redis respondendo?"""
    from app.db import engine
    from sqlalchemy import text

    checks: dict[str, dict] = {}

    # Check DB
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["db"] = {"status": "online"}
    except Exception as e:
        checks["db"] = {"status": "offline", "error": str(e)[:200]}

    # Check Redis (se configurado)
    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        try:
            import redis  # type: ignore[import-untyped]

            r = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            checks["redis"] = {"status": "online"}
        except Exception as e:
            checks["redis"] = {"status": "offline", "error": str(e)[:200]}

    all_ok = all(c.get("status") == "online" for c in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
        },
    )


@api_router.get(
    "/health/db",
    tags=["health"],
    summary="Health check granular: PostgreSQL",
    description=(
        "Verifica conectividade com PostgreSQL via SQLAlchemy `SELECT 1`. "
        "Retorna 200 com `{status: 'online', latency_ms: ...}` se OK, "
        "ou 503 com `{status: 'offline', error: ...}` se falhar."
    ),
    response_description="Status do banco + latencia em ms.",
)
async def health_db() -> JSONResponse:
    """Health check granular do PostgreSQL."""
    from app.db import engine
    from sqlalchemy import text

    start = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.time() - start) * 1000, 2)
        return JSONResponse(
            status_code=200,
            content={"status": "online", "service": "postgresql", "latency_ms": latency_ms},
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "offline", "service": "postgresql", "error": str(e)},
        )


@api_router.get(
    "/health/redis",
    tags=["health"],
    summary="Health check granular: Redis",
    description=(
        "Verifica conectividade com Redis via PING. "
        "Retorna 200 com `{status: 'online', latency_ms: ...}` se OK, "
        "ou 503 com `{status: 'offline', error: ...}` se falhar."
    ),
    response_description="Status do Redis + latencia em ms.",
)
async def health_redis() -> JSONResponse:
    """Health check granular do Redis."""

    start = time.time()
    try:
        import redis.asyncio as redis_async_lib

        r = redis_async_lib.from_url(settings.redis_url, socket_timeout=2.0)
        await r.ping()
        await r.close()
        latency_ms = round((time.time() - start) * 1000, 2)
        return JSONResponse(
            status_code=200,
            content={"status": "online", "service": "redis", "latency_ms": latency_ms},
        )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "offline", "service": "redis", "error": str(e)},
        )


@api_router.get(
    "/health/llm",
    tags=["health"],
    summary="Health check granular: LLM provider (Opencode-Go / OpenClaw)",
    description=(
        "Verifica conectividade com o provider LLM primario (Opencode-Go) "
        "via GET na URL base. Retorna 200 se responde (qualquer status), "
        "ou 503 se falha de conexao."
    ),
    response_description="Status do LLM provider.",
)
async def health_llm() -> JSONResponse:
    """Health check granular do LLM provider primario."""

    primary = settings.opencode_go_base_url or settings.openclaw_base_url
    if not primary:
        return JSONResponse(
            status_code=503,
            content={"status": "offline", "service": "llm", "error": "No LLM provider configured"},
        )
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(primary)
            return JSONResponse(
                status_code=200 if resp.status_code < 500 else 503,
                content={
                    "status": "online" if resp.status_code < 500 else "degraded",
                    "service": "llm",
                    "provider": "opencode_go" if settings.opencode_go_base_url else "openclaw",
                    "http_status": resp.status_code,
                },
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "offline", "service": "llm", "error": str(e)},
        )


@api_router.get(
    "/health/radar",
    tags=["health"],
    summary="Health radar multi-servico",
    description=(
        "Verifica conectividade de **todos** os 7 servicos da suite em paralelo: "
        "PostgreSQL, Redis, n8n, OpenClaw gateway, Evolution API, Chatwoot, Supabase. "
        "Retorna status individual por servico + status agregado (`green` se todos online). "
        "Para checks granulares use `/health/db`, `/health/redis`, `/health/llm`."
    ),
    response_description="Status por servico + status agregado.",
)
async def health_radar() -> dict:
    """Verifica conexoes de todos os servicos da suite."""
    from app.db import engine
    from sqlalchemy import text

    # 1. DB (PostgreSQL via SQLAlchemy)
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    # 2. Redis
    redis_ok = False
    try:
        r = redis.from_url(settings.redis_url, socket_timeout=2.0)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    # 3. n8n, OpenClaw, Evolution API, Chatwoot, Supabase (via httpx)
    n8n_ok = False
    openclaw_ok = False
    evolution_ok = False
    chatwoot_ok = False
    supabase_ok = False

    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.get(f"{settings.n8n_base_url}/healthz")
            if resp.status_code == 200:
                n8n_ok = True
        except Exception:
            pass

        try:
            resp = await client.get(f"{settings.openclaw_base_url}/health")
            if resp.status_code == 200:
                openclaw_ok = True
        except Exception:
            pass

        try:
            resp = await client.get(f"{settings.evolution_base_url}/")
            if resp.status_code == 200:
                evolution_ok = True
        except Exception:
            pass

        # Chatwoot - checa /health diretamente (retorna 200 {"status": "woot"})
        if settings.chatwoot_base_url:
            try:
                resp = await client.get(f"{settings.chatwoot_base_url}/health")
                if resp.status_code in (200, 201, 401, 403):
                    chatwoot_ok = True
            except Exception:
                pass

        # Supabase - checa /auth/v1/health (pode retornar 200, 401 ou 405 via Kong auth gate se acessado de fora)
        if settings.supabase_url:
            try:
                resp = await client.get(f"{settings.supabase_url}/auth/v1/health")
                if resp.status_code in (200, 401, 405):
                    supabase_ok = True
            except Exception:
                pass

    overall_status = (
        "green"
        if (
            db_ok
            and redis_ok
            and n8n_ok
            and openclaw_ok
            and evolution_ok
            and chatwoot_ok
            and supabase_ok
        )
        else "red"
    )

    return {
        "status": overall_status,
        "services": {
            "database": "online" if db_ok else "offline",
            "redis": "online" if redis_ok else "offline",
            "n8n": "online" if n8n_ok else "offline",
            "openclaw": "online" if openclaw_ok else "offline",
            "evolution": "online" if evolution_ok else "offline",
            "chatwoot": "online" if chatwoot_ok else "offline",
            "supabase": "online" if supabase_ok else "offline",
        },
    }


# ============================================================================
# Health Integracoes (v0.6.0) - B0.2 Sprint 3
# Faltava esse endpoint no workflow N8N #30 (Health Deep Check 15min).
# Mais detalhado que /health/radar: testa TBM LLM provider + auth + latencia.
# ============================================================================


@api_router.get(
    "/health/integracoes",
    tags=["health"],
    summary="Status de TODAS integracoes externas (N8N workflow #30)",
    description=(
        "Verifica conectividade + latencia + auth de **cada integracao externa** "
        "em paralelo: N8N, OpenClaw Gateway, Evolution API, Chatwoot, Supabase, "
        "OpenCode-Go (LLM), Redis, PostgreSQL. Retorna status individual + "
        "latencia_ms + status_code + erro (se houver).\n\n"
        "Diferenca vs /health/radar:\n"
        "- /health/radar: retorna so 'online'/'offline' por servico (7 servicos)\n"
        "- /health/integracoes: retorna latencia + status_code + auth_check "
        "  + LLM provider especifico (8 servicos)\n\n"
        "Usado pelo workflow N8N #30 (Health Deep Check 15min) que alerta "
        "via Chatwoot se qualquer != ok. **B0.2 Sprint 3** corrige o 404 "
        "que o workflow vinha recebendo desde 2026-06-23."
    ),
    response_description="Status por integracao (status, latency_ms, status_code, erro).",
)
async def health_integracoes() -> dict:
    """Verifica conectividade de TODAS as integracoes externas com latencia."""
    import time

    from app.db import engine
    from sqlalchemy import text

    results: dict[str, dict] = {}

    async def check(name: str, coro) -> dict:
        """Helper: mede latencia + captura erro sem explodir."""
        start = time.perf_counter()
        result = {"status": "offline", "latency_ms": 0, "status_code": None, "erro": None}
        try:
            resp = await coro
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result["latency_ms"] = elapsed_ms
            result["status_code"] = getattr(resp, "status_code", None)
            # 2xx = online; 401/403 = online (auth gate esperado); 405 = metodo nao permitido mas server UP
            if resp.status_code in (200, 201, 401, 403, 405):
                result["status"] = "online"
            else:
                result["erro"] = f"HTTP {resp.status_code}"
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result["latency_ms"] = elapsed_ms
            result["erro"] = str(e)[:200]
        return result

    # 1. PostgreSQL
    def _db_check():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return _FakeResp(200)

    # 2. Redis
    def _redis_check():
        r = redis.from_url(settings.redis_url, socket_timeout=2.0)
        r.ping()
        return _FakeResp(200)

    async with httpx.AsyncClient(timeout=3.0) as client:
        # HTTP-based checks (paralelos)
        checks_to_run = {
            "n8n": check("n8n", client.get(f"{settings.n8n_base_url}/healthz")),
            "openclaw": check("openclaw", client.get(f"{settings.openclaw_base_url}/health")),
            "evolution": check("evolution", client.get(f"{settings.evolution_base_url}/")),
        }
        if settings.chatwoot_base_url:
            checks_to_run["chatwoot"] = check(
                "chatwoot", client.get(f"{settings.chatwoot_base_url}/health")
            )
        if settings.supabase_url:
            checks_to_run["supabase"] = check(
                "supabase", client.get(f"{settings.supabase_url}/auth/v1/health")
            )
        # OpenCode-Go LLM: usa endpoint /models se disponivel, senao root
        if settings.opencode_go_base_url:
            checks_to_run["opencode_go"] = check(
                "opencode_go", client.get(f"{settings.opencode_go_base_url}/models")
            )

        # Sync checks (DB + Redis) - executa direto
        try:
            start = time.perf_counter()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            results["database"] = {
                "status": "online",
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "status_code": 200,
                "erro": None,
            }
        except Exception as e:
            results["database"] = {
                "status": "offline",
                "latency_ms": 0,
                "status_code": None,
                "erro": str(e)[:200],
            }

        try:
            start = time.perf_counter()
            r = redis.from_url(settings.redis_url, socket_timeout=2.0)
            r.ping()
            results["redis"] = {
                "status": "online",
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "status_code": 200,
                "erro": None,
            }
        except Exception as e:
            results["redis"] = {
                "status": "offline",
                "latency_ms": 0,
                "status_code": None,
                "erro": str(e)[:200],
            }

        # Aguarda HTTP checks em paralelo
        import asyncio

        http_results = await asyncio.gather(*checks_to_run.values(), return_exceptions=True)
        for name, res in zip(checks_to_run.keys(), http_results, strict=True):
            if isinstance(res, Exception):
                results[name] = {
                    "status": "offline",
                    "latency_ms": 0,
                    "status_code": None,
                    "erro": str(res)[:200],
                }
            else:
                # mypy: res eh dict[str, Any] (nao Exception) nesse branch
                results[name] = cast("dict[str, Any]", res)

    # Status agregado: green se TODOS online; senao red (com count de offline)
    offline_count = sum(1 for r in results.values() if r["status"] != "online")
    overall = "green" if offline_count == 0 else "red"

    return {
        "status": overall,
        "offline_count": offline_count,
        "integracoes": results,
        "checked_at": time.time(),
    }


class _FakeResp:
    """Helper para checks sincronos (DB/Redis) - imita shape de httpx.Response."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


# ============================================================================
# Health Backup (v0.4.0) - usado pelo N8N workflow #09 Monitor Backup Diario
# ============================================================================


@api_router.get(
    "/health/backup",
    tags=["health"],
    summary="Status do backup diario (N8N workflow #09)",
    description=(
        "Le o diretorio /var/backups/cartorio na VPS via SSH (Tailscale) e "
        "retorna idade do ultimo backup, quantidade de arquivos e tamanho. "
        "Usado pelo workflow N8N '09 - Monitor Backup Diario' para alertar "
        "via Chatwoot se backup falhou ou esta ausente ha > 26h."
    ),
    response_description="Status do backup: ok=true se ultimo < 26h, senao ok=false.",
)
async def health_backup() -> dict:
    """Verifica idade e tamanho do backup diario.

    E1.S4.T2 (fix 2026-06-23): leitura DIRETA via `os.listdir` + `os.path.getmtime`.
    NAO usa `subprocess` nem `docker exec` (privilegios desnecessarios).

    Pre-requisito OPS (NAO codigo):
      Volume mount do diretorio de backups no container cartorio_api.
      Em Easypanel: Services > cartorio_api > Volumes > Mount:
        Host: /var/backups/cartorio
        Container: /var/backups/cartorio
        Mode: read-only (recomendado)
      Sem o mount, o diretorio nao existe no container e o endpoint
      retorna ok=false com `error="No such directory"`.

    Usado pelo N8N workflow #09 (Monitor Backup Diario) que alerta via
    Chatwoot se backup falhou ou esta ausente ha > 26h.
    """
    from datetime import datetime, timezone

    BACKUP_DIR = "/var/backups/cartorio"
    last_backup_age_hours: float | None = None
    file_count = 0
    total_size_bytes = 0
    ok = False
    last_backup_iso: str | None = None
    error_msg: str | None = None

    try:
        if not os.path.isdir(BACKUP_DIR):
            return {
                "ok": False,
                "error": f"Diretorio de backup nao acessivel: {BACKUP_DIR} (verificar volume mount)",
                "file_count": 0,
                "dir_size": "?",
                "last_backup_age_hours": None,
                "last_backup_iso": None,
                "age_hours": None,
            }

        # Lista arquivos .tar.gz e calcula idade + tamanho
        newest_mtime: float | None = None
        for entry in os.listdir(BACKUP_DIR):
            if not entry.endswith(".tar.gz"):
                continue
            full_path = os.path.join(BACKUP_DIR, entry)
            try:
                mtime = os.path.getmtime(full_path)
                size = os.path.getsize(full_path)
            except OSError:
                # Arquivo sumiu entre listdir e stat (race) — pula
                continue
            file_count += 1
            total_size_bytes += size
            if newest_mtime is None or mtime > newest_mtime:
                newest_mtime = mtime

        if newest_mtime is not None:
            now_ts = datetime.now(timezone.utc).timestamp()
            age_s = now_ts - newest_mtime
            last_backup_age_hours = round(age_s / 3600, 1)
            last_backup_iso = datetime.fromtimestamp(newest_mtime, timezone.utc).isoformat()
            ok = last_backup_age_hours < 26

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    # Humaniza tamanho: B / K / M / G
    dir_size = "0"
    if total_size_bytes >= 1024**3:
        dir_size = f"{total_size_bytes / 1024**3:.1f}G"
    elif total_size_bytes >= 1024**2:
        dir_size = f"{total_size_bytes / 1024**2:.1f}M"
    elif total_size_bytes >= 1024:
        dir_size = f"{total_size_bytes / 1024:.1f}K"
    elif total_size_bytes > 0:
        dir_size = f"{total_size_bytes}B"

    payload: dict = {
        "ok": ok,
        "last_backup_age_hours": last_backup_age_hours,
        "last_backup_iso": last_backup_iso,
        "file_count": file_count,
        "dir_size": dir_size,
        "age_hours": last_backup_age_hours,
    }
    if error_msg:
        payload["error"] = error_msg
    return payload


# ============================================================================
# Agendamento disponibilidade (v0.4.0) - N8N workflow #05
# ============================================================================


@api_router.get(
    "/agendamento/disponibilidade",
    tags=["agendamento"],
    summary="Consultar disponibilidade de agenda (N8N workflow #05)",
    description=(
        "Retorna slots disponiveis para atendimento presencial no cartorio. "
        "v0.4.0 MVP: tabela estatica de segunda a sexta 09-17h com 5 vagas/hora. "
        "Sprint 2 integra com Google Calendar API."
    ),
    response_description="Lista de slots disponiveis no dia solicitado.",
)
async def agendamento_disponibilidade(
    dia: Annotated[
        str,
        Query(
            description="Dia da semana em portugues.",
            examples=["segunda", "terca", "quarta", "quinta", "sexta"],
        ),
    ],
    hora: Annotated[
        int,
        Query(ge=0, le=23, description="Hora do dia (0-23)."),
    ] = 9,
) -> dict:
    """Retorna vagas disponiveis para o slot pedido + slots seguintes."""
    dias_validos = {"segunda", "terca", "quarta", "quinta", "sexta"}
    if dia.lower() not in dias_validos:
        return {
            "vagas": 0,
            "slots": [],
            "erro": f"dia '{dia}' invalido. Validos: {sorted(dias_validos)}",
        }

    if hora < 9 or hora >= 17:
        return {"vagas": 0, "slots": [], "erro": "Atendimento apenas das 09h as 17h"}

    # MVP: tabela estatica - 5 vagas/hora
    # TODO Sprint 2: integrar com Google Calendar API para bloquear slots ja agendados
    slots = []
    for h in range(max(9, hora), 17):
        slots.append({"dia": dia.lower(), "hora": h, "vagas": 5})

    return {"dia": dia.lower(), "hora_pedida": hora, "vagas": 5, "slots": slots}


# ============================================================================
# Segunda via de documento (v0.4.0) - N8N workflow #06
# ============================================================================


@api_router.post(
    "/documento/segunda-via",
    tags=["documento"],
    summary="Emitir segunda via de documento (N8N workflow #06)",
    description=(
        "Gera PDF da segunda via do documento associado ao protocolo informado. "
        "v0.4.0 MVP: retorna URL placeholder. Sprint 2: integracao com storage "
        "Supabase para gerar PDF real."
    ),
    response_description="URL do PDF + validade em horas.",
)
async def documento_segunda_via(
    request: Request,
    protocolo: Annotated[str, Query(description="Numero do protocolo (YYYY-NNNNN).")],
    canal: Annotated[
        str, Query(description="Canal de envio: whatsapp/email/presencial.")
    ] = "whatsapp",
) -> dict:
    """Gera link de download da segunda via."""
    import hashlib

    # MVP: hash determinístico + timestamp = URL placeholder
    h = hashlib.sha256(f"{protocolo}:{time.time()}".encode()).hexdigest()[:16]
    url_pdf = (
        f"https://supbase.2notasudi.com.br/storage/v1/object/sign/documentos/{protocolo}-{h}.pdf"
    )

    # LGPD art. 37: audit log obrigatorio em toda mutacao (A01)
    try:
        with session_scope() as db:
            AuditService.log(
                db,
                actor_id="api",
                actor_type="api",
                action="documento.segunda_via.emitida",
                resource=f"protocolo:{protocolo}",
                payload={
                    "canal": canal,
                    "url_pdf_expires_hours": 24,
                },
                **audit_kwargs(request),
            )
    except Exception:
        # Audit eh best-effort; NAO quebra a operacao principal
        pass

    return {
        "url_pdf": url_pdf,
        "validade_horas": 24,
        "protocolo": protocolo,
        "canal": canal,
    }


# ============================================================================
# Atendimentos (v0.4.2) - registro de handoff humano + pesquisa satisfacao
# ============================================================================


@api_router.get(
    "/atendimento/ultimas-24h",
    tags=["atendimento"],
    summary="Listar atendimentos concluidos nas ultimas 24h (N8N workflow #07)",
    description=(
        "Retorna lista de atendimentos concluidos nas ultimas 24h que ainda "
        "nao receberam pesquisa de satisfacao. Usado pelo workflow N8N #07."
    ),
    response_description="Lista de atendimentos com id/canal/tipo.",
)
async def atendimentos_ultimas_24h() -> dict:
    """Lista atendimentos concluidos nas ultimas 24h (pesquisa satisfacao)."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.atendimento import Atendimento
    from app.services.atendimento_cache import get_cached, set_cached

    # A18 - squad A: cache Redis 60s. Reduz carga DB 4-12x em pico.
    # Fail-open: se Redis offline, retorna None e cai pro DB.
    cached = get_cached("24h")
    if cached is not None:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    with session_scope() as db:
        rows = (
            db.execute(
                select(Atendimento)
                .where(
                    Atendimento.concluido_em >= cutoff,
                    Atendimento.pesquisa_enviada_em.is_(None),
                )
                .order_by(Atendimento.concluido_em.desc())
                .limit(200)
            )
            .scalars()
            .all()
        )

        atendimentos = [
            {
                "id": a.id,
                "protocolo_id": a.protocolo_id,
                "canal": a.canal,
                "external_id": a.external_id,
                "tipo": a.tipo,
                "concluido_em": a.concluido_em.isoformat() if a.concluido_em else None,
            }
            for a in rows
        ]

    payload = {
        "window_hours": 24,
        "count": len(atendimentos),
        "atendimentos": atendimentos,
    }
    # A18: cache Redis 60s - reduz carga DB no N8N workflow #07
    set_cached(payload, "24h")
    return payload


@api_router.post(
    "/atendimento/{atendimento_id}/pesquisa-enviada",
    tags=["atendimento"],
    summary="Marcar pesquisa de satisfacao como enviada (N8N workflow #07)",
)
async def marcar_pesquisa_enviada(request: Request, atendimento_id: int) -> dict:
    """Marca pesquisa_enviada_em = now() para evitar envio duplicado."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.atendimento import Atendimento

    with session_scope() as db:
        a = db.execute(
            select(Atendimento).where(Atendimento.id == atendimento_id)
        ).scalar_one_or_none()
        if a is None:
            # LGPD art. 37: audit log de tentativa falhada (A01)
            try:
                AuditService.log(
                    db,
                    actor_id="api",
                    actor_type="api",
                    action="atendimento.pesquisa_enviada.not_found",
                    resource=f"atendimento:{atendimento_id}",
                    payload={"result": "not_found"},
                    **audit_kwargs(request),
                )
            except Exception:
                pass
            return {"ok": False, "error": "not_found"}
        a.pesquisa_enviada_em = datetime.now(timezone.utc)
        # LGPD art. 37: audit log de mutacao bem-sucedida (A01)
        try:
            AuditService.log(
                db,
                actor_id="api",
                actor_type="api",
                action="atendimento.pesquisa_enviada",
                resource=f"atendimento:{atendimento_id}",
                payload={"timestamp_envio": a.pesquisa_enviada_em.isoformat()},
                **audit_kwargs(request),
            )
        except Exception:
            pass
    return {"ok": True, "atendimento_id": atendimento_id}


@api_router.post(
    "/atendimento",
    tags=["atendimento"],
    summary="Criar atendimento (handoff Chatwoot ou webhook externo)",
    description=(
        "Cria atendimento. Chamado pelo workflow #03 (handoff humano) ou "
        "diretamente pela UI quando conversa e escalada."
    ),
)
async def criar_atendimento(request: Request, payload: dict) -> dict:
    """Cria atendimento (handoff)."""
    from datetime import datetime, timezone
    from app.models.atendimento import Atendimento

    canal = payload.get("canal", "whatsapp")
    external_id = payload.get("external_id", "unknown")
    tipo = payload.get("tipo", "duvida")
    contexto = payload.get("contexto_scrubbed")
    chatwoot_conv = payload.get("chatwoot_conversation_id")
    chatwoot_inbox = payload.get("chatwoot_inbox_id")
    chatwoot_agent = payload.get("chatwoot_agent_id")
    protocolo_id = payload.get("protocolo_id")
    cliente_cpf = payload.get("cliente_cpf")

    cliente_id = None
    if cliente_cpf:
        cpf_hash = hash_pii(cliente_cpf, salt=settings.audit_hmac_key[:32])
        with session_scope() as db:
            cliente = db.execute(
                select(Cliente).where(Cliente.cpf_hash == cpf_hash)
            ).scalar_one_or_none()
            if cliente is None and payload.get("cliente_nome"):
                cliente = Cliente(
                    cpf_hash=cpf_hash,
                    nome=payload["cliente_nome"],
                    consentimento_lgpd=True,
                    consentimento_em=datetime.now(timezone.utc),
                    consentimento_canal=canal,
                )
                db.add(cliente)
                db.flush()
                cliente_id = cliente.id
            elif cliente:
                cliente_id = cliente.id

    with session_scope() as db:
        a = Atendimento(
            canal=canal,
            external_id=external_id,
            tipo=tipo,
            contexto_scrubbed=contexto,
            chatwoot_conversation_id=chatwoot_conv,
            chatwoot_inbox_id=chatwoot_inbox,
            chatwoot_agent_id=chatwoot_agent,
            protocolo_id=protocolo_id,
            cliente_id=cliente_id,
            handoff_para_humano=True,
            iniciado_em=datetime.now(timezone.utc),
            status="em_atendimento",
        )
        db.add(a)
        db.flush()
        atendimento_id = a.id

        AuditService.log(
            db,
            actor_id=external_id,
            actor_type="bot",
            action="atendimento.create",
            resource=f"atendimento:{atendimento_id}",
            payload={
                "canal": canal,
                "tipo": tipo,
                "chatwoot_conversation_id": chatwoot_conv,
                "protocolo_id": protocolo_id,
                "pii_scrubbed": True,
            },
            **audit_kwargs(request),
        )

    return {"ok": True, "atendimento_id": atendimento_id}


@api_router.post(
    "/atendimento/{atendimento_id}/concluir",
    tags=["atendimento"],
    summary="Concluir atendimento (registra timestamp para pesquisa 24h)",
)
async def concluir_atendimento(
    request: Request,
    atendimento_id: int,
    payload: dict | None = None,
) -> dict:
    """Marca atendimento como concluido."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.atendimento import Atendimento

    nota = (payload or {}).get("nota")
    comentario = (payload or {}).get("comentario")

    with session_scope() as db:
        a = db.execute(
            select(Atendimento).where(Atendimento.id == atendimento_id)
        ).scalar_one_or_none()
        if a is None:
            # LGPD art. 37: audit log de tentativa falhada (A01)
            try:
                AuditService.log(
                    db,
                    actor_id="api",
                    actor_type="api",
                    action="atendimento.concluir.not_found",
                    resource=f"atendimento:{atendimento_id}",
                    payload={"result": "not_found"},
                    **audit_kwargs(request),
                )
            except Exception:
                pass
            return {"ok": False, "error": "not_found"}
        a.concluido_em = datetime.now(timezone.utc)
        a.status = "concluido"
        if nota is not None:
            a.pesquisa_nota = nota
        if comentario is not None:
            a.pesquisa_comentario = comentario
        # LGPD art. 37: audit log de mutacao bem-sucedida (A01)
        try:
            AuditService.log(
                db,
                actor_id="api",
                actor_type="api",
                action="atendimento.concluir",
                resource=f"atendimento:{atendimento_id}",
                payload={
                    "concluido_em": a.concluido_em.isoformat(),
                    "tem_pesquisa": nota is not None or comentario is not None,
                },
                **audit_kwargs(request),
            )
        except Exception:
            pass

    return {"ok": True, "atendimento_id": atendimento_id}


@api_router.get(
    "/atendimento/{session_id}/historico",
    tags=["atendimento"],
    summary="Obter historico de atendimento (Redis + Supabase)",
    description=(
        "Busca o historico de mensagens de uma sessao (canal/telefone). "
        "Consulta primeiro o cache quente no Redis e depois une/complementa "
        "com o historico de longo prazo persistido no Supabase."
    ),
)
async def obter_historico_atendimento(session_id: str) -> dict:
    """Retorna o historico completo de mensagens para uma sessao."""
    import json
    from sqlalchemy import select
    from app.models.conversa import Conversa

    messages = []

    # 1. Tenta buscar do cache quente do Redis (ADR-014)
    try:
        r_client = redis.from_url(settings.redis_url, socket_timeout=2.0, decode_responses=True)
        redis_key = f"cartorio:sess:{session_id}"
        cached = r_client.lrange(redis_key, 0, -1)
        r_client.close()
        if cached:
            for item in cached:
                try:
                    messages.append(json.loads(item))
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Se cache estiver vazio ou para garantir dados historicos, consulta o PostgreSQL
    if not messages:
        try:
            with session_scope() as db:
                rows = (
                    db.execute(
                        select(Conversa)
                        .where(Conversa.external_id == session_id)
                        .order_by(Conversa.created_at.asc())
                    )
                    .scalars()
                    .all()
                )

                for row in rows:
                    messages.append(
                        {
                            "role": "user",
                            "content": row.raw_message_scrubbed,
                            "timestamp": row.created_at.isoformat() if row.created_at else None,
                        }
                    )
                    if row.bot_response:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": row.bot_response,
                                "timestamp": row.updated_at.isoformat() if row.updated_at else None,
                            }
                        )
        except Exception:
            pass

    return {"session_id": session_id, "total": len(messages), "messages": messages}


# ============================================================================
# List active sessions (Sprint 3 follow-up E1.S4.T1 - WF #15 Session Sync)
# ============================================================================


@api_router.get(
    "/atendimento/list-active",
    tags=["atendimento"],
    summary="Lista sessoes ativas (ultimas N horas)",
    description=(
        "Retorna lista de sessoes com atividade recente, agrupadas por "
        "external_id + canal. Usado pelo N8N workflow #15 (Session Sync) "
        "que sincroniza Redis cache quente com DB. "
        "Substitui o proposto GET /sessao/list-active (que nunca existiu) "
        "com path alinhado aos demais /atendimento/*. "
        "Read-only, sem PII nova exposta (external_id ja eh publico para o cartorio)."
    ),
    response_description="Lista de sessoes ativas com external_id, canal e last_activity.",
)
async def listar_sessoes_ativas(
    since_hours: Annotated[
        int,
        Query(
            ge=1,
            le=168,  # max 7 dias
            description="Janela de tempo em horas (default 24h, max 7 dias).",
        ),
    ] = 24,
) -> dict:
    """Lista sessoes ativas nas ultimas N horas.

    Retorna sessoes unicas por (external_id, canal) com last_activity = MAX(updated_at).
    Ordenado por atividade mais recente primeiro.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func
    from app.models.conversa import Conversa

    with session_scope() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        # GROUP BY external_id + canal, MAX(updated_at) = last_activity
        rows = (
            db.query(
                Conversa.external_id,
                Conversa.canal,
                func.max(Conversa.updated_at).label("last_activity"),
            )
            .filter(Conversa.updated_at >= cutoff)
            .group_by(Conversa.external_id, Conversa.canal)
            .order_by(func.max(Conversa.updated_at).desc())
            .all()
        )

    sessions = [
        {
            "external_id": r.external_id,
            "canal": r.canal,
            "last_activity": r.last_activity.isoformat() if r.last_activity else None,
        }
        for r in rows
    ]
    return {"count": len(sessions), "sessions": sessions, "since_hours": since_hours}


# ============================================================================
# Chatwoot webhook (v0.4.2) + Sprint 2 (HMAC + idempotency)
# ============================================================================


@api_router.post(
    "/webhook/chatwoot",
    tags=["webhook"],
    summary="Webhook Chatwoot (HMAC + idempotency)",
    description=(
        "Recebe webhooks do Chatwoot. Valida signature HMAC-SHA256 (se "
        "CHATWOOT_WEBHOOK_SECRET configurado), deduplica por event_id, e "
        "processa conversation_status_changed -> resolved marcando o "
        "atendimento como concluido (workflow #07 pesquisa 24h depois)."
    ),
)
async def webhook_chatwoot(request: Request) -> dict:
    """Processa webhook do Chatwoot com HMAC + idempotency (Sprint 2)."""
    import json as _json
    from app.services.chatwoot_handoff import process_chatwoot_event

    raw_body = await request.body()
    try:
        payload = _json.loads(raw_body) if raw_body else {}
    except Exception:
        # LGPD art. 37: audit log de tentativa com payload invalido (A01)
        try:
            with session_scope() as db:
                AuditService.log(
                    db,
                    actor_id="chatwoot",
                    actor_type="webhook",
                    action="webhook.chatwoot.invalid_json",
                    resource="webhook:chatwoot",
                    payload={"body_size": len(raw_body)},
                    **audit_kwargs(request),
                )
        except Exception:
            pass
        return {"status": "rejected", "reason": "invalid_json"}

    signature = request.headers.get("X-Chatwoot-Signature")

    with session_scope() as db:
        result = process_chatwoot_event(db, payload, signature=signature, raw_body=raw_body)
        # LGPD art. 37: audit log de webhook processado (A01)
        try:
            AuditService.log(
                db,
                actor_id="chatwoot",
                actor_type="webhook",
                action="webhook.chatwoot.received",
                resource="webhook:chatwoot",
                payload={
                    "event_type": payload.get("event") if isinstance(payload, dict) else None,
                    "result_status": result.get("status") if isinstance(result, dict) else None,
                    "result_action": result.get("action") if isinstance(result, dict) else None,
                },
                **audit_kwargs(request),
            )
        except Exception:
            # Audit eh best-effort; NAO quebra o webhook
            pass

    return result


# ============================================================================
# CRON stale detector (Sprint 2) - chamado pelo N8N workflow #23
# ============================================================================


@api_router.post(
    "/cron/stale-detector",
    tags=["cron"],
    summary="CRON: marca atendimentos parados como stale (N8N workflow #23)",
    description=(
        "Chamado pelo workflow N8N #23 a cada 5min. Marca atendimentos com "
        "updated_at > STALE_THRESHOLD_MINUTES como 'stale'. Idempotente."
    ),
)
async def cron_stale_detector(request: Request) -> dict:
    """Roda stale detector."""
    from app.services.stale_detector import mark_stale_atendimentos

    with session_scope() as db:
        result = mark_stale_atendimentos(db, threshold_minutes=settings.stale_threshold_minutes)
        # LGPD art. 37: audit log de cron executado (A01)
        try:
            AuditService.log(
                db,
                actor_id="cron",
                actor_type="system",
                action="cron.stale_detector.run",
                resource="cron:stale_detector",
                payload={
                    "marked_count": result.get("marked_count", 0)
                    if isinstance(result, dict)
                    else 0,
                    "threshold_minutes": settings.stale_threshold_minutes,
                },
                **audit_kwargs(request),
            )
        except Exception:
            pass
    return result


# ============================================================================
# LGPD - Direito ao esquecimento (DELETE /cliente/{id})
# ============================================================================


@api_router.delete(
    "/cliente/{cliente_id}",
    tags=["cliente"],
    summary="Direito ao esquecimento (LGPD art. 18 VI)",
    description=(
        "Encerra tratamento de dados pessoais do cliente.\n\n"
        "- Cliente SEM protocolo: HARD DELETE (remove do DB).\n"
        "- Cliente COM protocolo: SOFT DELETE (anonimiza PII, marca motivo_encerramento).\n"
        "  Mantem integridade referencial dos atos cartorarios (Provimento CNJ 74/2018).\n\n"
        "Requer `X-API-Key` (escrevente autorizado). Idempotente: 2a chamada = 409.\n\n"
        "Ver ADR-018 para detalhes."
    ),
    responses={
        200: {"description": "Cliente encerrado (hard ou soft)."},
        404: {"description": "Cliente nao encontrado."},
        409: {"description": "Cliente ja revogado (idempotencia)."},
        401: {"description": "X-API-Key ausente ou invalida."},
    },
)
async def delete_cliente(
    request: Request,
    cliente_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Aplica direito ao esquecimento ao cliente (LGPD art. 18 VI)."""
    from app.services.lgpd.direito_esquecimento import (
        ClienteJaRevogadoError,
        ClienteNotFoundError,
        direito_esquecimento,
    )

    # Auth: exige X-API-Key (escrevente autorizado)
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "erro": "UNAUTHORIZED",
                "mensagem": "X-API-Key obrigatoria para DELETE /cliente/{id}.",
            },
        )

    try:
        result = direito_esquecimento(db, cliente_id)
    except ClienteNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "CLIENTE_NOT_FOUND",
                "mensagem": f"Cliente {cliente_id} nao encontrado.",
                "detalhes": {"cliente_id": cliente_id},
            },
        )
    except ClienteJaRevogadoError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "erro": "CLIENTE_JA_REVOGADO",
                "mensagem": str(e),
                "detalhes": {"cliente_id": cliente_id},
            },
        )

    # Audit log LGPD art. 37 (registro de operacao de tratamento)
    audit = AuditService.log(
        db,
        actor_id=f"escrevente:{api_key[:8]}",
        actor_type="bot",
        action=f"cliente.delete.{result.tipo}",
        resource=f"cliente:{cliente_id}",
        payload={
            "cliente_id": cliente_id,
            "tipo": result.tipo,
            "protocolos_ativos": result.protocolos_ativos,
            "motivo": result.motivo.value,
        },
        **audit_kwargs(request),
    )

    return {
        "status": "deleted",
        "tipo": result.tipo,
        "cliente_id": result.cliente_id,
        "protocolos_ativos": result.protocolos_ativos,
        "data_encerramento": result.data_encerramento.isoformat(),
        "motivo": result.motivo.value,
        "audit_id": audit.id,
    }


# ============================================================================
# LGPD - Job retenção (admin)
# ============================================================================


@api_router.post(
    "/admin/retencao/run",
    tags=["admin"],
    summary="Executa job de retenção LGPD (5y/2y)",
    description=(
        "Roda o job de retenção descrito em ADR-019. Aceita `dry_run=true` "
        "para apenas contar sem aplicar mutações.\n\n"
        "Requer `X-API-Key` + `X-Canal=cron` (ou X-Canal=dpo)."
    ),
    responses={
        200: {"description": "Job executado (ou dry-run)."},
        401: {"description": "X-API-Key ausente ou invalida."},
    },
)
async def admin_run_retencao(
    request: Request,
    payload: dict | None = None,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> dict:
    """Executa job de retenção (DPO/cron)."""
    from app.jobs.retencao import RetencaoConfig, run_retencao
    from app.services.audit_context import audit_kwargs

    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={"erro": "UNAUTHORIZED", "mensagem": "X-API-Key obrigatoria."},
        )

    dry_run = bool((payload or {}).get("dry_run", False))
    cfg = RetencaoConfig(enabled=not dry_run)

    result = run_retencao(db, config=cfg)

    # Audit log
    AuditService.log(
        db,
        actor_id="system:retencao",
        actor_type="system",
        action="retencao.run",
        resource="clientes",
        payload={
            "scanned": result.scanned,
            "soft_deleted_5y": result.soft_deleted_5y,
            "soft_deleted_inativo": result.soft_deleted_inativo,
            "errors": result.errors,
            "dry_run": dry_run,
            "cutoff_5y": result.cutoff_5y.isoformat() if result.cutoff_5y else None,
            "cutoff_inativo": (
                result.cutoff_inativo.isoformat() if result.cutoff_inativo else None
            ),
            "duration_ms": result.duration_ms,
        },
        **audit_kwargs(request),
    )

    return {
        "dry_run": dry_run,
        "scanned": result.scanned,
        "soft_deleted_5y": result.soft_deleted_5y,
        "soft_deleted_inativo": result.soft_deleted_inativo,
        "errors": result.errors,
        "cutoff_5y": result.cutoff_5y.isoformat() if result.cutoff_5y else None,
        "cutoff_inativo": (result.cutoff_inativo.isoformat() if result.cutoff_inativo else None),
        "duration_ms": result.duration_ms,
    }


# ============================================================================
# Postman collection export
# ============================================================================


@api_router.get(
    "/postman",
    tags=["dev"],
    summary="Exportar colecao Postman v2.1.0",
    description=(
        "Retorna a colecao Postman no schema v2.1.0 para download. Util para "
        "QA e desenvolvedores testarem os endpoints localmente."
    ),
    response_description="Colecao Postman em JSON.",
)
async def postman_collection() -> dict:
    """Retorna a colecao do Postman v2.1.0."""
    return {
        "info": {
            "name": "Cartorio API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "Calcular Emolumento",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/emolumento/calcular?tipo=escritura_compra_venda&folhas=3&urgencia=true",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "emolumento", "calcular"],
                        "query": [
                            {"key": "tipo", "value": "escritura_compra_venda"},
                            {"key": "folhas", "value": "3"},
                            {"key": "urgencia", "value": "true"},
                        ],
                    },
                },
            },
            {
                "name": "Consultar Protocolo",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/protocolo/2026-00001",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "protocolo", "2026-00001"],
                    },
                },
            },
            {
                "name": "Criar Protocolo",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": (
                            '{\n  "cliente_cpf": "123.456.789-09",\n'
                            '  "cliente_nome": "Joao da Silva",\n'
                            '  "tipo": "certidao_negativa",\n'
                            '  "canal_origem": "web",\n'
                            '  "consentimento_lgpd": true\n}'
                        ),
                    },
                    "url": {
                        "raw": "{{base_url}}/api/v1/protocolo",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "protocolo"],
                    },
                },
            },
            {
                "name": "Webhook Evolution",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"},
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": '{\n  "message": {\n    "text": "Ola, preciso de uma certidao"\n  },\n  "sender": "user123",\n  "instance": "inst1"\n}',
                    },
                    "url": {
                        "raw": "{{base_url}}/api/v1/webhook/evolution",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "webhook", "evolution"],
                    },
                },
            },
            {
                "name": "Audit Verify",
                "request": {
                    "method": "POST",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/audit/verify",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "audit", "verify"],
                    },
                },
            },
            {
                "name": "Health Radar",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/health/radar",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "health", "radar"],
                    },
                },
            },
        ],
        "variable": [
            {
                "key": "base_url",
                "value": "https://api.2notasudi.com.br",
                "type": "string",
            }
        ],
    }


@api_router.get(
    "/audit/logs",
    tags=["audit"],
    summary="Lista audit logs paginados (LGPD art. 37)",
    description=(
        "Consulta audit log com filtros. Apenas DPO/escrevente autorizado (X-API-Key). "
        "LGPD art. 37: titular tem direito de acesso aos dados sobre tratamento. "
        "Rate limit interno: 60 req/min (D4 - DPO dashboard).\n\n"
        "Filtros (todos opcionais, AND entre si):\n"
        "- actor_id, actor_type, action_prefix, resource, canal\n"
        "- since, until (ISO 8601)\n"
        "- page (1-indexed, default 1), page_size (default 50, max 200)"
    ),
    responses={
        200: {"model": AuditLogListResponse, "description": "Lista paginada de audit logs."},
        401: {"description": "X-API-Key ausente ou invalida."},
    },
)
async def list_audit_logs_endpoint(
    request: Request,
    actor_id: Annotated[str | None, Query(description="Filtrar por actor_id exato.")] = None,
    actor_type: Annotated[
        str | None,
        Query(
            description="Filtrar por tipo (user, system, bot, escrevente, tabeliao).",
            pattern="^(user|system|bot|escrevente|tabeliao)$",
        ),
    ] = None,
    action_prefix: Annotated[
        str | None, Query(description="Filtrar por prefixo de action.")
    ] = None,
    resource: Annotated[str | None, Query(description="Filtrar por resource exato.")] = None,
    canal: Annotated[str | None, Query(description="Filtrar por canal.")] = None,
    since: Annotated[
        datetime.datetime | None, Query(description="Entries >= since (ISO 8601).")
    ] = None,
    until: Annotated[
        datetime.datetime | None, Query(description="Entries <= until (ISO 8601).")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Pagina (1-indexed).")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Tamanho da pagina.")] = 50,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> AuditLogListResponse:
    """Lista audit logs paginados (DPO/escrevente)."""
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "erro": "UNAUTHORIZED",
                "mensagem": "X-API-Key obrigatoria para consultar audit log.",
            },
        )

    filter_ = AuditLogFilter(
        actor_id=actor_id,
        actor_type=actor_type,  # type: ignore[arg-type]
        action_prefix=action_prefix,
        resource=resource,
        canal=canal,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
    )
    return list_audit_logs(db, filter_)


@api_router.get(
    "/audit/logs/{log_id}",
    tags=["audit"],
    summary="Busca 1 entry de audit log por ID",
    description="Retorna AuditLog individual. Apenas DPO/escrevente (X-API-Key).",
    responses={
        200: {"model": AuditLogResponse, "description": "Entry encontrada."},
        401: {"description": "X-API-Key ausente ou invalida."},
        404: {"description": "Entry nao encontrada."},
    },
)
async def get_audit_log_endpoint(
    request: Request,
    log_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> AuditLogResponse:
    """Retorna 1 entry de audit log por ID."""
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={"erro": "UNAUTHORIZED", "mensagem": "X-API-Key obrigatoria."},
        )

    result = get_audit_log_by_id(db, log_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "AUDIT_LOG_NOT_FOUND",
                "mensagem": f"Audit log {log_id} nao encontrado.",
            },
        )
    return result


# ============================================================================
# LGPD - Historico completo do cliente (com timeline)
# ============================================================================


class ClienteHistoricoItem(BaseModel):
    """Item de timeline do cliente."""

    type: Annotated[str, Field(description="Tipo: 'protocolo' ou 'atendimento'.")]
    id: Annotated[int, Field(description="ID interno.")]
    numero: str | None = Field(default=None, description="Numero do protocolo (se aplicavel).")
    status: str | None = Field(default=None, description="Status atual.")
    titulo: str = Field(description="Descricao humana: 'Escritura compra e venda - em_andamento'.")
    canal: str | None = Field(default=None, description="Canal de origem.")
    timestamp: datetime.datetime = Field(description="Quando aconteceu.")


class ClienteHistoricoResponse(BaseModel):
    """Timeline consolidada do cliente (todos os protocolos + atendimentos)."""

    cliente_id: int
    cliente_nome: str
    total_eventos: int
    items: list[ClienteHistoricoItem] = Field(description="Eventos ordenados por timestamp DESC.")


@api_router.get(
    "/cliente/{cliente_id}/historico",
    tags=["cliente"],
    summary="Historico completo do cliente (timeline LGPD)",
    description=(
        "Retorna timeline consolidada de **todos** os protocolos + atendimentos "
        "do cliente, ordenados por timestamp DESC.\n\n"
        "LGPD art. 18 IV: titular tem direito de acesso aos dados sobre tratamento. "
        "DPO pode usar este endpoint para atender solicitacao de titular. "
        "Rate limit interno: 60 req/min (D4 - DPO dashboard).\n\n"
        "Requer X-API-Key (DPO/escrevente)."
    ),
    response_model=ClienteHistoricoResponse,
    responses={
        200: {"description": "Timeline do cliente."},
        401: {"description": "X-API-Key ausente."},
        404: {"description": "Cliente nao encontrado."},
    },
)
async def get_cliente_historico(
    request: Request,
    cliente_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ClienteHistoricoResponse:
    """Timeline consolidada de todos os eventos do cliente."""
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={"erro": "UNAUTHORIZED", "mensagem": "X-API-Key obrigatoria."},
        )

    from app.models.atendimento import Atendimento
    from app.models.protocolo import Protocolo

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "CLIENTE_NOT_FOUND",
                "mensagem": f"Cliente {cliente_id} nao encontrado.",
            },
        )

    items: list[ClienteHistoricoItem] = []

    protocolos = db.query(Protocolo).filter(Protocolo.cliente_id == cliente_id).all()
    for p in protocolos:
        items.append(
            ClienteHistoricoItem(
                type="protocolo",
                id=p.id,
                numero=p.numero,
                status=p.status,
                titulo=f"{p.tipo} - {p.status}",
                canal=p.canal_origem,
                timestamp=p.created_at,
            )
        )

    atendimentos = db.query(Atendimento).filter(Atendimento.cliente_id == cliente_id).all()
    for a in atendimentos:
        items.append(
            ClienteHistoricoItem(
                type="atendimento",
                id=a.id,
                numero=None,
                status=a.status,
                titulo=f"Atendimento via {a.canal or 'desconhecido'}",
                canal=a.canal,
                timestamp=a.iniciado_em,
            )
        )

    items.sort(key=lambda x: x.timestamp, reverse=True)

    return ClienteHistoricoResponse(
        cliente_id=cliente_id,
        cliente_nome=cliente.nome,
        total_eventos=len(items),
        items=items,
    )


# ============================================================================
# N8N Workflow #25 - Protocolos concluidos recentemente
# ============================================================================


@api_router.get(
    "/protocolo/recentes-concluidos",
    tags=["protocolo"],
    summary="Lista protocolos concluidos nos ultimos N minutos (N8N workflow #25)",
    description=(
        "Retorna protocolos com status='concluido' que foram atualizados nos ultimos "
        "N minutos. Usado pelo workflow N8N #25 para disparar envio de PDF via WhatsApp.\n\n"
        "Params:\n"
        "- minutos: janela de tempo (default 10, suficiente para cron 5min)\n"
        "- limit: maximo de items (default 50)\n\n"
        "Requer X-API-Key (workflow N8N). Nao expoe PII (telefone = None por design)."
    ),
    responses={
        200: {"description": "Lista de protocolos concluidos (pode ser vazia)."},
        401: {"description": "X-API-Key ausente."},
    },
)
async def get_protocolos_recentes_concluidos(
    request: Request,
    minutos: Annotated[
        int, Query(ge=1, le=1440, description="Janela em minutos (default 10).")
    ] = 10,
    limit: Annotated[int, Query(ge=1, le=200, description="Maximo de items (default 50).")] = 50,
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> dict:
    """Endpoint usado pelo N8N workflow #25 (protocolo concluido -> PDF WhatsApp)."""
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={"erro": "UNAUTHORIZED", "mensagem": "X-API-Key obrigatoria."},
        )

    from app.services.protocolo_query import listar_protocolos_recentes_concluidos

    items = listar_protocolos_recentes_concluidos(db, minutos=minutos, limit=limit)
    return {
        "items": [item.to_dict() for item in items],
        "total": len(items),
        "janela_minutos": minutos,
        "limit": limit,
    }


# ============================================================================
# Documento upload (PDF assinado + hash SHA256)
# ============================================================================


@api_router.post(
    "/documento/upload",
    tags=["documento"],
    summary="Upload de documento (PDF assinado) com hash SHA256",
    description=(
        "Recebe um arquivo (multipart/form-data), valida MIME type, calcula "
        "SHA256, persiste metadata no DB, e retorna storage_path + hash.\n\n"
        "Storage real: este endpoint apenas REGISTRA o documento. O arquivo em si "
        "precisa ser enviado para Supabase Storage via /api/v1/documento/storage-upload "
        "(Sprint 3.5+, a parte de storage). Aqui so persistimos o metadata + hash.\n\n"
        "Validacao humana: documento juridico exige revisao de escrevente. O campo "
        "`validado_por` fica NULL ate um escrevente revisar.\n\n"
        "Requer X-API-Key (workflow N8N ou escrevente)."
    ),
    responses={
        200: {"description": "Documento registrado."},
        400: {"description": "Arquivo invalido (mime, tamanho, hash mismatch)."},
        401: {"description": "X-API-Key ausente."},
        404: {"description": "Protocolo nao encontrado."},
    },
)
async def upload_documento(
    request: Request,
    protocolo_id: int = Form(..., description="ID do protocolo."),
    tipo: str = Form(..., description="Tipo: rg, cpf, escritura, certidao, etc."),
    storage_path: str = Form(..., description="Caminho no storage (Supabase Storage key)."),
    mime_type: str = Form(..., description="application/pdf, image/jpeg, etc."),
    hash_sha256: str = Form(..., description="SHA256 hex do arquivo (64 chars)."),
    tamanho_bytes: int | None = Form(None, description="Tamanho em bytes (opcional)."),
    uploaded_by: str = Form("sistema", description="Quem fez upload (nome/id)."),
    uploaded_by_tipo: str = Form("sistema", description="cliente, escrevente, sistema."),
    db: Session = Depends(get_db),
) -> dict:
    """Registra metadata de documento uploaded."""
    from app.models.documento import Documento
    from app.models.protocolo import Protocolo

    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != settings.cartorio_api_key:
        raise HTTPException(
            status_code=401,
            detail={"erro": "UNAUTHORIZED", "mensagem": "X-API-Key obrigatoria."},
        )

    # Validacao basica
    if len(hash_sha256) != 64 or not all(c in "0123456789abcdef" for c in hash_sha256.lower()):
        raise HTTPException(
            status_code=400,
            detail={"erro": "INVALID_HASH", "mensagem": "hash_sha256 deve ser hex de 64 chars."},
        )
    if mime_type not in {"application/pdf", "image/jpeg", "image/png", "image/tiff"}:
        raise HTTPException(
            status_code=400,
            detail={"erro": "INVALID_MIME", "mensagem": f"mime_type nao suportado: {mime_type}"},
        )

    # Verifica protocolo existe
    protocolo = db.get(Protocolo, protocolo_id)
    if protocolo is None:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "PROTOCOLO_NOT_FOUND",
                "mensagem": f"Protocolo {protocolo_id} nao existe.",
            },
        )

    # Cria documento
    doc = Documento(
        protocolo_id=protocolo_id,
        tipo=tipo,
        storage_path=storage_path,
        storage_provider="supabase",
        tamanho_bytes=tamanho_bytes,
        mime_type=mime_type,
        hash_sha256=hash_sha256.lower(),
        uploaded_by=uploaded_by,
        uploaded_by_tipo=uploaded_by_tipo,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Audit log (LGPD art. 37)
    AuditService.log(
        db,
        actor_id=f"upload:{uploaded_by}",
        actor_type="sistema",
        action="documento.upload",
        resource=f"documento:{doc.id}",
        payload={
            "protocolo_id": protocolo_id,
            "documento_id": doc.id,
            "tipo": tipo,
            "mime_type": mime_type,
            "tamanho_bytes": tamanho_bytes,
            "hash_sha256": hash_sha256,
        },
        **audit_kwargs(request),
    )

    return {
        "id": doc.id,
        "protocolo_id": doc.protocolo_id,
        "tipo": doc.tipo,
        "storage_path": doc.storage_path,
        "storage_provider": doc.storage_provider,
        "mime_type": doc.mime_type,
        "tamanho_bytes": doc.tamanho_bytes,
        "hash_sha256": doc.hash_sha256,
        "uploaded_by": doc.uploaded_by,
        "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ============================================================================
# Metrics Prometheus (open source, sem vendor)
# ============================================================================


@api_router.get(
    "/metrics/prometheus",
    tags=["meta"],
    summary="Metrics em formato Prometheus (open source)",
    description=(
        "Endpoint para Prometheus scraper (ou Grafana Agent, Mimir, Thanos). "
        "Formato text/plain, version 0.0.4. NAO requer auth (Prometheus scraper "
        "nao tem como passar X-API-Key).\n\n"
        "Metricas expostas:\n"
        "- `cartorio_uptime_seconds` - gauge, tempo de vida do processo\n"
        "- `cartorio_clientes_total` - gauge, total de clientes no DB\n"
        "- `cartorio_protocolos_total{status=...}` - gauge por status\n"
        "- `cartorio_audit_chain_length` - gauge, total entries no audit log\n"
        "- `cartorio_http_requests_total` (in-process) - counter quando \n"
        "  instrumentado no middleware\n\n"
        "Open source: nenhuma chave de API de vendor, dados nao sao enviados "
        "para terceiros. Pode ser auto-hospedado com Prometheus + Grafana."
    ),
    response_class=PlainTextResponse,
    responses={
        200: {
            "description": "Metrics em formato Prometheus text/plain.",
            "content": {
                "text/plain": {
                    "example": "# TYPE cartorio_uptime_seconds gauge\ncartorio_uptime_seconds 3600.0\n"
                }
            },
        },
    },
)
async def get_metrics_prometheus(
    db: Annotated[Session, Depends(get_db)],
) -> PlainTextResponse:
    """Renderiza metrics no formato Prometheus."""
    from app.services.metrics import render_full_prometheus

    output = render_full_prometheus(db)
    return PlainTextResponse(content=output, media_type="text/plain; version=0.0.4; charset=utf-8")


@api_router.get(
    "/metrics",
    tags=["meta"],
    summary="Metrics em formato JSON (N8N-friendly)",
    description=(
        "Endpoint para N8N workflows e integracoes que precisam consumir "
        "metrics estruturados (substitui Code nodes quebrados por sandbox "
        "JS do N8N 2.27 - Lesson 49).\n\n"
        "Mesmo modelo de auth do `/metrics/prometheus`: NAO requer X-API-Key "
        "(scrapers e workflows internos nao tem como passar header). "
        "Aceita header se fornecido (forward-compat com futuras rotas "
        "protegidas).\n\n"
        "Metricas expostas (Sprint 4 STREAM 1 - 2026-06-24):\n"
        "- `clientes_total` (int) - total de clientes ativos no DB\n"
        "- `protocolos_total` (dict[status, int]) - count de protocolos por status\n"
        "- `audit_chain_length` (int) - entries no audit log (LGPD art. 37)\n"
        "- `uptime_seconds` (float) - tempo de vida do processo backend\n"
        "- `counters` (dict) - contadores in-process (http_requests, pii_blocks)\n"
        "- `gauges` (dict) - gauges in-process (dlq_depth, etc)\n\n"
        "LGPD: NAO expoe PII (cpf, rg, telefone, email). Apenas contadores "
        "agregados e snapshots de contagens de tabela. Pode ser consumido "
        "publicamente."
    ),
    response_model=MetricsResponse,
    response_description="Metrics estruturados em JSON.",
    responses={
        200: {
            "description": "Metrics em JSON estruturado.",
            "content": {
                "application/json": {
                    "example": {
                        "clientes_total": 42,
                        "protocolos_total": {"aberto": 5, "concluido": 12},
                        "audit_chain_length": 1847,
                        "uptime_seconds": 3600.5,
                        "counters": {
                            "cartorio_http_requests_total": {
                                "endpoint=/api/v1/protocolo/{numero}|method=GET|status=200": 142
                            }
                        },
                        "gauges": {"dlq_depth": {"queue=evolution": 0}},
                    }
                }
            },
        },
    },
)
async def get_metrics_json(
    db: Annotated[Session, Depends(get_db)],
) -> MetricsResponse:
    """Renderiza metrics em JSON estruturado (N8N-friendly)."""
    from app.services.metrics import render_metrics_json

    data = render_metrics_json(db)
    return MetricsResponse(**data)


# ---------------------------------------------------------------------------
# POST /api/v1/metrics/n8n (B0.1 - Sprint 3)
# Recebe metrics do workflow N8N #25 (Metrics Collector, cron 1min).
# Corrige 404 que ocorria a cada 1min desde 2026-06-23 (Lesson 55).
# ---------------------------------------------------------------------------


@api_router.post(
    "/metrics/n8n",
    tags=["meta"],
    summary="Ingest metrics do N8N (auth X-API-Key)",
    description=(
        "Endpoint de ingestao para o workflow N8N #25 (Metrics Collector). "
        "Substitui o 404 que o workflow vinha recebendo a cada 1min desde "
        "2026-06-23 (Lesson 55 - workflow mal projetado pra chamar endpoint "
        "que nao existia).\n\n"
        "**Auth**: header `X-API-Key` (mesmo gate dos demais endpoints admin "
        "do cartorio). Sem auth = 401.\n\n"
        "**Payload flexivel**: aceita shape canonico (counters/gauges/"
        "uptime_seconds), texto Prometheus cru (caso Code node do N8N tenha "
        "passado string direto), ou qualquer JSON (modo `unknown` para "
        "telemetria). Cada counter/gauges eh registrado no MetricsStore com "
        "label `source=n8n` pra distinguir de metrics internas do backend.\n\n"
        "**Audit log**: action=`metrics.n8n_received`, actor_type=`n8n`, "
        "payload inclui `payload_kind`, contagens ingeridas, tamanho em "
        "bytes (LGPD art. 37 - logs de acesso).\n\n"
        "**LGPD**: NAO expoe PII. Soh agregados (uptime, memory counters, "
        "workflows_active). Audit log registra apenas tamanho + shape."
    ),
    status_code=200,
    response_model=N8nMetricsIngestResponse,
    responses={
        200: {"description": "Metrics recebidas e processadas (ou logged como unknown)."},
        401: {"description": "X-API-Key ausente ou invalida."},
    },
)
async def post_metrics_n8n(
    request: Request,
    payload: N8nMetricsIngest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: Session = Depends(get_db),
) -> N8nMetricsIngestResponse:
    """Ingere metrics vindas do N8N workflow #25.

    Detecta shape do payload e ingere no MetricsStore com label `source=n8n`.
    Se shape nao bate (desconhecido), loga no audit mas retorna 200 pra nao
    quebrar o cron (workflow continua funcionando mesmo se a API evoluir).
    """
    from app.services.metrics import store as metrics_store

    api_key_header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    _verify_api_key(api_key_header)

    # Serializa payload pra log (size, kind)
    payload_dict = payload.model_dump(exclude_none=True)
    metrics_size_bytes = len(json.dumps(payload_dict, default=str).encode("utf-8"))

    counters_ingested = 0
    gauges_ingested = 0
    payload_kind = "unknown"

    # Detecta shape: canonical > prometheus_raw > unknown
    has_canonical = bool(
        payload.counters is not None
        or payload.gauges is not None
        or payload.uptime_seconds is not None
        or payload.workflows_active is not None
        or payload.memory_rss_mb is not None
    )

    if has_canonical:
        payload_kind = "canonical"

        # Counters: {name: {labels_key: int}} -> inc com label source=n8n
        if payload.counters:
            for name, buckets in payload.counters.items():
                for labels_key, value in buckets.items():
                    # Parse labels_key "k=v|k=v" -> dict
                    extra_labels = _parse_labels_key_safe(labels_key)
                    extra_labels["source"] = "n8n"
                    metrics_store.inc_counter(name, labels=extra_labels, value=value)
                    counters_ingested += 1

        # Gauges: suporta escalar E dict-com-labels
        if payload.gauges:
            for name, val_or_map in payload.gauges.items():
                if isinstance(val_or_map, dict):
                    for labels_key, value in val_or_map.items():
                        extra_labels = _parse_labels_key_safe(labels_key)
                        extra_labels["source"] = "n8n"
                        metrics_store.set_gauge(name, float(value), labels=extra_labels)
                        gauges_ingested += 1
                else:
                    metrics_store.set_gauge(
                        "n8n_gauge", float(val_or_map), labels={"name": name, "source": "n8n"}
                    )
                    gauges_ingested += 1

        # Campos canonicos dedicados (facilitam Grafana queries)
        if payload.uptime_seconds is not None:
            metrics_store.set_gauge(
                "n8n_uptime_seconds",
                float(payload.uptime_seconds),
                labels={"source": "n8n"},
            )
            gauges_ingested += 1
        if payload.workflows_active is not None:
            metrics_store.set_gauge(
                "n8n_workflows_active",
                float(payload.workflows_active),
                labels={"source": "n8n"},
            )
            gauges_ingested += 1
        if payload.memory_rss_mb is not None:
            metrics_store.set_gauge(
                "n8n_memory_rss_mb",
                float(payload.memory_rss_mb),
                labels={"source": "n8n"},
            )
            gauges_ingested += 1

    elif isinstance(payload.raw, str) and _looks_like_prometheus(payload.raw):
        payload_kind = "prometheus_raw"
        # Parse simples: linhas "metric_name{labels} value"
        counters_ingested, gauges_ingested = _ingest_prometheus_text(
            payload.raw, metrics_store
        )

    else:
        # unknown: aceito, logado para investigacao. NUNCA 422 (workflow ja roda em prod).
        payload_kind = "unknown"

    # Audit log LGPD art. 37 (sem PII)
    AuditService.log(
        db,
        actor_id="n8n_workflow_25",
        actor_type="n8n",
        action="metrics.n8n_received",
        resource="metrics:n8n:ingest",
        payload={
            "payload_kind": payload_kind,
            "counters_ingested": counters_ingested,
            "gauges_ingested": gauges_ingested,
            "metrics_size_bytes": metrics_size_bytes,
        },
        **audit_kwargs(request),
    )

    return N8nMetricsIngestResponse(
        received=True,
        payload_kind=payload_kind,
        counters_ingested=counters_ingested,
        gauges_ingested=gauges_ingested,
        metrics_size_bytes=metrics_size_bytes,
    )


def _parse_labels_key_safe(labels_key: str) -> dict[str, str]:
    """Parse seguro de 'k=v|k=v' -> dict. Falha silenciosa (sem PII explodir)."""
    if not labels_key:
        return {}
    result: dict[str, str] = {}
    for item in labels_key.split("|"):
        if "=" in item:
            k, v = item.split("=", 1)
            # LGPD defense: limita tamanho pra nao logar valor PII gigante
            if len(v) <= 64:
                result[k] = v
    return result


def _looks_like_prometheus(text: str) -> bool:
    """Heuristica: linha comeca com nome de metrica + '{' ou numero no final."""
    if not text:
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines:
        return False
    sample = lines[0]
    # Formato: metric_name{label="val"} 42.0  OR  metric_name 42.0
    return " " in sample and not sample.startswith("{")


def _ingest_prometheus_text(text: str, metrics_store: Any) -> tuple[int, int]:
    """Ingere texto Prometheus cru no MetricsStore com label source=n8n.

    Formatos reconhecidos (subset minimo do Prometheus exposition format):
    - metric_name 42.0
    - metric_name{label="val"} 42.0
    - metric_name{label="val",label2="val2"} 42.0
    - HELP/TYPE comment lines (ignorados)

    Retorna (counters_ingested, gauges_ingested). Heuristica: se o nome termina
    com _total eh counter; senao eh gauge. Suficiente pra metricas de processo
    (uptime, memory, requests).
    """
    counters = 0
    gauges = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Split em "name{labels} value" ou "name value"
        if "{" in line and "}" in line:
            name_part, rest = line.split("{", 1)
            labels_part, value_part = rest.split("}", 1)
            name = name_part.strip()
            # Parse labels
            labels: dict[str, str] = {"source": "n8n"}
            for pair in labels_part.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    if len(v) <= 64:
                        labels[k.strip()] = v
            value_str = value_part.strip().split()[0] if value_part.strip() else "0"
        else:
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0]
            value_str = parts[1]
            labels = {"source": "n8n"}
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            continue
        # Heuristica: _total ou _count => counter
        if name.endswith("_total") or name.endswith("_count"):
            metrics_store.inc_counter(name, labels=labels, value=int(value))
            counters += 1
        else:
            metrics_store.set_gauge(name, value, labels=labels)
            gauges += 1
    return counters, gauges


# ---------------------------------------------------------------------------
# DLQ (Dead Letter Queue) - A2 endpoints
# ---------------------------------------------------------------------------


class DLQEnqueueRequest(BaseModel):
    """Payload para enqueue de mensagem na DLQ.

    A2: LGPD-by-design - `payload` deve chegar ja scrubbed pelo caller
    (escravo de services/pii.py). Endpoint NAO re-scrub (responsabilidade
    unica para manter audit chain consistente).
    """

    payload: dict[str, Any] = Field(..., description="Mensagem ja scrubbed (sem PII).")
    actor_id: str = Field(..., min_length=1, max_length=128)


class DLQEnqueueResponse(BaseModel):
    id: str
    queue: str
    status: str
    created_at: datetime.datetime


@api_router.post(
    "/dlq/{queue}/enqueue",
    tags=["dlq"],
    summary="Enfileirar mensagem na DLQ (auth X-API-Key)",
    description=(
        "Enfileira mensagem na **Dead Letter Queue** para reprocessamento "
        "assincrono. Usado quando integracao externa (WhatsApp Evolution, "
        "Chatwoot, Telegram) falhou entrega.\n\n"
        "**Auth**: header `X-API-Key` (escrevente autorizado).\n\n"
        "**LGPD**: payload DEVE chegar **ja scrubbed** pelo caller. "
        "Cardinalidade do label `queue` eh enum-fixa (4 valores max).\n\n"
        "**Audit log**: action=`dlq.enqueued`, actor_type=`api`, payload com "
        "`{queue, actor_id_hash, payload_size_bytes}`."
    ),
    status_code=201,
    response_model=DLQEnqueueResponse,
    responses={
        401: {"description": "X-API-Key ausente ou invalida."},
        422: {"description": "Payload vazio, queue invalida ou PII detectado."},
    },
)
def post_dlq_enqueue(
    request: Request,
    queue: str,
    body: DLQEnqueueRequest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: Session = Depends(get_db),
) -> DLQEnqueueResponse:
    """Enfileira mensagem na DLQ (LGPD-safe)."""
    from app.services.dlq import enqueue as dlq_enqueue
    from app.models.outbox_message import OutboxQueue

    api_key_header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    _verify_api_key(api_key_header)

    try:
        queue_enum = OutboxQueue(queue)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "QUEUE_INVALIDA",
                "mensagem": (
                    f"Queue '{queue}' invalida. Valores aceitos: "
                    f"{', '.join(q.value for q in OutboxQueue)}."
                ),
                "detalhes": {"queue_recebida": queue},
            },
        ) from e

    if not body.payload:
        raise HTTPException(
            status_code=422,
            detail={
                "erro": "PAYLOAD_VAZIO",
                "mensagem": "Payload nao pode ser vazio.",
            },
        )

    msg = dlq_enqueue(db, queue_enum, body.payload)

    AuditService.log(
        db,
        actor_id=body.actor_id,
        actor_type="api",
        action="dlq.enqueued",
        resource=f"dlq:{queue}:{msg.id}",
        payload={
            "queue": queue_enum.value,
            "actor_id_hash": hash_pii(body.actor_id, salt=settings.audit_hmac_key[:32]),
            "payload_size_bytes": len(json.dumps(body.payload, default=str)),
        },
        **audit_kwargs(request),
    )

    return DLQEnqueueResponse(
        id=str(msg.id),
        queue=msg.queue.value,
        status=msg.status.value,
        created_at=msg.created_at,
    )


@api_router.post(
    "/dlq/refresh-gauges",
    tags=["dlq"],
    summary="Refresh DLQ depth gauges (auth X-API-Key)",
    description=(
        "Forca refresh do gauge `dlq_depth{queue}` baseado em SELECT COUNT "
        "do DB. Util apos deploy/migration ou operacao manual.\n\n"
        "**Auth**: header `X-API-Key`.\n"
    ),
    status_code=200,
    responses={
        401: {"description": "X-API-Key ausente ou invalida."},
    },
)
def post_dlq_refresh_gauges(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Refresh DLQ depth gauges from DB."""
    from app.services.dlq import depth, _update_depth_gauge

    api_key_header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    _verify_api_key(api_key_header)

    _update_depth_gauge(db)
    counts = depth(db)
    return {q.value: cnt for q, cnt in counts.items()}
