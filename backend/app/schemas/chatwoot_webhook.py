"""Pydantic v2 schemas for Chatwoot webhook payloads (G8.03.T1).

LGPD: models do not require or persist raw PII fields; optional sender/contact
blobs are typed loosely and never logged here.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ChatwootConversationRef(BaseModel):
    """Minimal conversation object embedded in Chatwoot webhooks."""

    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    status: str | None = None
    meta: dict[str, Any] | None = None
    assignee: dict[str, Any] | None = None


class ChatwootAssignee(BaseModel):
    """Optional human assignee (HITL)."""

    model_config = ConfigDict(extra="ignore")

    id: int | str | None = None
    name: str | None = None
    email: str | None = None


class ChatwootConversationStatusChanged(BaseModel):
    """Chatwoot `conversation_status_changed` webhook body.

    Fields mirror what process_chatwoot_event/_handle_status_changed read.
    Extra Chatwoot keys are ignored (forward-compatible).
    """

    model_config = ConfigDict(extra="ignore")

    event: Literal["conversation_status_changed"]
    id: int | str | None = None
    status: str | None = None
    conversation: ChatwootConversationRef | None = None
    assignee: ChatwootAssignee | dict[str, Any] | None = None


class ChatwootMessageCreated(BaseModel):
    """Chatwoot `message_created` webhook body (minimal fields).

    message_type may be string ('outgoing'/'incoming') or Chatwoot enum int.
    """

    model_config = ConfigDict(extra="ignore")

    event: Literal["message_created"]
    id: int | str | None = None
    message_id: int | str | None = None
    message_type: str | int | None = None
    content: str | None = None
    conversation: ChatwootConversationRef | None = None
    sender: dict[str, Any] | None = Field(default=None)


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
