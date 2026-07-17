"""G8.05.T3 — Chaves Redis baseadas em CPF/CNPJ criptografadas/hashed.

Nunca usar CPF/CNPJ raw como parte de chave de cache.
Usa HMAC-SHA256 com pepper configurável (settings.pii_hash_pepper ou
fallback determinístico de desenvolvimento — NÃO usar em prod sem pepper).

LGPD Art.46 — proteção por design.

Modified by Gustavo Almeida — Wave 36.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from typing import Final

_DIGITS_RE = re.compile(r'\D+')

# Pepper default só para testes/dev local — prod DEVE setar PII_HASH_PEPPER
_DEFAULT_DEV_PEPPER: Final[str] = 'cartorio-dev-pepper-not-for-prod'


def normalize_document_digits(value: str) -> str:
    """Mantém só dígitos."""
    return _DIGITS_RE.sub('', value or '')


def _pepper() -> str:
    try:
        from app.config import settings

        pepper = getattr(settings, 'pii_hash_pepper', None) or getattr(
            settings, 'audit_hmac_key', None
        )
        if pepper:
            return str(pepper)
    except Exception:  # noqa: BLE001
        pass
    return _DEFAULT_DEV_PEPPER


def hash_document_for_cache(document: str, *, kind: str = 'cpf') -> str:
    """HMAC-SHA256 hex truncado (32 chars) para uso em chave Redis.

    Args:
        document: CPF/CNPJ (com ou sem máscara)
        kind: 'cpf' | 'cnpj' | 'doc' (só namespace na chave)

    Returns:
        string hex 32 chars (sem o documento original)
    """
    digits = normalize_document_digits(document)
    if not digits:
        raise ValueError('document required')
    digest = hmac.new(
        _pepper().encode('utf-8'),
        f'{kind}:{digits}'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return digest[:32]


def redis_doc_key(namespace: str, document: str, *, kind: str = 'cpf') -> str:
    """Monta chave Redis segura: `{namespace}:{kind}:{hash}`.

    Exemplo: `cache:lookup:cpf:a1b2...`
    """
    ns = (namespace or 'cache').strip(':')
    h = hash_document_for_cache(document, kind=kind)
    return f'{ns}:{kind}:{h}'


def looks_like_raw_cpf_in_key(key: str) -> bool:
    """Heurística de auditoria: detecta 11 dígitos contíguos em chave."""
    return bool(re.search(r'(?<!\d)\d{11}(?!\d)', key or ''))


def looks_like_raw_cnpj_in_key(key: str) -> bool:
    return bool(re.search(r'(?<!\d)\d{14}(?!\d)', key or ''))


__all__ = [
    'hash_document_for_cache',
    'looks_like_raw_cnpj_in_key',
    'looks_like_raw_cpf_in_key',
    'normalize_document_digits',
    'redis_doc_key',
]
