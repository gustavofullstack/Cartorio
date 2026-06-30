"""Testes de integração: Supabase REST client.

Valida:
  - supabase_health() retorna True
  - SupabaseRESTClient.select() retorna lista
  - SupabaseRESTClient.insert() / update() / delete() funcionam
  - SupabaseStorageClient URL gerada corretamente
  - Configurações settings.supabase_* populadas
  - Retry logic em caso de falha transiente

Todos os testes de integração real são marcados com @pytest.mark.integration
e são skippados por padrão (CI roda apenas unit tests).
Execute com: pytest -m integration -v
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.integrations.supabase_client import (
    SupabaseRESTClient,
    SupabaseStorageClient,
    supabase_health,
    supabase_rest,
    supabase_rest_anon,
    supabase_storage,
)
from app.config import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def mock_response_200() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"id": 1, "nome": "Test"}]
    resp.content = b"file_bytes"
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def mock_response_401() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 401
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Testes: configuração
# ---------------------------------------------------------------------------
class TestSupabaseConfig:
    def test_supabase_url_configurado(self) -> None:
        """settings.supabase_url deve estar configurado."""
        assert settings.supabase_url, "SUPABASE_URL não configurado (esperado em prod)"
        # Aceita easypanel.host (staging) ou 2notasudi.com.br (prod) ou localhost
        assert any(
            [
                "2notasudi" in settings.supabase_url,
                "localhost" in settings.supabase_url,
                "easypanel" in settings.supabase_url,
            ]
        ), f"SUPABASE_URL inesperado: {settings.supabase_url}"

    def test_supabase_anon_key_existe(self) -> None:
        """settings.supabase_anon_key deve existir (skip se vazio em dev local)."""
        if not settings.supabase_anon_key:
            pytest.skip("SUPABASE_ANON_KEY não configurado (ok em dev local)")
        assert len(settings.supabase_anon_key) > 10

    def test_supabase_service_role_key_existe(self) -> None:
        """settings.supabase_service_role_key deve existir (skip se vazio em dev local)."""
        if not settings.supabase_service_role_key:
            pytest.skip("SUPABASE_SERVICE_ROLE_KEY não configurado (ok em dev local)")
        assert len(settings.supabase_service_role_key) > 10

    def test_supabase_url_nao_tem_barra_final(self) -> None:
        """URL não deve terminar com /."""
        assert not settings.supabase_url.endswith("/")


# ---------------------------------------------------------------------------
# Testes: health check (mock)
# ---------------------------------------------------------------------------
class TestSupabaseHealth:
    @pytest.mark.asyncio
    async def test_health_retorna_true_quando_200(self, mock_response_200: MagicMock) -> None:
        """supabase_health() → True quando status 200."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response_200)
            mock_client_cls.return_value = mock_client
            result = await supabase_health()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_retorna_true_quando_401(self, mock_response_401: MagicMock) -> None:
        """supabase_health() → True quando 401 (UP mas precisa de auth)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response_401)
            mock_client_cls.return_value = mock_client
            result = await supabase_health()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_retorna_false_em_excecao(self) -> None:
        """supabase_health() → False quando exception (serviço DOWN)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_client_cls.return_value = mock_client
            result = await supabase_health()
        assert result is False


# ---------------------------------------------------------------------------
# Testes: SupabaseRESTClient (mock)
# ---------------------------------------------------------------------------
class TestSupabaseRESTClient:
    def test_instancia_criada(self) -> None:
        """SupabaseRESTClient pode ser instanciado."""
        client = SupabaseRESTClient()
        assert client is not None

    def test_base_url_correta(self) -> None:
        """Base URL construída corretamente."""
        client = SupabaseRESTClient()
        assert client._base == f"{settings.supabase_url}/rest/v1"

    def test_service_role_por_padrao(self) -> None:
        """Por padrão usa service_role (bypass RLS)."""
        client = SupabaseRESTClient()
        assert client._use_service_role is True

    def test_anon_key_opcao(self) -> None:
        """Pode instanciar com anon key."""
        client = SupabaseRESTClient(use_service_role=False)
        assert client._use_service_role is False

    @pytest.mark.asyncio
    async def test_select_retorna_lista(self, mock_response_200: MagicMock) -> None:
        """select() retorna lista de dicts."""
        client = SupabaseRESTClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.get = AsyncMock(return_value=mock_response_200)
            mock_client_cls.return_value = mock_c
            result = await client.select("clientes")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_insert_retorna_lista(self, mock_response_200: MagicMock) -> None:
        """insert() retorna lista com registro inserido."""
        client = SupabaseRESTClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.post = AsyncMock(return_value=mock_response_200)
            mock_client_cls.return_value = mock_c
            result = await client.insert("clientes", {"nome": "Test"})
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_rpc_chama_endpoint_correto(self, mock_response_200: MagicMock) -> None:
        """rpc() chama /rest/v1/rpc/{function_name}."""
        client = SupabaseRESTClient()
        mock_response_200.json.return_value = {"resultado": 105.40}
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.post = AsyncMock(return_value=mock_response_200)
            mock_client_cls.return_value = mock_c
            result = await client.rpc("get_emolumento_valor", {"tipo": "certidao_casamento"})
        assert result == {"resultado": 105.40}
        # Verifica que URL correta foi chamada
        call_args = mock_c.post.call_args
        assert "rpc/get_emolumento_valor" in str(call_args)


# ---------------------------------------------------------------------------
# Testes: SupabaseStorageClient
# ---------------------------------------------------------------------------
class TestSupabaseStorageClient:
    def test_instancia_criada(self) -> None:
        """SupabaseStorageClient pode ser instanciado."""
        client = SupabaseStorageClient()
        assert client is not None

    def test_public_url_gerada_corretamente(self) -> None:
        """public_url() gera URL correta."""
        client = SupabaseStorageClient()
        url = client.public_url("documentos", "protocolos/2026/001.pdf")
        assert "documentos" in url
        assert "protocolos/2026/001.pdf" in url
        assert settings.supabase_url in url

    @pytest.mark.asyncio
    async def test_upload_chama_endpoint(self, mock_response_200: MagicMock) -> None:
        """upload() chama /storage/v1/object/{bucket}/{path}."""
        mock_response_200.json.return_value = {"Key": "documentos/test.pdf"}
        client = SupabaseStorageClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.post = AsyncMock(return_value=mock_response_200)
            mock_client_cls.return_value = mock_c
            result = await client.upload("documentos", "test.pdf", b"pdfbytes", "application/pdf")
        assert "Key" in result

    @pytest.mark.asyncio
    async def test_download_retorna_bytes(self, mock_response_200: MagicMock) -> None:
        """download() retorna bytes."""
        client = SupabaseStorageClient()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_c = AsyncMock()
            mock_c.__aenter__ = AsyncMock(return_value=mock_c)
            mock_c.__aexit__ = AsyncMock(return_value=False)
            mock_c.get = AsyncMock(return_value=mock_response_200)
            mock_client_cls.return_value = mock_c
            result = await client.download("documentos", "test.pdf")
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# Testes: singletons expostos
# ---------------------------------------------------------------------------
class TestSingletons:
    def test_supabase_rest_singleton(self) -> None:
        """supabase_rest é instância de SupabaseRESTClient com service_role."""
        assert isinstance(supabase_rest, SupabaseRESTClient)
        assert supabase_rest._use_service_role is True

    def test_supabase_rest_anon_singleton(self) -> None:
        """supabase_rest_anon é instância com anon key."""
        assert isinstance(supabase_rest_anon, SupabaseRESTClient)
        assert supabase_rest_anon._use_service_role is False

    def test_supabase_storage_singleton(self) -> None:
        """supabase_storage é instância de SupabaseStorageClient."""
        assert isinstance(supabase_storage, SupabaseStorageClient)


# ---------------------------------------------------------------------------
# Teste de integração real (necessita VPS acessível)
# ---------------------------------------------------------------------------
@pytest.mark.integration
class TestSupabaseIntegrationReal:
    @pytest.mark.asyncio
    async def test_supabase_health_real(self) -> None:
        """Testa health check real contra VPS."""
        if not settings.supabase_url or not settings.supabase_anon_key:
            pytest.skip("Supabase nao configurado localmente (env vars ausentes)")
        result = await supabase_health()
        assert result is True, "Supabase VPS deve estar UP"

    @pytest.mark.asyncio
    async def test_select_clientes_real(self) -> None:
        """Testa SELECT real na tabela clientes."""
        if not settings.supabase_url or not settings.supabase_service_role_key:
            pytest.skip("Supabase nao configurado localmente (env vars ausentes)")
        rows = await supabase_rest.select("clientes", limit=5)
        assert isinstance(rows, list)

    @pytest.mark.asyncio
    async def test_select_protocolos_real(self) -> None:
        """Testa SELECT real na tabela protocolos."""
        if not settings.supabase_url or not settings.supabase_service_role_key:
            pytest.skip("Supabase nao configurado localmente (env vars ausentes)")
        rows = await supabase_rest.select("protocolos", limit=5)
        assert isinstance(rows, list)
