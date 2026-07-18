"""G8.22.T2 — valida o template de monitoramento offline da Evolution API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.schemas.n8n_workflow import N8nWorkflow

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / "infra" / "n8n-workflows" / "template-monitoramento-evolution.json"


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload["nodes"]


def test_template_valid_n8n_workflow(payload: dict[str, Any]) -> None:
    workflow = N8nWorkflow.model_validate(payload)

    assert workflow.name == "WF-TEMPLATE Monitoramento Evolution"
    assert workflow.active is False


def test_template_has_cron(nodes: list[dict[str, Any]]) -> None:
    cron = next(node for node in nodes if node["name"] == "Cron")
    interval = cron["parameters"]["rule"]["interval"][0]

    assert cron["type"] == "n8n-nodes-base.scheduleTrigger"
    assert interval == {"field": "minutes", "minutesInterval": 5}


def test_template_routes_open_state_to_noop(
    payload: dict[str, Any], nodes: list[dict[str, Any]]
) -> None:
    state_node = next(node for node in nodes if node["name"] == "If State=open")
    condition = state_node["parameters"]["conditions"]["string"][0]
    branches = payload["connections"]["If State=open"]["main"]

    assert condition == {
        "value1": "={{ $json.instance.state }}",
        "operation": "equal",
        "value2": "open",
    }
    assert branches[0][0]["node"] == "NoOp (online)"
    assert branches[1][0]["node"] == "GET /instance/status"


def test_template_has_alert_telegram(nodes: list[dict[str, Any]]) -> None:
    alert = next(node for node in nodes if node["name"] == "Alert Telegram Escrevente")
    parameters = alert["parameters"]

    assert alert["type"] == "n8n-nodes-base.telegram"
    assert parameters["chatId"] == "={{ $env.ESCREVENTE_TELEGRAM_CHAT_ID }}"
    assert "$env.EVOLUTION_INSTANCE" in parameters["text"]
    assert "$json.status" in parameters["text"]


def test_template_has_audit_lgpd(nodes: list[dict[str, Any]]) -> None:
    audit = next(node for node in nodes if node["name"] == "Audit LGPD Art.37")
    parameters = audit["parameters"]
    body = {item["name"]: item["value"] for item in parameters["bodyParameters"]["parameters"]}

    assert audit["type"] == "n8n-nodes-base.httpRequest"
    assert parameters["url"].endswith("/api/v1/audit")
    assert parameters["method"] == "POST"
    assert body == {
        "action": "evolution_disconnect_alert",
        "entity": "evolution_instance",
        "protocolo": "ALERT",
    }


def test_template_max_execution_time(nodes: list[dict[str, Any]]) -> None:
    http_nodes = [node for node in nodes if node["type"] == "n8n-nodes-base.httpRequest"]

    assert http_nodes
    assert all(node["parameters"]["options"]["timeout"] <= 30_000 for node in http_nodes)


PII_PATTERNS = (
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b"),
    re.compile(r"\b\d{2}\.\d{3}\.\d{3}-?[\dXx]\b"),
    re.compile(r"\+?55\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b"),
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
)


@pytest.mark.parametrize("pattern", PII_PATTERNS)
def test_template_no_pii_in_static(pattern: re.Pattern[str]) -> None:
    static_json = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert pattern.search(static_json) is None
