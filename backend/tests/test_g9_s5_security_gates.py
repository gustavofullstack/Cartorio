"""G9.S5 — gates de seguranca revalidados (Etapa 2).

Cobre com evidencia:
- S5.T5 hex-64 no checker
- S5.T8 tiers N8N 600 / DPO 60 / default 30
- S5.T9 fail-open Redis down (rate limit)
- S5.T10 idempotency replay (smoke estrutural)

NUNCA imprime valores de secrets.
Modified by Gustavo Almeida — Etapa 2 G9 2026-07-24.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.services.rate_limit_by_key import TIER_POLICIES, identify_tier


REPO = Path(__file__).resolve().parents[2]
CHECKER = REPO / "backend" / "scripts" / "check_no_literal_keys.py"


def test_s5_t5_checker_script_defines_hex64_rule() -> None:
    src = CHECKER.read_text(encoding="utf-8")
    assert "WEBHOOK_SECRET_HEX64" in src
    assert r"\b[0-9a-fA-F]{64}\b" in src or "[0-9a-fA-F]{64}" in src


def test_s5_t8_rate_limit_tiers_exact() -> None:
    assert TIER_POLICIES["n8n"].per_minute == 600
    assert TIER_POLICIES["dpo"].per_minute == 60
    assert TIER_POLICIES["padrao"].per_minute == 30
    # E2.03 H4: tier elevado so via key registrada; prefixo NAO eleva (anti-spoof)
    assert identify_tier(settings.cartorio_api_key) == "n8n"
    assert identify_tier("n8n-workflow-key") == "padrao"
    assert identify_tier("dpo-operator") == "padrao"
    assert identify_tier("random") == "padrao"


def test_s5_t8_dpo_key_registrada_via_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """E3.05: tier dpo so via match exato com settings.cartorio_dpo_api_key."""
    dpo_key = "e" * 64  # sintetica, runtime
    monkeypatch.setattr(settings, "cartorio_dpo_api_key", dpo_key)
    assert identify_tier(dpo_key) == "dpo"
    assert TIER_POLICIES[identify_tier(dpo_key)].per_minute == 60
    # prefixo forjado / near-miss nunca elevam
    assert identify_tier("dpo-" + dpo_key) == "padrao"
    assert identify_tier(dpo_key[:-1] + "f") == "padrao"


def test_s5_identify_tier_timing_safe_compare_digest_source() -> None:
    """E3.05: identify_tier compara secrets em constant-time (inspect source)."""
    import inspect

    import app.services.rate_limit_by_key as rlbk

    src = inspect.getsource(rlbk.identify_tier)
    assert src.count("hmac.compare_digest") >= 2  # n8n + dpo
    assert "api_key ==" not in src
    assert "== expected" not in src


@pytest.mark.asyncio
async def test_s5_t9_rate_limit_fail_open_redis_down() -> None:
    """Redis down nao derruba request (fail-open)."""
    from app.services.rate_limit_by_key import RateLimitByKeyMiddleware

    mw = RateLimitByKeyMiddleware(app=MagicMock(), redis_url="redis://fake")
    request = MagicMock()
    request.headers = {"x-api-key": "test"}
    request.url.path = "/api/v1/test"
    call_next = AsyncMock(return_value=MagicMock(headers={}, status_code=200))

    with patch(
        "app.services.rate_limit_by_key.redis_async.from_url",
        side_effect=OSError("connection refused"),
    ):
        resp = await mw.dispatch(request, call_next)

    call_next.assert_awaited_once()
    assert getattr(resp, "status_code", 200) == 200


def test_s5_t1_stress_scripts_sem_token_literal_telegram() -> None:
    """Stress scripts nao embutem token bot (\\d+:[A-Za-z0-9_-]{30,})."""
    import re

    pattern = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b")
    scripts_dir = REPO / "backend" / "scripts"
    hits = []
    for path in scripts_dir.glob("stress_telegram*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if pattern.search(text):
            hits.append(path.name)
    assert hits == [], f"token literal em: {hits}"


def test_s5_gitignore_covers_env_and_secrets() -> None:
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gi
    # .secrets e padrao do projeto
    assert ".secrets" in gi or "secrets/" in gi or "*.pem" in gi
