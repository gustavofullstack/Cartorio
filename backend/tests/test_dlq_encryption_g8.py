"""G8.08.T2 — Testes para criptografia at-rest do DLQ payload.

Cobre:
  - encrypt_dlq_payload: idempotência, versionamento, ciphertext Fernet válido
  - decrypt_dlq_payload: round-trip, levanta ValueError em payload inválido
  - is_encrypted_payload: detecta envelope corretamente
  - should_encrypt_payload: heurística PII (cpf/rg/email/nome etc)
  - Backward compat: decrypt de payload raw (não criptografado) retorna as-is
  - Nested dict PII detection

Modified by Gustavo Almeida — G8 Wave 30 A2.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from cryptography.fernet import InvalidToken

from app.services.dlq_encryption import (
    decrypt_dlq_payload,
    encrypt_dlq_payload,
    is_encrypted_payload,
    should_encrypt_payload,
)


# Chave de teste (32+ chars, derivada pelo Fernet internamente)
TEST_KEY = "test-dlq-encryption-key-2026-07-17-not-for-prod"


@pytest.fixture
def sample_payload_with_pii() -> dict[str, Any]:
    return {
        "queue": "evolution",
        "cpf": "123.456.789-09",
        "nome": "Gustavo Almeida",
        "telefone": "+55 34 99999-0000",
        "message": "Olá, gostaria de informações",
    }


@pytest.fixture
def sample_payload_no_pii() -> dict[str, Any]:
    return {
        "queue": "evolution",
        "message_id": "abc-123",
        "status_code": 200,
    }


@pytest.fixture
def sample_payload_nested_pii() -> dict[str, Any]:
    return {
        "queue": "chatwoot",
        "event": "conversation.created",
        "payload": {
            "contact": {
                "name": "João Silva",
                "email": "joao@example.com",
            },
        },
    }


class TestEncryptDLQPayload:
    def test_encrypt_returns_envelope(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        assert is_encrypted_payload(envelope)
        assert envelope["v"] == 1
        assert "_encrypted" in envelope
        assert envelope["_encrypted"] is True
        assert "ciphertext" in envelope

    def test_ciphertext_is_fernet_token(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        # Fernet token: starts with "gAAAAA" (version byte 0x80 + 128-bit IV)
        assert envelope["ciphertext"].startswith("gAAAAA")

    def test_encrypt_idempotent(self, sample_payload_with_pii):
        envelope1 = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        envelope2 = encrypt_dlq_payload(envelope1, TEST_KEY)
        # Segunda chamada não re-criptografa
        assert envelope2 == envelope1

    def test_encrypt_with_different_keys_produces_different_ciphertext(self, sample_payload_with_pii):
        env1 = encrypt_dlq_payload(sample_payload_with_pii, "key-A-2026")
        env2 = encrypt_dlq_payload(sample_payload_with_pii, "key-B-2026")
        assert env1["ciphertext"] != env2["ciphertext"]

    def test_encrypt_preserves_no_plaintext(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        # Garante que CPF e nome NÃO aparecem em plaintext no envelope
        assert "123.456.789-09" not in str(envelope)
        assert "Gustavo Almeida" not in str(envelope)


class TestDecryptDLQPayload:
    def test_round_trip_recovers_original(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        recovered = decrypt_dlq_payload(envelope, TEST_KEY)
        assert recovered == sample_payload_with_pii

    def test_round_trip_with_unicode(self):
        payload = {"nome": "José da Silva Açúcar", "cpf": "987.654.321-00"}
        envelope = encrypt_dlq_payload(payload, TEST_KEY)
        recovered = decrypt_dlq_payload(envelope, TEST_KEY)
        assert recovered == payload

    def test_decrypt_with_wrong_key_raises(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        with pytest.raises((ValueError, InvalidToken)):
            decrypt_dlq_payload(envelope, "wrong-key-2026")

    def test_decrypt_raw_payload_returns_as_is(self):
        # Backward compat: payload sem envelope vira self
        raw = {"cpf": "123.456.789-00", "nome": "Test"}
        result = decrypt_dlq_payload(raw, TEST_KEY)
        assert result == raw

    def test_decrypt_invalid_envelope_raises(self):
        # Envelope COM _encrypted+ciphertext+v mas ciphertext Fernet inválido
        with pytest.raises(ValueError):
            decrypt_dlq_payload(
                {"_encrypted": True, "v": 1, "ciphertext": "gAAAAAbroken-token-invalid!!!"},
                TEST_KEY,
            )

    def test_decrypt_non_dict_raises(self):
        with pytest.raises(ValueError):
            decrypt_dlq_payload("not-a-dict", TEST_KEY)  # type: ignore[arg-type]


class TestIsEncryptedPayload:
    def test_true_for_valid_envelope(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        assert is_encrypted_payload(envelope) is True

    def test_false_for_raw_dict(self, sample_payload_no_pii):
        assert is_encrypted_payload(sample_payload_no_pii) is False

    def test_false_for_empty_dict(self):
        assert is_encrypted_payload({}) is False

    def test_false_for_partial_envelope(self):
        # Tem _encrypted mas falta ciphertext
        assert is_encrypted_payload({"_encrypted": True, "v": 1}) is False


class TestShouldEncryptPayload:
    @pytest.mark.parametrize(
        "field",
        ["cpf", "rg", "cnpj", "nome", "name", "email", "telefone", "phone",
         "endereco", "address", "data_nascimento", "birth_date", "cnh", "passaporte"],
    )
    def test_detects_pii_field_top_level(self, field):
        payload = {"queue": "evolution", field: "value"}
        assert should_encrypt_payload(payload) is True

    def test_detects_pii_field_nested(self):
        payload = {"queue": "evolution", "data": {"email": "x@y.z"}}
        assert should_encrypt_payload(payload) is True

    def test_no_pii_returns_false(self, sample_payload_no_pii):
        assert should_encrypt_payload(sample_payload_no_pii) is False

    def test_empty_dict_returns_false(self):
        assert should_encrypt_payload({}) is False

    def test_already_encrypted_returns_false(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        # Já criptografado: heurística não duplica
        assert should_encrypt_payload(envelope) is False

    def test_non_dict_returns_false(self):
        assert should_encrypt_payload("string") is False  # type: ignore[arg-type]
        assert should_encrypt_payload(123) is False  # type: ignore[arg-type]

    def test_case_insensitive_key_match(self):
        # Keys em uppercase (comum em JSON de Evolution/Telegram)
        payload = {"CPF": "123", "NOME": "Test"}
        assert should_encrypt_payload(payload) is True


class TestEncryptionCompliance:
    """Testes de compliance LGPD Art.46."""

    def test_ciphertext_is_not_human_readable(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        # O ciphertext NÃO deve conter nenhuma chave do payload original
        for key in sample_payload_with_pii:
            assert key not in envelope["ciphertext"]

    def test_payload_size_grows_minimally(self, sample_payload_with_pii):

        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        # Overhead esperado: ~150 bytes (Fernet overhead + JSON envelope)
        original_size = len(json.dumps(sample_payload_with_pii).encode())
        envelope_size = len(json.dumps(envelope).encode())
        overhead = envelope_size - original_size
        # Aceita overhead de até 300 bytes (Fernet + envelope)
        assert overhead < 300, f"Overhead {overhead} bytes muito alto"

    def test_pii_field_preserved_in_decrypted(self, sample_payload_with_pii):
        envelope = encrypt_dlq_payload(sample_payload_with_pii, TEST_KEY)
        recovered = decrypt_dlq_payload(envelope, TEST_KEY)
        assert recovered["cpf"] == sample_payload_with_pii["cpf"]
        assert recovered["nome"] == sample_payload_with_pii["nome"]