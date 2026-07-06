"""Testes para app.services.lgpd.* — opposition, portability, anonymize.

Cobre stubs com comportamento determinístico (LGPD Art. 12, 18).
"""

from __future__ import annotations

import json
import pytest


class TestOpposition:
    """Testes para lgpd/opposition.py."""

    def test_register_opposition_retorna_dict(self) -> None:
        """register_opposition retorna dict com campos obrigatórios."""
        from app.services.lgpd.opposition import register_opposition

        result = register_opposition(cliente_id=1, scope="marketing")
        assert result["cliente_id"] == 1
        assert result["scope"] == "marketing"
        assert result["registered"] is True
        assert "lgpd_article" in result
        assert "effect" in result

    def test_register_opposition_scope_all(self) -> None:
        """Scope 'all' é aceito."""
        from app.services.lgpd.opposition import register_opposition

        result = register_opposition(cliente_id=99, scope="all")
        assert result["scope"] == "all"

    def test_check_opposition_retorna_false_default(self) -> None:
        """check_opposition retorna False (stub — sem DB real)."""
        from app.services.lgpd.opposition import check_opposition

        assert check_opposition(cliente_id=1, scope="marketing") is False

    def test_check_opposition_retorna_bool(self) -> None:
        """check_opposition sempre retorna bool."""
        from app.services.lgpd.opposition import check_opposition

        result = check_opposition(cliente_id=42, scope="decisao_automatizada")
        assert isinstance(result, bool)


class TestPortability:
    """Testes para lgpd/portability.py."""

    def test_export_cliente_data_retorna_dict(self) -> None:
        """export_cliente_data retorna dict com campos obrigatórios."""
        from app.services.lgpd.portability import export_cliente_data

        result = export_cliente_data(cliente_id=1)
        assert result["cliente_id"] == 1
        assert "dados_pessoais" in result
        assert "conversas" in result
        assert "protocolos" in result
        assert "documentos" in result
        assert "lgpd_article" in result
        assert result["formato"] == "JSON"

    def test_export_cliente_data_versao_schema(self) -> None:
        """versao_schema presente e é string."""
        from app.services.lgpd.portability import export_cliente_data

        result = export_cliente_data(cliente_id=99)
        assert isinstance(result["versao_schema"], str)

    def test_export_to_json_retorna_string_json(self) -> None:
        """export_to_json retorna string JSON válido."""
        from app.services.lgpd.portability import export_to_json

        data = {"cliente_id": 1, "nome": "Fulano"}
        json_str = export_to_json(data)
        parsed = json.loads(json_str)
        assert parsed["cliente_id"] == 1
        assert parsed["nome"] == "Fulano"

    def test_export_to_json_utf8_caracteres(self) -> None:
        """export_to_json preserva caracteres UTF-8 (nomes brasileiros)."""
        from app.services.lgpd.portability import export_to_json

        data = {"nome": "Antônio José Gonçalves"}
        json_str = export_to_json(data)
        assert "Antônio" in json_str


class TestAnonymize:
    """Testes para lgpd/anonymize.py."""

    def test_anonymize_cpf_formato_canonico(self) -> None:
        """anonymize_cpf mascara preservando últimos 2 dígitos."""
        from app.services.lgpd.anonymize import anonymize_cpf

        result = anonymize_cpf("123.456.789-09")
        assert result == "***.***.***-09"

    def test_anonymize_cpf_sem_formatacao(self) -> None:
        """anonymize_cpf aceita CPF sem formatação."""
        from app.services.lgpd.anonymize import anonymize_cpf

        result = anonymize_cpf("12345678909")
        assert result.startswith("***.***.***-")
        assert result.endswith("09")

    def test_anonymize_cpf_vazio(self) -> None:
        """anonymize_cpf string vazia retorna string vazia."""
        from app.services.lgpd.anonymize import anonymize_cpf

        assert anonymize_cpf("") == ""

    def test_anonymize_cpf_invalido(self) -> None:
        """anonymize_cpf inválido retorna '***'."""
        from app.services.lgpd.anonymize import anonymize_cpf

        assert anonymize_cpf("123") == "***"

    def test_anonymize_email_preserva_dominio(self) -> None:
        """anonymize_email preserva domínio, mascara local."""
        from app.services.lgpd.anonymize import anonymize_email

        result = anonymize_email("fulano@example.com")
        assert result.endswith("@example.com")
        assert result.startswith("f")

    def test_anonymize_email_sem_arroba(self) -> None:
        """anonymize_email sem @ retorna '***'."""
        from app.services.lgpd.anonymize import anonymize_email

        assert anonymize_email("nao-eh-email") == "***"

    def test_anonymize_email_vazio(self) -> None:
        """anonymize_email vazio retorna '***'."""
        from app.services.lgpd.anonymize import anonymize_email

        assert anonymize_email("") == "***"

    def test_anonymize_phone_preserva_ultimos_4(self) -> None:
        """anonymize_phone preserva últimos 4 dígitos."""
        from app.services.lgpd.anonymize import anonymize_phone

        result = anonymize_phone("(34) 99876-5432")
        assert "5432" in result

    def test_anonymize_phone_curto(self) -> None:
        """anonymize_phone com < 8 dígitos retorna '***'."""
        from app.services.lgpd.anonymize import anonymize_phone

        assert anonymize_phone("123") == "***"

    def test_anonymize_auto_detecta_email(self) -> None:
        """anonymize() auto-detecta email."""
        from app.services.lgpd.anonymize import anonymize

        result = anonymize("fulano@test.com")
        assert "@test.com" in result

    def test_anonymize_auto_detecta_cpf(self) -> None:
        """anonymize() auto-detecta CPF."""
        from app.services.lgpd.anonymize import anonymize

        result = anonymize("123.456.789-09")
        assert "***" in result

    def test_anonymize_vazio(self) -> None:
        """anonymize() string vazia retorna string vazia."""
        from app.services.lgpd.anonymize import anonymize

        assert anonymize("") == ""

    def test_anonymize_desconhecido_retorna_asteriscos(self) -> None:
        """anonymize() valor desconhecido retorna '***'."""
        from app.services.lgpd.anonymize import anonymize

        assert anonymize("valor-sem-padrao-conhecido") == "***"

    def test_anonymize_record_mascara_campos_pii(self) -> None:
        """anonymize_record mascara campos PII conhecidos."""
        from app.services.lgpd.anonymize import anonymize_record

        record = {
            "cpf": "123.456.789-09",
            "email": "fulano@test.com",
            "nome": "Fulano",
            "protocolo": "P-12345",
        }
        result = anonymize_record(record)
        assert "***" in result["cpf"]
        assert result["nome"] == "Fulano"  # não mascarado
        assert result["protocolo"] == "P-12345"  # não mascarado

    def test_hash_pii_retorna_sha256(self) -> None:
        """hash_pii retorna string SHA256 hex."""
        from app.services.lgpd.anonymize import hash_pii

        result = hash_pii("12345678900")
        assert len(result) == 64
        assert result.isalnum()

    def test_hash_pii_deterministico(self) -> None:
        """hash_pii mesmo input → mesmo output (determinístico)."""
        from app.services.lgpd.anonymize import hash_pii

        assert hash_pii("abc") == hash_pii("abc")

    def test_hash_pii_diferente_para_entradas_diferentes(self) -> None:
        """hash_pii inputs diferentes → outputs diferentes."""
        from app.services.lgpd.anonymize import hash_pii

        assert hash_pii("cpf1") != hash_pii("cpf2")
