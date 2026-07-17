"""G7 Wave 23 — coverage leverage DMS/send_alert + evolution reject paths.

Modified by Gustavo Almeida — G7 Wave 23.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.dead_mans_switch import check_audit_log_alive, send_alert
from app.services.evolution_ingest import ingest_evolution_event, validate_evolution_signature

ROOT = Path(__file__).resolve().parents[2]


def test_send_alert_success_http_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("httpx.post", return_value=mock_resp) as post:
        assert send_alert("ok", chat_id="-1001") is True
        post.assert_called_once()


def test_send_alert_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_GRUPO_PIEIRA_CHAT_ID", "-99")

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "err"
    with patch("httpx.post", return_value=mock_resp):
        assert send_alert("fail") is False


def test_send_alert_network_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    with patch("httpx.post", side_effect=OSError("down")):
        assert send_alert("x") is False


def test_check_audit_alive_recent() -> None:
    db = MagicMock()
    recent = datetime.now(tz=timezone.utc) - timedelta(minutes=10)
    db.execute.return_value.scalar.return_value = recent
    r = check_audit_log_alive(db)
    assert r["alive"] is True
    assert r["cold_start"] is False
    assert r["seconds_since_last"] is not None
    assert r["seconds_since_last"] < 3600


def test_check_audit_dead_after_threshold() -> None:
    db = MagicMock()
    old = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    db.execute.return_value.scalar.return_value = old
    r = check_audit_log_alive(db)
    assert r["alive"] is False
    assert r["seconds_since_last"] is not None
    assert r["seconds_since_last"] >= 3600


def test_ingest_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "sec")
    db = MagicMock()
    out = ingest_evolution_event(
        db,
        {"event": "messages.upsert", "data": {}},
        raw_body=b"{}",
        signature="bad",
    )
    assert out["status"] == "rejected"
    assert out["reason"] == "invalid_signature"


def test_ingest_ignores_non_upsert() -> None:
    db = MagicMock()
    out = ingest_evolution_event(db, {"event": "connection.update"})
    assert out["status"] == "ignored"


def test_ingest_rejects_missing_data() -> None:
    db = MagicMock()
    out = ingest_evolution_event(db, {"event": "messages.upsert", "data": "nope"})
    assert out["status"] == "rejected"
    assert out["reason"] == "missing_data"


def test_ingest_accepts_image_caption(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "")
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    payload = {
        "event": "messages.upsert",
        "instance": "cartorio",
        "data": {
            "key": {"id": "IMG1", "remoteJid": "5534@s.whatsapp.net"},
            "message": {"imageMessage": {"caption": "quanto custa autenticacao"}},
        },
    }
    out = ingest_evolution_event(db, payload)
    assert out["status"] == "accepted"
    assert "autenticacao" in out["text"]
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_validate_signature_dev_mode_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET", "")
    monkeypatch.setenv("EVOLUTION_WEBHOOK_SECRET_PREV", "")
    assert validate_evolution_signature(b"x", None) is True


def test_runbooks_wave23_exist() -> None:
    assert (ROOT / "docs" / "CHATWOOT_AGENT_BOT_SETUP_G7.md").is_file()
    assert (ROOT / "docs" / "LOBECHAT_OPENAI_KEY_G7.md").is_file()
    assert (ROOT / "docs" / "G7_PROGRESS_DASHBOARD.md").is_file()
