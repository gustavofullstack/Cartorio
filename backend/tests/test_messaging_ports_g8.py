"""G8.11.T2 — DI messaging ports tests.

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

from app.services.messaging_ports import (
    NotificationService,
    RecordingEmailSender,
    RecordingMessageSender,
    build_default_notification_service,
)


def test_inject_recording_email() -> None:
    rec = RecordingEmailSender()
    svc = NotificationService(email=rec)
    assert svc.notify_email('a@b.com', 'Hi', 'Body') is True
    assert len(rec.sent) == 1
    assert rec.sent[0].to == 'a@b.com'


def test_inject_recording_chat() -> None:
    rec = RecordingMessageSender()
    svc = NotificationService(messaging=rec)
    assert svc.notify_chat('telegram', '123', 'ola') is True
    assert rec.sent[0].channel == 'telegram'


def test_default_builder() -> None:
    svc = build_default_notification_service()
    assert svc.notify_email('x@y.z', 's', 'b') is True


def test_both_injected() -> None:
    e, m = RecordingEmailSender(), RecordingMessageSender()
    svc = NotificationService(email=e, messaging=m)
    svc.notify_email('t@t.t', 's', 'b')
    svc.notify_chat('whatsapp', '9', 'x')
    assert len(e.sent) == 1 and len(m.sent) == 1
