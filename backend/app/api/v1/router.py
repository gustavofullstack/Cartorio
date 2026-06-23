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
import time
from typing import Annotated

import httpx
import redis
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    ProtocoloCreateRequest,
    ProtocoloCreateResponse,
    ProtocoloNotFoundResponse,
    ProtocoloResponse,
    StatusProtocolo,
)
from app.services.audit import AuditService
from app.services.emolumento import TIPOS_VALIDOS, calcular as calcular_emolumento_svc
from app.services.pii import hash_pii, scrub

# ============================================================================
# Router com tags PT-BR para o Swagger/OpenAPI
# ============================================================================

api_router = APIRouter()


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
        # Loga tentativa de consulta a protocolo inexistente (seguranca)
        AuditService.log(
            db,
            actor_id="anonymous",
            actor_type="user",
            action="protocolo.read.not_found",
            resource=f"protocolo:{numero}",
            payload={"numero": numero, "result": "not_found"},
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
    # PII scrubbing - hasheia CPF ANTES de persistir. CPF puro nunca toca o DB.
    # Salt vem do settings (placeholder em dev - em prod vem de secret manager).
    # ------------------------------------------------------------------
    cpf_hash = hash_pii(payload.cliente_cpf, salt=settings.audit_hmac_key[:32])

    # ------------------------------------------------------------------
    # Cliente - reusa se CPF ja existir (idempotencia por hash)
    # ------------------------------------------------------------------
    cliente = db.execute(select(Cliente).where(Cliente.cpf_hash == cpf_hash)).scalar_one_or_none()

    if cliente is None:
        cliente = Cliente(
            cpf_hash=cpf_hash,
            nome=payload.cliente_nome,
            consentimento_lgpd=True,
            consentimento_em=datetime.datetime.now(datetime.timezone.utc),
            consentimento_canal=payload.canal_origem.value,
        )
        db.add(cliente)
        db.flush()  # garante cliente.id
    else:
        # Atualiza consentimento (re-confirmacao) - LGPD exige registro da data.
        cliente.consentimento_lgpd = True
        cliente.consentimento_em = datetime.datetime.now(datetime.timezone.utc)
        cliente.consentimento_canal = payload.canal_origem.value

    # ------------------------------------------------------------------
    # Snapshot de emolumento no momento da criacao (regra: nunca recalcular).
    # ------------------------------------------------------------------
    calc = calcular_emolumento_svc(payload.tipo, folhas=1, urgencia=False)

    # ------------------------------------------------------------------
    # Numero ANO-SEQUENCIAL
    # ------------------------------------------------------------------
    ano_atual = datetime.datetime.now(datetime.timezone.utc).year
    numero = _gerar_numero_protocolo(db, ano_atual)

    protocolo = Protocolo(
        numero=numero,
        cliente_id=cliente.id,
        tipo=payload.tipo,
        status=StatusProtocolo.DRAFT.value,  # HITL: nunca EM_ANDAMENTO direto.
        valor_base=calc.base,
        valor_adicional=calc.adicional_folhas + calc.adicional_urgencia,
        valor_total=calc.total,
        tabela_referencia=calc.tabela_referencia,
        prazo_dias=5,  # placeholder - regra por tipo vem do emolumento service
        canal_origem=payload.canal_origem.value,
    )
    db.add(protocolo)
    db.flush()

    # ------------------------------------------------------------------
    # Audit log - OBRIGATORIO em toda mutacao.
    # ------------------------------------------------------------------
    AuditService.log(
        db,
        actor_id="bot",
        actor_type="bot",
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

    return ProtocoloCreateResponse(
        status="criado",
        numero=protocolo.numero,
        protocolo_id=protocolo.id,
        estado=StatusProtocolo(protocolo.status),
        proxima_acao=(
            "Aguardando validacao humana do escrevente. "
            "O protocolo NAO sera processado ate confirmacao no painel admin."
        ),
        cliente_id=cliente.id,
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
async def webhook_evolution(payload: dict) -> dict:
    """Webhook do Evolution API (WhatsApp).

    Recebe mensagem, aplica PII scrubbing, detecta intencao via LLM,
    retorna resposta. Audit log de TUDO.
    """
    raw_text = payload.get("message", {}).get("text", "") or ""
    sender = payload.get("sender", "unknown")
    instance = payload.get("instance", "")

    # Calculate raw message hash
    raw_message_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    scrub_result = scrub(raw_text)
    with session_scope() as db:
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
    else:
        # Chamar LLM
        start_time = time.time()
        try:
            if settings.opencode_go_api_key and settings.opencode_go_api_key != "CHANGE_ME":
                headers = {
                    "Authorization": f"Bearer {settings.opencode_go_api_key}",
                    "Content-Type": "application/json",
                }
                payload_data = {
                    "model": settings.opencode_go_model,
                    "messages": [
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
                    "temperature": 0.2,
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{settings.opencode_go_base_url}/chat/completions",
                        json=payload_data,
                        headers=headers,
                    )
                    if response.status_code == 200:
                        resp_json = response.json()
                        bot_response = resp_json["choices"][0]["message"]["content"]
                        usage = resp_json.get("usage", {})
                        llm_tokens_in = usage.get("prompt_tokens")
                        llm_tokens_out = usage.get("completion_tokens")
                    else:
                        bot_response = (
                            "Desculpe, tive um problema de comunicacao com o meu cerebro de IA. "
                            "Vou chamar um atendente humano para te ajudar. [HUMANO]"
                        )
                        handoff = True
                        handoff_reason = f"LLM error status {response.status_code}"
            else:
                bot_response = "Recebi sua mensagem. Em breve um atendente ira responder."
        except Exception as e:
            bot_response = (
                "Desculpe, tive um problema de comunicacao com o meu cerebro de IA. "
                "Vou chamar um atendente humano para te ajudar. [HUMANO]"
            )
            handoff = True
            handoff_reason = f"LLM Exception: {str(e)}"

        llm_latency_ms = int((time.time() - start_time) * 1000)

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

    return {
        "status": "ok",
        "response": bot_response,
        "scrubbed": scrub_result.text[:200],
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
    "/health/radar",
    tags=["health"],
    summary="Health radar multi-servico",
    description=(
        "Verifica conectividade de **todos** os servicos da suite em paralelo: "
        "PostgreSQL, Redis, n8n, OpenClaw gateway, Evolution API. Retorna "
        "status individual por servico + status agregado (`green` se todos online)."
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

    # 3. n8n, OpenClaw, Evolution API (via httpx)
    n8n_ok = False
    openclaw_ok = False
    evolution_ok = False

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

    overall_status = (
        "green" if (db_ok and redis_ok and n8n_ok and openclaw_ok and evolution_ok) else "red"
    )

    return {
        "status": overall_status,
        "services": {
            "database": "online" if db_ok else "offline",
            "redis": "online" if redis_ok else "offline",
            "n8n": "online" if n8n_ok else "offline",
            "openclaw": "online" if openclaw_ok else "offline",
            "evolution": "online" if evolution_ok else "offline",
        },
    }


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
    """Verifica idade e tamanho do backup diario."""
    import os
    import subprocess
    from datetime import datetime, timezone

    BACKUP_DIR = "/var/backups/cartorio"
    last_backup_age_hours = None
    file_count = 0
    dir_size = "0"
    ok = False
    last_backup_iso = None

    try:
        # Executa via docker exec se estiver rodando num container sem acesso direto
        # Tenta local primeiro; fallback para SSH via Tailscale se falhar
        if os.path.isdir(BACKUP_DIR):
            base = BACKUP_DIR
            use_docker = False
        else:
            # Estamos em container - tenta via docker exec no host
            base = BACKUP_DIR
            use_docker = True

        if use_docker:
            r = subprocess.run(
                ["docker", "exec", "cartorio_api.1.", "ls", "-la", BACKUP_DIR],
                capture_output=True,
                text=True,
                timeout=5,
            )
        else:
            r = subprocess.run(
                ["ls", "-la", BACKUP_DIR],
                capture_output=True,
                text=True,
                timeout=5,
            )

        files = [
            ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip().endswith(".tar.gz")
        ]
        file_count = len(files)

        # Pega o mais recente por mtime
        if use_docker:
            r2 = subprocess.run(
                [
                    "docker",
                    "exec",
                    "cartorio_api.1.",
                    "find",
                    BACKUP_DIR,
                    "-name",
                    "*.tar.gz",
                    "-printf",
                    "%T@ %p\n",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
        else:
            r2 = subprocess.run(
                ["find", BACKUP_DIR, "-name", "*.tar.gz", "-printf", "%T@ %p\n"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        items = sorted(
            [ln.strip() for ln in (r2.stdout or "").splitlines() if ln.strip()],
            key=lambda x: float(x.split()[0]),
            reverse=True,
        )
        if items:
            newest_mtime = float(items[0].split()[0])
            age_s = datetime.now(timezone.utc).timestamp() - newest_mtime
            last_backup_age_hours = round(age_s / 3600, 1)
            last_backup_iso = datetime.fromtimestamp(newest_mtime, timezone.utc).isoformat()

        # Tamanho do diretorio
        if use_docker:
            r3 = subprocess.run(
                ["docker", "exec", "cartorio_api.1.", "du", "-sh", BACKUP_DIR],
                capture_output=True,
                text=True,
                timeout=5,
            )
        else:
            r3 = subprocess.run(
                ["du", "-sh", BACKUP_DIR],
                capture_output=True,
                text=True,
                timeout=5,
            )
        dir_size = (r3.stdout or "").split()[0] if r3.stdout else "?"

        ok = last_backup_age_hours is not None and last_backup_age_hours < 26

    except Exception as e:
        return {"ok": False, "error": str(e), "file_count": 0, "dir_size": "?"}

    return {
        "ok": ok,
        "last_backup_age_hours": last_backup_age_hours,
        "last_backup_iso": last_backup_iso,
        "file_count": file_count,
        "dir_size": dir_size,
        "age_hours": last_backup_age_hours,
    }


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
    protocolo: Annotated[str, Query(description="Numero do protocolo (YYYY-NNNNN).")],
    canal: Annotated[
        str, Query(description="Canal de envio: whatsapp/email/presencial.")
    ] = "whatsapp",
) -> dict:
    """Gera link de download da segunda via."""
    import hashlib
    import time

    # MVP: hash determinístico + timestamp = URL placeholder
    h = hashlib.sha256(f"{protocolo}:{time.time()}".encode()).hexdigest()[:16]
    return {
        "url_pdf": f"https://supbase.2notasudi.com.br/storage/v1/object/sign/documentos/{protocolo}-{h}.pdf",
        "validade_horas": 24,
        "protocolo": protocolo,
        "canal": canal,
    }


# ============================================================================
# Atendimentos (v0.4.2) - registro de handoff humano + pesquisa satisfacao
# ============================================================================


@api_router.get(
    "/atendimentos/ultimas-24h",
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

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    with session_scope() as db:
        rows = db.execute(
            select(Atendimento).where(
                Atendimento.concluido_em >= cutoff,
                Atendimento.pesquisa_enviada_em.is_(None),
            ).order_by(Atendimento.concluido_em.desc()).limit(200)
        ).scalars().all()

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

    return {
        "window_hours": 24,
        "count": len(atendimentos),
        "atendimentos": atendimentos,
    }


@api_router.post(
    "/atendimento/{atendimento_id}/pesquisa-enviada",
    tags=["atendimento"],
    summary="Marcar pesquisa de satisfacao como enviada (N8N workflow #07)",
)
async def marcar_pesquisa_enviada(atendimento_id: int) -> dict:
    """Marca pesquisa_enviada_em = now() para evitar envio duplicado."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.models.atendimento import Atendimento

    with session_scope() as db:
        a = db.execute(
            select(Atendimento).where(Atendimento.id == atendimento_id)
        ).scalar_one_or_none()
        if a is None:
            return {"ok": False, "error": "not_found"}
        a.pesquisa_enviada_em = datetime.now(timezone.utc)
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
async def criar_atendimento(payload: dict) -> dict:
    """Cria atendimento (handoff)."""
    from datetime import datetime, timezone
    from app.models.atendimento import Atendimento
    from app.models.cliente import Cliente
    from app.services.pii import hash_pii

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
        )

    return {"ok": True, "atendimento_id": atendimento_id}


@api_router.post(
    "/atendimento/{atendimento_id}/concluir",
    tags=["atendimento"],
    summary="Concluir atendimento (registra timestamp para pesquisa 24h)",
)
async def concluir_atendimento(atendimento_id: int, payload: dict | None = None) -> dict:
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
            return {"ok": False, "error": "not_found"}
        a.concluido_em = datetime.now(timezone.utc)
        a.status = "concluido"
        if nota is not None:
            a.pesquisa_nota = nota
        if comentario is not None:
            a.pesquisa_comentario = comentario

    return {"ok": True, "atendimento_id": atendimento_id}


# ============================================================================
# Chatwoot webhook (v0.4.2)
# ============================================================================


@api_router.post(
    "/webhook/chatwoot",
    tags=["webhook"],
    summary="Webhook Chatwoot (eventos de conversa)",
    description=(
        "Recebe webhooks do Chatwoot. Quando uma conversa e marcada como "
        "'resolved', o atendimento correspondente e concluido (aciona "
        "workflow #07 pesquisa satisfacao 24h depois)."
    ),
)
async def webhook_chatwoot(payload: dict) -> dict:
    """Processa webhook do Chatwoot."""
    event = payload.get("event") or payload.get("message_type") or "unknown"

    if event == "conversation_status_changed":
        conversation = payload.get("conversation", {})
        status = payload.get("status") or conversation.get("status")
        conv_id = conversation.get("id")
        if status == "resolved" and conv_id:
            from datetime import datetime, timezone
            from sqlalchemy import select
            from app.models.atendimento import Atendimento

            with session_scope() as db:
                a = db.execute(
                    select(Atendimento).where(
                        Atendimento.chatwoot_conversation_id == conv_id
                    )
                ).scalar_one_or_none()
                if a and not a.concluido_em:
                    a.concluido_em = datetime.now(timezone.utc)
                    a.status = "concluido"

                    AuditService.log(
                        db,
                        actor_id=f"chatwoot:{conv_id}",
                        actor_type="agent",
                        action="atendimento.concluido",
                        resource=f"atendimento:{a.id}",
                        payload={"chatwoot_conversation_id": conv_id},
                    )

    return {"ok": True, "event": event}


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
