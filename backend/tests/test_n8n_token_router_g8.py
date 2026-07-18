"""Tests for N8N token router (G8.23.T4).

Cobre:
- bootstrap_legacy idempotente a partir de settings (test_load_from_env_initial)
- register / rotate / get_token
- revoke_old com grace period (regressao: kid ROTATING -> REVOKED)
- integracao com ``app.integrations.n8n.get_n8n_headers()``
- snapshots nao vazam tokens

Modified by Gustavo Almeida + cartorio-n8n -- G8.23.T4 (Wave 53).
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

import pytest

from app.services.n8n_token_router import (
    DEFAULT_GRACE_PERIOD_DAYS,
    DEFAULT_LEGACY_KID,
    DEFAULT_TTL_DAYS,
    N8NTokenRouter,
    TokenStatus,
    get_router,
)


@pytest.fixture(autouse=True)
def reset_router():
    """Reset singleton antes e depois de cada teste para isolamento."""
    get_router().reset_for_tests()
    yield
    get_router().reset_for_tests()


@pytest.fixture
def fresh_router():
    """Instancia isolada (sem usar o singleton) para testes de concorrencia."""
    return N8NTokenRouter()


# ========================================================================
# register / bootstrap
# ========================================================================


def test_register_first_becomes_active(reset_router):
    """Primeiro register com status ACTIVE vira o active do registry."""
    r = get_router()
    r.register("k1", "token-1", ttl_days=30)

    assert r.status_of("k1") == TokenStatus.ACTIVE
    kid, token = r.get_token()
    assert kid == "k1"
    assert token == "token-1"


def test_register_duplicate_kid_raises(reset_router):
    """Kid duplicado eh erro fatal (reuse de key id NAO permitido)."""
    r = get_router()
    r.register("k1", "token-1", ttl_days=30)
    with pytest.raises(ValueError, match="already registered"):
        r.register("k1", "token-1-different")


def test_register_second_active_raises(reset_router):
    """Registrar ACTIVE enquanto ja existe ACTIVE nao eh permitido."""
    r = get_router()
    r.register("k1", "token-1")
    with pytest.raises(RuntimeError, match="cannot register active"):
        r.register("k2", "token-2")


def test_register_rotating_kid_is_allowed(reset_router):
    """Registrar kid em estado ROTATING nao muda o active."""
    r = get_router()
    r.register("k1", "token-1")  # active
    r.register("k2", "token-2", status=TokenStatus.ROTATING)  # ok
    assert r.status_of("k1") == TokenStatus.ACTIVE
    assert r.status_of("k2") == TokenStatus.ROTATING


def test_register_invalid_status_raises(reset_router):
    """Status fora do enum eh ValueError."""
    r = get_router()
    with pytest.raises(ValueError, match="invalid status"):
        r.register("k1", "token-1", status="banana")


def test_register_empty_args_raises(reset_router):
    """kid/token vazios sao ValueError."""
    r = get_router()
    with pytest.raises(ValueError, match="non-empty"):
        r.register("", "token-1")
    with pytest.raises(ValueError, match="non-empty"):
        r.register("k1", "")


# ========================================================================
# bootstrap_legacy
# ========================================================================


def test_bootstrap_legacy_basic(reset_router):
    """bootstrap_legacy registra kid=legacy com token dado."""
    r = get_router()
    r.bootstrap_legacy("legacy-token-xyz")
    assert r.status_of(DEFAULT_LEGACY_KID) == TokenStatus.ACTIVE
    kid, token = r.get_token()
    assert kid == DEFAULT_LEGACY_KID
    assert token == "legacy-token-xyz"


def test_bootstrap_legacy_idempotent(reset_router):
    """Chamar duas vezes com mesmo token nao duplica kid."""
    r = get_router()
    r.bootstrap_legacy("t1")
    r.bootstrap_legacy("t1")
    assert len(r.list_active()) == 1


def test_bootstrap_legacy_conflicting_token_raises(reset_router):
    """bootstrap_legacy com kid existente e token diferente -> ValueError."""
    r = get_router()
    r.bootstrap_legacy("t1")
    with pytest.raises(ValueError, match="different token"):
        r.bootstrap_legacy("t2")


def test_bootstrap_legacy_empty_token_is_noop(reset_router):
    """Token vazio em bootstrap = noop silencioso (warning log)."""
    r = get_router()
    r.bootstrap_legacy("")
    assert r.list_active() == []


def test_load_from_env_initial(reset_router):
    """Integration: get_n8n_headers() puxa settings.n8n_api_key via bootstrap."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.n8n_api_key = "n8n-test-key-from-env"
        mock_settings.n8n_base_url = "http://cartorio_n8n:5678"
        # Lazy import do modulo de integracao (singleton lazy bootstrap)
        integration = importlib.import_module("app.integrations.n8n")
        integration.get_n8n_headers()

    r = get_router()
    assert r.status_of(DEFAULT_LEGACY_KID) == TokenStatus.ACTIVE
    kid, token = r.get_token()
    assert token == "n8n-test-key-from-env"
    assert kid == DEFAULT_LEGACY_KID


def test_load_from_env_empty_raises(reset_router):
    """Se settings.n8n_api_key eh None, _ensure_bootstrapped falha limpo."""
    integration = importlib.import_module("app.integrations.n8n")
    with patch("app.config.settings") as mock_settings:
        mock_settings.n8n_api_key = None
        mock_settings.n8n_base_url = "http://cartorio_n8n:5678"
        with pytest.raises(RuntimeError, match="settings.n8n_api_key is empty"):
            integration._ensure_bootstrapped()


# ========================================================================
# rotate
# ========================================================================


def test_rotate_marks_old_rotating(reset_router):
    """apos rotate(), old kid -> ROTATING, new kid -> ACTIVE."""
    r = get_router()
    r.register("k1", "token-1")
    old = r.rotate("k2", "token-2")
    assert old == "k1"
    assert r.status_of("k1") == TokenStatus.ROTATING
    assert r.status_of("k2") == TokenStatus.ACTIVE
    kid, token = r.get_token()
    assert kid == "k2"
    assert token == "token-2"


def test_rotate_without_active_raises(reset_router):
    """Rotacionar sem active registered -> RuntimeError."""
    r = get_router()
    with pytest.raises(RuntimeError, match="without an active token"):
        r.rotate("k1", "token-1")


def test_rotate_same_kid_raises(reset_router):
    """new_kid == active_kid -> ValueError (nada pra rotacionar)."""
    r = get_router()
    r.register("k1", "token-1")
    with pytest.raises(ValueError, match="== active kid"):
        r.rotate("k1", "token-1-new")


def test_rotate_duplicate_new_kid_raises(reset_router):
    """new_kid ja registrado -> ValueError."""
    r = get_router()
    r.register("k1", "token-1")
    r.register("k2", "token-2-rot", status=TokenStatus.ROTATING)
    with pytest.raises(ValueError, match="already registered"):
        r.rotate("k2", "token-2-new")


# ========================================================================
# get_token
# ========================================================================


def test_get_token_returns_active_only(reset_router):
    """get_token() ignora kids em ROTATING/REVOKED."""
    r = get_router()
    r.register("k1", "token-1")
    r.register("k2", "token-2-old", status=TokenStatus.ROTATING)
    r.register("k3", "token-3-old", status=TokenStatus.REVOKED)
    kid, token = r.get_token()
    assert kid == "k1"
    assert token == "token-1"


def test_get_token_without_active_raises(reset_router):
    """Router vazio -> RuntimeError."""
    r = get_router()
    with pytest.raises(RuntimeError, match="no active token"):
        r.get_token()


def test_get_token_fails_if_active_revoked(reset_router):
    """Se active_kid foi marcada REVOKED, get_token falha."""
    r = get_router()
    r.register("k1", "token-1")
    # Forcar inconsistencia (simula bug): marca active direto
    with r._lock:  # noqa: SLF001
        r._tokens["k1"]["status"] = TokenStatus.REVOKED  # noqa: SLF001
    with pytest.raises(RuntimeError, match="not in ACTIVE state"):
        r.get_token()


# ========================================================================
# revoke_old + grace period
# ========================================================================


def test_revoke_old_after_grace(reset_router):
    """ROTATING com grace expirado vira REVOKED."""
    r = get_router()
    r.register("k1", "token-1")
    r.rotate("k2", "token-2")

    # Simula que k1 foi rotacionado ha 30 dias
    long_ago = datetime.now(UTC) - timedelta(days=30)
    with r._lock:  # noqa: SLF001
        r._tokens["k1"]["rotated_at"] = long_ago  # noqa: SLF001

    revoked = r.revoke_old(grace_period_days=7)
    assert revoked == ["k1"]
    assert r.status_of("k1") == TokenStatus.REVOKED


def test_revoke_old_within_grace_keeps_rotating(reset_router):
    """ROTATING dentro do grace NAO eh revogado."""
    r = get_router()
    r.register("k1", "token-1")
    r.rotate("k2", "token-2")

    # Rotated ha 1 dia (< 7 dia grace)
    one_day_ago = datetime.now(UTC) - timedelta(days=1)
    with r._lock:  # noqa: SLF001
        r._tokens["k1"]["rotated_at"] = one_day_ago  # noqa: SLF001

    revoked = r.revoke_old(grace_period_days=7)
    assert revoked == []
    assert r.status_of("k1") == TokenStatus.ROTATING


def test_revoke_old_ignores_active_and_revoked(reset_router):
    """ACTIVES e REVOKED nao aparecem no revoke_old (ja estao terminais)."""
    r = get_router()
    r.register("k1", "token-1")  # active
    r.register("k2", "token-2", status=TokenStatus.ROTATING)
    r.register("k3", "token-3", status=TokenStatus.REVOKED)

    revoked = r.revoke_old(grace_period_days=7)
    assert revoked == []


def test_revoke_old_zero_grace_revokes_immediately(reset_router):
    """grace_period_days=0 revoga qualquer ROTATING."""
    r = get_router()
    r.register("k1", "token-1")
    r.rotate("k2", "token-2")
    revoked = r.revoke_old(grace_period_days=0)
    # rotated_at ~= now, e cutoff = now - 0 == now, entao rotated_at <= cutoff
    assert "k1" in revoked
    assert r.status_of("k1") == TokenStatus.REVOKED


# ========================================================================
# Integracao com app.integrations.n8n
# ========================================================================


def test_integration_with_n8n_headers(reset_router):
    """get_n8n_headers() retorna X-N8N-API-KEY + X-N8N-KEY-ID alinhados."""
    integration = importlib.import_module("app.integrations.n8n")
    r = get_router()
    r.register("prod-2026-q3", "secret-prod-q3", ttl_days=30)

    headers = integration.get_n8n_headers()
    assert headers["X-N8N-API-KEY"] == "secret-prod-q3"
    assert headers["X-N8N-KEY-ID"] == "prod-2026-q3"


def test_integration_get_n8n_base_url(reset_router):
    """get_n8n_base_url() le settings.n8n_base_url."""
    integration = importlib.import_module("app.integrations.n8n")
    with patch("app.config.settings") as mock_settings:
        mock_settings.n8n_base_url = "https://n8n.example.com:5678"
        assert integration.get_n8n_base_url() == "https://n8n.example.com:5678"


def test_integration_bootstrap_from_settings(reset_router):
    """bootstrap_from_settings() eh idempotente e popula o router."""
    integration = importlib.import_module("app.integrations.n8n")
    with patch("app.config.settings") as mock_settings:
        mock_settings.n8n_api_key = "k-env-x"
        mock_settings.n8n_base_url = "http://n8n"
        integration.bootstrap_from_settings()
        integration.bootstrap_from_settings()  # idempotente

    r = get_router()
    assert r.status_of(DEFAULT_LEGACY_KID) == TokenStatus.ACTIVE
    _, token = r.get_token()
    assert token == "k-env-x"


# ========================================================================
# Snapshot + misc
# ========================================================================


def test_snapshot_does_not_leak_tokens(reset_router):
    """snapshot() retorna hash, nao o token raw (LGPD)."""
    r = get_router()
    r.register("k1", "super-secret-token-xyz")
    snap = r.snapshot()
    assert "super-secret-token-xyz" not in str(snap)
    assert "token_hash" in snap["k1"]
    assert len(snap["k1"]["token_hash"]) == 8


def test_snapshot_includes_all_kids(reset_router):
    """snapshot() cobre ACTIVE + ROTATING + REVOKED."""
    r = get_router()
    r.register("k1", "t1")
    r.rotate("k2", "t2")
    snap = r.snapshot()
    assert set(snap.keys()) == {"k1", "k2"}
    assert snap["k1"]["status"] == TokenStatus.ROTATING
    assert snap["k2"]["status"] == TokenStatus.ACTIVE


def test_list_active_returns_only_actives(reset_router):
    """list_active() retorna apenas ACTIVE kids."""
    r = get_router()
    r.register("k1", "t1")
    r.register("k2", "t2", status=TokenStatus.ROTATING)
    r.register("k3", "t3", status=TokenStatus.REVOKED)
    assert r.list_active() == ["k1"]


def test_status_of_unknown_kid_returns_none(reset_router):
    """status_of() retorna None para kid nao registrado."""
    r = get_router()
    assert r.status_of("nao_existe") is None


def test_ttl_default_is_30_days(reset_router):
    """DEFAULT_TTL_DAYS=30 confere com docs."""
    assert DEFAULT_TTL_DAYS == 30
    r = get_router()
    r.register("k1", "t1")
    expires = r._tokens["k1"]["expires_at"]  # noqa: SLF001
    delta = expires - datetime.now(UTC)
    # tolera ~10s de clock drift
    assert abs(delta.total_seconds() - 30 * 86400) < 10


def test_grace_period_default_is_7_days():
    """DEFAULT_GRACE_PERIOD_DAYS=7 confere com docs."""
    assert DEFAULT_GRACE_PERIOD_DAYS == 7


# ========================================================================
# Thread-safety (smoke)
# ========================================================================


def test_thread_safety_register_no_double_active(reset_router):
    """Concorrencia: dois registers nao conseguem criar dois ACTIVE."""
    import threading

    r = get_router()
    errors: list[Exception] = []

    def attempt(kid: str, token: str) -> None:
        try:
            r.register(kid, token)
        except RuntimeError as e:
            errors.append(e)

    t1 = threading.Thread(target=attempt, args=("k1", "t1"))
    t2 = threading.Thread(target=attempt, args=("k2", "t2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Pelo menos um deles deve ter falhado (nao podemos ter 2 ACTIVE)
    assert len(errors) >= 1
    assert len(r.list_active()) == 1
