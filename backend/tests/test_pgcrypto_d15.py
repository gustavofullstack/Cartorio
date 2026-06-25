"""Tests for D15 pgcrypto encryption at-rest.

TDD: RED → GREEN → COMMIT

Requires PostgreSQL (pgcrypto is a PG extension).
Skipped when running against SQLite (CI/local default).

Tests:
1. pgcrypto extension exists
2. encrypt_pii function exists
3. decrypt_pii function exists
4. encrypt_pii + decrypt_pii roundtrip
5. encrypt_pii handles NULL
6. encrypt_pii handles empty string
7. cpf_encrypted column exists in clientes
8. rg_encrypted column exists in clientes
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

_is_postgres = "postgresql" in os.environ.get("DATABASE_URL", "sqlite:///:memory:")


@pytest.mark.skipif(not _is_postgres, reason="pgcrypto requires PostgreSQL")
class TestPgcryptoD15:
    """D15 — pgcrypto encryption at-rest tests."""

    def test_pgcrypto_extension_exists(self, db_session: Session) -> None:
        """Test 1: pgcrypto extension is installed."""
        result = db_session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'")
        ).scalar()
        assert result == 1, "pgcrypto extension not found"

    def test_encrypt_pii_function_exists(self, db_session: Session) -> None:
        """Test 2: encrypt_pii function exists."""
        result = db_session.execute(
            text("SELECT 1 FROM pg_proc WHERE proname = 'encrypt_pii'")
        ).scalar()
        assert result == 1, "encrypt_pii function not found"

    def test_decrypt_pii_function_exists(self, db_session: Session) -> None:
        """Test 3: decrypt_pii function exists."""
        result = db_session.execute(
            text("SELECT 1 FROM pg_proc WHERE proname = 'decrypt_pii'")
        ).scalar()
        assert result == 1, "decrypt_pii function not found"

    def test_encrypt_decrypt_roundtrip(self, db_session: Session) -> None:
        """Test 4: encrypt_pii + decrypt_pii roundtrip."""
        db_session.execute(text("SET app.pii_key = 'test-key-32-chars-long-for-aes'"))
        plaintext = "123.456.789-00"
        result = db_session.execute(
            text("SELECT decrypt_pii(encrypt_pii(:plaintext))"),
            {"plaintext": plaintext},
        ).scalar()
        assert result == plaintext, f"Roundtrip failed: {result}"

    def test_encrypt_pii_handles_null(self, db_session: Session) -> None:
        """Test 5: encrypt_pii handles NULL input."""
        result = db_session.execute(text("SELECT encrypt_pii(NULL)")).scalar()
        assert result is None, f"Expected NULL, got {result}"

    def test_encrypt_pii_handles_empty(self, db_session: Session) -> None:
        """Test 6: encrypt_pii handles empty string."""
        result = db_session.execute(text("SELECT encrypt_pii('')")).scalar()
        assert result is None, f"Expected NULL for empty, got {result}"

    def test_cpf_encrypted_column_exists(self, db_session: Session) -> None:
        """Test 7: cpf_encrypted column exists in clientes."""
        result = db_session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'clientes' AND column_name = 'cpf_encrypted'"
            )
        ).scalar()
        assert result == 1, "cpf_encrypted column not found"

    def test_rg_encrypted_column_exists(self, db_session: Session) -> None:
        """Test 8: rg_encrypted column exists in clientes."""
        result = db_session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'clientes' AND column_name = 'rg_encrypted'"
            )
        ).scalar()
        assert result == 1, "rg_encrypted column not found"
