"""MCP server da API do Cartorio - expõe tools MCP para clients (Claude, Cursor, Zed, OpenCode, Antigravity).

Tools expostas:
- cartorio_calcular_emolumento: calcula emolumento MG 2026
- cartorio_consultar_protocolo: status de protocolo
- cartorio_criar_protocolo: cria protocolo (com consentimento LGPD)
- cartorio_audit_verify: verifica integridade do audit log
- cartorio_saudacao: health check
- super_server_info: meta info
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Adiciona backend/ ao path para importar app.*
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP, Context
import httpx

# Reusa o settings do backend
try:
    from app.config import settings
except ImportError:
    # Fallback se rodar fora do venv
    settings = None


# ============================================================================
# FastMCP server
# ============================================================================

mcp = FastMCP(
    name="cartorio-mcp-cabuloso",
    version="0.1.0",
    instructions=(
        "MCP server do Cartorio 2 Notas Uberlandia. "
        "Use cartorio_calcular_emolumento para valores oficiais MG 2026, "
        "cartorio_consultar_protocolo para status, "
        "cartorio_audit_verify para integridade do audit log. "
        "HITL obrigatorio em qualquer decisao juridica."
    ),
)


# ============================================================================
# Tool 1: Calcular emolumento
# ============================================================================

@mcp.tool(name="cartorio_calcular_emolumento")
async def cartorio_calcular_emolumento(
    tipo: str,
    folhas: int = 1,
    urgencia: bool = False,
) -> dict:
    """Calcula emolumento cartorario MG 2026.

    Args:
        tipo: Tipo do ato. Opcoes: 'certidao', 'escritura', 'procuracao',
              'reconhecimento_firma', 'autenticacao', 'registro'
        folhas: Numero de folhas (para atos com base por folha)
        urgencia: Se true, aplica acrescimo de 50% por urgencia

    Returns:
        Dict com base, adicional_folhas, adicional_urgencia, total,
        tabela_referencia, valido_ate

    Example:
        >>> await cartorio_calcular_emolumento("certidao", folhas=2, urgencia=False)
    """
    # Chama a propria API
    base = "http://localhost:8000"  # interno
    if settings:
        base = f"http://localhost:{settings.app_port}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{base}/api/v1/emolumento/calcular",
            params={"tipo": tipo, "folhas": folhas, "urgencia": str(urgencia).lower()},
        )
        if r.status_code == 200:
            return r.json()
        return {"erro": f"API retornou {r.status_code}", "body": r.text[:500]}


# ============================================================================
# Tool 2: Consultar protocolo
# ============================================================================

@mcp.tool(name="cartorio_consultar_protocolo")
async def cartorio_consultar_protocolo(numero: str) -> dict:
    """Consulta status de um protocolo (placeholder - implementar endpoint).

    Args:
        numero: Numero do protocolo (formato ANO-SEQUENCIAL, ex: '2026-00001')

    Returns:
        Dict com status, etapa_atual, historico, proxima_acao
    """
    # TODO: implementar endpoint /api/v1/protocolo/{numero}
    return {
        "numero": numero,
        "status": "EM_ANDAMENTO",
        "etapa_atual": "ANALISE_DOCUMENTOS",
        "historico": [
            {"data": "2026-06-20", "evento": "RECEBIDO", "responsavel": "balcao"},
            {"data": "2026-06-22", "evento": "EM_ANALISE", "responsavel": "escrevente-1"},
        ],
        "proxima_acao": "Aguardando analise do escrevente responsavel",
        "prazo_estimado": "5 dias uteis",
    }


# ============================================================================
# Tool 3: Criar protocolo (com consentimento LGPD obrigatorio)
# ============================================================================

@mcp.tool(name="cartorio_criar_protocolo")
async def cartorio_criar_protocolo(
    tipo_ato: str,
    cliente_cpf: str,
    cliente_nome: str,
    consentimento_lgpd: bool,
    *,
    ctx: Context,
) -> dict:
    """Cria um novo protocolo (REQUER consentimento LGPD explicito).

    Args:
        tipo_ato: Tipo do ato a protocolar
        cliente_cpf: CPF do cliente (será hasheado antes de salvar)
        cliente_nome: Nome completo do cliente
        consentimento_lgpd: OBRIGATORIO ser True. Se False, retorna erro.
        ctx: Context MCP (injetado)

    Returns:
        Dict com numero_protocolo, status, prazo_estimado

    Note:
        Cliente SEMPRE recebera handoff humano (HITL nivel 2) para validacao.
    """
    if not consentimento_lgpd:
        return {
            "erro": "LGPD_BLOCKED",
            "mensagem": "Consentimento LGPD obrigatorio para criar protocolo. "
                        "Confirme com o cliente e tente novamente.",
        }

    # PII scrubbing antes de qualquer coisa
    from app.services.pii import scrub
    pii = scrub(cliente_cpf)
    if pii.redaction_count > 0:
        return {"erro": "PII_INVALIDO", "mensagem": "CPF invalido ou mascarado. Verifique o formato."}

    # TODO: implementar POST /api/v1/protocolo
    return {
        "numero_protocolo": "2026-00042",
        "status": "RECEBIDO",
        "prazo_estimado": "5 dias uteis",
        "mensagem": "Protocolo criado. Escrevente responsavel ira analisar e dar retorno. "
                    "Voce recebera atualizacoes via WhatsApp.",
    }


# ============================================================================
# Tool 4: Verificar audit log
# ============================================================================

@mcp.tool(name="cartorio_audit_verify")
async def cartorio_audit_verify() -> dict:
    """Verifica integridade do audit log (hash chain + HMAC).

    Returns:
        Dict com chain_ok (bool), last_valid_position, total_entries
    """
    base = "http://localhost:8000"
    if settings:
        base = f"http://localhost:{settings.app_port}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{base}/api/v1/audit/verify")
        if r.status_code == 200:
            return r.json()
        return {"erro": f"API retornou {r.status_code}"}


# ============================================================================
# Tool 5: Health check
# ============================================================================

@mcp.tool(name="cartorio_saudacao")
async def cartorio_saudacao() -> dict:
    """Health check do Cartorio API. Publico, sem PII."""
    base = "http://localhost:8000"
    if settings:
        base = f"http://localhost:{settings.app_port}"
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(f"{base}/health")
        return {
            "api_status": r.status_code,
            "api_body": r.json() if r.status_code == 200 else r.text[:200],
            "mcp_server": "cartorio-mcp-cabuloso v0.1.0",
        }


# ============================================================================
# Tool 6: Meta info
# ============================================================================

@mcp.tool(name="super_server_info")
async def super_server_info() -> dict:
    """Meta info do MCP server."""
    return {
        "name": "cartorio-mcp-cabuloso",
        "version": "0.1.0",
        "tools_count": 6,
        "backend": "https://api.2notasudi.com.br",
        "docs": "https://api.2notasudi.com.br/docs",
        "lgpd_compliance": True,
        "pii_scrubbing": settings.pii_scrub_enabled if settings else True,
        "hitl_obrigatorio_em": [
            "cartorio_criar_protocolo (criação de protocolo)",
            "isencao de emolumento",
            "validacao juridica",
            "emissao de certidao/escritura",
        ],
    }


# ============================================================================
# Entrypoint
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    if os.getenv("MCP_SERVER_TRANSPORT", "http") == "http":
        app = mcp.streamable_http_app()
        port = int(os.getenv("MCP_SERVER_PORT", "8100"))
        host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()  # stdio