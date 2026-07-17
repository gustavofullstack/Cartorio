"""G8 Wave 33 — 4 tasks com evidência:

- G8.07.T2 cartorio_audit_hash_sequence / verify_hash_sequence
- G8.07.T3 scrub_mcp_output PII interceptor
- G8.05.T2 X-Idempotency-Key alias em webhooks
- G8.01.T4 WS concorrência mock (N conexões sequenciais)

Modified by Gustavo Almeida — G8 Wave 33.
"""

from __future__ import annotations

import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.idempotency import IdempotencyMiddleware
from app.services.audit import AuditService
from app.services.idempotency_store_fake import FakeIdempotencyStore
from app.services.mcp_pii import mcp_output_has_raw_cpf, scrub_mcp_output

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "mcp_server.py"


# ---------------------------------------------------------------------------
# G8.07.T2 — hash sequence offline
# ---------------------------------------------------------------------------


def _chain_entry(prev: str | None, payload: dict, ts: str) -> dict:
    h = AuditService._compute_hash(prev, payload, ts)
    return {
        "payload": payload,
        "timestamp": ts,
        "hash": h,
        "prev_hash": prev,
    }


def test_verify_hash_sequence_ok_three_entries() -> None:
    e0 = _chain_entry(None, {"action": "a", "n": 0}, "2026-07-17T10:00:00.000000")
    e1 = _chain_entry(e0["hash"], {"action": "b", "n": 1}, "2026-07-17T10:00:01.000000")
    e2 = _chain_entry(e1["hash"], {"action": "c", "n": 2}, "2026-07-17T10:00:02.000000")
    result = AuditService.verify_hash_sequence([e0, e1, e2])
    assert result["chain_ok"] is True
    assert result["last_valid_position"] == 3
    assert result["broken_at"] is None
    assert result["detail"] == "ok"


def test_verify_hash_sequence_detects_mid_chain_tamper() -> None:
    e0 = _chain_entry(None, {"action": "a"}, "2026-07-17T10:00:00.000000")
    e1 = _chain_entry(e0["hash"], {"action": "b"}, "2026-07-17T10:00:01.000000")
    e2 = _chain_entry(e1["hash"], {"action": "c"}, "2026-07-17T10:00:02.000000")
    # Tamper mid-chain payload without recalculating hash
    e1["payload"] = {"action": "TAMPERED"}
    result = AuditService.verify_hash_sequence([e0, e1, e2])
    assert result["chain_ok"] is False
    assert result["broken_at"] == 1
    assert result["last_valid_position"] == 1


def test_verify_hash_sequence_empty_ok() -> None:
    result = AuditService.verify_hash_sequence([])
    assert result["chain_ok"] is True
    assert result["total"] == 0


def test_verify_hash_sequence_bad_payload_type() -> None:
    result = AuditService.verify_hash_sequence(
        [{"payload": "not-a-dict", "timestamp": "t", "hash": "x", "prev_hash": None}]
    )
    assert result["chain_ok"] is False
    assert result["detail"] == "payload_not_dict"


@pytest.mark.asyncio
async def test_mcp_tool_audit_hash_sequence_callable() -> None:
    spec = importlib.util.spec_from_file_location("mcp_server_w33", MCP_SERVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    if "mcp_server_w33" in sys.modules:
        del sys.modules["mcp_server_w33"]
    spec.loader.exec_module(mod)
    e0 = _chain_entry(None, {"k": 1}, "2026-07-17T12:00:00.000000")
    out = await mod.cartorio_audit_hash_sequence([e0])
    assert out["chain_ok"] is True
    assert out["total"] == 1


# ---------------------------------------------------------------------------
# G8.07.T3 — MCP PII scrub
# ---------------------------------------------------------------------------


def test_scrub_mcp_output_masks_cpf_in_string() -> None:
    out = scrub_mcp_output("Cliente CPF 529.982.247-25 compareceu")
    assert "529.982.247-25" not in out
    assert "CPF_REDACTED" in out or "REDACTED" in out


def test_scrub_mcp_output_masks_nested_dict() -> None:
    data = {
        "ok": True,
        "cliente": {"cpf": "529.982.247-25", "nome": "Fulano"},
        "msg": "tel 34999998888",
    }
    scrubbed = scrub_mcp_output(data)
    assert not mcp_output_has_raw_cpf(scrubbed)
    blob = str(scrubbed)
    assert "529.982.247-25" not in blob


def test_scrub_mcp_output_preserves_safe_numbers() -> None:
    data = {"total": 105.4, "folhas": 2, "chain_ok": True}
    assert scrub_mcp_output(data) == data


def test_scrub_mcp_output_list() -> None:
    out = scrub_mcp_output(["ok", "CPF 111.444.777-35"])
    assert "111.444.777-35" not in str(out)


def test_mcp_tool_inventory_includes_hash_sequence() -> None:
    text = MCP_SERVER.read_text(encoding="utf-8")
    assert "cartorio_audit_hash_sequence" in text
    assert "scrub_mcp_output" in text


# ---------------------------------------------------------------------------
# G8.05.T2 — X-Idempotency-Key
# ---------------------------------------------------------------------------

WEBHOOK_PATHS = (
    "/api/v1/telegram/webhook",
    "/api/v1/webhook/evolution",
    "/api/v1/whatsapp/webhook",
)


def _app_with_idem() -> tuple[FastAPI, FakeIdempotencyStore]:
    app = FastAPI()
    store = FakeIdempotencyStore()

    @app.post("/api/v1/telegram/webhook")
    async def tg() -> dict:
        return {"ok": True, "channel": "telegram"}

    @app.post("/api/v1/webhook/evolution")
    async def evo() -> dict:
        return {"ok": True, "channel": "evolution"}

    @app.post("/api/v1/whatsapp/webhook")
    async def wa() -> dict:
        return {"ok": True, "channel": "whatsapp"}

    app.add_middleware(IdempotencyMiddleware, store=store, paths_prefixes=("/api/v1/",))
    return app, store


@pytest.mark.parametrize("path", WEBHOOK_PATHS)
def test_x_idempotency_key_caches_webhook(path: str) -> None:
    app, _store = _app_with_idem()
    client = TestClient(app)
    headers = {"X-Idempotency-Key": "wave33-key-1", "Content-Type": "application/json"}
    body = {"event": "message", "id": "m1"}
    r1 = client.post(path, json=body, headers=headers)
    assert r1.status_code == 200
    r2 = client.post(path, json=body, headers=headers)
    assert r2.status_code == 200
    assert r2.json() == r1.json()


@pytest.mark.parametrize("path", WEBHOOK_PATHS)
def test_x_idempotency_key_conflict_on_different_body(path: str) -> None:
    app, _ = _app_with_idem()
    client = TestClient(app)
    headers = {"X-Idempotency-Key": "wave33-key-conflict", "Content-Type": "application/json"}
    assert client.post(path, json={"a": 1}, headers=headers).status_code == 200
    r2 = client.post(path, json={"a": 2}, headers=headers)
    assert r2.status_code == 422
    assert r2.json()["erro"] == "IDEMPOTENCY_KEY_CONFLICT"


def test_idempotency_key_and_x_alias_same_header_family() -> None:
    """Ambos headers devem ser lidos (não exige mesma cache key cross-alias)."""
    app, _ = _app_with_idem()
    client = TestClient(app)
    path = "/api/v1/telegram/webhook"
    r1 = client.post(
        path,
        json={"x": 1},
        headers={"Idempotency-Key": "plain-1", "Content-Type": "application/json"},
    )
    r2 = client.post(
        path,
        json={"x": 1},
        headers={"X-Idempotency-Key": "x-alias-1", "Content-Type": "application/json"},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_webhook_paths_are_under_api_v1_prefix() -> None:
    """Contrato: todos webhooks listados ficam sob /api/v1/ (middleware default)."""
    for p in WEBHOOK_PATHS:
        assert p.startswith("/api/v1/")


# ---------------------------------------------------------------------------
# G8.01.T4 — WS concurrent mock
# ---------------------------------------------------------------------------


def test_ws_50_sequential_connections_ping_pong() -> None:
    """50 conexões sequenciais (mock API) — cada uma ping→pong."""
    from app.api.v1.ws.atendimentos import ws_router

    app = FastAPI()
    app.include_router(ws_router, prefix="/api/v1")
    client = TestClient(app)
    for i in range(50):
        with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping", "n": i})
            assert ws.receive_json() == {"type": "pong"}


def test_ws_20_threaded_connections_no_crash() -> None:
    """20 conexões em threads paralelas (stress leve do mock)."""
    from app.api.v1.ws.atendimentos import ws_router

    app = FastAPI()
    app.include_router(ws_router, prefix="/api/v1")

    def one(i: int) -> bool:
        # TestClient não é 100% thread-safe com mesmo app; cada thread cria client
        c = TestClient(app)
        with c.websocket_connect("/api/v1/ws/atendimentos") as ws:
            ws.send_json({"type": "ping", "n": i})
            return ws.receive_json().get("type") == "pong"

    ok = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(one, i) for i in range(20)]
        for f in as_completed(futs):
            if f.result():
                ok += 1
    assert ok == 20


def test_ws_echo_under_burst_messages() -> None:
    from app.api.v1.ws.atendimentos import ws_router

    app = FastAPI()
    app.include_router(ws_router, prefix="/api/v1")
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/atendimentos") as ws:
        for i in range(30):
            ws.send_json({"type": "burst", "i": i})
            echo = ws.receive_json()
            assert echo["type"] == "echo"
            assert echo["data"]["i"] == i
