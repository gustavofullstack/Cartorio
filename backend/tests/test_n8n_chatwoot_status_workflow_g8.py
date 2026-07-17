"""G8.03.T3 — valida workflow n8n Chatwoot status sync (estrutura JSON).

Não chama n8n live. Garante nós essenciais + path webhook.

Modified by Gustavo Almeida — Wave 38.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / "infra" / "n8n-workflows" / "30-chatwoot-status-sync-g8.json"


def test_workflow_file_exists() -> None:
    assert WF.exists(), f"missing {WF}"


def test_workflow_json_valid() -> None:
    data = json.loads(WF.read_text(encoding="utf-8"))
    assert data.get("name")
    nodes = data.get("nodes") or []
    assert len(nodes) >= 3
    types = {n.get("type") for n in nodes}
    assert "n8n-nodes-base.webhook" in types
    assert "n8n-nodes-base.httpRequest" in types


def test_webhook_path() -> None:
    data = json.loads(WF.read_text(encoding="utf-8"))
    wh = next(n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.webhook")
    assert wh["parameters"]["path"] == "chatwoot-status-sync"


def test_idempotency_header_in_http() -> None:
    data = json.loads(WF.read_text(encoding="utf-8"))
    http = next(n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.httpRequest")
    headers = http["parameters"]["headerParameters"]["parameters"]
    names = {h["name"] for h in headers}
    assert "X-Idempotency-Key" in names


def test_meta_g8_task() -> None:
    data = json.loads(WF.read_text(encoding="utf-8"))
    assert data.get("meta", {}).get("g8_task") == "G8.03.T3"


def test_connections_chain() -> None:
    data = json.loads(WF.read_text(encoding="utf-8"))
    conn = data.get("connections") or {}
    assert "Webhook Chatwoot Status" in conn
    assert "Normalize Status Payload" in conn
