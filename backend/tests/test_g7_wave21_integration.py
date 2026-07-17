"""G7 Wave 21 — LobeChat import safety + smoke inventory + webhook helper.

Modified by Gustavo Almeida — G7 Wave 21.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_lobechat_import_json_valid_and_no_literal_secret() -> None:
    path = ROOT / "infra" / "lobechat" / "agent_cartorio_import.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "agents" in data
    assert data["agents"][0]["identifier"]
    providers = data.get("providers") or []
    assert providers
    api_key = providers[0].get("apiKey", "")
    # must not look like a real committed password
    assert api_key.startswith("${") or api_key in ("", "sk-xxxx", "REPLACE_ME")
    assert "@Techno" not in json.dumps(data)
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", json.dumps(data))


def test_openclaw_bot_json_still_valid() -> None:
    path = ROOT / "infra" / "openclaw" / "cartorio-bot.openclaw.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["name"] == "cartorio-bot"
    assert len(data.get("tools") or []) >= 6


def test_smoke_inventory_finds_tests() -> None:
    import runpy

    script = ROOT / "scripts" / "smoke_inventory.py"
    ns = runpy.run_path(str(script), run_name="x")
    inv = ns["inventory"]()
    assert inv["total_tests"] >= 5
    assert inv["total_files"] >= 3


def test_telegram_webhook_runbook_and_script_exist() -> None:
    assert (ROOT / "docs" / "TELEGRAM_WEBHOOK_REREGISTER_G7.md").is_file()
    assert (ROOT / "scripts" / "telegram_set_webhook.py").is_file()
    assert (ROOT / "docs" / "LOBCHAT_OPENCLAW_IMPORT_G7.md").is_file()
    assert (ROOT / "docs" / "MUTMUT_REPORT_G7_WAVE21.md").is_file()


def test_telegram_set_webhook_mask() -> None:
    import runpy

    ns = runpy.run_path(str(ROOT / "scripts" / "telegram_set_webhook.py"), run_name="x")
    masked = ns["_mask"]("1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    assert "…" in masked or "***" in masked
    assert "AAH" not in masked or masked.count("x") == 0
