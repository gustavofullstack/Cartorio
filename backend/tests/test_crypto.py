"""Testes do encryption at-rest (A9) + mask helpers.

A9: encryption Fernet de PII (cpf, rg, etc) com chave derivada de AUDIT_HMAC_KEY.
Helpers: mask_cpf -> '***.***.***-**', mask_email -> 'g***@example.com'.

- encrypt + decrypt = roundtrip
- encrypt com chave diferente = falha decrypt
- mask_cpf preserva formato
- mask_email preserva dominio e primeira letra
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

import pytest  # noqa: E402

from app.services.crypto import (  # noqa: E402
    decrypt_pii,
    encrypt_pii,
    mask_cpf,
    mask_email,
    mask_cnpj,
)


KEY = "a" * 64
KEY2 = "b" * 64


# ============================================================================
# encrypt_pii / decrypt_pii (Fernet)
# ============================================================================


def test_encrypt_decrypt_roundtrip() -> None:
    """encrypt + decrypt com mesma chave = valor original."""
    plain = "123.456.789-09"
    cipher = encrypt_pii(plain, KEY)
    assert cipher != plain
    assert decrypt_pii(cipher, KEY) == plain


def test_encrypt_produz_ciphertext_diferente_para_mesmo_plaintext() -> None:
    """Fernet usa nonce aleatorio -> mesmo plaintext gera ciphertexts diferentes."""
    plain = "123.456.789-09"
    c1 = encrypt_pii(plain, KEY)
    c2 = encrypt_pii(plain, KEY)
    assert c1 != c2  # Fernet tem IV aleatorio
    assert decrypt_pii(c1, KEY) == plain
    assert decrypt_pii(c2, KEY) == plain


def test_encrypt_com_chave_diferente_falha_decrypt() -> None:
    """encrypt com KEY, decrypt com KEY2 = levanta exception."""
    plain = "123.456.789-09"
    cipher = encrypt_pii(plain, KEY)
    with pytest.raises(Exception):  # InvalidToken
        decrypt_pii(cipher, KEY2)


def test_encrypt_retorna_string_ascii() -> None:
    """Ciphertext Fernet eh base64 url-safe ASCII."""
    cipher = encrypt_pii("test", KEY)
    assert isinstance(cipher, str)
    cipher.encode("ascii")  # NAO levanta


# ============================================================================
# mask_cpf
# ============================================================================


def test_mask_cpf_formato_completo() -> None:
    """CPF formatado 123.456.789-09 -> ***.***.***-**"""
    assert mask_cpf("123.456.789-09") == "***.***.***-**"


def test_mask_cpf_sem_formatacao() -> None:
    """CPF sem formatacao 12345678909 -> ***.***.***-**"""
    assert mask_cpf("12345678909") == "***.***.***-**"


def test_mask_cpf_vazio() -> None:
    """CPF vazio retorna string vazia."""
    assert mask_cpf("") == ""


# ============================================================================
# mask_cnpj
# ============================================================================


def test_mask_cnpj_formato_completo() -> None:
    """CNPJ formatado 12.345.678/0001-90 -> **.***.***/****-**"""
    assert mask_cnpj("12.345.678/0001-90") == "**.***.***/****-**"


def test_mask_cnpj_sem_formatacao() -> None:
    """CNPJ sem formatacao 12345678000190 -> **.***.***/****-**"""
    assert mask_cnpj("12345678000190") == "**.***.***/****-**"


# ============================================================================
# mask_email
# ============================================================================


def test_mask_email_preserva_dominio_e_primeira_letra() -> None:
    """Email joao@example.com -> j***@example.com"""
    assert mask_email("joao@example.com") == "j***@example.com"


def test_mask_email_uma_letra() -> None:
    """Email 'a@b.com' -> 'a***@b.com'"""
    assert mask_email("a@b.com") == "a***@b.com"


def test_mask_email_sem_arroba() -> None:
    """Email sem @ retorna mask generico."""
    assert mask_email("notanemail") == "***"


def test_mask_email_vazio() -> None:
    """Email vazio retorna string vazia."""
    assert mask_email("") == ""
