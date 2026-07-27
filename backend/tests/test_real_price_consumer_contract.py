"""Regressões dos consumidores do catálogo TJMG seguro, sem preços placeholder."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SAFE_ENDPOINT = "/api/v1/emolumentos/real/calcular"
LEGACY_ENDPOINTS = ("/api/v1/emolumento/calcular", "/api/v1/emolumentos/calcular-api")


def _workflow(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_n8n_workflows_use_safe_price_contract() -> None:
    for path in (
        "infra/n8n-workflows/01-consulta-emolumento.json",
        "infra/n8n-workflows/38-emolumento-calculator.json",
    ):
        serialized = (ROOT / path).read_text(encoding="utf-8")
        assert SAFE_ENDPOINT in serialized
        assert all(endpoint not in serialized for endpoint in LEGACY_ENDPOINTS)


def test_n8n_calculator_never_formats_hitl_as_a_price() -> None:
    workflow = _workflow("infra/n8n-workflows/38-emolumento-calculator.json")
    messages = [
        node["parameters"].get("jsonBody", "")
        for node in workflow["nodes"]
        if node["name"] in {"Send to Telegram Chatbot", "Send to WhatsApp (Evolution)"}
    ]
    assert len(messages) == 2
    assert all("HITL" not in body or "PUBLISHED" in body for body in messages)
    assert all("conferência do escrevente" in body for body in messages)
    assert all("adicional_urgencia" not in body for body in messages)


def test_openclaw_tool_points_to_safe_contract() -> None:
    registry = json.loads(
        (ROOT / "infra/openclaw-agent/agent-tools-registry.json").read_text(encoding="utf-8")
    )
    tool = next(
        item for item in registry["tools"] if item["name"] == "cartorio_api_emolumento_calcular"
    )
    assert tool["endpoint"].startswith("POST " + SAFE_ENDPOINT)
    assert tool["version"] == "2.0.0"
    assert "HITL_REQUIRED" in tool["description"]
