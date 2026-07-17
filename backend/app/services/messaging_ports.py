"""G8.11.T2 — Injeção de dependências explícita para email e mensageria.

Ports (Protocol) + adapters default no-op / logging.
Controllers/services dependem da porta, não de SMTP/SDK concreto.

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    channel: str
    recipient_id: str
    text: str


@runtime_checkable
class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> bool: ...


@runtime_checkable
class MessageSender(Protocol):
    def send(self, message: ChatMessage) -> bool: ...


class LoggingEmailSender:
    """Adapter default: só loga (dev/test)."""

    def send(self, message: EmailMessage) -> bool:
        logger.info('email.send to=%s subject=%s', message.to[:3] + '***', message.subject[:40])
        return True


class LoggingMessageSender:
    def send(self, message: ChatMessage) -> bool:
        logger.info(
            'msg.send channel=%s recipient_hash=%s len=%d',
            message.channel,
            hash(message.recipient_id) % 10_000,
            len(message.text),
        )
        return True


class RecordingEmailSender:
    """Test double: grava mensagens."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> bool:
        self.sent.append(message)
        return True


class RecordingMessageSender:
    def __init__(self) -> None:
        self.sent: list[ChatMessage] = []

    def send(self, message: ChatMessage) -> bool:
        self.sent.append(message)
        return True


@dataclass
class NotificationService:
    """Application service com DI explícita (construtor)."""

    email: EmailSender = field(default_factory=LoggingEmailSender)
    messaging: MessageSender = field(default_factory=LoggingMessageSender)

    def notify_email(self, to: str, subject: str, body: str) -> bool:
        return self.email.send(EmailMessage(to=to, subject=subject, body=body))

    def notify_chat(self, channel: str, recipient_id: str, text: str) -> bool:
        return self.messaging.send(
            ChatMessage(channel=channel, recipient_id=recipient_id, text=text)
        )


def build_default_notification_service() -> NotificationService:
    return NotificationService()


__all__ = [
    'ChatMessage',
    'EmailMessage',
    'EmailSender',
    'LoggingEmailSender',
    'LoggingMessageSender',
    'MessageSender',
    'NotificationService',
    'RecordingEmailSender',
    'RecordingMessageSender',
    'build_default_notification_service',
]
