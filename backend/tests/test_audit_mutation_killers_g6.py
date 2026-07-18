"""Mutation killers for AuditService (G6.A.T7 / Wave 13).

Mutmut report G6 showed audit.py at ~0% killed — many pure helpers were
only exercised indirectly. These tests pin:
- _canonical_block determinism (sort_keys, separators, prev_hash zero-fill)
- _compute_hash avalanche (payload/timestamp/prev change → different digest)
- _compute_hmac key-binding (wrong key or message → different signature)
- log() dual-IP D5 (full ip stored, ip_truncated derived via truncate_ip)

Target: raise kill rate on audit.py pure paths without full mutmut re-run.
Modified by Gustavo Almeida + cartorio-dev — G6 Wave 13.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest

from app.services.audit import AuditService
from app.utils.ip import truncate_ip


class TestCanonicalBlock:
    """_canonical_block must be byte-stable for chain integrity."""

    def test_prev_hash_none_uses_64_zeroes(self) -> None:
        block = AuditService._canonical_block(None, {"a": 1}, "2026-07-16T12:00:00.000000")
        parsed = json.loads(block)
        assert parsed["prev_hash"] == "0" * 64
        assert len(parsed["prev_hash"]) == 64

    def test_prev_hash_empty_string_also_zero_filled(self) -> None:
        """Empty string is falsy — same zero-fill as None (chain head)."""
        block = AuditService._canonical_block("", {"a": 1}, "t")
        parsed = json.loads(block)
        assert parsed["prev_hash"] == "0" * 64

    def test_sort_keys_and_compact_separators(self) -> None:
        block = AuditService._canonical_block("abc", {"z": 1, "a": 2}, "ts")
        # sort_keys → "a" before "z" inside payload; compact separators
        assert ',"payload":{"a":2,"z":1},' in block or '"payload":{"a":2,"z":1}' in block
        assert ": " not in block  # separators=(",", ":") — no spaces after colon
        assert ", " not in block

    def test_same_inputs_same_canonical_string(self) -> None:
        a = AuditService._canonical_block("h1", {"x": True}, "2026-01-01T00:00:00.000001")
        b = AuditService._canonical_block("h1", {"x": True}, "2026-01-01T00:00:00.000001")
        assert a == b


class TestComputeHash:
    """_compute_hash is SHA256 of the canonical block — kill identity mutants."""

    def test_hash_is_64_hex_chars(self) -> None:
        h = AuditService._compute_hash(None, {"i": 0}, "2026-07-16T00:00:00.000000")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_payload_change_changes_hash(self) -> None:
        ts = "2026-07-16T00:00:00.000000"
        h1 = AuditService._compute_hash(None, {"valor": 100}, ts)
        h2 = AuditService._compute_hash(None, {"valor": 101}, ts)
        assert h1 != h2

    def test_timestamp_change_changes_hash(self) -> None:
        payload = {"x": 1}
        h1 = AuditService._compute_hash(None, payload, "2026-07-16T00:00:00.000000")
        h2 = AuditService._compute_hash(None, payload, "2026-07-16T00:00:00.000001")
        assert h1 != h2

    def test_prev_hash_change_changes_hash(self) -> None:
        payload = {"x": 1}
        ts = "2026-07-16T00:00:00.000000"
        h1 = AuditService._compute_hash("a" * 64, payload, ts)
        h2 = AuditService._compute_hash("b" * 64, payload, ts)
        assert h1 != h2

    def test_matches_manual_sha256(self) -> None:
        prev = "c" * 64
        payload = {"k": "v"}
        ts = "2026-07-16T12:34:56.789012"
        expected_block = json.dumps(
            {"prev_hash": prev, "timestamp": ts, "payload": payload},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        expected = hashlib.sha256(expected_block.encode("utf-8")).hexdigest()
        assert AuditService._compute_hash(prev, payload, ts) == expected


class TestComputeHmac:
    """_compute_hmac binds server key — kills constant-return mutants."""

    def test_hmac_is_64_hex(self) -> None:
        _kid, sig = AuditService._compute_hmac("message")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_different_message_different_hmac(self) -> None:
        _k1, s1 = AuditService._compute_hmac("a")
        _k2, s2 = AuditService._compute_hmac("b")
        assert s1 != s2

    def test_matches_hmac_sha256_with_settings_key(self) -> None:
        from app.config import settings

        msg = "hash:ts:actor:action"
        expected = hmac.new(
            settings.audit_hmac_key.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        _kid, sig = AuditService._compute_hmac(msg)
        assert sig == expected

    def test_wrong_key_does_not_match(self) -> None:
        msg = "forged"
        _kid, real = AuditService._compute_hmac(msg)
        forged = hmac.new(b"wrong-key", msg.encode("utf-8"), hashlib.sha256).hexdigest()
        assert real != forged


class TestLogDualIpD5:
    """AuditService.log must store full IP + truncated IP (LGPD D5)."""

    def test_log_sets_ip_and_ip_truncated(self, db_session) -> None:
        entry = AuditService.log(
            db_session,
            actor_id="user:test",
            action="test.d5",
            resource="test:1",
            payload={"ok": True},
            ip="203.0.113.77",
        )
        db_session.commit()
        assert entry.ip == "203.0.113.77"
        assert entry.ip_truncated == "203.0.113.0/24"
        assert entry.ip_truncated == truncate_ip("203.0.113.77")

    def test_log_none_ip_yields_none_truncated(self, db_session) -> None:
        entry = AuditService.log(
            db_session,
            actor_id="user:test",
            action="test.d5.none",
            resource="test:2",
            payload={"ok": True},
            ip=None,
        )
        db_session.commit()
        assert entry.ip is None
        assert entry.ip_truncated is None

    def test_hmac_message_format_includes_hash_ts_actor_action(self, db_session) -> None:
        """Pins the HMAC message composition used in log()."""
        with patch.object(AuditService, "_compute_hmac", wraps=AuditService._compute_hmac) as spy:
            entry = AuditService.log(
                db_session,
                actor_id="actor-x",
                action="act-y",
                resource="res",
                payload={"n": 1},
            )
            db_session.commit()
            assert spy.called
            msg = spy.call_args[0][0]
            assert entry.hash in msg
            assert "actor-x" in msg
            assert "act-y" in msg
            # format: f"{new_hash}:{timestamp}:{actor_id}:{action}"
            parts = msg.split(":")
            assert len(parts) >= 4
            assert parts[0] == entry.hash


class TestVerifyChainEdge:
    """Edge cases that kill 'always return True' mutants on verify_chain."""

    def test_empty_chain_is_ok(self, db_session) -> None:
        ok, count = AuditService.verify_chain(db_session)
        assert ok is True
        assert count == 0

    def test_single_entry_verifies(self, db_session) -> None:
        AuditService.log(
            db_session,
            actor_id="u",
            action="a",
            resource="r",
            payload={"solo": True},
        )
        db_session.commit()
        ok, count = AuditService.verify_chain(db_session)
        assert ok is True
        assert count == 1

    def test_hash_tamper_detected(self, db_session) -> None:
        AuditService.log(db_session, actor_id="u", action="a", resource="r", payload={"v": 1})
        db_session.commit()
        entry = db_session.query(
            __import__("app.models.audit_log", fromlist=["AuditLog"]).AuditLog
        ).first()
        entry.hash = "f" * 64  # type: ignore[union-attr]
        db_session.commit()
        ok, last_valid = AuditService.verify_chain(db_session)
        assert ok is False
        assert last_valid == 0


@pytest.mark.parametrize(
    "payload_a,payload_b",
    [
        ({"a": 1}, {"a": 2}),
        ({"nested": {"x": 1}}, {"nested": {"x": 2}}),
        ({"list": [1, 2]}, {"list": [1, 3]}),
    ],
)
def test_hash_sensitivity_parametrized(payload_a: dict, payload_b: dict) -> None:
    ts = "2026-07-16T00:00:00.000000"
    assert AuditService._compute_hash(None, payload_a, ts) != AuditService._compute_hash(
        None, payload_b, ts
    )
