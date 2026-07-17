"""G8.05.T3 — Testes chaves Redis com CPF/CNPJ hashed.

Modified by Gustavo Almeida — Wave 36.
"""

from __future__ import annotations

import pytest

from app.services.redis_doc_keys import (
    hash_document_for_cache,
    looks_like_raw_cnpj_in_key,
    looks_like_raw_cpf_in_key,
    normalize_document_digits,
    redis_doc_key,
)


def test_normalize() -> None:
    assert normalize_document_digits('529.982.247-25') == '52998224725'


def test_hash_stable() -> None:
    a = hash_document_for_cache('529.982.247-25', kind='cpf')
    b = hash_document_for_cache('52998224725', kind='cpf')
    assert a == b
    assert len(a) == 32
    assert '529' not in a


def test_hash_kind_namespace() -> None:
    cpf = hash_document_for_cache('52998224725', kind='cpf')
    cnpj = hash_document_for_cache('52998224725', kind='cnpj')
    assert cpf != cnpj


def test_redis_doc_key_no_raw_cpf() -> None:
    key = redis_doc_key('cache:lookup', '529.982.247-25', kind='cpf')
    assert key.startswith('cache:lookup:cpf:')
    assert not looks_like_raw_cpf_in_key(key)
    assert '52998224725' not in key


def test_looks_like_raw_cpf() -> None:
    assert looks_like_raw_cpf_in_key('cache:cpf:52998224725') is True
    assert looks_like_raw_cpf_in_key('cache:cpf:deadbeef') is False


def test_looks_like_raw_cnpj() -> None:
    assert looks_like_raw_cnpj_in_key('x:11222333000181') is True


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        hash_document_for_cache('')
