import pytest
from brain.privacy_sanitizer import PrivacySanitizer

def test_cpf_masking():
    text = "O CPF do cliente é 123.456.789-00 ou 98765432100 para o inventário."
    sanitized = PrivacySanitizer.sanitize(text)
    assert "123.456.789-00" not in sanitized
    assert "98765432100" not in sanitized
    assert "123.***.***-00" in sanitized or "[CPF MASKED]" in sanitized

def test_email_masking():
    text = "Enviar certidões para cliente@email.com e cartorio@notarial.com.br"
    sanitized = PrivacySanitizer.sanitize(text)
    assert "cliente@email.com" not in sanitized
    assert "c***@email.com" in sanitized or "[EMAIL MASKED]" in sanitized

def test_phone_masking():
    text = "Telefone de contato: (11) 98765-4321 ou +55 21 91234-5678"
    sanitized = PrivacySanitizer.sanitize(text)
    assert "98765-4321" not in sanitized
    assert "[TELEFONE MASKED]" in sanitized

def test_pii_detection():
    assert PrivacySanitizer.contains_pii("Contato: maria@exemplo.com") is True
    assert PrivacySanitizer.contains_pii("Texto sem dados pessoais") is False
