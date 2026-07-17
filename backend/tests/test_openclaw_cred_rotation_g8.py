"""G8.04.T3 — Validação segura de rotação de credenciais OpenClaw.

Cobre:
- fingerprints aceitos (hex curto / fp: prefix)
- rejeição de valores que parecem secret completo (len>40 sem fp:)
- plano válido vs inválido (same fp, empty, non-hex)
- checklist canônico (backup → dual-write → swap → revoke → health)
- sem leak de raw secret em exceptions / to_dict

Modified by Gustavo Almeida — G8.04.T3 Wave 32.
"""

from __future__ import annotations

import pytest

from app.services.openclaw_cred_rotation import (
    FP_PREFIX,
    MAX_FP_BODY_LEN,
    MIN_FP_BODY_LEN,
    ROTATION_STEPS,
    RotationPlanResult,
    UnsafeCredentialError,
    assert_safe_fingerprint,
    is_safe_fingerprint,
    rotation_checklist,
    validate_rotation_plan,
)

# Fingerprints sintéticos (NÃO são secrets reais).
_OLD_FP = "a1b2c3d4e5f60718"
_NEW_FP = "f0e1d2c3b4a59687"
_OLD_FP_PREFIXED = f"{FP_PREFIX}{_OLD_FP}"
_NEW_FP_PREFIXED = f"{FP_PREFIX}{_NEW_FP}"

# Valor sintético com len>40 sem fp: — parece secret, deve ser rejeitado.
_FAKE_LONG_SECRET = "x" * (MAX_FP_BODY_LEN + 1)  # 41 chars, not hex-safe either
_FAKE_LONG_HEX_SECRET = "ab" * 32  # 64 hex chars, no fp: prefix


def test_rotation_checklist_canonical_order() -> None:
    steps = rotation_checklist()
    assert steps == list(ROTATION_STEPS)
    assert steps == [
        "backup",
        "dual-write window",
        "swap",
        "revoke old",
        "verify health",
    ]
    # Imutabilidade do source: checklist retorna cópia.
    steps.append("mutate")
    assert "mutate" not in rotation_checklist()


def test_assert_safe_fingerprint_accepts_short_hex() -> None:
    out = assert_safe_fingerprint(_OLD_FP)
    assert out == _OLD_FP_PREFIXED
    assert out.startswith(FP_PREFIX)
    assert len(out) > MIN_FP_BODY_LEN


def test_assert_safe_fingerprint_accepts_fp_prefix() -> None:
    out = assert_safe_fingerprint(_NEW_FP_PREFIXED)
    assert out == _NEW_FP_PREFIXED


def test_assert_safe_fingerprint_normalizes_case() -> None:
    mixed = "AbCdEf0123456789"
    out = assert_safe_fingerprint(mixed)
    assert out == f"{FP_PREFIX}{mixed.lower()}"


def test_assert_safe_fingerprint_rejects_empty() -> None:
    with pytest.raises(UnsafeCredentialError, match="empty"):
        assert_safe_fingerprint("")
    with pytest.raises(UnsafeCredentialError, match="empty"):
        assert_safe_fingerprint("   ")
    with pytest.raises(UnsafeCredentialError, match="empty"):
        assert_safe_fingerprint(f"{FP_PREFIX}")


def test_assert_safe_fingerprint_rejects_too_short() -> None:
    short = "abc"  # < MIN_FP_BODY_LEN
    with pytest.raises(UnsafeCredentialError, match="too short"):
        assert_safe_fingerprint(short)


def test_assert_safe_fingerprint_rejects_non_hex() -> None:
    with pytest.raises(UnsafeCredentialError, match="hex"):
        assert_safe_fingerprint("not-a-hex!!")


def test_assert_safe_fingerprint_rejects_full_secret_like() -> None:
    """Spec: len>40 and no 'fp:' prefix → reject (looks like full secret)."""
    assert len(_FAKE_LONG_SECRET) > MAX_FP_BODY_LEN
    assert not _FAKE_LONG_SECRET.startswith(FP_PREFIX)
    with pytest.raises(UnsafeCredentialError, match="full secret"):
        assert_safe_fingerprint(_FAKE_LONG_SECRET)


def test_assert_safe_fingerprint_rejects_long_hex_without_prefix() -> None:
    assert len(_FAKE_LONG_HEX_SECRET) > MAX_FP_BODY_LEN
    with pytest.raises(UnsafeCredentialError, match="full secret"):
        assert_safe_fingerprint(_FAKE_LONG_HEX_SECRET)


def test_assert_safe_fingerprint_accepts_full_sha256_with_fp_prefix() -> None:
    """Com fp: permite até 64 hex (sha256 completo como fingerprint)."""
    body = "ab" * 32  # 64 hex
    out = assert_safe_fingerprint(f"{FP_PREFIX}{body}")
    assert out == f"{FP_PREFIX}{body}"


def test_exception_message_does_not_echo_secret() -> None:
    """LGPD/security: exception não deve ecoar o valor bruto longo."""
    try:
        assert_safe_fingerprint(_FAKE_LONG_SECRET)
        pytest.fail("expected UnsafeCredentialError")
    except UnsafeCredentialError as exc:
        msg = str(exc)
        assert _FAKE_LONG_SECRET not in msg
        assert "full secret" in msg


def test_is_safe_fingerprint_bool() -> None:
    assert is_safe_fingerprint(_OLD_FP) is True
    assert is_safe_fingerprint(_OLD_FP_PREFIXED) is True
    assert is_safe_fingerprint(_FAKE_LONG_SECRET) is False
    assert is_safe_fingerprint("") is False
    assert is_safe_fingerprint("short") is False


def test_validate_rotation_plan_ok() -> None:
    result = validate_rotation_plan(_OLD_FP, _NEW_FP)
    assert isinstance(result, RotationPlanResult)
    assert result.ok is True
    assert result.old_fp == _OLD_FP_PREFIXED
    assert result.new_fp == _NEW_FP_PREFIXED
    assert result.reasons == ()
    assert list(result.checklist) == list(ROTATION_STEPS)

    d = result.to_dict()
    assert d["ok"] is True
    assert d["old_fp"] == _OLD_FP_PREFIXED
    assert d["new_fp"] == _NEW_FP_PREFIXED
    # Sem campos de secret raw.
    assert "token" not in d
    assert "secret" not in str(d).lower() or "full secret" not in str(d).lower()


def test_validate_rotation_plan_ok_with_fp_prefix() -> None:
    result = validate_rotation_plan(_OLD_FP_PREFIXED, _NEW_FP_PREFIXED)
    assert result.ok is True
    assert result.old_fp == _OLD_FP_PREFIXED
    assert result.new_fp == _NEW_FP_PREFIXED


def test_validate_rotation_plan_rejects_same_fingerprints() -> None:
    result = validate_rotation_plan(_OLD_FP, _OLD_FP)
    assert result.ok is False
    assert any("differ" in r for r in result.reasons)
    assert result.checklist == ()


def test_validate_rotation_plan_rejects_old_secret_like() -> None:
    result = validate_rotation_plan(_FAKE_LONG_SECRET, _NEW_FP)
    assert result.ok is False
    assert any("old_token_fp" in r and "full secret" in r for r in result.reasons)
    # Não vazar o secret no reasons.
    joined = " ".join(result.reasons)
    assert _FAKE_LONG_SECRET not in joined
    assert result.checklist == ()


def test_validate_rotation_plan_rejects_new_secret_like() -> None:
    result = validate_rotation_plan(_OLD_FP, _FAKE_LONG_HEX_SECRET)
    assert result.ok is False
    assert any("new_token_fp" in r and "full secret" in r for r in result.reasons)
    assert _FAKE_LONG_HEX_SECRET not in " ".join(result.reasons)


def test_validate_rotation_plan_rejects_both_invalid() -> None:
    result = validate_rotation_plan("", "!!")
    assert result.ok is False
    assert len(result.reasons) >= 2
    assert any("old_token_fp" in r for r in result.reasons)
    assert any("new_token_fp" in r for r in result.reasons)


def test_validate_rotation_plan_rejects_non_hex_new() -> None:
    result = validate_rotation_plan(_OLD_FP, "nothex!!nothex")
    assert result.ok is False
    assert any("new_token_fp" in r and "hex" in r for r in result.reasons)


def test_rotation_steps_constant_matches_checklist() -> None:
    assert len(ROTATION_STEPS) == 5
    assert ROTATION_STEPS[0] == "backup"
    assert ROTATION_STEPS[-1] == "verify health"
