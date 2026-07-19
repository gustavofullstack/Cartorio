from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "n8n_error_handler_audit.py"
_SPEC = importlib.util.spec_from_file_location("n8n_error_handler_audit", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

audit_workflow = _MODULE.audit_workflow
is_error_handler_name = _MODULE.is_error_handler_name


def test_error_handler_name_accepts_n8n_export_spelling() -> None:
    assert is_error_handler_name("00 - Error Handler Global (T25) v4")
    assert is_error_handler_name("00-error-handler")
    assert not is_error_handler_name("30 - Chatwoot status sync")


def test_audit_does_not_mark_named_handler_as_missing(tmp_path: Path) -> None:
    workflow = tmp_path / "error-handler.json"
    workflow.write_text(
        '{"name":"00 - Error Handler Global (T25) v4","settings":{"errorWorkflow":null}}',
        encoding="utf-8",
    )

    result = audit_workflow(workflow)

    assert not result.has_error_workflow
    assert result.name.startswith("00 - Error Handler")
