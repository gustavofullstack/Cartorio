"""Encryption at-rest de PII (A9) + mask helpers.

A9: encripta colunas sensiveis (cpf, rg) no DB com Fernet (AES-128-CBC + HMAC).
Chave derivada de AUDIT_HMAC_KEY (32 bytes via SHA256).

LGPD L3 (art. 46): protecao contra acesso nao autorizado a dados pessoais
em repouso. Mesmo com acesso ao DB, PII so eh legivel com a chave de
criptografia (que vive em variavel de ambiente, NAO no codigo).

API:
- encrypt_pii(plaintext, key) -> str (base64 url-safe)
- decrypt_pii(ciphertext, key) -> str
- mask_cpf(plaintext) -> "***.***.***-**" (para logs/UI)
- mask_cnpj(plaintext) -> "**.***.***/****-**"
- mask_email(email) -> "j***@example.com"
- mask_nome(nome, empty=...) -> "G*** A***" (export / privacy policy)
- mask_email_display(email, empty=..., domain_mode=...) -> display-safe email
"""

from __future__ import annotations

import base64
import hashlib
from typing import Literal

from cryptography.fernet import Fernet


def _derive_fernet_key(key: str) -> bytes:
    """Deriva chave Fernet (32 bytes url-safe base64) a partir de qualquer string.

    Fernet exige chave de 32 bytes em formato url-safe base64.
    AUDIT_HMAC_KEY pode ter qualquer tamanho; derivamos via SHA256.
    """
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet(key: str) -> Fernet:
    return Fernet(_derive_fernet_key(key))


def encrypt_pii(plaintext: str, key: str) -> str:
    """Encripta PII com Fernet (AES-128-CBC + HMAC).

    Args:
        plaintext: Valor em texto puro (CPF, RG, etc).
        key: Chave mestra (em prod, vem de env var).

    Returns:
        Ciphertext em base64 url-safe (string ASCII).
    """
    fernet = _get_fernet(key)
    token = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_pii(ciphertext: str, key: str) -> str:
    """Decripta PII. Levanta InvalidToken se chave errada ou ciphertext invalido."""
    fernet = _get_fernet(key)
    plain = fernet.decrypt(ciphertext.encode("ascii"))
    return plain.decode("utf-8")


# ============================================================================
# Mask helpers (para logs e UI — LGPD by design)
# ============================================================================


def mask_cpf(cpf: str) -> str:
    """Mascara CPF preservando formato. `123.456.789-09` -> `***.***.***-**`."""
    if not cpf:
        return ""
    return "***.***.***-**"


def mask_cnpj(cnpj: str) -> str:
    """Mascara CNPJ preservando formato. `12.345.678/0001-90` -> `**.***.***/****-**`."""
    if not cnpj:
        return ""
    return "**.***.***/****-**"


def mask_email(email: str) -> str:
    """Mascara email preservando 1a letra e dominio. `joao@example.com` -> `j***@example.com`."""
    if not email:
        return ""
    if "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return "***@***"
    return f"{local[0]}***@{domain}"


def mask_nome(nome: str | None, *, empty: str = "[nome indisponivel]") -> str:
    """Mascara nome: 1a letra de cada parte + `***`.

    Shared by lgpd_export + lgpd_privacy_policy (G7.20.T2 DRY).
    `empty` customiza placeholder (export vs titular anonimizado).
    """
    if not nome or not str(nome).strip():
        return empty
    parts = str(nome).strip().split()
    masked = " ".join(f"{p[0]}***" if p else "" for p in parts)
    return masked or empty


def mask_email_display(
    email: str | None,
    *,
    empty: str = "[email indisponivel]",
    domain_mode: Literal["full", "tld"] = "full",
) -> str:
    """Mascara email para exibicao (export LGPD / privacy policy).

    - domain_mode='full': `fulano@dominio.com` -> `f***@dominio.com`
    - domain_mode='tld':  `fulano@sub.dominio.com` -> `f***@com` (LGPD D29 export)
    """
    if not email or "@" not in email:
        return empty
    local, _, domain = email.partition("@")
    if domain_mode == "tld":
        domain = domain.split(".")[-1] if domain else ""
    if not local:
        return f"***@{domain or '***'}"
    return f"{local[0]}***@{domain}"


__all__ = [
    "decrypt_pii",
    "encrypt_pii",
    "mask_cnpj",
    "mask_cpf",
    "mask_email",
    "mask_email_display",
    "mask_nome",
]
