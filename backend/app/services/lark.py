"""Servicos de integracao com Lark (Feishu/Larksuite).

Funcoes auxiliares para autenticacao e envio de mensagens via Message API.
Todas as chamadas usam httpx e respeitam o padrao de PII scrubbing do
projeto (o caller deve scrubbar conteudo antes de chamar).

Documentacao:
- Auth: https://open.larksuite.com/document/server-docs/api-token-management/tenant_access_token_internal
- Messages: https://open.larksuite.com/document/server-docs/im-v1/message/create
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

LARK_API_BASE = os.environ.get("LARK_API_BASE", "https://open.larksuite.com")
TENANT_TOKEN_URL = f"{LARK_API_BASE.rstrip('/')}/open-apis/auth/v3/tenant_access_token/internal"
SEND_MESSAGE_URL = f"{LARK_API_BASE.rstrip('/')}/open-apis/im/v1/messages"


def _get_credentials() -> tuple[str, str]:
    """Retorna (app_id, app_secret) a partir de settings/env.

    Preferencia explicita por settings; fallback para env vars para
    retrocompatibilidade com deploys que ainda injetam via environment.
    """
    app_id = getattr(settings, "lark_app_id", None) or os.environ.get("LARK_APP_ID", "")
    app_secret = getattr(settings, "lark_app_secret", None) or os.environ.get("LARK_APP_SECRET", "")
    return app_id, app_secret


def _auth_headers(tenant_access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8",
    }


async def get_tenant_access_token(
    app_id: str | None = None,
    app_secret: str | None = None,
    timeout_seconds: float = 10.0,
) -> str:
    """Obtem tenant_access_token via App ID + App Secret.

    Raises:
        RuntimeError: se as credenciais estiverem ausentes ou a API retornar erro.
    """
    cid, secret = app_id, app_secret
    if not cid or not secret:
        cid, secret = _get_credentials()
    if not cid or not secret:
        raise RuntimeError("LARK_APP_ID e LARK_APP_SECRET sao obrigatorios")

    payload = {"app_id": cid, "app_secret": secret}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(TENANT_TOKEN_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Lark auth error: {data.get('code')} - {data.get('msg')}")
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError("Lark auth response missing tenant_access_token")
    return str(token)


async def send_text_message(
    receive_id: str,
    text: str,
    receive_id_type: str = "open_id",
    tenant_access_token: str | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Envia mensagem de texto simples para um usuario/chat do Lark.

    Args:
        receive_id: ID do destinatario (open_id / user_id / chat_id).
        text: Conteudo textual (ja scrubbado pelo caller).
        receive_id_type: Tipo do ID (open_id, user_id, chat_id, union_id).
        tenant_access_token: Token opcional (se omitido, obtem novo).
        timeout_seconds: Timeout da requisicao.
    """
    token = tenant_access_token or await get_tenant_access_token()
    content = json.dumps({"text": text}, ensure_ascii=False)
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": content,
    }
    params = {"receive_id_type": receive_id_type}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(
            SEND_MESSAGE_URL,
            params=params,
            json=payload,
            headers=_auth_headers(token),
        )
    resp.raise_for_status()
    return resp.json()


async def send_rich_text_message(
    receive_id: str,
    title: str,
    content: list[list[dict[str, Any]]],
    receive_id_type: str = "open_id",
    tenant_access_token: str | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Envia mensagem rich text (post) para o Lark.

    Args:
        receive_id: ID do destinatario.
        title: Titulo do post.
        content: Matriz de linhas/elementos no formato Lark post.
        receive_id_type: Tipo do receive_id.
        tenant_access_token: Token opcional.
        timeout_seconds: Timeout da requisicao.
    """
    token = tenant_access_token or await get_tenant_access_token()
    post_content = json.dumps(
        {
            "zh_cn": {
                "title": title,
                "content": content,
            }
        },
        ensure_ascii=False,
    )
    payload = {
        "receive_id": receive_id,
        "msg_type": "post",
        "content": post_content,
    }
    params = {"receive_id_type": receive_id_type}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(
            SEND_MESSAGE_URL,
            params=params,
            json=payload,
            headers=_auth_headers(token),
        )
    resp.raise_for_status()
    return resp.json()


async def send_image_message(
    receive_id: str,
    image_bytes: bytes,
    image_type: str = "message",
    receive_id_type: str = "open_id",
    tenant_access_token: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Envia imagem para o Lark (upload + message).

    Args:
        receive_id: ID do destinatario.
        image_bytes: Bytes brutos da imagem.
        image_type: Tipo de imagem (message ou avatar).
        receive_id_type: Tipo do receive_id.
        tenant_access_token: Token opcional.
        timeout_seconds: Timeout da requisicao.

    Returns:
        Resposta da API de mensagens ou dict com erro se upload falhar.
    """
    token = tenant_access_token or await get_tenant_access_token()
    image_key = await _upload_image(image_bytes, image_type=image_type, token=token)
    if not image_key:
        logger.warning("Lark image upload failed for receive_id=%s", receive_id)
        return {"code": -1, "msg": "image upload failed"}

    content = json.dumps({"image_key": image_key}, ensure_ascii=False)
    payload = {
        "receive_id": receive_id,
        "msg_type": "image",
        "content": content,
    }
    params = {"receive_id_type": receive_id_type}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(
            SEND_MESSAGE_URL,
            params=params,
            json=payload,
            headers=_auth_headers(token),
        )
    resp.raise_for_status()
    return resp.json()


async def send_file_message(
    receive_id: str,
    file_bytes: bytes,
    file_name: str,
    file_type: str = "stream",
    receive_id_type: str = "open_id",
    tenant_access_token: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    """Envia arquivo para o Lark (upload + message).

    Args:
        receive_id: ID do destinatario.
        file_bytes: Bytes brutos do arquivo.
        file_name: Nome do arquivo.
        file_type: Tipo de arquivo (stream, doc, sheet, slide).
        receive_id_type: Tipo do receive_id.
        tenant_access_token: Token opcional.
        timeout_seconds: Timeout da requisicao.
    """
    token = tenant_access_token or await get_tenant_access_token()
    file_key = await _upload_file(file_bytes, file_name=file_name, file_type=file_type, token=token)
    if not file_key:
        logger.warning("Lark file upload failed for receive_id=%s", receive_id)
        return {"code": -1, "msg": "file upload failed"}

    content = json.dumps({"file_key": file_key}, ensure_ascii=False)
    payload = {
        "receive_id": receive_id,
        "msg_type": "file",
        "content": content,
    }
    params = {"receive_id_type": receive_id_type}
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(
            SEND_MESSAGE_URL,
            params=params,
            json=payload,
            headers=_auth_headers(token),
        )
    resp.raise_for_status()
    return resp.json()


async def _upload_image(
    image_bytes: bytes,
    *,
    image_type: str = "message",
    token: str,
    timeout_seconds: float = 30.0,
) -> str | None:
    """Faz upload de imagem para o Lark e retorna image_key."""
    url = f"{LARK_API_BASE.rstrip('/')}/open-apis/im/v1/images"
    b64_data = base64.b64encode(image_bytes).decode("utf-8")
    data = {
        "image_type": image_type,
        "image": b64_data,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(url, json=data, headers=_auth_headers(token))
    if resp.status_code >= 400:
        logger.warning("Lark image upload HTTP %s: %s", resp.status_code, resp.text[:200])
        return None
    body = resp.json()
    if body.get("code") != 0:
        logger.warning("Lark image upload error %s: %s", body.get("code"), body.get("msg"))
        return None
    return body.get("data", {}).get("image_key")


async def _upload_file(
    file_bytes: bytes,
    *,
    file_name: str,
    file_type: str = "stream",
    token: str,
    timeout_seconds: float = 30.0,
) -> str | None:
    """Faz upload de arquivo para o Lark e retorna file_key."""
    url = f"{LARK_API_BASE.rstrip('/')}/open-apis/im/v1/files"
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    data = {
        "file_type": file_type,
        "file_name": file_name,
        "file": b64_data,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0)) as client:
        resp = await client.post(url, json=data, headers=_auth_headers(token))
    if resp.status_code >= 400:
        logger.warning("Lark file upload HTTP %s: %s", resp.status_code, resp.text[:200])
        return None
    body = resp.json()
    if body.get("code") != 0:
        logger.warning("Lark file upload error %s: %s", body.get("code"), body.get("msg"))
        return None
    return body.get("data", {}).get("file_key")


__all__ = [
    "get_tenant_access_token",
    "send_text_message",
    "send_rich_text_message",
    "send_image_message",
    "send_file_message",
]
