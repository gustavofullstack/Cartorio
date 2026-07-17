"""G8.03.T2 — Testes mute HITL do bot (Redis key).

Modified by Gustavo Almeida — Wave 36.
"""

from __future__ import annotations

import pytest

from app.services.bot_mute import (
    BotMuteConfig,
    is_bot_muted,
    mute_bot,
    mute_key,
    parse_mute_value,
    unmute_bot,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, name: str):
        return self.store.get(name)

    def set(self, name: str, value, ex: int | None = None):
        self.store[name] = value
        if ex is not None:
            self.ttls[name] = int(ex)

    def delete(self, *names: str):
        for n in names:
            self.store.pop(n, None)
            self.ttls.pop(n, None)


def test_mute_key_normalized() -> None:
    assert mute_key('Telegram', '123') == 'bot:mute:telegram:123'


def test_mute_key_requires_conversation() -> None:
    with pytest.raises(ValueError):
        mute_key('telegram', '')


def test_mute_and_check() -> None:
    r = FakeRedis()
    key = mute_bot(r, 'telegram', '42', reason='escrevente', ttl_sec=60)
    assert key == 'bot:mute:telegram:42'
    assert is_bot_muted(r, 'telegram', '42') is True
    assert r.ttls[key] == 60


def test_unmute() -> None:
    r = FakeRedis()
    mute_bot(r, 'whatsapp', '99')
    assert is_bot_muted(r, 'whatsapp', '99') is True
    assert unmute_bot(r, 'whatsapp', '99') is True
    assert is_bot_muted(r, 'whatsapp', '99') is False


def test_not_muted_by_default() -> None:
    r = FakeRedis()
    assert is_bot_muted(r, 'telegram', '1') is False


def test_fail_open_on_redis_error() -> None:
    class Boom:
        def get(self, name: str):
            raise RuntimeError('down')

    assert is_bot_muted(Boom(), 'telegram', '1') is False


def test_parse_mute_value() -> None:
    assert parse_mute_value(None) == (False, '')
    assert parse_mute_value(b'1|hitl') == (True, 'hitl')
    assert parse_mute_value('0') == (False, '')


def test_config_prefix() -> None:
    r = FakeRedis()
    cfg = BotMuteConfig(ttl_sec=10, key_prefix='x:mute')
    mute_bot(r, 'tg', '7', config=cfg)
    assert 'x:mute:tg:7' in r.store
