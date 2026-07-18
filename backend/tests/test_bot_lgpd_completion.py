from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from app.api.v1.bot_lgpd import (
    AccessRequest,
    ExportRequest,
    RestaurarRequest,
    post_access,
    post_export,
    post_restaurar,
)
from app.services.lgpd.bot_direito_esquecimento import ExportResult


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/bot/lgpd",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


@pytest.mark.asyncio
async def test_export_continua_quando_audit_falha() -> None:
    db = MagicMock()
    result = ExportResult(
        cliente_id=7,
        filename="cliente_7.json",
        data_json={"cliente": {"id": 7}},
        sha256="a" * 64,
        size_bytes=42,
    )

    with (
        patch("app.api.v1.bot_lgpd.exportar_dados_cliente", return_value=result),
        patch("app.api.v1.bot_lgpd.AuditService.log", side_effect=RuntimeError("audit down")),
    ):
        response = await post_export(
            _request(),
            ExportRequest(channel="whatsapp", sender_id="sender-7", cliente_id=7),
            db,
        )

    assert response.filename == "cliente_7.json"
    db.rollback.assert_called_once_with()


@pytest.mark.asyncio
async def test_access_continua_quando_audit_falha() -> None:
    db = MagicMock()
    cliente = MagicMock(
        id=7,
        nome="Cliente Teste",
        email="cliente@example.com",
        cpf_hash="b" * 64,
        consentimento_lgpd=True,
        created_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
    )
    db.get.return_value = cliente

    with patch("app.api.v1.bot_lgpd.AuditService.log", side_effect=RuntimeError("audit down")):
        response = await post_access(
            _request(),
            AccessRequest(channel="telegram", sender_id="sender-7", cliente_id=7),
            db,
        )

    assert response.cliente_id == 7
    assert response.cpf_hash == "b" * 64
    db.rollback.assert_called_once_with()


@pytest.mark.asyncio
async def test_restaurar_continua_quando_audit_falha() -> None:
    db = MagicMock()

    with (
        patch("app.api.v1.bot_lgpd.restaurar_revogacao", return_value=True),
        patch("app.api.v1.bot_lgpd.AuditService.log", side_effect=RuntimeError("audit down")),
    ):
        response = await post_restaurar(
            _request(),
            RestaurarRequest(revogacao_id="revogacao-123"),
            db,
        )

    assert response.status == "ok"
    assert response.revogacao_id == "revogacao-123"
    db.rollback.assert_called_once_with()
