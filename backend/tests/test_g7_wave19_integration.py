"""G7 Wave 19 — PII inventory sites + redlock peer skip + openapi baseline.

Modified by Gustavo Almeida — G7 Wave 19.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[2]


def test_pii_pre_llm_inventory_script_work() -> None:
    import runpy
    import sys

    script = ROOT / "scripts" / "pii_pre_llm_inventory.py"
    assert script.is_file()
    # run as __main__ with --strict
    with patch.object(sys, "argv", ["pii_pre_llm_inventory.py", "--strict"]):
        # execute module
        ns = runpy.run_path(str(script), run_name="not_main")
        # call main directly
        sys.argv = ["pii_pre_llm_inventory.py", "--strict"]
        code = ns["main"]()
    assert code == 0


def test_required_llm_paths_contain_scrub() -> None:
    app = ROOT / "backend" / "app"
    required = [
        "services/chat_pipeline.py",
        "services/cartorio_agent.py",
        "integrations/opencode_go.py",
        "integrations/openclaw.py",
        "api/v1/telegram.py",
    ]
    for rel in required:
        text = (app / rel).read_text(encoding="utf-8")
        assert "scrub(" in text or "pii_scrub(" in text, f"missing scrub in {rel}"


def test_redlock_peer_skip_when_busy() -> None:
    """G7.07.T4: segundo peer não adquire dms-loop (skip silencioso)."""
    from app.services.redlock import acquire_lock

    with patch("app.services.redlock._get_redis_client") as mock_get:
        r = MagicMock()
        # first acquire True, second False
        r.set.side_effect = [True, False]
        mock_get.return_value = r
        t1 = acquire_lock("dms-loop", ttl_seconds=50)
        t2 = acquire_lock("dms-loop", ttl_seconds=50)
    assert t1 is not None
    assert t2 is None  # peer skip


def test_openapi_baseline_exists_and_has_paths() -> None:
    import json

    baseline = ROOT / "snapshots" / "openapi.baseline.json"
    assert baseline.is_file()
    data = json.loads(baseline.read_text(encoding="utf-8"))
    paths = data.get("paths") or {}
    assert len(paths) >= 100
    # critical integration paths
    joined = " ".join(paths.keys())
    assert "radar" in joined or any("radar" in p for p in paths)
    assert any("telegram" in p for p in paths)


def test_chatwoot_handoff_doc_exists() -> None:
    doc = ROOT / "docs" / "CHATWOOT_HANDOFF_G7.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "handoff_to_chatwoot" in text
    assert "HITL" in text
