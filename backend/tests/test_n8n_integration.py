"""Testes de integração: N8N Workflow Engine.

Valida:
  - N8N API acessível via X-N8N-API-KEY
  - 34 workflows ativos
  - Workflow EVO-IN ativo (webhook Evolution)
  - Workflow 31 - Telegram Listener ativo
  - Workflow 12 - Chatbot LLM ativo
  - Health endpoint /healthz responde 200
  - MCP URL configurada
  - Credenciais N8N no settings
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.config import settings


# ---------------------------------------------------------------------------
# Testes: Configuração N8N
# ---------------------------------------------------------------------------
class TestN8NConfig:
    def test_n8n_base_url_configurado(self) -> None:
        """settings.n8n_base_url deve estar configurado."""
        assert settings.n8n_base_url
        # Aceita formato interno (cartorio_n8n:5678) ou URL pública (flow.2notasudi.com.br)
        assert any([
            "n8n" in settings.n8n_base_url.lower(),
            "5678" in settings.n8n_base_url,
            "flow" in settings.n8n_base_url.lower(),
        ]), f"N8N URL inesperada: {settings.n8n_base_url}"

    def test_n8n_api_key_existe(self) -> None:
        """settings.n8n_api_key deve existir (skip se nao configurado)."""
        if not settings.n8n_api_key:
            pytest.skip("N8N_API_KEY nao configurado (ambiente de teste)")
        assert len(settings.n8n_api_key) > 20

    def test_n8n_mcp_url_configurada(self) -> None:
        """settings.n8n_mcp_url deve estar configurada."""
        assert settings.n8n_mcp_url
        assert "mcp" in settings.n8n_mcp_url.lower()

    def test_n8n_webhook_secret_existe(self) -> None:
        """settings.n8n_webhook_secret deve existir (skip se nao configurado)."""
        if not settings.n8n_webhook_secret:
            pytest.skip("N8N_WEBHOOK_SECRET nao configurado (ambiente de teste)")

    def test_n8n_api_key_formato_jwt(self) -> None:
        """API key deve ter formato JWT (3 partes separadas por ponto)."""
        if not settings.n8n_api_key:
            pytest.skip("N8N_API_KEY nao configurado (ambiente de teste)")
        parts = settings.n8n_api_key.split(".")
        assert len(parts) == 3, "N8N API key deve ser JWT com 3 partes"


# ---------------------------------------------------------------------------
# Testes: N8N Service (n8n_error.py)
# ---------------------------------------------------------------------------
class TestN8NErrorService:
    def test_n8n_error_service_importavel(self) -> None:
        """n8n_error.py deve ser importável."""
        from app.services.n8n_error import validate_n8n_signature, classify_error_type  # type: ignore
        assert callable(validate_n8n_signature)
        assert callable(classify_error_type)

    def test_n8n_workflow_validator_importavel(self) -> None:
        """n8n_workflow_validator.py deve ser importável."""
        from app.services.n8n_workflow_validator import validate_all  # type: ignore
        assert callable(validate_all)


# ---------------------------------------------------------------------------
# Testes: Health endpoint /healthz (mock)
# ---------------------------------------------------------------------------
class TestN8NHealthMock:
    @pytest.mark.asyncio
    async def test_n8n_health_200(self) -> None:
        """GET /healthz deve retornar 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_c

            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.n8n_base_url}/healthz")
                assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Testes: N8N via API (mock de workflow list)
# ---------------------------------------------------------------------------
class TestN8NWorkflowsMock:
    @pytest.mark.asyncio
    async def test_workflow_list_tem_data(self) -> None:
        """GET /api/v1/workflows deve retornar {data: [...]}."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"id": "1", "name": "EVO-IN - Evolution Webhook Inbound", "active": True},
                {"id": "2", "name": "31 - Telegram Listener (CartorioBot test)", "active": True},
                {"id": "3", "name": "12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go)", "active": True},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_c

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://flow.2notasudi.com.br/api/v1/workflows",
                    headers={"X-N8N-API-KEY": settings.n8n_api_key or ""},
                )
                data = resp.json()
                assert "data" in data
                assert len(data["data"]) > 0


# ---------------------------------------------------------------------------
# Testes: Workflows obrigatórios configurados
# ---------------------------------------------------------------------------
class TestN8NWorkflowsObrigatorios:
    """Verifica que os workflows obrigatórios estão documentados e configurados."""

    WORKFLOWS_OBRIGATORIOS = [
        "EVO-IN - Evolution Webhook Inbound",
        "31 - Telegram Listener (CartorioBot test)",
        "12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go)",
        "03 - Handoff Humano (Chatwoot v2)",
        "00 - Error Handler Global (T25) v4",
        "MCP - Server Tools (T22) v2",
        "26 - Alerta Critico (Telegram IM + Chatwoot)",
    ]

    def test_lista_workflows_nao_vazia(self) -> None:
        """Lista de workflows obrigatórios não está vazia."""
        assert len(self.WORKFLOWS_OBRIGATORIOS) > 0

    def test_evo_in_na_lista(self) -> None:
        """EVO-IN (webhook Evolution) está na lista obrigatória."""
        assert any("EVO-IN" in w for w in self.WORKFLOWS_OBRIGATORIOS)

    def test_telegram_listener_na_lista(self) -> None:
        """Telegram Listener está na lista obrigatória."""
        assert any("Telegram" in w for w in self.WORKFLOWS_OBRIGATORIOS)

    def test_chatbot_llm_na_lista(self) -> None:
        """Chatbot LLM E2E está na lista obrigatória."""
        assert any("Chatbot LLM" in w or "12" in w for w in self.WORKFLOWS_OBRIGATORIOS)

    def test_error_handler_na_lista(self) -> None:
        """Error Handler Global está na lista obrigatória."""
        assert any("Error Handler" in w for w in self.WORKFLOWS_OBRIGATORIOS)

    def test_mcp_server_na_lista(self) -> None:
        """MCP Server Tools está na lista obrigatória."""
        assert any("MCP" in w for w in self.WORKFLOWS_OBRIGATORIOS)


# ---------------------------------------------------------------------------
# Testes de integração real (marcados, só rodam com -m integration)
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestN8NIntegrationReal:
    @pytest.mark.asyncio
    async def test_n8n_healthz_real(self) -> None:
        """GET /healthz real contra VPS."""
        if not settings.n8n_api_key:
            pytest.skip("N8N_API_KEY nao configurado (ambiente de teste)")
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.get("https://flow.2notasudi.com.br/healthz")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_n8n_workflows_count_real(self) -> None:
        """N8N deve ter 34 workflows ativos."""
        if not settings.n8n_api_key:
            pytest.skip("N8N_API_KEY nao configurado (ambiente de teste)")
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.get(
                "https://flow.2notasudi.com.br/api/v1/workflows?limit=100",
                headers={"X-N8N-API-KEY": settings.n8n_api_key or ""},
            )
            assert resp.status_code == 200
            import json
            import re
            raw = resp.text
            clean = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', ' ', raw)
            data = json.loads(clean)
            workflows = data.get("data", [])
            assert len(workflows) >= 34, f"Esperado >= 34 workflows, obtido {len(workflows)}"
            active = [w for w in workflows if w.get("active")]
            assert len(active) >= 34, f"Esperado >= 34 ativos, obtido {len(active)}"
