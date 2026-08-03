"""Testes de contrato P2 para Lark (V3)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "lark_p2_v3"


def test_lark_p2_event_structure() -> None:
    dm_file = FIXTURES_DIR / "dm_text_p2.json"
    assert dm_file.exists()
    payload = json.loads(dm_file.read_text(encoding="utf-8"))
    assert payload["header"]["event_type"] == "im.message.receive_v1"
    assert payload["event"]["message"]["chat_type"] == "p2p"
