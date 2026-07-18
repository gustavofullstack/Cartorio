"""G8.19.T2 — testes do roteador de chaves HMAC do audit log.

Foco: provar que o sistema permite rotacionar ``AUDIT_HMAC_KEY`` sem
invalidar entries antigos do audit (cada entry referencia qual ``kid``
assinou).

Cenarios cobertos (9+):
1. test_register_key_first_becomes_active
2. test_register_two_active_keys_raises
3. test_register_key_rejects_short_secret
4. test_register_key_rejects_duplicate_kid
5. test_rotate_to_new_key_old_marked_rotating
6. test_rotate_with_no_prior_active_no_error
7. test_get_key_for_signing_returns_active_only
8. test_get_key_by_kid_returns_correct_secret
9. test_get_key_by_kid_unknown_raises
10. test_verify_old_entry_with_old_key_succeeds
11. test_verify_old_entry_with_new_key_fails_gracefully
12. test_verify_legacy_kid_used_when_kid_is_none
13. test_verify_unknown_kid_fails_silently
14. test_cleanup_rotated_keys_after_grace_period
15. test_cleanup_rotated_keys_within_grace_period_noop
16. test_audit_chain_integrity_preserved_across_rotation
17. test_concurrent_rotate_thread_safe
18. test_generate_new_secret_minimum_length

Modified by Gustavo Almeida
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, UTC
from unittest.mock import patch

import pytest

from app.services.audit_keys import (
    DEFAULT_GRACE_PERIOD_DAYS,
    KeyStatus,
    bootstrap_legacy,
    cleanup_rotated_keys_thunk,
    generate_new_secret,
    get_router,
    sign_audit_entry,
    verify_audit_entry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Reset o singleton antes e depois de cada teste (isolamento total)."""
    router = get_router()
    router.reset_for_tests()
    yield
    router.reset_for_tests()


@pytest.fixture
def secret_a() -> bytes:
    return b"secret_a_" + b"x" * 24  # 32 bytes


@pytest.fixture
def secret_b() -> bytes:
    return b"secret_b_" + b"y" * 24


@pytest.fixture
def canonical() -> bytes:
    return b"canonical_payload_v1:data:user:action"


# ---------------------------------------------------------------------------
# T1 — register_key
# ---------------------------------------------------------------------------


def test_register_key_first_becomes_active(secret_a):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ACTIVE)
    kid, sec = get_router().get_key_for_signing()
    assert kid == "k1"
    assert sec == secret_a
    assert get_router().status_of("k1") == KeyStatus.ACTIVE


def test_register_two_active_keys_raises(secret_a):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ACTIVE)
    with pytest.raises(ValueError, match="ja existe active"):
        register("k2", secret_a, status=KeyStatus.ACTIVE)


def test_register_key_rejects_short_secret():
    with pytest.raises(ValueError, match="pelo menos 16"):
        get_router().register_key("k1", b"short", status=KeyStatus.ROTATING)


def test_register_key_rejects_duplicate_kid(secret_a):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ROTATING)
    with pytest.raises(ValueError, match="kid duplicado"):
        register("k1", secret_a, status=KeyStatus.ROTATING)


# ---------------------------------------------------------------------------
# T2 — rotate_to_new_key
# ---------------------------------------------------------------------------


def test_rotate_to_new_key_old_marked_rotating(secret_a, secret_b):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ACTIVE)
    old_kid = get_router().rotate_to_new_key("k2", secret_b)
    assert old_kid == "k1"
    assert get_router().status_of("k1") == KeyStatus.ROTATING
    kid, sec = get_router().get_key_for_signing()
    assert kid == "k2"
    assert sec == secret_b


def test_rotate_with_no_prior_active_no_error(secret_b):
    old_kid = get_router().rotate_to_new_key("k_first", secret_b)
    assert old_kid == ""
    kid, _ = get_router().get_key_for_signing()
    assert kid == "k_first"


# ---------------------------------------------------------------------------
# T3 — get_key_*
# ---------------------------------------------------------------------------


def test_get_key_for_signing_returns_active_only(secret_a, secret_b):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ACTIVE)
    register("k2", secret_b, status=KeyStatus.ROTATING)
    kid, sec = get_router().get_key_for_signing()
    assert kid == "k1"
    assert sec == secret_a


def test_get_key_by_kid_returns_correct_secret(secret_a, secret_b):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ACTIVE)
    register("k2", secret_b, status=KeyStatus.ROTATING)
    assert get_router().get_key_by_kid("k2") == secret_b


def test_get_key_by_kid_unknown_raises(secret_a):
    register = get_router().register_key
    register("k1", secret_a, status=KeyStatus.ACTIVE)
    with pytest.raises(KeyError, match="Unknown HMAC kid"):
        get_router().get_key_by_kid("nao_existe")


# ---------------------------------------------------------------------------
# T4 — verify
# ---------------------------------------------------------------------------


def test_verify_old_entry_with_old_key_succeeds(canonical):
    """Entry assinada com key antiga deve verificar mesmo apos rotacao."""
    register = get_router().register_key
    register("legacy", b"k_a_" + b"a" * 28, status=KeyStatus.ACTIVE)
    _, sig = sign_audit_entry(canonical)
    get_router().rotate_to_new_key("k_b", b"k_b_" + b"b" * 28)
    assert verify_audit_entry(canonical, "legacy", sig) is True


def test_verify_old_entry_with_new_key_fails_gracefully(canonical):
    """Tentar verify entry antiga COM key nova deve retornar False (sem raise)."""
    register = get_router().register_key
    register("legacy", b"k_a_" + b"a" * 28, status=KeyStatus.ACTIVE)
    _, sig = sign_audit_entry(canonical)
    get_router().rotate_to_new_key("k_b", b"k_b_" + b"b" * 28)
    assert verify_audit_entry(canonical, "k_b", sig) is False


def test_verify_legacy_kid_used_when_kid_is_none(canonical):
    """Entries pre-rotacao (kid=None) verificam contra kid 'legacy' do bootstrap."""
    bootstrap_legacy(b"k_legacy_x" + b"x" * 20, kid="legacy")
    _, sig = sign_audit_entry(canonical)  # usa "legacy" (active)
    # Simula entry antiga sem kid (vai cair em 'legacy' automaticamente)
    assert verify_audit_entry(canonical, kid=None, sig=sig) is True


def test_verify_unknown_kid_fails_silently(canonical):
    bootstrap_legacy(b"k_legacy_y" + b"y" * 20, kid="legacy")
    _, sig = sign_audit_entry(canonical)
    assert verify_audit_entry(canonical, kid="fantasma", sig=sig) is False


# ---------------------------------------------------------------------------
# T5 — cleanup
# ---------------------------------------------------------------------------


def test_cleanup_rotated_keys_after_grace_period(secret_a, secret_b):
    register = get_router().register_key
    register("k_old", secret_a, status=KeyStatus.ACTIVE)
    get_router().rotate_to_new_key("k_new", secret_b)
    # Força o rotated_at da chave antiga para alem do grace period
    rotated_at_old = datetime.now(UTC) - timedelta(days=DEFAULT_GRACE_PERIOD_DAYS + 5)
    with get_router()._lock:  # noqa: SLF001
        get_router()._keys["k_old"]["rotated_at"] = rotated_at_old  # noqa: SLF001
    deprecated = cleanup_rotated_keys_thunk(grace_period_days=DEFAULT_GRACE_PERIOD_DAYS)
    assert "k_old" in deprecated
    assert get_router().status_of("k_old") == KeyStatus.DEPRECATED
    # E verify agora falha (KeyError -> False silencioso)
    assert verify_audit_entry(b"x", "k_old", "sig") is False


def test_cleanup_rotated_keys_within_grace_period_noop(secret_a, secret_b):
    register = get_router().register_key
    register("k_old", secret_a, status=KeyStatus.ACTIVE)
    get_router().rotate_to_new_key("k_new", secret_b)
    # rotated_at = now (recent); cleanup nao promove
    deprecated = cleanup_rotated_keys_thunk(grace_period_days=DEFAULT_GRACE_PERIOD_DAYS)
    assert "k_old" not in deprecated
    assert get_router().status_of("k_old") == KeyStatus.ROTATING


# ---------------------------------------------------------------------------
# T6 — integracao com AuditService (chain preservada)
# ---------------------------------------------------------------------------


def test_audit_chain_integrity_preserved_across_rotation(db_session):
    """Rotacao de HMAC key NO MEIO do AuditLog NAO quebra o sha256 chain."""
    from app.models.audit_log import AuditLog
    from app.services.audit import AuditService
    from app.services.audit_keys import (
        get_router,
        sign_audit_entry as _sign_via_registry,
        DEFAULT_LEGACY_KID,
    )

    # Bootstrap com kid deterministico a partir do settings
    from app.config import settings
    bootstrap_legacy(settings.audit_hmac_key.encode("utf-8"))

    # 3 entries com kid legacy
    with patch.object(
        AuditService,
        "_compute_hmac",
        staticmethod(lambda msg: _sign_via_registry(msg.encode("utf-8"))),
    ):
        for i in range(3):
            AuditService.log(
                db_session,
                actor_id=f"u{i}",
                action="rotation_test",
                resource=f"r:{i}",
                payload={"i": i, "phase": "old"},
            )
        db_session.commit()

        # Rotaciona
        new_secret = generate_new_secret(nbytes=32)
        old = get_router().rotate_to_new_key("post_rotation", new_secret)
        assert old == DEFAULT_LEGACY_KID

        # 2 entries com kid novo
        for i in range(2):
            AuditService.log(
                db_session,
                actor_id=f"u{i}",
                action="rotation_test",
                resource=f"r:{i}",
                payload={"i": i, "phase": "new"},
            )
        db_session.commit()

    # Chain deve estar integra (5 entries, hash chain conecta)
    ok, count = AuditService.verify_chain(db_session)
    assert ok is True
    assert count == 5

    # Cada entry tem seu kid (entries antigas podem ter legacy OU post_rotation
    # dependendo de quando o bootstrap rodou — ambas devem verificar)
    entries = db_session.query(AuditLog).order_by(AuditLog.id.asc()).all()
    for i, entry in enumerate(entries):
        if i < 3:
            assert entry.hmac_kid == DEFAULT_LEGACY_KID
        else:
            assert entry.hmac_kid == "post_rotation"
        assert len(entry.hmac_signature) == 64  # SHA256 hex


# ---------------------------------------------------------------------------
# T7 — concurrency
# ---------------------------------------------------------------------------


def test_concurrent_rotate_thread_safe(secret_a):
    """Multiplas threads chamando rotate simultaneamente nao corrompem o state."""
    router = get_router()
    router.register_key("initial", secret_a, status=KeyStatus.ACTIVE)
    errors: list[BaseException] = []
    iterations = 50

    def rotate_attempt(i: int) -> None:
        try:
            # Tenta rotacionar; algumas threads vao falhar (kid duplicado)
            # o que eh comportamento esperado — NAO conta como erro de teste.
            router.rotate_to_new_key(f"k_{i}", b"k_secret_" + bytes([i + 1]) * 22)
        except ValueError:
            pass
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [
        threading.Thread(target=rotate_attempt, args=(i,))
        for i in range(iterations)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # Estado final coerente: uma unica active kid, restante rotating
    snap = router.snapshot()
    actives = [kid for kid, st in snap.items() if st["status"] == KeyStatus.ACTIVE]
    assert len(actives) == 1
    assert snap[actives[0]]["status"] == KeyStatus.ACTIVE
    # Pelo menos algumas foram promovidas a rotating
    rotatings = [
        kid for kid, st in snap.items() if st["status"] == KeyStatus.ROTATING
    ]
    assert len(rotatings) >= 1


def test_generate_new_secret_minimum_length():
    with pytest.raises(ValueError):
        generate_new_secret(nbytes=8)
    s = generate_new_secret(nbytes=32)
    assert isinstance(s, bytes)
    assert len(s) == 32
    # unicidade estatistica
    s2 = generate_new_secret()
    assert s != s2
