"""Tests for LogMasker (A11 - PII masking in log output).

Cobre linhas nao testadas do MaskingFilter.
"""

from __future__ import annotations

import logging


from app.services.log_masker import MaskingFilter, _scrub_string


class TestScrubString:
    """Testes unitarios de _scrub_string."""

    def test_scrub_cpf(self) -> None:
        """CPF em texto e' substituido."""
        result = _scrub_string("Meu CPF e 123.456.789-09")
        assert "[MASKED:cpf]" in result
        assert "123.456.789-09" not in result

    def test_scrub_email(self) -> None:
        """Email e' substituido."""
        result = _scrub_string("email: joao@example.com")
        assert "[MASKED:email]" in result
        assert "joao@example.com" not in result

    def test_sem_pii_permanece(self) -> None:
        """String sem PII nao e' alterada."""
        result = _scrub_string("Ola, tudo bem?")
        assert result == "Ola, tudo bem?"

    def test_scrub_financeiro_cliente(self) -> None:
        """Valores financeiros atrelados ao nome de clientes são mascarados (G8.20.T3)."""
        # Caso 1: cliente com hífen e valor decimal
        res1 = _scrub_string("cliente: Joao da Silva - valor: 1500.50")
        assert "[MASKED:financeiro_cliente]" in res1
        assert "1500.50" not in res1
        assert "Joao da Silva" not in res1

        # Caso 2: português natural com R$
        res2 = _scrub_string("cliente João da Silva no valor de R$ 1.500,00")
        assert "[MASKED:financeiro_cliente]" in res2
        assert "1.500,00" not in res2
        assert "João da Silva" not in res2

        # Caso 3: chaves com vírgula e total
        res3 = _scrub_string("nome=Maria Souza, total=125.00")
        assert "[MASKED:financeiro_cliente]" in res3
        assert "125.00" not in res3
        assert "Maria Souza" not in res3


class TestMaskingFilter:
    """Testes do MaskingFilter de logging."""

    def test_filter_mascara_cpf(self) -> None:
        """Filtro mascara CPF em mensagem de log."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="CPF do cliente: 123.456.789-09",
            args=(),
            exc_info=None,
        )
        filtro = MaskingFilter()
        assert filtro.filter(record) is True  # sempre retorna True
        assert "[MASKED:cpf]" in record.msg
        assert "123.456.789-09" not in record.msg

    def test_filter_mascara_cnpj(self) -> None:
        """Filtro mascara CNPJ."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="CNPJ: 12.345.678/0001-90",
            args=(),
            exc_info=None,
        )
        filtro = MaskingFilter()
        filtro.filter(record)
        assert "[MASKED:cnpj]" in record.msg

    def test_filter_sem_pii_inalterado(self) -> None:
        """Mensagem sem PII permanece igual."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Sistema operacional normal",
            args=(),
            exc_info=None,
        )
        filtro = MaskingFilter()
        filtro.filter(record)
        assert record.msg == "Sistema operacional normal"

    def test_filter_nao_quebra_logging(self) -> None:
        """Filtro nunca levanta excecao (fail-open)."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="teste %s",
            args=("valor",),
            exc_info=None,
        )
        filtro = MaskingFilter()
        # Deve executar sem excecao mesmo com formato diferente
        result = filtro.filter(record)
        assert result is True
