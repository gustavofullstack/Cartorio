"""Testes A11 — Log masker (MaskingFilter para LGPD art. 46)."""

from __future__ import annotations

import logging

from app.services.log_masker import MaskingFilter


def _make_record(msg: str) -> logging.LogRecord:
    """Helper: cria LogRecord com mensagem simples."""
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


def test_filter_mascara_cpf() -> None:
    """CPF em log eh mascarado."""
    f = MaskingFilter()
    rec = _make_record("cliente 123.456.789-00 logado")
    f.filter(rec)
    assert "[MASKED:cpf]" in rec.getMessage()
    assert "123.456.789-00" not in rec.getMessage()


def test_filter_mascara_email() -> None:
    """Email em log eh mascarado."""
    f = MaskingFilter()
    rec = _make_record("login: cliente@example.com sucesso")
    f.filter(rec)
    assert "[MASKED:email]" in rec.getMessage()
    assert "cliente@example.com" not in rec.getMessage()


def test_filter_preserva_mensagem_sem_pii() -> None:
    """Mensagem sem PII passa intacta."""
    f = MaskingFilter()
    rec = _make_record("operacao normal sem dados pessoais")
    f.filter(rec)
    assert rec.getMessage() == "operacao normal sem dados pessoais"


def test_filter_mascara_multiplos_pii() -> None:
    """Multiplos PII na mesma mensagem sao mascarados."""
    f = MaskingFilter()
    rec = _make_record("user=gustavo@example.com cpf=12345678900 phone=34999998888")
    f.filter(rec)
    msg = rec.getMessage()
    assert "[MASKED:email]" in msg
    assert "[MASKED:" in msg  # pelo menos 1 mask
    assert "gustavo@example.com" not in msg
    assert "12345678900" not in msg


def test_filter_nunca_quebra_logging() -> None:
    """Filter nao lanca excecao mesmo com input estranho."""
    f = MaskingFilter()
    # LogRecord com args problematicos
    rec = _make_record("test %s")
    rec.args = (object(),)  # type: ignore[arg-type]
    # Deve retornar True (pass) sem excecao
    assert f.filter(rec) is True


def test_filter_exception_path_caught() -> None:
    """Filter captura excecao em getMessage() e retorna True (linhas 60-62)."""
    f = MaskingFilter()
    # Criamos um LogRecord cujo getMessage() levanta excecao
    # Usando um formato que quebra com os args fornecidos
    rec = _make_record("test %d %s")
    rec.args = ("not-an-int",)  # type: ignore[arg-type]  # %d com string = TypeError
    # Deve capturar a excecao e retornar True (fail-open)
    assert f.filter(rec) is True


def test_filter_exception_path_with_non_string_msg() -> None:
    """Filter captura excecao quando record.msg nao eh string (linhas 60-62)."""
    f = MaskingFilter()
    # Se record.msg nao for string, getMessage() pode falhar
    rec = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=None,  # type: ignore[arg-type]
        args=(),
        exc_info=None,
    )
    assert f.filter(rec) is True
