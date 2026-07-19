"""Regressoes do gate OpenAPI semantico executado pelo CI raiz."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_snapshot_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "openapi_snapshot.py"
    spec = importlib.util.spec_from_file_location("openapi_snapshot_under_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _operation(**extra: object) -> dict[str, object]:
    return {"responses": {"200": {"description": "ok"}}, **extra}


def test_semantic_diff_ignores_cosmetic_docs_and_added_path() -> None:
    module = _load_snapshot_module()
    baseline = {"paths": {"/health": {"get": _operation(summary="old")}}}
    current = {
        "paths": {
            "/health": {"get": _operation(summary="new", description="expanded")},
            "/new": {"post": _operation()},
        }
    }

    diff = module.semantic_diff(baseline, current)

    assert diff.added_paths == ["/new"]
    assert diff.breaking == []


def test_semantic_diff_detects_removed_operation_and_required_parameter() -> None:
    module = _load_snapshot_module()
    baseline = {
        "paths": {
            "/items": {
                "get": _operation(parameters=[{"in": "query", "name": "page", "required": False}]),
                "post": _operation(),
            }
        }
    }
    current = {
        "paths": {
            "/items": {"get": _operation(parameters=[{"in": "query", "name": "page", "required": True}])}
        }
    }

    diff = module.semantic_diff(baseline, current)

    assert any("operation removed: POST /items" in item for item in diff.breaking)
    assert any("parameter became required: GET /items query page" in item for item in diff.breaking)


def test_semantic_diff_detects_security_regression() -> None:
    module = _load_snapshot_module()
    baseline = {
        "components": {"securitySchemes": {"ApiKey": {"type": "apiKey", "in": "header", "name": "X-Key"}}},
        "paths": {"/secure": {"get": _operation(security=[{"ApiKey": []}])}},
    }
    current = {
        "components": {"securitySchemes": {"ApiKey": {"type": "apiKey", "in": "header", "name": "X-Other"}}},
        "paths": {"/secure": {"get": _operation(security=[])}},
    }

    diff = module.semantic_diff(baseline, current)

    assert len(diff.changed_security) == 2


def test_validate_internal_refs_handles_escaped_pointer_and_rejects_missing() -> None:
    module = _load_snapshot_module()
    valid = {"components": {"schemas": {"A/B": {"type": "object"}}}, "x": {"$ref": "#/components/schemas/A~1B"}}
    invalid = {"x": {"$ref": "#/components/schemas/Missing"}}

    assert module.validate_internal_refs(valid, label="valid") == []
    assert module.validate_internal_refs(invalid, label="invalid") == [
        "invalid:$/x -> #/components/schemas/Missing"
    ]
