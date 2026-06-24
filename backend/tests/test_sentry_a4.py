"""Testes A4 — Sentry error tracking + PII scrubber (LGPD-by-design)."""
from __future__ import annotations

from app.services.sentry import scrub_pii


def test_scrub_pii_cpf_formatado() -> None:
    """CPF formatado 123.456.789-00 -> [MASKED:cpf]."""
    result = scrub_pii("CPF do cliente: 123.456.789-00")
    assert "[MASKED:cpf]" in result
    assert "123.456.789-00" not in result


def test_scrub_pii_cpf_sem_formatacao() -> None:
    """CPF sem formatacao 12345678900 -> [MASKED:cpf]."""
    result = scrub_pii("doc=12345678900")
    assert "[MASKED:cpf]" in result
    assert "12345678900" not in result


def test_scrub_pii_email() -> None:
    """Email eh masked."""
    result = scrub_pii("contato: cliente@example.com")
    assert "[MASKED:email]" in result
    assert "cliente@example.com" not in result


def test_scrub_pii_telefone_br() -> None:
    """Telefone BR com DDD eh masked."""
    result = scrub_pii("ligar para (34) 99999-8888")
    assert "[MASKED:phone_br]" in result
    assert "(34) 99999-8888" not in result


def test_scrub_pii_dict_recursivo() -> None:
    """Scrub recursivo em dicts."""
    payload = {
        "user": "gustavo",
        "doc": {"cpf": "123.456.789-00", "obs": "cliente OK"},
        "items": ["abc@def.com", "lalala"],
    }
    result = scrub_pii(payload)
    assert result["user"] == "gustavo"
    assert "[MASKED:cpf]" in result["doc"]["cpf"]
    assert "123.456.789-00" not in result["doc"]["cpf"]
    assert "[MASKED:email]" in result["items"][0]


def test_scrub_pii_lista() -> None:
    """Scrub em listas."""
    result = scrub_pii(["gustavo@example.com", "nenhum pii aqui", "11999998888"])
    assert "[MASKED:email]" in result[0]
    assert result[1] == "nenhum pii aqui"
    # 11999998888 (11 digitos) = CPF pattern (11) ou CNH (11). Vira masked.
    assert "[MASKED:" in result[2]


def test_scrub_pii_preserva_estrutura() -> None:
    """Tipo do objeto eh preservado (dict -> dict, list -> list)."""
    d = {"a": 1, "b": ["x", "y"]}
    result = scrub_pii(d)
    assert isinstance(result, dict)
    assert isinstance(result["b"], list)
    assert result["a"] == 1


def test_scrub_pii_nao_altera_sem_pii() -> None:
    """String sem PII retorna identica."""
    text = "operacao concluida com sucesso, protocolo 12345"
    assert scrub_pii(text) == text
