"""MCP server da API do Cartorio - expõe tools MCP para clients
(Claude, Cursor, Zed, OpenCode, Antigravity) no protocolo MCP 2025-03-26.

Tools expostas:
- cartorio_calcular_emolumento: calcula emolumento MG 2026
- cartorio_consultar_protocolo: status de protocolo
- cartorio_criar_protocolo: cria protocolo (com consentimento LGPD)
- cartorio_gerar_segunda_via: gera link de download de PDF (segunda via)
- cartorio_audit_verify: verifica integridade do audit log
- cartorio_audit_hash_sequence: valida sequência de hashes offline (G8.07.T2)
- cartorio_saudacao: health check
- super_server_info: meta info
- scrub_mcp_output em tools sensíveis (G8.07.T3)

Modos de execucao:
1. **Standalone** (`python mcp_server.py`): sobe uvicorn em :8100 (ou
   `MCP_SERVER_PORT`) com o endpoint MCP na raiz `/`.
   Util para clients MCP que preferem endpoint dedicado.
2. **Montado na FastAPI** (`mcp_app()`): retorna sub-app Starlette que pode ser
   `app.mount("/mcp", mcp_server.mcp_app())` em main.py. Criterio do projeto:
   o cliente MCP deve enviar JSON-RPC para `https://api.2notasudi.com.br/mcp`.

Implementacao chama os services do app diretamente (sem HTTP self-loop) para
evitar timeout em recursao localhost:8000 -> /mcp -> localhost:8000.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import functools
import inspect
import os
import re
import sys
import hashlib
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable, TypeVar, cast

from starlette.applications import Starlette
from starlette.routing import Mount

# Adiciona backend/ ao path para importar app.*
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP

# Reusa o settings do backend
try:
    from app.config import Settings, settings  # noqa: F401
except ImportError:
    # Fallback se rodar fora do venv
    settings = None  # type: ignore[assignment]

# Reusa o MetricsStore do backend (Fase 3 — telemetria de MCP tools).
try:
    from app.services.metrics import store as _metrics_store
except ImportError:
    _metrics_store = None  # type: ignore[assignment]

from app.services.mcp_pii import scrub_mcp_output

F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Fase 3 — Counter cartorio_mcp_tool_calls_total{tool}
# ============================================================================


def contabilizar_tool(nome: str) -> Callable[[F], F]:
    """Incrementa `cartorio_mcp_tool_calls_total{tool}` a cada chamada da tool.

    Aplicado logo abaixo de `@mcp.tool(...)` (functools.wraps preserva a
    assinatura inspecionada pelo FastMCP). O label `tool` eh um literal fixo
    por tool (whitelist natural — cardinalidade controlada, zero PII).
    Fail-safe: se o MetricsStore nao estiver importavel, a tool roda normal.
    """

    def decorator(func: F) -> F:
        def _contar() -> None:
            if _metrics_store is not None:
                _metrics_store.inc_counter("cartorio_mcp_tool_calls_total", labels={"tool": nome})

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _contar()
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _contar()
            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


# ============================================================================
# FastMCP server
# ============================================================================

mcp = FastMCP(
    name="cartorio-mcp-cabuloso",
    version="0.6.0",
    instructions=(
        "MCP server do Cartorio 2 Notas Uberlandia. "
        "Use cartorio_calcular_emolumento para valores oficiais MG 2026, "
        "cartorio_consultar_protocolo para status, "
        "cartorio_audit_verify para integridade do audit log. "
        "HITL obrigatorio em qualquer decisao juridica."
    ),
)

mcp_public = FastMCP(
    name="cartorio-mcp-public",
    version="0.6.0",
    instructions=(
        "Perfil publico do 2o Cartorio de Notas de Uberlandia. "
        "Disponibiliza somente cartorio_calcular_emolumento."
    ),
)


# ============================================================================
# E2.06 — Erro estruturado + scrubbed para tools MCP
# ============================================================================

# Telegram bot token aparece na URL de chamadas httpx
# (.../bot<TOKEN>/setMessageReaction). Se uma chamada falha, o str(exc) do
# httpx embute a URL completa -> vazamento de credencial no payload MCP.
_BOT_TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]{10,}")


def _strip_secrets(text: str) -> str:
    """Remove segredos conhecidos (bot token Telegram) de mensagens de erro."""
    return _BOT_TOKEN_RE.sub("bot[REDACTED]", text)


def _tool_error(code: str, exc: Exception, mensagem: str | None = None) -> dict:
    """Payload de erro estruturado, truncado e PII-scrubbed (E2.06).

    Nunca retorna str(exc) cru: aplica _strip_secrets (credenciais) e
    scrub_mcp_output (CPF/telefone/email) antes de sair no protocolo MCP.
    """
    from app.services.mcp_pii import scrub_mcp_output

    detail = _strip_secrets(str(exc))[:200]
    return scrub_mcp_output(
        {
            "erro": code,
            "mensagem": mensagem or detail,
            "tipo_erro": type(exc).__name__,
        }
    )


# ============================================================================
# Tool 1: Calcular emolumento (direto via service)
# ============================================================================


def _normalizar_slug_calculo(tipo: str) -> str:
    # Aliases de slugs legados do placeholder para slugs oficiais da Tabela 1.
    legacy = {
        "procuracao": "procuracao_geral",
        "autenticacao": "autenticacao_copia_folha",
        "autenticação": "autenticacao_copia_folha",
        "reconhecimento_firma": "reconhecimento_firma_assinatura",
    }
    return legacy.get(tipo, tipo)


def _normalizar_layer(pricing_layer: str) -> str:
    return (pricing_layer or "regulatory_tjmg").strip().lower()


@mcp.tool(
    name="cartorio_calcular_emolumento",
    description=(
        "Consulta emolumento oficial MG 2026 (Portaria CGJ/TJMG 8.664/2025, "
        "Tabela 1 - Atos do Tabeliao de Notas) ou tabela operacional do balcão 2026. "
        "Atos compostos (folhas adicionais, urgencia, conteudo financeiro) retornam "
        "HITL_REQUIRED - nunca infira preco. NAO envolve PII - pode ser consumido publicamente."
    ),
)
@contabilizar_tool("cartorio_calcular_emolumento")
async def cartorio_calcular_emolumento(
    tipo: str,
    folhas: int = 1,
    urgencia: bool = False,
    pricing_layer: str = "regulatory_tjmg",
) -> dict:
    """Calcula emolumento cartorario MG 2026 (Portaria CGJ/TJMG 8.664/2025).

    Fonte autoritativa: app/services/emolumento_real_djalma.py (Tabela 1 —
    Atos do Tabeliao de Notas, valor final ao usuario = emolumentos + TFJ)
    ou app/services/emolumento_operacional_balcao.py (Tabela Operacional de Balcão).

    Args:
        tipo: Tipo do ato. Aceita slugs oficiais e operacionais.
        folhas: Numero de folhas.
        urgencia: Se true, retorna HITL_REQUIRED (sem acrescimo publicado).
        pricing_layer: Camada de preço ('regulatory_tjmg' ou 'operational_pos_2notas').

    Returns:
        Dict com status (PUBLISHED|HITL_REQUIRED), total, item_portaria,
        motivo_hitl, tabela_referencia e ecos de tipo/folhas/urgencia.
    """
    from app.services.emolumento_real_djalma import calcular_emolumento_real_djalma
    from app.services.emolumento_operacional_balcao import calcular_emolumento_operacional

    layer = _normalizar_layer(pricing_layer)
    if layer in {"operational_pos_2notas", "operational"}:
        res = calcular_emolumento_operacional(tipo, folhas=folhas, urgencia=urgencia)
        res["tipo"] = tipo
        res["folhas"] = folhas
        res["urgencia"] = urgencia
        return res

    if layer not in {"regulatory_tjmg"}:
        return {
            "status": "HITL_REQUIRED",
            "tipo": tipo,
            "motivo_hitl": f"Camada de precificacao desconhecida: {pricing_layer}",
            "tabela_referencia": "INVALID_LAYER",
            "pricing_layer": layer,
            "item_portaria": None,
            "total": None,
            "folhas": folhas,
            "urgencia": urgencia,
        }

    resultado = calcular_emolumento_real_djalma(_normalizar_slug_calculo(tipo), folhas=folhas, urgencia=urgencia)
    payload = resultado.to_dict()
    payload["tipo"] = tipo
    payload["pricing_layer"] = "regulatory_tjmg"
    payload["folhas"] = folhas
    payload["urgencia"] = urgencia
    return payload


@mcp_public.tool(
    name="cartorio_calcular_emolumento",
    description=(
        "Consulta somente atos canônicos da Tabela 1 de emolumentos MG 2026. "
        "Tipo inválido ou ato composto não é aceito no perfil público."
    ),
)
async def cartorio_calcular_emolumento_publico(
    tipo: str,
    folhas: int = 1,
    urgencia: bool = False,
    pricing_layer: str = "regulatory_tjmg",
) -> dict:
    """Calcula somente um ato canônico e sem conteúdo identificável no perfil público."""
    from app.services.emolumento_real_djalma import ATOS_PUBLICADOS_2026

    if tipo not in ATOS_PUBLICADOS_2026:
        return scrub_mcp_output(
            {
                "erro": "INVALID_EMOLUMENTO_TYPE",
                "mensagem": "Tipo de ato não disponível para consulta pública.",
            }
        )
    if pricing_layer != "regulatory_tjmg":
        return scrub_mcp_output(
            {
                "erro": "UNSUPPORTED_PRICING_LAYER",
                "mensagem": "No perfil publico, apenas pricing_layer=regulatory_tjmg é suportado.",
            }
        )
    if folhas != 1 or urgencia:
        return scrub_mcp_output(
            {
                "erro": "UNSUPPORTED_PUBLIC_EMOLUMENTO_REQUEST",
                "mensagem": "A consulta pública aceita apenas um ato simples da Tabela 1.",
            }
        )

    payload = await cartorio_calcular_emolumento(
        tipo=tipo,
        folhas=folhas,
        urgencia=urgencia,
        pricing_layer=pricing_layer,
    )
    payload["tipo"] = tipo
    return scrub_mcp_output(payload)


@mcp.tool(
    name="cartorio_extrair_e_calcular_real",
    description=(
        "Extrai dados de solicitação em linguagem natural com PII scrubbing "
        "e calcula o valor exato dos emolumentos notariais com discriminativo fiscal completo "
        "(Emolumento, TFJ, Recompe-MG e ISSQN Uberlândia 5%) para o 2º Serviço Notarial de Uberlândia (Djalma)."
    ),
)
@contabilizar_tool("cartorio_extrair_e_calcular_real")
async def cartorio_extrair_e_calcular_real(
    texto_usuario: str,
    forcar_urgencia: bool = False,
) -> dict:
    """Extrai entidades e calcula orçamento notarial real para Uberlândia/MG 2026.

    Args:
        texto_usuario: Texto em linguagem natural da solicitação do cliente.
        forcar_urgencia: Se true, força a taxa de urgência notarial.

    Returns:
        Dict com entidades extraídas, PII sanitizado, cálculo discriminado e indicador HITL.
    """
    from app.services.ai_data_extractor import extrair_e_calcular_solicitacao

    res = extrair_e_calcular_solicitacao(texto_usuario, forcar_urgencia=forcar_urgencia)
    return res.to_dict()


# ============================================================================
# Tool 2: Consultar protocolo
# ============================================================================


@mcp.tool(
    name="cartorio_consultar_protocolo",
    description=(
        "Consulta status atual de um protocolo pelo numero ANO-SEQUENCIAL. "
        "Retorna status, etapa atual, historico de etapas, proxima acao e "
        "prazo estimado. Toda consulta e registrada no audit log (LGPD art. 37)."
    ),
)
@contabilizar_tool("cartorio_consultar_protocolo")
async def cartorio_consultar_protocolo(numero: str) -> dict:
    """Consulta status de um protocolo.

    Args:
        numero: Numero do protocolo (formato ANO-SEQUENCIAL, ex: '2026-00001').

    Returns:
        Dict com numero, status, etapa_atual, tipo, canal_origem, valor_base,
        valor_total, tabela_referencia, prazo_estimado, proxima_acao, created_at.
        Zero PII (campo cliente intencionalmente ausente).
    """
    from sqlalchemy import select
    from app.db import session_scope
    from app.models.protocolo import Protocolo
    from app.services.mcp_pii import scrub_mcp_output

    try:
        with session_scope() as db:
            protocolo = db.execute(
                select(Protocolo).where(Protocolo.numero == numero)
            ).scalar_one_or_none()

            if protocolo is None:
                return scrub_mcp_output(
                    {
                        "erro": "PROTOCOLO_NOT_FOUND",
                        "mensagem": f"Protocolo {numero} nao encontrado.",
                        "numero": numero,
                    }
                )

            return scrub_mcp_output(
                {
                    "numero": protocolo.numero,
                    "status": protocolo.status,
                    "etapa_atual": "criado",
                    "tipo": protocolo.tipo,
                    "canal_origem": protocolo.canal_origem,
                    "valor_base": str(protocolo.valor_base) if protocolo.valor_base else None,
                    "valor_total": str(protocolo.valor_total) if protocolo.valor_total else None,
                    "tabela_referencia": protocolo.tabela_referencia,
                    "prazo_estimado": f"{protocolo.prazo_dias} dias uteis"
                    if protocolo.prazo_dias
                    else None,
                    "proxima_acao": "Aguardando validacao humana do escrevente.",
                    "created_at": protocolo.created_at.isoformat()
                    if protocolo.created_at
                    else None,
                }
            )
    except Exception as e:
        return scrub_mcp_output({"erro": "INTERNAL_ERROR", "mensagem": str(e)[:200]})


# ============================================================================
# Tool 3: Criar protocolo (com consentimento LGPD obrigatorio)
# ============================================================================


@mcp.tool(
    name="cartorio_criar_protocolo",
    description=(
        "Cria um novo protocolo em modo DRAFT (HITL obrigatorio). "
        "REQUER consentimento LGPD explicito - sem isso, retorna LGPD_BLOCKED. "
        "Cliente SEMPRE recebera handoff humano para validacao."
    ),
)
@contabilizar_tool("cartorio_criar_protocolo")
async def cartorio_criar_protocolo(
    tipo: str,
    cliente_cpf: str,
    cliente_nome: str,
    consentimento_lgpd: bool,
    canal_origem: str = "web",
) -> dict:
    """Cria protocolo (REQUER consentimento LGPD explicito).

    Args:
        tipo: Tipo do ato a protocolar (deve estar na tabela de emolumentos).
        cliente_cpf: CPF do cliente (11 digitos, com ou sem pontuacao).
                     Sera hasheado antes de persistir.
        cliente_nome: Nome completo do cliente.
        consentimento_lgpd: OBRIGATORIO ser True. Se False, retorna LGPD_BLOCKED.
        canal_origem: Canal de origem (whatsapp/telegram/web/balcao/email).

    Returns:
        Dict com status (criado/erro), numero, protocolo_id, cliente_id.
    """
    if not consentimento_lgpd:
        return {
            "erro": "LGPD_BLOCKED",
            "mensagem": "Consentimento LGPD obrigatorio para criar protocolo. "
            "Confirme com o cliente e tente novamente.",
        }

    # Validacao basica de CPF (11 digitos)
    digits = "".join(c for c in cliente_cpf if c.isdigit())
    if len(digits) != 11:
        return {"erro": "PII_INVALIDO", "mensagem": "CPF invalido. Deve conter 11 digitos."}

    # Chama a service function diretamente - SEM self-loop HTTP.
    # Self-loop (httpx.post pra localhost:8000) causava deadlock em carga
    # porque MCP sub-app + API principal compartilham o mesmo event loop.
    # Refator: logica de negocio extraida para app.services.protocolo.criar_protocolo_svc
    # e reusada tanto pelo endpoint FastAPI quanto por esta tool MCP.
    from app.db import session_scope
    from app.services.protocolo import (
        LGPDBlockedError,
        TipoInvalidoError,
        criar_protocolo_svc,
    )

    try:
        with session_scope() as db:
            return criar_protocolo_svc(
                db,
                tipo=tipo,
                cliente_cpf=digits,
                cliente_nome=cliente_nome,
                consentimento_lgpd=True,
                canal_origem=canal_origem,
            )
    except LGPDBlockedError as e:
        return {"erro": "LGPD_BLOCKED", "mensagem": str(e)}
    except TipoInvalidoError as e:
        return {"erro": "TIPO_INVALIDO", "mensagem": str(e)}
    except Exception as e:
        # E2.06: excecao de banco/ORM pode embutir CPF/nome do payload ou DSN.
        # Nunca devolver str(exc) cru — strip secrets + scrub PII.
        return _tool_error("INTERNAL_ERROR", e)


# ============================================================================
# Tool 4: Gerar segunda via de documento
# ============================================================================


@mcp.tool(
    name="cartorio_gerar_segunda_via",
    description=(
        "Gera link de download da segunda via de um documento associado a "
        "um protocolo. v0.4.0 MVP: retorna URL placeholder com hash deterministico. "
        "Sprint 2: integracao com storage Supabase para PDF real."
    ),
)
@contabilizar_tool("cartorio_gerar_segunda_via")
async def cartorio_gerar_segunda_via(
    protocolo: str,
    canal: str = "whatsapp",
) -> dict:
    """Gera link de download da segunda via.

    Args:
        protocolo: Numero do protocolo (YYYY-NNNNN).
        canal: Canal de envio (whatsapp/email/presencial).

    Returns:
        Dict com url_pdf, validade_horas, protocolo, canal.
    """
    h = hashlib.sha256(f"{protocolo}:{time.time()}".encode()).hexdigest()[:16]
    return {
        "url_pdf": f"https://supbase.2notasudi.com.br/storage/v1/object/sign/documentos/{protocolo}-{h}.pdf",
        "validade_horas": 24,
        "protocolo": protocolo,
        "canal": canal,
        "mensagem": "Link gerado. Em producao (Sprint 2) o PDF sera assinado digitalmente.",
    }


# ============================================================================
# Tool 5: Verificar audit log
# ============================================================================


@mcp.tool(
    name="cartorio_audit_verify",
    description=(
        "Verifica integridade da cadeia de audit log (hash chain SHA256 + "
        "HMAC). Retorna chain_ok (bool), last_valid_position, total_entries. "
        "Recomendado rodar diariamente via cron (AUDIT_VERIFY_CRON)."
    ),
)
@contabilizar_tool("cartorio_audit_verify")
async def cartorio_audit_verify() -> dict:
    """Verifica integridade do audit log (hash chain + HMAC)."""
    from app.db import session_scope
    from app.services.audit import AuditService
    from app.services.mcp_pii import scrub_mcp_output

    try:
        with session_scope() as db:
            ok, last_valid = AuditService.verify_chain(db)
            from app.models.audit_log import AuditLog

            total = db.query(AuditLog).count()
        return scrub_mcp_output(
            {
                "chain_ok": ok,
                "last_valid_position": last_valid,
                "total_entries": total,
            }
        )
    except Exception as e:
        return scrub_mcp_output({"erro": "INTERNAL_ERROR", "mensagem": str(e)[:200]})


@mcp.tool(
    name="cartorio_audit_hash_sequence",
    description=(
        "G8.07.T2: valida sequência de hashes SHA256 da audit chain **offline** "
        "(sem DB). Recebe lista de entries {payload, timestamp, hash, prev_hash}. "
        "Use para drills, mutmut killers e validação de samples exportados. "
        "Para chain live no DB use cartorio_audit_verify."
    ),
)
@contabilizar_tool("cartorio_audit_hash_sequence")
async def cartorio_audit_hash_sequence(entries: list[dict]) -> dict:
    """Valida sequência de hashes da audit chain (offline).

    Args:
        entries: Lista ordenada (mais antiga → mais nova). Cada item:
            payload (dict), timestamp (ISO str), hash (hex), prev_hash (hex|null).

    Returns:
        chain_ok, last_valid_position, total, broken_at, detail (sem PII raw).
    """
    from app.services.audit import AuditService
    from app.services.mcp_pii import scrub_mcp_output

    if not isinstance(entries, list):
        return scrub_mcp_output(
            {
                "erro": "INVALID_ENTRIES",
                "mensagem": "entries deve ser uma lista de objetos audit.",
            }
        )
    if len(entries) > 5000:
        return scrub_mcp_output(
            {
                "erro": "TOO_MANY_ENTRIES",
                "mensagem": "limite 5000 entries por chamada MCP.",
            }
        )
    result = AuditService.verify_hash_sequence(entries)
    return scrub_mcp_output(result)


# ============================================================================
# Tool 6: Health check
# ============================================================================


@mcp.tool(
    name="cartorio_saudacao",
    description="Health check do Cartorio API. Publico, sem PII.",
)
@contabilizar_tool("cartorio_saudacao")
async def cartorio_saudacao() -> dict:
    """Health check do Cartorio API.

    Retorna metadata estatico do MCP server + timestamp.
    Antes fazia httpx.get('/health') em localhost - self-loop HTTP que causava
    deadlock em carga. Refator: sem chamada HTTP, apenas settings locais.
    """
    import datetime

    return {
        "api_status": 200,
        "mcp_server": "cartorio-mcp-cabuloso v0.6.0",
        "app_name": settings.app_name if settings else "cartorio-api",
        "app_version": "0.6.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "transport": "streamable_http",
        "lgpd_compliance": True,
    }


# ============================================================================
# Tool 7: Meta info
# ============================================================================


# ============================================================================
# Tools de Interação Rica (Telegram & WhatsApp - Evolution API)
# ============================================================================


@mcp.tool(
    name="cartorio_enviar_whatsapp_reaction",
    description="Envia uma reação com emoji (ex: 👍, ❤️) para uma mensagem específica no WhatsApp do cliente.",
)
@contabilizar_tool("cartorio_enviar_whatsapp_reaction")
async def cartorio_enviar_whatsapp_reaction(number: str, message_id: str, emoji: str) -> dict:
    """Envia uma reação no WhatsApp do cliente."""
    from app.services.notificacao import NotificationService

    try:
        success = await NotificationService.enviar_whatsapp_reaction(number, message_id, emoji)
    except Exception as e:
        # E2.06: nunca propagar excecao crua (pode embutir numero/PII).
        return _tool_error("SEND_FAILED", e) | {"sucesso": False}
    return {"sucesso": success}


@mcp.tool(
    name="cartorio_enviar_whatsapp_poll",
    description="Envia uma enquete com opções para o WhatsApp do cliente.",
)
@contabilizar_tool("cartorio_enviar_whatsapp_poll")
async def cartorio_enviar_whatsapp_poll(number: str, question: str, options: list[str]) -> dict:
    """Envia uma enquete no WhatsApp do cliente."""
    from app.services.notificacao import NotificationService

    try:
        success = await NotificationService.enviar_whatsapp_poll(number, question, options)
    except Exception as e:
        return _tool_error("SEND_FAILED", e) | {"sucesso": False}
    return {"sucesso": success}


@mcp.tool(
    name="cartorio_enviar_whatsapp_media",
    description="Envia imagem ou documento (PDF/doc) para o WhatsApp do cliente.",
)
@contabilizar_tool("cartorio_enviar_whatsapp_media")
async def cartorio_enviar_whatsapp_media(
    number: str, media_url: str, mediatype: str, filename: str, caption: str | None = None
) -> dict:
    """Envia mídia no WhatsApp do cliente. mediatype deve ser 'image' ou 'document'."""
    from app.services.notificacao import NotificationService

    try:
        success = await NotificationService.enviar_whatsapp_media(
            number, media_url, mediatype, filename, caption
        )
    except Exception as e:
        return _tool_error("SEND_FAILED", e) | {"sucesso": False}
    return {"sucesso": success}


@mcp.tool(
    name="cartorio_enviar_telegram_reaction",
    description="Envia uma reação com emoji (ex: 👍, 👀) para uma mensagem do cliente no Telegram.",
)
@contabilizar_tool("cartorio_enviar_telegram_reaction")
async def cartorio_enviar_telegram_reaction(chat_id: int, message_id: int, emoji: str) -> dict:
    """Envia uma reação no Telegram do cliente."""
    from app.api.v1.telegram import _react

    emoji_key = "thumbsup"
    for k, v in {
        "thumbsup": "👍",
        "heart": "❤️",
        "smile": "😊",
        "eyes": "👀",
        "check": "✅",
        "cross": "❌",
    }.items():
        if emoji == v or emoji == k:
            emoji_key = k
            break
    try:
        await _react(chat_id, message_id, emoji_key)
        return {"sucesso": True}
    except Exception as e:
        # E2.06: str(exc) de httpx embute a URL com o bot token e pode trazer
        # contexto do chat. Strip secrets + scrub PII antes de responder.
        return _tool_error("SEND_FAILED", e) | {"sucesso": False}


@mcp.tool(
    name="cartorio_enviar_telegram_poll",
    description="Envia uma enquete de múltipla escolha para o chat do cliente no Telegram.",
)
@contabilizar_tool("cartorio_enviar_telegram_poll")
async def cartorio_enviar_telegram_poll(chat_id: int, question: str, options: list[str]) -> dict:
    """Envia uma enquete no Telegram do cliente."""
    from app.api.v1.telegram import _send_poll

    try:
        success = await _send_poll(chat_id, question, options)
    except Exception as e:
        return _tool_error("SEND_FAILED", e) | {"sucesso": False}
    return {"sucesso": success}


@mcp.tool(
    name="cartorio_enviar_telegram_media",
    description="Envia imagem ou documento (PDF) para o chat do cliente no Telegram.",
)
@contabilizar_tool("cartorio_enviar_telegram_media")
async def cartorio_enviar_telegram_media(
    chat_id: int, media_url: str, mediatype: str, filename: str, caption: str | None = None
) -> dict:
    """Envia mídia no Telegram do cliente. mediatype deve ser 'image' ou 'document'."""
    from app.api.v1.telegram import _send_photo, _send_document

    try:
        if mediatype == "image":
            success = await _send_photo(chat_id, media_url, caption)
        else:
            success = await _send_document(chat_id, media_url, filename, caption)
    except Exception as e:
        return _tool_error("SEND_FAILED", e) | {"sucesso": False}
    return {"sucesso": success}


@mcp.tool(
    name="super_server_info",
    description="Meta info do MCP server (versao, contagem de tools, etc).",
)
@contabilizar_tool("super_server_info")
async def super_server_info() -> dict:
    """Meta info do MCP server."""
    tools_list = await mcp.list_tools()
    return {
        "name": "cartorio-mcp-cabuloso",
        "version": "0.6.0",
        "tools_count": len(tools_list),
        "backend": "https://api.2notasudi.com.br",
        "docs": "https://api.2notasudi.com.br/docs",
        "lgpd_compliance": True,
        "pii_scrubbing": settings.pii_scrub_enabled if settings else True,
        "hitl_obrigatorio_em": [
            "cartorio_criar_protocolo",
            "isencao de emolumento",
            "validacao juridica",
            "emissao de certidao/escritura",
        ],
        "protocolo_mcp": "2025-03-26",
        "tools": [t.name for t in tools_list],
    }


# ============================================================================
# HTTP app factory (para mount dentro da FastAPI principal)
# ============================================================================


def mcp_app() -> Any:
    """Retorna o Starlette sub-app para montar em `app.mount("/mcp", ...)` na FastAPI.

    Quando o MCP server esta montado na FastAPI principal, ele compartilha o
    mesmo processo/porta. Isso evita o self-loop HTTP e simplifica deploy
    (1 so container, 1 so Traefik router).

    IMPORTANTE: ao montar na FastAPI, passar `lifespan=mcp_app.lifespan` no
    construtor do FastAPI para que o TaskGroup do StreamableHTTP seja inicializado.
    Ver https://gofastmcp.com/deployment/asgi

    path="/" porque o sub-app sera montado em `app.mount("/mcp", ...)`. Se o
    path interno tambem fosse "/mcp", a URL final seria /mcp/mcp (duplicada).
    path="/" garante que clientes batem em `/mcp` direto (consistente com docs
    e clients MCP configurados em ~/.mavis/mcp/clients/). Sprint 5 — 2026-07-13.
    """
    from app.middleware.mcp_api_key import MCPApiKeyMiddleware

    api_key = getattr(settings, "mcp_api_key", None) if settings is not None else None
    public_api_key = getattr(settings, "mcp_public_api_key", None) if settings is not None else None
    public_max_body_bytes = (
        getattr(settings, "mcp_public_max_body_bytes", 16_384) if settings is not None else 16_384
    )
    internal_app = mcp.http_app(path="/")
    public_app = mcp_public.http_app(path="/")
    protected_app = MCPApiKeyMiddleware(
        internal_app,
        api_key=api_key,
        public_api_key=public_api_key,
        public_app=public_app,
        public_max_body_bytes=public_max_body_bytes,
    )

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with internal_app.router.lifespan_context(app):
            async with public_app.router.lifespan_context(app):
                yield

    return Starlette(routes=[Mount("/", app=protected_app)], lifespan=lifespan)


# ============================================================================
# Standalone entrypoint (porta separada em :8100, opcional)
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    if os.getenv("MCP_SERVER_TRANSPORT", "http") == "http":
        # Modo standalone: o endpoint Streamable HTTP fica na raiz `/`.
        # O mount da API principal adiciona o prefixo externo `/mcp`.
        app = mcp_app()
        port = int(os.getenv("MCP_SERVER_PORT", "8100"))
        host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()  # stdio
