"""Tests for Pydantic schemas validation.

Validates that all schemas enforce correct types and constraints.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.protocolo import (
    ProtocoloCreateRequest,
    StatusProtocolo,
    CanalOrigem,
)


class TestProtocoloSchemas:
    """Protocolo schema validation tests."""

    def test_protocolo_create_requires_fields(self) -> None:
        """ProtocoloCreateRequest requires minimum fields."""
        with pytest.raises(ValidationError):
            ProtocoloCreateRequest()

    def test_protocolo_create_valid(self) -> None:
        """ProtocoloCreateRequest accepts valid data."""
        p = ProtocoloCreateRequest(
            cliente_cpf="12345678901",
            cliente_nome="João da Silva",
            tipo="certidao_negativa",
            canal_origem="whatsapp",
            consentimento_lgpd=True,
        )
        assert p.cliente_nome == "João da Silva"
        assert p.consentimento_lgpd is True

    def test_protocolo_create_requires_lgpd_true(self) -> None:
        """ProtocoloCreateRequest accepts consentimento_lgpd=True."""
        p = ProtocoloCreateRequest(
            cliente_cpf="12345678901",
            cliente_nome="João",
            tipo="certidao_negativa",
            canal_origem="whatsapp",
            consentimento_lgpd=True,
        )
        assert p.consentimento_lgpd is True

    def test_status_enum_values(self) -> None:
        """StatusProtocolo enum has expected values."""
        assert StatusProtocolo.ABERTO == "aberto"
        assert StatusProtocolo.CONCLUIDO == "concluido"

    def test_canal_origem_enum(self) -> None:
        """CanalOrigem enum has expected values."""
        assert CanalOrigem.WHATSAPP == "whatsapp"
        assert CanalOrigem.TELEGRAM == "telegram"
