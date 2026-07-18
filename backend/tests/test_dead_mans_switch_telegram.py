"""Tests para dead_mans_switch.py + Telegram GRUPO PIETRA alert (G6.B.T4)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

import logging  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from app.services.dead_mans_switch import (  # noqa: E402
    check_audit_log_alive,
    last_audit_timestamp,
    send_alert,
)


# ============================================================================
# check_audit_log_alive (testes existentes)
# ============================================================================


def _make_db_with_audit(timestamp: datetime | None = None):
    """Cria mock Session com 1 audit_log opcional."""
    db = MagicMock()
    if timestamp is None:
        # Tabela vazia (cold start)
        db.execute.return_value.scalar.return_value = None
    else:
        db.execute.return_value.scalar.return_value = timestamp
    return db


def test_check_audit_alive_quando_recente() -> None:
    """Audit log com timestamp agora deve estar alive."""
    now = datetime.now(tz=timezone.utc)
    db = _make_db_with_audit(now)
    result = check_audit_log_alive(db)
    assert result["alive"] is True
    assert result["cold_start"] is False


def test_check_audit_morto_quando_2h() -> None:
    """Audit log com timestamp 2h atras deve estar morto."""
    past = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    db = _make_db_with_audit(past)
    result = check_audit_log_alive(db)
    assert result["alive"] is False
    assert result["cold_start"] is False
    assert result["seconds_since_last"] >= 7200  # 2h


def test_check_audit_cold_start_quando_tabela_vazia() -> None:
    """Tabela vazia (max timestamp = None) = cold start."""
    db = _make_db_with_audit(None)
    result = check_audit_log_alive(db)
    assert result["alive"] is False
    assert result["cold_start"] is True
    assert result["last_seen"] is None


def test_last_audit_timestamp_retorna_max() -> None:
    """last_audit_timestamp retorna o max(timestamp) do DB."""
    db = MagicMock()
    expected = datetime.now(tz=timezone.utc)
    db.execute.return_value.scalar.return_value = expected
    result = last_audit_timestamp(db)
    assert result == expected


# ============================================================================
# send_alert com Telegram GRUPO PIETRA (G6.B.T4 NOVO)
# ============================================================================


def test_send_alert_sem_token_apenas_loga(caplog: pytest.LogCaptureFixture) -> None:
    """Sem TELEGRAM_BOT_TOKEN, send_alert deve apenas logar (fail-open)."""
    with patch.dict(os.environ, {}, clear=True):
        with caplog.at_level(logging.ERROR):
            ok = send_alert("audit parado ha 2h")
        assert ok is False, "deve retornar False sem Telegram configurado"
        assert any("DEAD_MANS_SWITCH_ALERT" in r.message for r in caplog.records)


def test_send_alert_sem_chat_id_apenas_loga(caplog: pytest.LogCaptureFixture) -> None:
    """Sem TELEGRAM_CHAT_ID, send_alert deve apenas logar (fail-open)."""
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test_token"}, clear=True):
        with caplog.at_level(logging.ERROR):
            ok = send_alert("audit parado ha 2h")
        assert ok is False


def test_send_alert_com_httpx_sucesso() -> None:
    """Com token + chat_id + httpx mock 200, send_alert deve retornar True."""
    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "123456"},
        clear=True,
    ):
        with patch("httpx.post") as mock_httpx_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_httpx_post.return_value = mock_resp
            ok = send_alert("audit parado ha 2h")
        assert ok is True
        # Verificar URL chamada
        call_url = mock_httpx_post.call_args[0][0]
        assert "api.telegram.org/bottest_token/sendMessage" in call_url
        # Verificar chat_id no body
        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["chat_id"] == "123456"
        assert "DEAD MAN'S SWITCH" in call_body["text"]


def test_send_alert_com_httpx_falha() -> None:
    """httpx 500 (Telegram down) deve retornar False mas NAO quebrar."""
    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "123456"},
        clear=True,
    ):
        with patch("httpx.post") as mock_httpx_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_httpx_post.return_value = mock_resp
            ok = send_alert("audit parado ha 2h")
        assert ok is False, "deve retornar False em falha Telegram"


def test_send_alert_com_httpx_exception() -> None:
    """httpx timeout/connection error deve retornar False (fail-open)."""
    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "123456"},
        clear=True,
    ):
        with patch("httpx.post") as mock_httpx_post:
            mock_httpx_post.side_effect = Exception("timeout")
            ok = send_alert("audit parado ha 2h")
        assert ok is False


def test_send_alert_usa_grupo_pietra_chat_id_primeiro() -> None:
    """Se GRUPO PIETRA CHAT ID definido, usa ele (nao TELEGRAM_CHAT_ID generico)."""
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "TELEGRAM_CHAT_ID": "111",
            "TELEGRAM_GRUPO_PIEIRA_CHAT_ID": "222",  # GRUPO PIETRA especifico
        },
        clear=True,
    ):
        with patch("httpx.post") as mock_httpx_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_httpx_post.return_value = mock_resp
            send_alert("test")
        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["chat_id"] == "222", "GRUPO PIETRA chat_id deve prevalecer"


def test_send_alert_aceita_chat_id_explicito() -> None:
    """Argumento chat_id explicito sobrescreve env."""
    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "111"},
        clear=True,
    ):
        with patch("httpx.post") as mock_httpx_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_httpx_post.return_value = mock_resp
            send_alert("test", chat_id="999")
        call_body = mock_httpx_post.call_args[1]["json"]
        assert call_body["chat_id"] == "999"
