"""Integracao com Jules API (Google Gemini 3.1 Pro via async sessions).

Jules eh o agente de coding do Google, expoe API REST propria em
`https://jules.googleapis.com/v1alpha`. NAO eh compativel com OpenAI Chat
Completions direto — usa sessions assincronas com polling.

Workflow:
1. POST /v1alpha/sessions {prompt: "<mensagem do user>"} → retorna session.id
2. GET /v1alpha/sessions/{id}/activities (poll a cada 2s ate timeout)
3. Procura activity com `agentMessaged.agentMessage` — esse eh o texto de
   resposta do Jules
4. Fallback se polling exceder timeout: retorna ChatError HTTP_TIMEOUT

Adicionado como fallback terciario em `chat_with_fallback` (opencode_go →
openclaw → jules), util quando primary e secondary estao ambos down e
quer validar uma LLM baseline antes de failed-LLM handoff.

LGPD: Scrubbing INTERNO via _scrub_messages() (defense-in-depth).
Mesmo padrao de consent/rate limit dos outros providers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING

import httpx

from app.integrations.opencode_go import ChatError, ChatErrorKind, ChatResponse
from app.services.pii import scrub

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


JULES_API_BASE = "https://jules.googleapis.com/v1alpha"
DEFAULT_POLL_TIMEOUT_SEC = 25.0
DEFAULT_POLL_INTERVAL_SEC = 2.0


def _scrub_messages(messages: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Reuso da logica de scrubbing (defense-in-depth LGPD art. 46)."""
    scrubbed: list[dict[str, str]] = []
    total_redacted = 0
    for msg in messages:
        content = msg.get("content", "") or ""
        result = scrub(content)
        scrubbed.append(
            {
                "role": msg.get("role", "user"),
                "content": result.text,
            }
        )
        total_redacted += result.redaction_count
    return scrubbed, total_redacted


def _flatten_messages_to_prompt(messages: list[dict[str, str]]) -> str:
    """Combina system + user messages em 1 prompt pra Jules.

    Jules API session.prompt eh string unica. Concatenamos mantendo
    marcadores de role pra preservar contexto minimo.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "") or ""
        if role == "SYSTEM":
            parts.append(f"[SYSTEM]\n{content}")
        elif role == "ASSISTANT":
            parts.append(f"[ASSISTANT]\n{content}")
        else:
            parts.append(f"[USER]\n{content}")
    return "\n\n".join(parts)


async def chat_with_settings(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    consent_granted: bool = False,
    actor_id: str = "anonymous",
    db: "Session | None" = None,
    session_id: str | None = None,
    rate_limit_per_minute: int | None = None,
    request_id: str | None = None,
    client_ip: str | None = None,
    jules_api_key: str | None = None,
    poll_timeout_sec: float = DEFAULT_POLL_TIMEOUT_SEC,
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
) -> ChatResponse:
    """Cria session Jules e faz polling pela resposta do agent.

    Args:
        messages: lista de mensagens OpenAI-format (system/user/assistant).
        temperature: ignorado (Jules nao expoe).
        consent_granted: LGPD art. 7 I — se False, levanta ChatError LGPD_BLOCKED.
        actor_id: id do ator pra audit log.
        db: SQLAlchemy session pra audit log OPCIONAL (sync).
        session_id: identificador da sessao (informativo).
        rate_limit_per_minute: NAO implementado ainda (Jules tem quota propria).
        request_id: request_id pra audit log (LGPD-015).
        client_ip: client_ip pra audit log (LGPD-015).
        jules_api_key: injetada por param OU lida de env (JULES_API_KEY).
        poll_timeout_sec: max espera pelo agent responder (default 25s).
        poll_interval_sec: intervalo entre polls (default 2s).

    Returns:
        ChatResponse com content = agentMessage do Jules, model = "jules".

    Raises:
        ChatError: LGPD_BLOCKED, CONFIG, HTTP_4XX, HTTP_5XX, TIMEOUT, PARSE.
    """
    if not consent_granted:
        raise ChatError(
            "Consentimento LGPD nao concedido (art. 7 I).",
            kind=ChatErrorKind.LGPD_BLOCKED,
        )

    api_key = jules_api_key or os.getenv("JULES_API_KEY")
    if not api_key:
        raise ChatError(
            "JULES_API_KEY ausente. Defina no .env ou passe via param.",
            kind=ChatErrorKind.CONFIG,
        )

    # 1) Scrub messages (defense-in-depth)
    scrubbed_messages, pii_count = _scrub_messages(messages)
    prompt = _flatten_messages_to_prompt(scrubbed_messages)

    t0 = time.time()
    headers = {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 2) POST session
        try:
            resp = await client.post(
                f"{JULES_API_BASE}/sessions",
                headers=headers,
                json={"prompt": prompt},
            )
        except httpx.HTTPError as exc:
            raise ChatError(
                f"Jules HTTP error na criacao de session: {exc}",
                kind=ChatErrorKind.NETWORK,
            ) from exc

        if resp.status_code >= 400:
            raise ChatError(
                f"Jules session POST retorno {resp.status_code}: {resp.text[:200]}",
                kind=(
                    ChatErrorKind.HTTP_4XX
                    if resp.status_code < 500
                    else ChatErrorKind.HTTP_5XX
                ),
                status_code=resp.status_code,
                body=resp.text[:500],
            )

        session_data = resp.json()
        session_id_jules = session_data.get("id") or session_data.get("name", "").split("/")[-1]
        if not session_id_jules:
            raise ChatError(
                f"Jules session criada sem id: {session_data}",
                kind=ChatErrorKind.PARSE,
            )

        logger.info(
            "jules.session.created sid=%s actor=%s",
            session_id_jules,
            actor_id,
        )

        # 3) Polling activities ate agentMessaged ou timeout
        deadline = time.time() + poll_timeout_sec
        agent_message: str | None = None
        last_activity_count = 0

        while time.time() < deadline:
            await asyncio.sleep(poll_interval_sec)
            try:
                aresp = await client.get(
                    f"{JULES_API_BASE}/sessions/{session_id_jules}/activities",
                    headers=headers,
                    params={"pageSize": 30},
                )
            except httpx.HTTPError:
                # Network blip — continua tentando ate deadline
                continue

            if aresp.status_code >= 400:
                # Erro de GET — se 4xx, abort; se 5xx, continua
                if aresp.status_code < 500:
                    raise ChatError(
                        f"Jules activities GET {aresp.status_code}: {aresp.text[:200]}",
                        kind=ChatErrorKind.HTTP_4XX,
                        status_code=aresp.status_code,
                    )
                continue

            try:
                data = aresp.json()
            except Exception:
                continue

            activities = data.get("activities", [])
            for activity in activities:
                if activity.get("originator") == "agent":
                    msg_data = activity.get("agentMessaged", {})
                    if msg_data:
                        agent_message = msg_data.get("agentMessage", "")
                        break

            if agent_message:
                break
            last_activity_count = len(activities)

        if not agent_message:
            raise ChatError(
                f"Jules timeout apos {poll_timeout_sec}s (activities={last_activity_count}). "
                f"SID={session_id_jules}",
                kind=ChatErrorKind.TIMEOUT,
            )

    latency_ms = int((time.time() - t0) * 1000)

    # 4) Sanitiza output (PII defense-in-depth boundary 2, LGPD-015)
    output_scrub = scrub(agent_message)
    final_content = output_scrub.text
    output_pii = output_scrub.redaction_count

    # 5) Audit log LGPD-015 (request_id + ip)
    if db is not None:
        try:
            from app.services.audit import AuditService

            AuditService.log(
                db,
                actor_id=actor_id,
                actor_type="bot",
                action="llm.jules_called",
                resource=f"llm:jules:{session_id_jules}",
                payload={
                    "model": "jules",
                    "session_id_jules": session_id_jules,
                    "prompt_chars": len(prompt),
                    "input_pii_redacted": pii_count,
                    "output_pii_redacted": output_pii,
                    "latency_ms": latency_ms,
                },
                request_id=request_id,
                ip=client_ip,
                canal="api",
            )
            if output_pii > 0:
                AuditService.log(
                    db,
                    actor_id=actor_id,
                    actor_type="bot",
                    action="llm.output_scrubbed",
                    resource=f"llm:jules:{session_id_jules}",
                    payload={
                        "redaction_count": output_pii,
                        "provider": "jules",
                    },
                    request_id=request_id,
                    ip=client_ip,
                    canal="api",
                )
        except Exception as exc:
            logger.warning("jules.audit_log_failed: %s", exc)

    return ChatResponse(
        content=final_content,
        model="jules",
        tokens_in=None,  # Jules nao expoe usage tokens
        tokens_out=None,
        latency_ms=latency_ms,
        finish_reason="stop",
        pii_redacted_count=pii_count,
        output_pii_redacted_count=output_pii,
    )
