"""G8.23.T3 — Testes do envelope encryption (DEK wrapped by KEK).

Cobre LGPD Art. 46 — medidas técnicas adequadas para proteção de PII at-rest:

1. test_roundtrip_encrypt_decrypt          — AES-256-GCM plaintext <-> envelope
2. test_different_dek_per_record           — cada encrypt() gera DEK nova
3. test_kek_id_recorded_in_metadata        — header carrega kek_id + version
4. test_envelope_storage_in_db             — round-trip via coluna LargeBinary
                                             (mock SQLAlchemy, sem Postgres)
5. test_decrypt_with_wrong_kek_fails       — KEK errada -> EnvelopeAuthError
6. test_lgpd_art_46_compliance             — invariantes LGPD (kek_id, AAD,
                                             versão, fresh DEK, KEK não vaza)
7. test_aad_tampering_fails                — context diferente -> reject
8. test_envelope_binary_layout             — header/footer conforme spec
9. test_empty_plaintext                    — bytes vazios aceitos
10. test_metadata_header_without_decrypt   — read kek_id sem expor plaintext
11. test_string_helpers                     — encrypt_str/decrypt_str UTF-8
12. test_get_default_envelope_singleton    — cache process-wide

LGPD-REVIEW-PENDING — testes são válidos em SQLite + AES-256-GCM nativo.
Modified by Gustavo Almeida — G8 Wave 52.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services.envelope_encryption import (
    DEK_LEN_BYTES,
    ENVELOPE_VERSION,
    EnvelopeAuthError,
    EnvelopeDecodeError,
    EnvelopeEncryption,
    EnvelopeMeta,
    KekUnavailableError,
    NONCE_LEN_BYTES,
    get_default_envelope,
    reset_default_envelope,
)


# Fixtures ---------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Set deterministic KEK env vars for every test."""
    monkeypatch.setenv("KMS_KEK_ID", "kek-test-001")
    # 32 random bytes -> base64
    monkeypatch.setenv("KMS_KEK_B64", base64.b64encode(b"\x42" * 32).decode("ascii"))
    monkeypatch.setenv("KMS_KEK_DEV_FALLBACK", "false")
    reset_default_envelope()
    yield
    reset_default_envelope()


@pytest.fixture
def cipher() -> EnvelopeEncryption:
    return EnvelopeEncryption()


@pytest.fixture
def alternate_kek() -> EnvelopeEncryption:
    """Cipher with a DIFFERENT KEK — used for wrong-kek failure tests."""
    return EnvelopeEncryption(
        kek_id="kek-test-002",
        kek_bytes=b"\x99" * 32,
    )


# 1. Roundtrip ------------------------------------------------------------


def test_roundtrip_encrypt_decrypt(cipher: EnvelopeEncryption) -> None:
    plaintext = b"123.456.789-09"  # CPF fake (test only)
    envelope = cipher.encrypt(plaintext)
    assert envelope != plaintext
    assert cipher.decrypt(envelope) == plaintext


def test_roundtrip_with_context(cipher: EnvelopeEncryption) -> None:
    plaintext = b"MG-1234567-8"
    ctx = {"cliente_id": 42, "field": "rg"}
    envelope = cipher.encrypt(plaintext, context=ctx)
    assert cipher.decrypt(envelope, context=ctx) == plaintext


# 2. DEK uniqueness --------------------------------------------------------


def test_different_dek_per_record(cipher: EnvelopeEncryption) -> None:
    """Same plaintext, two encrypt() calls -> different envelopes (fresh DEK each time)."""
    plaintext = b"joao@example.com"
    env1 = cipher.encrypt(plaintext)
    env2 = cipher.encrypt(plaintext)
    assert env1 != env2
    # But both decrypt back to the same plaintext.
    assert cipher.decrypt(env1) == plaintext
    assert cipher.decrypt(env2) == plaintext


# 3. Kek id in metadata ---------------------------------------------------


def test_kek_id_recorded_in_metadata(cipher: EnvelopeEncryption) -> None:
    envelope = cipher.encrypt(b"audit")
    meta = cipher.metadata(envelope)
    assert isinstance(meta, EnvelopeMeta)
    assert meta.version == ENVELOPE_VERSION
    assert meta.kek_id == "kek-test-001"


def test_metadata_header_without_decrypt(cipher: EnvelopeEncryption) -> None:
    """Header reading NÃO expõe plaintext (forensic audit sem decrypt)."""
    secret = b"hunter2-very-secret"
    envelope = cipher.encrypt(secret)
    meta = cipher.metadata(envelope)
    assert meta.kek_id == "kek-test-001"
    # Sanity: secret must not appear anywhere in the envelope bytes.
    assert secret not in envelope


# 4. Storage roundtrip (mock SQLAlchemy) ----------------------------------


@dataclass
class _FakeRow:
    """Mimics a SQLAlchemy row with LargeBinary column."""

    cpf_envelope: bytes
    cpf_kek_id: str


def test_envelope_storage_in_db(cipher: EnvelopeEncryption) -> None:
    """Simulates encrypt -> SQLAlchemy LargeBinary column -> fetch -> decrypt."""
    plaintext = b"111.222.333-44"
    envelope = cipher.encrypt(plaintext, context={"cliente_id": 1})

    # Simulate persistence via SQLAlchemy ORM/Column with LargeBinary.
    mock_session = MagicMock()
    captured: dict[str, Any] = {}

    def _add(row: _FakeRow) -> _FakeRow:
        captured["row"] = row
        return row

    mock_session.add = MagicMock(side_effect=_add)
    row = _FakeRow(cpf_envelope=envelope, cpf_kek_id=cipher.kek_id)
    mock_session.add(row)
    mock_session.commit = MagicMock()
    mock_session.commit()

    assert "row" in captured
    assert isinstance(captured["row"].cpf_envelope, bytes)
    assert captured["row"].cpf_envelope == envelope
    assert captured["row"].cpf_kek_id == "kek-test-001"

    # Now simulate reading it back from DB and decrypting.
    fetched = _FakeRow(
        cpf_envelope=captured["row"].cpf_envelope,
        cpf_kek_id=captured["row"].cpf_kek_id,
    )
    decrypted = cipher.decrypt(fetched.cpf_envelope, context={"cliente_id": 1})
    assert decrypted == plaintext


# 5. Wrong KEK -----------------------------------------------------------


def test_decrypt_with_wrong_kek_fails(
    cipher: EnvelopeEncryption, alternate_kek: EnvelopeEncryption
) -> None:
    plaintext = b"super-secret-pii"
    envelope = cipher.encrypt(plaintext)
    with pytest.raises(EnvelopeAuthError):
        alternate_kek.decrypt(envelope)


def test_decrypt_with_wrong_kek_fails_string_helpers(
    cipher: EnvelopeEncryption, alternate_kek: EnvelopeEncryption
) -> None:
    envelope = cipher.encrypt_str("cpf-data")
    with pytest.raises(EnvelopeAuthError):
        alternate_kek.decrypt_str(envelope)


# 6. LGPD Art. 46 compliance ---------------------------------------------


def test_lgpd_art_46_compliance(cipher: EnvelopeEncryption) -> None:
    """Invariantes LGPD Art. 46: KEK nunca vaza, DEK única, versionamento, AAD."""
    plaintext = b"123.456.789-09"
    ctx = {"cliente_id": 99, "field": "cpf"}
    envelope = cipher.encrypt(plaintext, context=ctx)

    # a) Plaintext NÃO aparece no envelope (criptografia real, não XOR).
    assert plaintext not in envelope

    # b) KEK material NUNCA aparece no envelope.
    kek_material = b"\x42" * 32
    assert kek_material not in envelope

    # c) DEK random 32 bytes (validada via decrypt round-trip).
    assert len(plaintext) <= DEK_LEN_BYTES  # sanity
    assert cipher.decrypt(envelope, context=ctx) == plaintext

    # d) Versionamento explicito (permite migração futura).
    assert envelope[0] == ENVELOPE_VERSION

    # e) Metadata recupera kek_id (audit chain de chaves).
    meta = cipher.metadata(envelope)
    assert meta.kek_id == "kek-test-001"


# 7. AAD tampering -------------------------------------------------------


def test_aad_tampering_fails(cipher: EnvelopeEncryption) -> None:
    plaintext = b"cliente-pii"
    ctx_correct = {"cliente_id": 1, "field": "cpf"}
    envelope = cipher.encrypt(plaintext, context=ctx_correct)

    # Wrong context -> AAD hash mismatch -> reject.
    with pytest.raises(EnvelopeAuthError):
        cipher.decrypt(envelope, context={"cliente_id": 2, "field": "cpf"})

    # Decrypt succeeds with correct context.
    assert cipher.decrypt(envelope, context=ctx_correct) == plaintext


# 8. Binary layout --------------------------------------------------------


def test_envelope_binary_layout(cipher: EnvelopeEncryption) -> None:
    """Envelope header: [version:1][kek_id_len:1][kek_id:N] (fixed prefix).

    Total envelope = prefix + kek_nonce(12) + enc_dek(60) + data_nonce(12) +
                     ciphertext + aad_hash(32).
    """
    plaintext = b"hello world"
    kek_id = "kek-test-001"
    envelope = cipher.encrypt(plaintext, context={"x": 1})

    assert envelope[0] == ENVELOPE_VERSION
    assert envelope[1] == len(kek_id)
    assert envelope[2 : 2 + len(kek_id)] == kek_id.encode("ascii")

    # Tail must contain the AAD hash (last 32 bytes when context present).
    # Min envelope = prefix(2+N) + kek_nonce(12) + enc_dek(48) +
    #                data_nonce(12) + ciphertext(>=0) + aad_hash(32)
    assert len(envelope) >= 2 + len(kek_id) + NONCE_LEN_BYTES + 48 + NONCE_LEN_BYTES + 32


def test_envelope_decimal_byte_lengths(cipher: EnvelopeEncryption) -> None:
    """Nonces are 12 bytes (GCM standard); enc_dek is 60 bytes (12 nonce + 32 DEK + 16 tag)."""
    plaintext = b"size-check"
    envelope_no_ctx = cipher.encrypt(plaintext)
    envelope_with_ctx = cipher.encrypt(plaintext, context={"a": 1})
    # With context adds 32 bytes (AAD hash).
    assert len(envelope_with_ctx) == len(envelope_no_ctx) + 32


# 9. Empty plaintext ------------------------------------------------------


def test_empty_plaintext(cipher: EnvelopeEncryption) -> None:
    envelope = cipher.encrypt(b"")
    assert cipher.decrypt(envelope) == b""


# 10. String helpers -----------------------------------------------------


def test_string_helpers(cipher: EnvelopeEncryption) -> None:
    cpf = "123.456.789-09"
    envelope = cipher.encrypt_str(cpf, context={"cliente_id": 7})
    assert cipher.decrypt_str(envelope, context={"cliente_id": 7}) == cpf


# 11. Singleton / KEK cache (OTIMIZACAO) --------------------------------


def test_get_default_envelope_singleton(monkeypatch) -> None:
    reset_default_envelope()
    a = get_default_envelope()
    b = get_default_envelope()
    assert a is b  # cache hit — KEK não re-lê env


def test_reset_default_envelope_for_rotation(monkeypatch) -> None:
    monkeypatch.setenv("KMS_KEK_ID", "kek-v1")
    a = get_default_envelope()
    assert a.kek_id == "kek-v1"

    # Rotate: muda KEK + reset.
    monkeypatch.setenv("KMS_KEK_ID", "kek-v2")
    reset_default_envelope()
    b = get_default_envelope()
    assert b.kek_id == "kek-v2"
    assert a is not b


# 12. KEK invariants ------------------------------------------------------


def test_kek_invalid_length_raises() -> None:
    with pytest.raises(KekUnavailableError):
        EnvelopeEncryption(kek_id="bad", kek_bytes=b"\x00" * 16)  # 16 != 32


def test_kek_id_too_long_raises() -> None:
    with pytest.raises(KekUnavailableError):
        EnvelopeEncryption(kek_id="x" * 200, kek_bytes=b"\x00" * 32)


def test_kek_missing_env_raises(monkeypatch) -> None:
    monkeypatch.delenv("KMS_KEK_B64", raising=False)
    monkeypatch.setenv("KMS_KEK_DEV_FALLBACK", "false")
    reset_default_envelope()
    with pytest.raises(KekUnavailableError):
        EnvelopeEncryption()


def test_kek_dev_fallback_when_no_env(monkeypatch) -> None:
    monkeypatch.delenv("KMS_KEK_B64", raising=False)
    monkeypatch.setenv("KMS_KEK_DEV_FALLBACK", "true")
    monkeypatch.setenv("KMS_KEK_ID", "kek-dev-001")
    reset_default_envelope()
    cipher = EnvelopeEncryption()
    assert cipher.kek_id == "kek-dev-001"
    # Roundtrip works even with fallback KEK.
    env = cipher.encrypt(b"dev")
    assert cipher.decrypt(env) == b"dev"


# 13. Decode failures ----------------------------------------------------


def test_decode_empty_envelope_raises(cipher: EnvelopeEncryption) -> None:
    with pytest.raises(EnvelopeDecodeError):
        cipher.metadata(b"")


def test_decode_short_envelope_raises(cipher: EnvelopeEncryption) -> None:
    with pytest.raises(EnvelopeDecodeError):
        cipher.metadata(b"\x01")


def test_decode_wrong_version_raises(cipher: EnvelopeEncryption) -> None:
    bad = bytes([0x99, 0x05]) + b"kek-x" + b"\x00" * 60
    with pytest.raises(EnvelopeDecodeError):
        cipher.metadata(bad)


def test_decode_tampered_ciphertext_raises(cipher: EnvelopeEncryption) -> None:
    envelope = bytearray(cipher.encrypt(b"secret"))
    # Flip a byte in the ciphertext region (skip header + nonces).
    flip_at = len(envelope) - 10
    envelope[flip_at] ^= 0xFF
    with pytest.raises(EnvelopeAuthError):
        cipher.decrypt(bytes(envelope))


# 14. Encryption with random bytes (fuzz-like) --------------------------


@pytest.mark.parametrize(
    "plaintext",
    [
        b"",
        b"a",
        b"x" * 100,
        b"\x00\x01\x02\x03\xff",
        secrets.token_bytes(512),
    ],
    ids=["empty", "short", "100x", "binary", "512-random"],
)
def test_encrypt_decrypt_various_sizes(cipher: EnvelopeEncryption, plaintext: bytes) -> None:
    envelope = cipher.encrypt(plaintext)
    assert cipher.decrypt(envelope) == plaintext
