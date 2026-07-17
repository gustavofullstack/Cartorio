"""G7 Wave 15 — integration artifacts validation (catalog + openclaw + postman).

Does not call prod LLM. Loads catalog via importlib (path .brain/api-specs
has hyphen — not a normal package).

Modified by Gustavo Almeida + cartorio-dev — G7 Wave 15.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / ".brain" / "api-specs" / "catalog.py"
OPENCLAW_BOT = ROOT / "infra" / "openclaw" / "cartorio-bot.openclaw.json"
POSTMAN = ROOT / "docs" / "postman_collection.json"
INTEGRATION_MATRIX = ROOT / "docs" / "INTEGRATION_MATRIX_G7.md"
REDIS_OPS = ROOT / "docs" / "platforms" / "REDIS_OPS_G7.md"


def _load_catalog():
    import sys

    spec = importlib.util.spec_from_file_location("brain_catalog_g7", CATALOG_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # dataclasses resolve annotations via sys.modules[cls.__module__]
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def catalog():
    return _load_catalog()


def test_catalog_file_exists() -> None:
    assert CATALOG_PATH.is_file()


def test_catalog_stats_include_openclaw_and_ws(catalog) -> None:
    stats = catalog.get_stats()
    assert stats["total"] == stats["v1"] + stats["v2"] + stats["openclaw"]
    assert stats["v1"] >= 55  # wave15 added radar/ws/brain
    assert stats["openclaw"] >= 8
    assert stats["websocket"] >= 1
    status_sum = (
        stats["stable"] + stats["alpha"] + stats["beta"] + stats["deprecated"]
    )
    assert status_sum == stats["total"]


def test_catalog_has_g7_integration_paths(catalog) -> None:
    paths = {(e.method, e.path) for e in catalog.get_all_endpoints()}
    assert ("GET", "/api/v1/health/radar/expanded") in paths
    assert ("GET", "/api/v1/health/radar") in paths
    assert ("WS", "/api/v1/ws/atendimentos") in paths
    assert ("GET", "/api/v1/brain/loop-state") in paths
    assert ("POST", "/api/v1/telegram/webhook") in paths
    assert ("GET", "/api/v1/webhook/evolution/health") in paths
    assert ("POST", "/api/v1/integrations/chatwoot/handoff") in paths
    assert ("POST", "/v1/chat/completions") in paths  # openclaw


def test_openclaw_cartorio_bot_json_valid() -> None:
    assert OPENCLAW_BOT.is_file()
    data = json.loads(OPENCLAW_BOT.read_text(encoding="utf-8"))
    assert data["name"] == "cartorio-bot"
    assert data["slug"] == "cartorio-bot"
    assert "HITL" in data["system_prompt"] or "HITL" in data["system_prompt"].upper() or "HITL" in json.dumps(data)
    assert len(data["tools"]) >= 8
    assert any(t["name"] == "criar_protocolo" and t.get("hitl") for t in data["tools"])
    assert "operator.read" in data["auth"]["required_scopes"]
    assert data["api_base"].startswith("https://api.")


def test_postman_no_double_api_v1_prefix() -> None:
    text = POSTMAN.read_text(encoding="utf-8")
    assert "/api/v1/api/v1/" not in text
    data = json.loads(text)
    assert "item" in data or "info" in data


def test_integration_matrix_and_redis_docs_exist() -> None:
    assert INTEGRATION_MATRIX.is_file()
    assert "OpenClaw" in INTEGRATION_MATRIX.read_text(encoding="utf-8")
    assert REDIS_OPS.is_file()
    assert "maxmemory" in REDIS_OPS.read_text(encoding="utf-8")
