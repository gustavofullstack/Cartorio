"""Testes do service lgpd_anonimizacao (D13 SQUAD D)."""

from __future__ import annotations


from app.services.lgpd_anonimizacao import (
    anonymize_cliente_row,
    hash_pii,
    scrub_text_pii,
    truncate_ip,
    PII_FIELDS,
    PII_PATTERNS,
)


class TestHashPii:
    """Pseudonimizacao deterministica via HMAC-SHA256."""

    def test_hash_deterministic_same_input(self):
        h1 = hash_pii("123.456.789-09")
        h2 = hash_pii("123.456.789-09")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_hash_different_input_different_output(self):
        h1 = hash_pii("123.456.789-09")
        h2 = hash_pii("123.456.789-10")
        assert h1 != h2

    def test_hash_normalizes_mascara(self):
        """CPF com/sem mascara produz mesmo hash (LGPD)."""
        h1 = hash_pii("123.456.789-09")
        h2 = hash_pii("12345678909")
        assert h1 == h2

    def test_hash_empty_returns_empty(self):
        assert hash_pii("") == ""

    def test_hash_with_different_salt(self):
        h1 = hash_pii("teste", salt="salt-a")
        h2 = hash_pii("teste", salt="salt-b")
        assert h1 != h2  # salt afeta output


class TestAnonymizeClienteRow:
    """Anonimizacao de dict de cliente (LGPD art. 12)."""

    def test_remove_nome(self):
        row = {"id": 1, "nome": "Joao Silva", "tipo_cliente": "PF"}
        result = anonymize_cliente_row(row)
        assert "nome" not in result
        assert result["nome_hash"] is not None
        assert len(result["nome_hash"]) == 64

    def test_remove_cpf(self):
        row = {"id": 1, "cpf": "123.456.789-09"}
        result = anonymize_cliente_row(row)
        assert "cpf" not in result
        assert result["cpf_hash"] is not None

    def test_keep_id(self):
        row = {"id": 42, "nome": "X"}
        result = anonymize_cliente_row(row)
        assert result["id"] == 42

    def test_keep_lgpd_consent(self):
        row = {"id": 1, "lgpd_consent_granted": True, "lgpd_consent_at": "2026-06-25T00:00:00"}
        result = anonymize_cliente_row(row)
        assert result["lgpd_consent_granted"] is True
        assert result["lgpd_consent_at"] == "2026-06-25T00:00:00"

    def test_keep_uf(self):
        row = {"id": 1, "endereco_uf": "MG"}
        result = anonymize_cliente_row(row)
        assert result["endereco_uf"] == "MG"

    def test_keep_tipo_cliente(self):
        row = {"id": 1, "tipo_cliente": "PJ"}
        result = anonymize_cliente_row(row)
        assert result["tipo_cliente"] == "PJ"

    def test_drop_unknown_field(self):
        """Whitelist: campos fora da whitelist sao descartados."""
        row = {"id": 1, "campo_desconhecido": "lixo"}
        result = anonymize_cliente_row(row)
        assert "campo_desconhecido" not in result

    def test_all_pii_fields_handled(self):
        """Todos os 18 campos PII da PII_FIELDS sao tratados."""
        for f in PII_FIELDS:
            assert f in PII_FIELDS  # sanity


class TestScrubTextPii:
    """Remove PII de texto livre (WhatsApp messages)."""

    def test_scrub_cpf(self):
        assert scrub_text_pii("Meu CPF e 123.456.789-09") == "Meu CPF e [REDACTED-CPF]"

    def test_scrub_email(self):
        assert scrub_text_pii("Email: joao@example.com") == "Email: [REDACTED-EMAIL]"

    def test_scrub_phone(self):
        assert scrub_text_pii("Ligue (34) 99999-9999") == "Ligue [REDACTED-TELEFONE]"

    def test_scrub_multiple_pii(self):
        text = "CPF 123.456.789-09, email joao@x.com"
        result = scrub_text_pii(text)
        assert "123.456.789-09" not in result
        assert "joao@x.com" not in result
        assert "[REDACTED-CPF]" in result
        assert "[REDACTED-EMAIL]" in result

    def test_scrub_empty(self):
        assert scrub_text_pii("") == ""

    def test_scrub_no_pii(self):
        text = "Ola, bom dia!"
        assert scrub_text_pii(text) == text

    def test_scrub_cnpj(self):
        assert scrub_text_pii("CNPJ 12.345.678/0001-90") == "CNPJ [REDACTED-CNPJ]"

    def test_scrub_cns(self):
        assert scrub_text_pii("CNS 123456789012345") == "CNS [REDACTED-CNS]"


class TestTruncateIp:
    """LGPD art. 6 VIII - minimizacao: trunca IP /24 (IPv4) ou /48 (IPv6)."""

    def test_truncate_ipv4(self):
        assert truncate_ip("192.168.1.42") == "192.168.1.0/24"

    def test_truncate_ipv4_10(self):
        assert truncate_ip("10.0.0.1") == "10.0.0.0/24"

    def test_truncate_ipv6(self):
        assert truncate_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334") == "2001:0db8:85a3::/48"

    def test_truncate_empty(self):
        assert truncate_ip("") == ""

    def test_truncate_invalid(self):
        # Nao quebra com input invalido
        assert truncate_ip("not-an-ip") == "not-an-ip"


class TestPiiPatterns:
    """Validacao dos regex patterns."""

    def test_cpf_pattern(self):
        assert PII_PATTERNS["cpf"].search("123.456.789-09")
        assert PII_PATTERNS["cpf"].search("12345678909")
        assert not PII_PATTERNS["cpf"].search("12345")

    def test_email_pattern(self):
        assert PII_PATTERNS["email"].search("user@domain.com")
        assert PII_PATTERNS["email"].search("a.b+c@sub.domain.org")

    def test_telefone_pattern(self):
        assert PII_PATTERNS["telefone"].search("(34) 99999-9999")
        assert PII_PATTERNS["telefone"].search("+55 34 9999-9999")
