"""Testes para parsers do app/api/v1/telegram.py (cobertura SQUAD C).

Cobre:
1. _parse_date com "hoje", "amanha", "dd/mm/yyyy", invalido
2. _parse_time com "HH:MM" valido, invalido
3. _resumir_mensagens com 0/1/multiplas, saudoes, perguntas

Sobe cobertura telegram.py de 48% -> >=70%.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.api.v1.telegram import _parse_date, _parse_time, _resumir_mensagens


# =============================================================================
# _parse_date
# =============================================================================


def test_parse_date_hoje() -> None:
    """_parse_date('hoje') retorna data atual."""
    expected = datetime.now().strftime("%Y-%m-%d")
    assert _parse_date("hoje") == expected
    assert _parse_date("hj") == expected
    assert _parse_date("HOJE") == expected
    assert _parse_date(" Hoje ") == expected


def test_parse_date_amanha() -> None:
    """_parse_date('amanha') retorna amanha."""
    expected = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    assert _parse_date("amanha") == expected
    assert _parse_date("am") == expected
    # So funciona com a string EXATA "amanha" (sem acento) no codigo
    # _parse_date("Amanhã") pode ser None se ã nao estiver no set
    # Apenas verificamos a string canonica


def test_parse_date_formato_dd_mm_yyyy() -> None:
    """_parse_date('dd/mm/yyyy') retorna ISO date."""
    assert _parse_date("25/12/2026") == "2026-12-25"
    assert _parse_date("1/1/2026") == "2026-01-01"
    assert _parse_date("31/01/2027") == "2027-01-31"


def test_parse_date_formato_invalido_retorna_none() -> None:
    """_parse_date com texto sem pattern retorna None."""
    assert _parse_date("ontem") is None
    assert _parse_date("2026-12-25") is None  # formato ISO nao aceito
    assert _parse_date("25-12-2026") == "2026-12-25"  # parser aceita hifens
    assert _parse_date("abc/def/ghij") is None


def test_parse_date_data_invalida_calendario_retorna_none() -> None:
    """_parse_date com data impossivel (32/13) retorna None."""
    assert _parse_date("32/01/2026") is None
    assert _parse_date("01/13/2026") is None
    assert _parse_date("29/02/2026") is None  # 2026 nao eh bissexto


# =============================================================================
# _parse_time
# =============================================================================


def test_parse_time_formato_valido() -> None:
    """_parse_time('HH:MM') valido retorna normalizado."""
    assert _parse_time("14:30") == "14:30"
    assert _parse_time("09:05") == "09:05"
    assert _parse_time("0:00") == "00:00"  # normaliza com zero-pad
    assert _parse_time("23:59") == "23:59"


def test_parse_time_com_whitespace() -> None:
    """_parse_time aceita whitespace."""
    assert _parse_time("  10:00  ") == "10:00"


def test_parse_time_formato_invalido_retorna_none() -> None:
    """_parse_time com formato invalido retorna None."""
    assert _parse_time("25:00") is None  # hora > 23
    assert _parse_time("12:60") is None  # minuto > 59
    assert _parse_time("1230") is None  # sem :
    assert _parse_time("12:30:00") is None  # 3 partes
    assert _parse_time("ab:cd") is None


# =============================================================================
# _resumir_mensagens
# =============================================================================


def test_resumir_mensagens_lista_vazia() -> None:
    """_resumir_mensagens([]) retorna string vazia."""
    assert _resumir_mensagens([]) == ""


def test_resumir_mensagens_uma_mensagem() -> None:
    """_resumir_mensagens([unica]) retorna a propria mensagem."""
    assert _resumir_mensagens(["Oi tudo bem?"]) == "Oi tudo bem?"


def test_resumir_mensagens_saudacoes_predominantes() -> None:
    """Se >=50% das mensagens sao saudacoes, retorna 'Ola! Como posso ajudar?'."""
    msgs = ["oi", "ola", "bom dia"]
    result = _resumir_mensagens(msgs)
    assert "Ola" in result
    assert "ajudar" in result.lower()


def test_resumir_mensagens_com_perguntas() -> None:
    """Se tem perguntas, retorna count de mensagens + perguntas."""
    msgs = [
        "Oi?",
        "Quanto custa?",
        "Posso agendar?",
    ]
    result = _resumir_mensagens(msgs)
    assert "Recebi" in result
    assert "perguntas" in result.lower()


def test_resumir_mensagens_geral_ultima() -> None:
    """Caso geral: retorna count + ultima mensagem."""
    msgs = ["Primeira coisa", "Segunda coisa", "Terceira coisa final"]
    result = _resumir_mensagens(msgs)
    assert "3 mensagens" in result or "3" in result
    assert "Terceira coisa final" in result


def test_resumir_mensagens_deduplica_iguais() -> None:
    """Mensagens identicas (case-insensitive) sao deduplicadas."""
    msgs = ["oi", "OI", "Oi"]
    result = _resumir_mensagens(msgs)
    # Apenas 1 unica -> retorna ela
    assert result == "oi" or "Ola" in result  # pode ser saudacao ou a msg


# =============================================================================
# Sanity: regex usado nos parsers (Cobertura dos imports)
# =============================================================================


def test_telegram_importa_re_para_parsers() -> None:
    """Modulo telegram importa re (usado em _parse_date/_parse_time)."""
    import app.api.v1.telegram as tg

    # Verifica que 're' foi importado
    assert "re" in dir(tg)
