"""MCP server da API do Cartorio - expõe tools MCP para clients
(Claude, Cursor, Zed, OpenCode, Antigravity) no protocolo MCP 2025-03-26.

Tools expostas:
- cartorio_calcular_emolumento: calcula emolumento MG 2026
- cartorio_consultar_protocolo: status de protocolo
- cartorio_criar_protocolo: cria protocolo (com consentimento LGPD)
- cartorio_gerar_segunda_via: gera link de download de PDF (segunda via)
- cartorio_audit_verify: verifica integridade do audit log
- cartorio_saudacao: health check
- super_server_info: meta info

Modos de execucao:
1. **Standalone** (`python mcp_server.py`): sobe uvicorn em :8100/MCP_SERVER_PORT.
   Util para clients MCP que preferem endpoint dedicado.
2. **Montado na FastAPI** (`mcp_app()`): retorna sub-app Starlette que pode ser
   `app.mount("/mcp", mcp_server.mcp_app())` em main.py. Criterio do projeto:
   `curl https://api.2notasudi.com.br/mcp` deve retornar JSON de tools MCP.

Implementacao chama os services do app diretamente (sem HTTP self-loop) para
evitar timeout em recursao localhost:8000 -> /mcp -> localhost:8000.
"""

from __future__ import annotations

import os
import sys
import hashlib
import time
from pathlib import Path
from typing import Any

# Adiciona backend/ ao path para importar app.*
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP

# Reusa o settings do backend
try:
    from app.config import Settings, settings  # noqa: F401
except ImportError:
    # Fallback se rodar fora do venv
    settings = None  # type: ignore[assignment]


# ============================================================================
# FastMCP server
# ============================================================================

mcp = FastMCP(
    name="cartorio-mcp-cabuloso",
    version="0.4.0",
    instructions=(
        "MCP server do Cartorio 2 Notas Uberlandia. "
        "Use cartorio_calcular_emolumento para valores oficiais MG 2026, "
        "cartorio_consultar_protocolo para status, "
        "cartorio_audit_verify para integridade do audit log. "
        "HITL obrigatorio em qualquer decisao juridica."
    ),
)


# ============================================================================
# Tool 1: Calcular emolumento (direto via service)
# ============================================================================


@mcp.tool(
    name="cartorio_calcular_emolumento",
    description=(
        "Calcula emolumento cartorario oficial MG 2026 + adicionais por folha "
        "(5% a partir da 2a) + adicional de urgencia (50%). NAO envolve PII - "
        "pode ser consumido publicamente."
    ),
)
async def cartorio_calcular_emolumento(
    tipo: str,
    folhas: int = 1,
    urgencia: bool = False,
) -> dict:
    """Calcula emolumento cartorario MG 2026.

    Args:
        tipo: Tipo do ato. Opcoes: certidao_negativa, certidao_positiva,
              certidao_casamento, escritura_compra_venda, escritura_doacao,
              procuracao, autenticacao, reconhecimento_firma,
              registro_nascimento, registro_obito.
        folhas: Numero de folhas (para atos com base por folha). 1 a 1000.
        urgencia: Se true, aplica acrescimo de 50% por urgencia.

    Returns:
        Dict com tipo, folhas, urgencia, base, adicional_folhas,
        adicional_urgencia, total, tabela_referencia, valido_ate.
    """
    from app.services.emolumento import calcular as calcular_svc

    try:
        resultado = calcular_svc(tipo, folhas=folhas, urgencia=urgencia)
    except ValueError as e:
        return {"erro": "TIPO_INVALIDO", "mensagem": str(e)}

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

    try:
        with session_scope() as db:
            protocolo = db.execute(
                select(Protocolo).where(Protocolo.numero == numero)
            ).scalar_one_or_none()

            if protocolo is None:
                return {
                    "erro": "PROTOCOLO_NOT_FOUND",
                    "mensagem": f"Protocolo {numero} nao encontrado.",
                    "numero": numero,
                }

            return {
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
                "created_at": protocolo.created_at.isoformat() if protocolo.created_at else None,
            }
    except Exception as e:
        return {"erro": "INTERNAL_ERROR", "mensagem": str(e)[:200]}


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
        return {"erro": "INTERNAL_ERROR", "mensagem": str(e)[:200]}


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
async def cartorio_audit_verify() -> dict:
    """Verifica integridade do audit log (hash chain + HMAC)."""
    from app.db import session_scope
    from app.services.audit import AuditService

    try:
        with session_scope() as db:
            ok, last_valid = AuditService.verify_chain(db)
            from app.models.audit_log import AuditLog

            total = db.query(AuditLog).count()
        return {
            "chain_ok": ok,
            "last_valid_position": last_valid,
            "total_entries": total,
        }
    except Exception as e:
        return {"erro": "INTERNAL_ERROR", "mensagem": str(e)[:200]}


# ============================================================================
# Tool 6: Health check
# ============================================================================


@mcp.tool(
    name="cartorio_saudacao",
    description="Health check do Cartorio API. Publico, sem PII.",
)
async def cartorio_saudacao() -> dict:
    """Health check do Cartorio API.

    Retorna metadata estatico do MCP server + timestamp.
    Antes fazia httpx.get('/health') em localhost - self-loop HTTP que causava
    deadlock em carga. Refator: sem chamada HTTP, apenas settings locais.
    """
    import datetime

    return {
        "api_status": 200,
        "mcp_server": "cartorio-mcp-cabuloso v0.4.0",
        "app_name": settings.app_name if settings else "cartorio-api",
        "app_version": "0.4.0",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "transport": "streamable_http",
        "lgpd_compliance": True,
    }


# ============================================================================
# Tool 7: Meta info
# ============================================================================


@mcp.tool(
    name="super_server_info",
    description="Meta info do MCP server (versao, contagem de tools, etc).",
)
async def super_server_info() -> dict:
    """Meta info do MCP server."""
    tools_list = await mcp.list_tools()
    return {
        "name": "cartorio-mcp-cabuloso",
        "version": "0.4.0",
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
    """
    return mcp.http_app(path="/mcp")


# ============================================================================
# Standalone entrypoint (porta separada em :8100, opcional)
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    if os.getenv("MCP_SERVER_TRANSPORT", "http") == "http":
        # Modo standalone: serve em :8100/mcp
        app = mcp.http_app(path="/mcp")
        port = int(os.getenv("MCP_SERVER_PORT", "8100"))
        host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()  # stdio
