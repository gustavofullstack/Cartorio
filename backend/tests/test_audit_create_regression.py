from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.audit import AuditLogCreate
from app.services.audit_create import create_audit_log_entry


def test_create_audit_log_entry_delegates_to_audit_service() -> None:
    db = MagicMock()
    entry = AuditLogCreate(
        actor_id="system",
        action="cliente.read",
        resource="cliente:1",
        payload={"result": "ok"},
    )
    created = MagicMock()

    with patch("app.services.audit_create.AuditService.log", return_value=created) as log:
        result = create_audit_log_entry(db, entry)

    assert result is created
    log.assert_called_once_with(
        db,
        actor_id="system",
        actor_type="system",
        action="cliente.read",
        resource="cliente:1",
        payload={"result": "ok"},
        canal=None,
        ip=None,
        user_agent=None,
        request_id=None,
    )


def test_create_audit_log_entry_rejects_empty_required_values() -> None:
    db = MagicMock()
    entry = AuditLogCreate.model_construct(
        actor_id="",
        actor_type="system",
        action="cliente.read",
        resource="cliente:1",
        payload={},
        canal=None,
        ip=None,
        user_agent=None,
        request_id=None,
    )

    with pytest.raises(ValueError, match="requer actor_id"):
        create_audit_log_entry(db, entry)
