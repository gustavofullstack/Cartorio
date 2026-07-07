"""Testes para anonimização PII (LGPD Art. 12)."""

from app.services.lgpd.anonymize import (
    anonymize_cpf,
    anonymize_email,
    anonymize_phone,
    anonymize,
    anonymize_record,
    hash_pii,
)


def test_anonymize_cpf_formato():
    assert anonymize_cpf("123.456.789-09") == "***.***.***-09"


def test_anonymize_cpf_invalido():
    assert anonymize_cpf("123") == "***"


def test_anonymize_email():
    assert anonymize_email("fulano@example.com") == "f***@example.com"


def test_anonymize_email_sem_local():
    assert anonymize_email("@example.com") == "***@example.com"


def test_anonymize_phone():
    result = anonymize_phone("(34) 99876-5432")
    assert "5432" in result
    assert result.startswith("(**)")


def test_anonymize_auto_detect_cpf():
    assert anonymize("123.456.789-09") == "***.***.***-09"


def test_anonymize_auto_detect_email():
    assert anonymize("test@example.com") == "t***@example.com"


def test_anonymize_auto_detect_desconhecido():
    assert anonymize("hello world") == "***"


def test_anonymize_record():
    rec = {"cpf": "123.456.789-09", "nome": "Fulano", "idade": 30}
    out = anonymize_record(rec)
    assert out["cpf"] == "***.***.***-09"
    assert out["nome"] == "Fulano"
    assert out["idade"] == 30


def test_hash_pii_deterministic():
    assert hash_pii("123") == hash_pii("123")
    assert hash_pii("123") != hash_pii("456")


def test_hash_pii_sha256_length():
    assert len(hash_pii("test")) == 64
