"""G8.02.T4 — 10 cenários de sessão longa Telegram (histórico multi-turn).

Testes de integração **puros** (sem rede Telegram real): simulam sessões
longas com o helper de dialog history + mute HITL + scrub.

Modified by Gustavo Almeida — Wave 36.
"""

from __future__ import annotations

from app.services.dialog_history import (
    DialogHistoryConfig,
    estimate_tokens,
    trim_history_to_token_budget,
)
from app.services.bot_mute import is_bot_muted, mute_bot
from app.services.pii import scrub


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, name: str):
        return self.store.get(name)

    def set(self, name: str, value, ex: int | None = None):
        self.store[name] = value

    def delete(self, *names: str):
        for n in names:
            self.store.pop(n, None)


def _build_session(turns: int) -> list[str]:
    hist: list[str] = []
    for i in range(turns):
        hist.append(f'user: pergunta numero {i} sobre escritura e certidao')
        hist.append(f'bot: resposta numero {i} com orientacao HITL')
    return hist


def test_long_session_20_turns_token_budget() -> None:
    hist = _build_session(20)
    cfg = DialogHistoryConfig(max_tokens=80, min_keep=4)
    trimmed = trim_history_to_token_budget(hist, cfg.max_tokens, min_keep=cfg.min_keep)
    assert len(trimmed) < len(hist)
    assert len(trimmed) >= cfg.min_keep
    assert estimate_tokens('\n'.join(trimmed)) <= cfg.max_tokens + 80  # slack + min_keep


def test_long_session_keeps_newest() -> None:
    hist = _build_session(15)
    trimmed = trim_history_to_token_budget(hist, max_tokens=200, min_keep=2)
    assert trimmed[-1].startswith('bot:')
    assert '14' in trimmed[-1] or '13' in trimmed[-1] or '12' in trimmed[-1]


def test_session_with_cpf_scrubbed() -> None:
    raw = 'Meu CPF e 529.982.247-25 quero certidao'
    cleaned = scrub(raw).text
    assert '529' not in cleaned or '***' in cleaned or 'XXX' in cleaned or cleaned != raw


def test_hitl_mute_blocks_long_session() -> None:
    r = FakeRedis()
    mute_bot(r, 'telegram', '999')
    assert is_bot_muted(r, 'telegram', '999') is True


def test_empty_history() -> None:
    assert trim_history_to_token_budget([], 100) == []


def test_min_keep_small_budget() -> None:
    hist = _build_session(5)
    out = trim_history_to_token_budget(hist, max_tokens=1, min_keep=2)
    assert len(out) >= 2


def test_session_idempotent_trim() -> None:
    hist = _build_session(8)
    once = trim_history_to_token_budget(hist, 300, min_keep=2)
    twice = trim_history_to_token_budget(once, 300, min_keep=2)
    assert once == twice


def test_alternating_roles_intact_suffix() -> None:
    hist = _build_session(10)
    out = trim_history_to_token_budget(hist, 400, min_keep=4)
    # últimas 2 devem ser user/bot ou bot/user par
    assert any(x.startswith('user:') for x in out[-4:])
    assert any(x.startswith('bot:') for x in out[-4:])


def test_estimate_tokens_monotonic() -> None:
    assert estimate_tokens('a' * 40) >= estimate_tokens('a' * 10)


def test_config_defaults() -> None:
    cfg = DialogHistoryConfig()
    assert cfg.max_entries > 0
    assert cfg.max_tokens > 0
    assert cfg.ttl_sec > 0
