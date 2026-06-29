"""Testes do HMAC validation em evolution_ingest (A8).

A8: webhooks externos (Evolution API) enviam X-Signature: sha256=<hmac>.
Backend valida com EVOLUTION_WEBHOOK_SECRET.

- Webhook com signature valida = processado normalmente.
- Webhook com signature invalida = rejected.
- Webhook sem signature + secret configurado = rejected.
- Webhook sem signature + secret NAO configurado = aceita (dev mode).
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import hashlib  # noqa: E402
import hmac  # noqa: E402

import pytest  # noqa: E402

from app.services.evolution_ingest import (  # noqa: E402
    validate_evolution_signature,
)


def _compute_sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_validate_signature_valida(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signature valida + secret configurado = aceita."""
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "my-secret-123")
    body = b'{"event": "messages.upsert"}'
    sig = _compute_sig("my-secret-123", body)
    assert validate_evolution_signature(body, sig) is True


def test_validate_signature_invalida(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signature invalida = rejeita."""
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "my-secret-123")
    body = b'{"event": "messages.upsert"}'
    assert validate_evolution_signature(body, "invalida") is False


def test_validate_signature_sem_sig_com_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem signature + secret configurado = rejeita (fail-secure)."""
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "my-secret-123")
    body = b'{"event": "messages.upsert"}'
    assert validate_evolution_signature(body, None) is False
    assert validate_evolution_signature(body, "") is False


def test_validate_signature_sem_sig_sem_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem signature + sem secret configurado = aceita (dev mode)."""
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "")
    body = b'{"event": "messages.upsert"}'
    assert validate_evolution_signature(body, None) is True
    assert validate_evolution_signature(body, "") is True


def test_validate_signature_sha256_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signature no formato `sha256=<hex>` (estilo GitHub) eh aceita."""
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "my-secret-123")
    body = b'{"event": "messages.upsert"}'
    sig = "sha256=" + _compute_sig("my-secret-123", body)
    assert validate_evolution_signature(body, sig) is True


def test_validate_signature_timing_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comparacao usa hmac.compare_digest (timing-safe)."""
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "my-secret-123")
    body = b"x" * 100
    sig = _compute_sig("my-secret-123", body)
    # Substitui 1 char: deve falhar
    bad = "a" + sig[1:]
    assert validate_evolution_signature(body, bad) is False
