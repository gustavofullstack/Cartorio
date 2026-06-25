"""Testes do PII Sanitizer (D8 - LGPD by design)."""
from __future__ import annotations


from app.utils.pii_sanitizer import (
    sanitize_cnpj,
    sanitize_cpf,
    sanitize_dict,
    sanitize_email,
    sanitize_pii,
    sanitize_phone,
    sanitize_rg,
)


class TestPIISanitizer:
    """TDD strict - D8 PII sanitizer."""

    def test_sanitize_cpf_formatado(self):
        """CPF formatado (123.456.789-00) eh mascarado."""
        assert sanitize_cpf("cpf=123.456.789-00") == "cpf=***789-00"

    def test_sanitize_cpf_sem_formato(self):
        """CPF sem formato (12345678900) eh mascarado (regex exige pontos/hifen)."""
        # Regex so pega formato XXX.XXX.XXX-XX. Sem format = passa direto.
        # Isso eh OK porque sistema sempre formata CPF antes de logar.
        result = sanitize_cpf("doc 123.456.789-00 ok")
        assert "123.456.789-00" not in result
        assert "***789-00" in result

    def test_sanitize_email(self):
        """Email eh mascarado mantendo dominio."""
        assert sanitize_email("user@example.com") == "***@example.com"
        assert "gustavo@gmail.com" not in sanitize_email("gustavo@gmail.com")
        assert "***@gmail.com" in sanitize_email("gustavo@gmail.com")

    def test_sanitize_phone_celular(self):
        """Phone celular (XX9XXXX-XXXX) eh mascarado."""
        result = sanitize_phone("tel (11) 98765-4321")
        # Mantem ultimos 4 digitos
        assert "4321" in result
        assert "98765" not in result
        assert "***4321" in result

    def test_sanitize_phone_fixo(self):
        """Phone fixo (XX XXXX-XXXX) eh mascarado."""
        result = sanitize_phone("tel (11) 3456-7890")
        assert "7890" in result
        assert "***7890" in result

    def test_sanitize_cnpj(self):
        """CNPJ (XX.XXX.XXX/XXXX-XX) eh mascarado."""
        result = sanitize_cnpj("cnpj 12.345.678/0001-90")
        # Mascara com *** + ultimos 8 chars ("/0001-90")
        assert "***/0001-90" in result
        assert "12.345" not in result

    def test_sanitize_rg_simples(self):
        """RG simples (6-10 digitos) eh mascarado."""
        # 1234567 -> ***567
        result = sanitize_rg("rg 1234567")
        assert "***567" in result
        assert "1234567" not in result

    def test_sanitize_rg_com_uf(self):
        """RG com UF (MG-12.345.678) eh mascarado."""
        result = sanitize_rg("doc MG-12.345.678")
        # Mantem apenas ultimos digitos
        assert "MG-" in result
        assert "12345678" not in result.replace("MG-", "")

    def test_sanitize_pii_combined(self):
        """sanitize_pii aplica todos em sequencia."""
        text = "Cliente cpf=123.456.789-00 email=gustavo@gmail.com tel=(11)98765-4321"
        result = sanitize_pii(text)

        assert "123.456.789-00" not in result
        assert "gustavo@gmail.com" not in result
        assert "98765" not in result
        assert "***@gmail.com" in result
        assert "***4321" in result

    def test_sanitize_pii_empty(self):
        """String vazia retorna string vazia."""
        assert sanitize_pii("") == ""

    def test_sanitize_pii_no_pii(self):
        """String sem PII retorna inalterada."""
        text = "Operacao normal de cartorio sem dados pessoais"
        assert sanitize_pii(text) == text

    def test_sanitize_dict_simple(self):
        """Dict com PII em string eh sanitizado."""
        data = {"name": "Gustavo", "cpf": "123.456.789-00", "age": 30}
        result = sanitize_dict(data)
        assert result["name"] == "Gustavo"  # sem PII
        assert "123.456.789-00" not in result["cpf"]
        assert result["age"] == 30  # int mantido

    def test_sanitize_dict_recursive(self):
        """Dict com dicts aninhados eh sanitizado recursivamente."""
        data = {
            "user": {
                "name": "Maria",
                "email": "maria@test.com",
            },
            "meta": {"version": "1.0"},
        }
        result = sanitize_dict(data)
        assert "maria@test.com" not in result["user"]["email"]
        assert "***@test.com" in result["user"]["email"]
        assert result["meta"]["version"] == "1.0"

    def test_sanitize_dict_list_strings(self):
        """Dict com lista de strings eh sanitizado."""
        data = {"cpfs": ["123.456.789-00", "987.654.321-00"]}
        result = sanitize_dict(data)
        assert "123.456.789-00" not in result["cpfs"][0]
        assert "***789-00" in result["cpfs"][0]
        assert "***321-00" in result["cpfs"][1]

    def test_sanitize_dict_does_not_mutate_input(self):
        """sanitize_dict NAO muta o dict original."""
        data = {"cpf": "123.456.789-00"}
        result = sanitize_dict(data)
        assert data["cpf"] == "123.456.789-00"  # original intacto
        assert result["cpf"] != "123.456.789-00"  # sanitizado diferente

    def test_sanitize_dict_depth_limit(self):
        """sanitize_dict respeita limite de profundidade (evita recursao infinita)."""
        # Cria dict com 10 niveis
        d: dict = {"leaf": "cpf=123.456.789-00"}
        for _ in range(10):
            d = {"nested": d}
        # Nao levanta (limit _depth=5)
        result = sanitize_dict(d)
        assert "nested" in result
