"""Cliente Supabase para integração direta com PostgREST, Auth, Storage e Realtime.

O Supabase auto-hospedado expõe:
  - /rest/v1/*      → PostgREST (CRUD em todas as tabelas)
  - /auth/v1/*      → Auth (JWT, magic links, OAuth)
  - /storage/v1/*   → Storage (arquivos, PDFs, documentos)
  - /realtime/v1/*  → Realtime WebSocket (5 canais)
  - /functions/v1/* → Edge Functions (Deno runtime)

Este módulo encapsula o acesso via httpx async, com:
  - Autenticação via service_role_key (bypass RLS) ou anon_key (RLS ativo)
  - Retry automático (3x exponential backoff)
  - Timeout configurável
  - Health check endpoint
  - Tipagem Pydantic para responses

Uso:
    from app.integrations.supabase_client import supabase_rest, supabase_health

    # CRUD via PostgREST
    rows = await supabase_rest.select("clientes", filters={"cpf_hash": "eq.abc123"})

    # Health check
    ok = await supabase_health()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração de timeout e retry
# ---------------------------------------------------------------------------
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 0.5  # segundos


async def _with_retry(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Executa fn com retry exponential backoff até _MAX_RETRIES tentativas."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await fn(*args, **kwargs)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            wait = _RETRY_BACKOFF_BASE * (2**attempt)
            logger.warning(
                "supabase_client retry %d/%d após %.1fs — %s",
                attempt + 1,
                _MAX_RETRIES,
                wait,
                exc,
            )
            await asyncio.sleep(wait)
    raise RuntimeError(f"Supabase client falhou após {_MAX_RETRIES} tentativas: {last_exc}")


# ---------------------------------------------------------------------------
# Headers padrão
# ---------------------------------------------------------------------------
def _headers(use_service_role: bool = True) -> dict[str, str]:
    """Retorna headers com Authorization e apikey corretos."""
    key = (
        settings.supabase_service_role_key
        if use_service_role
        else settings.supabase_anon_key
    ) or ""
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
async def supabase_health() -> bool:
    """Verifica se o Supabase está respondendo corretamente.

    Returns:
        True se saudável, False caso contrário.
    """
    url = f"{settings.supabase_url}/auth/v1/health"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers())
            return resp.status_code in (200, 401)  # 401 = requer auth = está UP
    except Exception as exc:
        logger.error("supabase_health falhou: %s", exc)
        return False


# ---------------------------------------------------------------------------
# PostgREST REST Client
# ---------------------------------------------------------------------------
class SupabaseRESTClient:
    """Cliente para PostgREST (CRUD em tabelas via REST API).

    Acessa `{supabase_url}/rest/v1/{table}`.
    Por padrão usa service_role_key (bypass RLS).
    Para operações com RLS ativo, use use_service_role=False.
    """

    def __init__(self, use_service_role: bool = True) -> None:
        self._base = f"{settings.supabase_url}/rest/v1"
        self._use_service_role = use_service_role

    def _hdrs(self) -> dict[str, str]:
        return _headers(self._use_service_role)

    async def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: Optional[dict[str, str]] = None,
        order: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """SELECT em uma tabela via PostgREST.

        Args:
            table: nome da tabela (ex: "clientes")
            columns: colunas a retornar (ex: "id,nome,cpf_hash")
            filters: dict de filtros PostgREST (ex: {"status": "eq.ativo"})
            order: ordenação (ex: "created_at.desc")
            limit: max registros
            offset: offset para paginação

        Returns:
            Lista de dicts com os registros.
        """
        url = f"{self._base}/{table}"
        params: dict[str, Any] = {"select": columns, "limit": limit, "offset": offset}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order

        hdrs = self._hdrs()
        hdrs["Prefer"] = "count=exact"

        async def _do() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=hdrs)
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]

        return await _with_retry(_do)  # type: ignore[return-value]

    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """INSERT em uma tabela via PostgREST.

        Args:
            table: nome da tabela
            data: dict único ou lista de dicts para inserir

        Returns:
            Lista de registros inseridos (com id gerado).
        """
        url = f"{self._base}/{table}"

        async def _do() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=data, headers=self._hdrs())
                resp.raise_for_status()
                result = resp.json()
                return result if isinstance(result, list) else [result]

        return await _with_retry(_do)  # type: ignore[return-value]

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        """UPDATE em uma tabela via PostgREST.

        Args:
            table: nome da tabela
            data: campos a atualizar
            filters: filtros para WHERE clause (ex: {"id": "eq.123"})

        Returns:
            Lista de registros atualizados.
        """
        url = f"{self._base}/{table}"

        async def _do() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.patch(url, json=data, params=filters, headers=self._hdrs())
                resp.raise_for_status()
                result = resp.json()
                return result if isinstance(result, list) else [result]

        return await _with_retry(_do)  # type: ignore[return-value]

    async def delete(
        self,
        table: str,
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        """DELETE em uma tabela via PostgREST.

        Args:
            table: nome da tabela
            filters: filtros para WHERE clause (ex: {"id": "eq.123"})

        Returns:
            Lista de registros deletados.
        """
        url = f"{self._base}/{table}"

        async def _do() -> list[dict[str, Any]]:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.delete(url, params=filters, headers=self._hdrs())
                resp.raise_for_status()
                result = resp.json()
                return result if isinstance(result, list) else [result]

        return await _with_retry(_do)  # type: ignore[return-value]

    async def rpc(
        self,
        function_name: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Chamar uma função PostgreSQL (RPC) via PostgREST.

        Args:
            function_name: nome da função (ex: "get_emolumento_valor")
            params: parâmetros da função

        Returns:
            Resultado da função.
        """
        url = f"{self._base}/rpc/{function_name}"

        async def _do() -> Any:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=params or {}, headers=self._hdrs())
                resp.raise_for_status()
                return resp.json()

        return await _with_retry(_do)


# ---------------------------------------------------------------------------
# Supabase Storage Client
# ---------------------------------------------------------------------------
class SupabaseStorageClient:
    """Cliente para Supabase Storage (upload/download de arquivos).

    Acessa `{supabase_url}/storage/v1/object/{bucket}/{path}`.
    """

    def __init__(self) -> None:
        self._base = f"{settings.supabase_url}/storage/v1"

    def _hdrs(self) -> dict[str, str]:
        return _headers(use_service_role=True)

    async def upload(
        self,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Upload de arquivo para o Supabase Storage.

        Args:
            bucket: nome do bucket (ex: "documentos")
            path: caminho no bucket (ex: "protocolos/2026/001.pdf")
            content: bytes do arquivo
            content_type: MIME type

        Returns:
            Dict com key do objeto criado.
        """
        url = f"{self._base}/object/{bucket}/{path}"
        hdrs = self._hdrs()
        hdrs["Content-Type"] = content_type

        async def _do() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, content=content, headers=hdrs)
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]

        return await _with_retry(_do)  # type: ignore[return-value]

    async def download(self, bucket: str, path: str) -> bytes:
        """Download de arquivo do Supabase Storage.

        Args:
            bucket: nome do bucket
            path: caminho no bucket

        Returns:
            Bytes do arquivo.
        """
        url = f"{self._base}/object/{bucket}/{path}"

        async def _do() -> bytes:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, headers=self._hdrs())
                resp.raise_for_status()
                return resp.content

        return await _with_retry(_do)  # type: ignore[return-value]

    def public_url(self, bucket: str, path: str) -> str:
        """Gera URL pública para um arquivo (bucket deve ser público).

        Args:
            bucket: nome do bucket público
            path: caminho no bucket

        Returns:
            URL pública do arquivo.
        """
        return f"{self._base}/object/public/{bucket}/{path}"


# ---------------------------------------------------------------------------
# Instâncias singleton para uso no aplicativo
# ---------------------------------------------------------------------------
supabase_rest = SupabaseRESTClient(use_service_role=True)
"""Cliente PostgREST com service_role (bypass RLS). Use para operações internas."""

supabase_rest_anon = SupabaseRESTClient(use_service_role=False)
"""Cliente PostgREST com anon key (RLS ativo). Use para operações de usuário final."""

supabase_storage = SupabaseStorageClient()
"""Cliente Storage para upload/download de documentos e PDFs."""
