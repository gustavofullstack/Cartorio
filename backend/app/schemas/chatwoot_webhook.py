"""Pydantic v2 schemas for Chatwoot webhook payloads (G8.03.T1 + G8.17.T2).

LGPD: models do not require or persist raw PII fields; optional sender/contact
blobs are typed loosely and never logged here.

G8.17.T2: enriched every field with `Field(description=...)` for Swagger
documentation. PII fields are marked with `PIIField` (prefix `**LGPD PII**`)
to support automatic LGPD scanning tools.

Webhooks Chatwoot cobertos:
- `conversation_status_changed` -> status update (resolve/open/pending)
- `message_created` -> nova mensagem na conversa
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.pii_marker import PIIField

_CW_CONFIG = ConfigDict(extra="ignore")


class ChatwootConversationRef(BaseModel):
    """Minimal conversation object embedded in Chatwoot webhooks."""

    model_config = _CW_CONFIG

    id: Annotated[
        int | str | None,
        Field(
            default=None,
            description="ID da conversa no Chatwoot (int ou UUID legacy).",
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(
            default=None,
            description="Status da conversa: 'open', 'resolved', 'pending', 'snoozed'.",
            examples=["open", "resolved"],
        ),
    ] = None
    meta: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Metadata adicional da conversa (sender, channel, custom).",
        ),
    ] = None
    assignee: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Atendente atribuido (HITL - escrevente).",
        ),
    ] = None


class ChatwootAssignee(BaseModel):
    """Optional human assignee (HITL - escrevente do cartorio)."""

    model_config = _CW_CONFIG

    id: Annotated[
        int | str | None,
        Field(
            default=None,
            description="ID do atendente no Chatwoot.",
        ),
    ] = None
    name: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Nome do atendente (LGPD PII).",
            max_length=255,
        ),
    ] = None
    email: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Email do atendente (LGPD PII).",
            max_length=255,
        ),
    ] = None


class ChatwootConversationStatusChanged(BaseModel):
    """Chatwoot `conversation_status_changed` webhook body.

    Fields mirror what process_chatwoot_event/_handle_status_changed read.
    Extra Chatwoot keys are ignored (forward-compatible).
    """

    model_config = _CW_CONFIG

    event: Annotated[
        Literal["conversation_status_changed"],
        Field(
            description="Tipo do evento Chatwoot (discriminator).",
            examples=["conversation_status_changed"],
        ),
    ]
    id: Annotated[
        int | str | None,
        Field(
            default=None,
            description="ID da conversa que mudou de status.",
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(
            default=None,
            description="Novo status da conversa.",
            examples=["resolved", "open"],
        ),
    ] = None
    conversation: Annotated[
        ChatwootConversationRef | None,
        Field(
            default=None,
            description="Snapshot da conversa (com assignee, meta).",
        ),
    ] = None
    assignee: Annotated[
        ChatwootAssignee | dict[str, Any] | None,
        PIIField(
            default=None,
            description="Atendente atribuido (HITL - LGPD PII).",
        ),
    ] = None


class ChatwootMessageCreated(BaseModel):
    """Chatwoot `message_created` webhook body (minimal fields).

    message_type may be string ('outgoing'/'incoming') or Chatwoot enum int.
    """

    model_config = _CW_CONFIG

    event: Annotated[
        Literal["message_created"],
        Field(
            description="Tipo do evento Chatwoot (discriminator).",
            examples=["message_created"],
        ),
    ]
    id: Annotated[
        int | str | None,
        Field(
            default=None,
            description="ID do evento no Chatwoot (idempotency key opcional).",
        ),
    ] = None
    message_id: Annotated[
        int | str | None,
        Field(
            default=None,
            description="ID da mensagem criada.",
        ),
    ] = None
    message_type: Annotated[
        str | int | None,
        Field(
            default=None,
            description="Tipo da mensagem: 'incoming' (cliente) ou 'outgoing' (agente).",
            examples=["incoming", "outgoing"],
        ),
    ] = None
    content: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Conteudo da mensagem (LGPD PII).",
            max_length=10000,
        ),
    ] = None
    conversation: Annotated[
        ChatwootConversationRef | None,
        Field(
            default=None,
            description="Conversa onde a mensagem foi criada.",
        ),
    ] = None
    sender: Annotated[
        dict[str, Any] | None,
        PIIField(
            default=None,
            description="Dict com dados do remetente (LGPD PII: name, email, phone).",
        ),
    ] = None


ChatwootWebhookModel = Union[ChatwootConversationStatusChanged, ChatwootMessageCreated]


def parse_chatwoot_payload(payload: dict[str, Any] | Any) -> ChatwootWebhookModel | None:
    """Validate a Chatwoot webhook dict into a typed model.

    Returns:
        Typed model for known handled events, or None if the payload is empty,
        not a mapping, has an unhandled event type, or fails shape validation.
    """
    if not isinstance(payload, dict) or not payload:
        return None

    event = payload.get("event")
    try:
        if event == "conversation_status_changed":
            return ChatwootConversationStatusChanged.model_validate(payload)
        if event == "message_created":
            return ChatwootMessageCreated.model_validate(payload)
    except ValidationError:
        return None
    return None


__all__ = [
    "ChatwootAssignee",
    "ChatwootConversationRef",
    "ChatwootConversationStatusChanged",
    "ChatwootMessageCreated",
    "ChatwootWebhookModel",
    "parse_chatwoot_payload",
]
