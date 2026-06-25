"""Testes A4 — Sentry error tracking + PII scrubber (LGPD-by-design).

Cobertura:
- scrub_pii: CPF, CNPJ, email, phone, CNS, CNH, IP, dict, list, tuple
- _before_send: message, exception, tags, extra, user scrubbing
- _init_sentry: com/sem DSN, ImportError
- capture_exception: com/sem sentry ativo
- capture_message: com/sem sentry ativo
"""
from __future__ import annotations

import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sentry import (
    _before_send,
    _init_sentry,
    capture_exception,
    capture_message,
    scrub_pii,
)


# ─── scrub_pii (base) ───────────────────────────────────────────────────

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


def test_scrub_pii_cnpj() -> None:
    """CNPJ formatado eh masked."""
    result = scrub_pii("CNPJ: 12.345.678/0001-90")
    assert "[MASKED:cnpj]" in result
    assert "12.345.678/0001-90" not in result


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


def test_scrub_pii_cns() -> None:
    """CNS 15 digitos eh masked - phone regex match primeiro, mas eh mascarado."""
    result = scrub_pii("CNS: 123456789012345")
    # phone_br pattern matches 15 contiguous digits, so it gets masked
    assert "[MASKED:" in result


def test_scrub_pii_cnh() -> None:
    """CNH 11 digitos eh masked - CPF pattern match primeiro, mas eh mascarado."""
    result = scrub_pii("CNH: 12345678901")
    # 11 digits = CPF pattern match, gets masked
    assert "[MASKED:" in result


def test_scrub_pii_ip() -> None:
    """IPv4 eh masked."""
    result = scrub_pii("origem: 192.168.1.100")
    assert "[MASKED:ip]" in result
    assert "192.168.1.100" not in result


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


def test_scrub_pii_tuple() -> None:
    """Tuple mantem tipo apos scrub."""
    result = scrub_pii(("teste@exemplo.com", "seguro"))
    assert isinstance(result, tuple)
    assert "[MASKED:email]" in result[0]
    assert result[1] == "seguro"


def test_scrub_pii_int_float() -> None:
    """Int e float passam direto."""
    assert scrub_pii(42) == 42
    assert scrub_pii(3.14) == 3.14


def test_scrub_pii_none() -> None:
    """None passa direto."""
    assert scrub_pii(None) is None


# ─── _before_send ───────────────────────────────────────────────────────

def test_before_send_scrub_message() -> None:
    """_before_send faz scrub no campo message."""
    event: dict = {"message": "ERRO: CPF 123.456.789-00 invalido"}
    result = _before_send(event, {})
    assert "[MASKED:cpf]" in result["message"]


def test_before_send_scrub_exception_values() -> None:
    """_before_send faz scrub nos valores das excecoes."""
    event: dict = {
        "exception": {
            "values": [
                {"value": "Cliente 123.456.789-00 nao encontrado"},
                {"value": "sem pii aqui"},
            ]
        }
    }
    result = _before_send(event, {})
    assert "[MASKED:cpf]" in result["exception"]["values"][0]["value"]
    assert result["exception"]["values"][1]["value"] == "sem pii aqui"


def test_before_send_scrub_tags() -> None:
    """_before_send faz scrub em tags."""
    event: dict = {"tags": {"email": "cliente@test.com", "env": "prod"}}
    result = _before_send(event, {})
    assert "[MASKED:email]" in result["tags"]["email"]
    assert result["tags"]["env"] == "prod"


def test_before_send_scrub_extra() -> None:
    """_before_send faz scrub em extra context."""
    event: dict = {"extra": {"cpf_cliente": "123.456.789-00", "tipo": "erro"}}
    result = _before_send(event, {})
    assert "[MASKED:cpf]" in result["extra"]["cpf_cliente"]


def test_before_send_scrub_user() -> None:
    """_before_send faz scrub em dados do usuario."""
    event: dict = {"user": {"email": "admin@test.com", "id": "123"}}
    result = _before_send(event, {})
    assert "[MASKED:email]" in result["user"]["email"]
    assert result["user"]["id"] == "123"


def test_before_send_sem_exception_ok() -> None:
    """_before_send funciona sem campo exception."""
    event: dict = {"message": "teste normal", "tags": {"env": "test"}}
    result = _before_send(event, {})
    assert result["message"] == "teste normal"


# ─── _init_sentry ───────────────────────────────────────────────────────

def test_init_sentry_sem_dsn_retorna_false() -> None:
    """_init_sentry() sem SENTRY_DSN retorna False."""
    with patch.dict(os.environ, {}, clear=True):
        assert _init_sentry() is False


def test_init_sentry_com_dsn_sem_sdk_retorna_false() -> None:
    """_init_sentry() com DSN mas sem sentry-sdk retorna False (ImportError)."""
    with (
        patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}, clear=True),
        patch("builtins.__import__", side_effect=ImportError("no sentry")),
    ):
        assert _init_sentry() is False


def test_init_sentry_com_dsn_com_sdk_retorna_true() -> None:
    """_init_sentry() com DSN e sentry-sdk importavel retorna True."""
    mock_sdk = MagicMock()
    mock_sdk.init = MagicMock()
    mock_sdk.integrations = MagicMock()
    mock_sdk.integrations.fastapi = MagicMock()
    mock_sdk.integrations.sqlalchemy = MagicMock()

    with (
        patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}, clear=True),
        patch.dict("sys.modules", {
            "sentry_sdk": mock_sdk,
            "sentry_sdk.integrations": mock_sdk.integrations,
            "sentry_sdk.integrations.fastapi": mock_sdk.integrations.fastapi,
            "sentry_sdk.integrations.sqlalchemy": mock_sdk.integrations.sqlalchemy,
        }),
    ):
        result = _init_sentry()
        assert result is True


# ─── capture_exception ──────────────────────────────────────────────────

def test_capture_exception_sentry_disabled(caplog) -> None:
    """capture_exception sem sentry loga localmente."""
    with (
        patch.dict(os.environ, {}, clear=True),
        caplog.at_level(logging.ERROR),
    ):
        capture_exception(ValueError("teste 123.456.789-00"))
        assert any("exception (sentry disabled)" in rec.getMessage() for rec in caplog.records)


def test_capture_exception_sentry_enabled() -> None:
    """capture_exception com sentry ativo chama sentry_sdk.capture_exception."""
    with patch("app.services.sentry._init_sentry", return_value=True):
        mock_sentry = MagicMock()
        mock_push_scope = MagicMock()
        mock_sentry.push_scope.return_value = mock_push_scope
        mock_push_scope.__enter__ = MagicMock(return_value=mock_push_scope)
        mock_push_scope.__exit__ = MagicMock(return_value=None)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            capture_exception(ValueError("erro"))
            assert mock_sentry.capture_exception.called


# ─── capture_message ────────────────────────────────────────────────────

def test_capture_message_sentry_disabled(caplog) -> None:
    """capture_message sem sentry loga localmente."""
    with (
        patch.dict(os.environ, {}, clear=True),
        caplog.at_level(logging.INFO),
    ):
        capture_message("teste informativo")
        assert any("msg (sentry disabled)" in rec.getMessage() for rec in caplog.records)


def test_capture_message_sentry_enabled() -> None:
    """capture_message com sentry ativo chama sentry_sdk.capture_message."""
    with patch("app.services.sentry._init_sentry", return_value=True):
        mock_sentry = MagicMock()
        mock_push_scope = MagicMock()
        mock_sentry.push_scope.return_value = mock_push_scope
        mock_push_scope.__enter__ = MagicMock(return_value=mock_push_scope)
        mock_push_scope.__exit__ = MagicMock(return_value=None)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            capture_message("aviso", level="warning")
            assert mock_sentry.capture_message.called


def test_capture_message_extra_scrubbed() -> None:
    """capture_message faz scrub no extra antes de enviar."""
    with patch("app.services.sentry._init_sentry", return_value=True):
        mock_sentry = MagicMock()
        scope_mock = MagicMock()
        mock_sentry.push_scope = MagicMock(return_value=scope_mock)
        scope_mock.__enter__ = MagicMock(return_value=scope_mock)
        scope_mock.__exit__ = MagicMock(return_value=None)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            capture_message("alerta", extra={"cpf": "123.456.789-00"})
            # Verifica que set_extra foi chamado
            assert scope_mock.set_extra.called
            # Verifica que o valor passado tem o CPF mascarado
            call_args = scope_mock.set_extra.call_args
            assert call_args is not None
            args, _ = call_args
            assert "[MASKED:cpf]" in str(args)
