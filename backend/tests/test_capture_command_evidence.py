"""Testes para o capturador de evidências de comandos (V3)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_redact_sensitive() -> None:
    from scripts.capture_command_evidence import redact_sensitive

    raw = "My key is sk-123456789012345678901234567890 and CPF is 123.456.789-00"
    redacted = redact_sensitive(raw)
    assert "sk-123456789012345678901234567890" not in redacted
    assert "123.456.789-00" not in redacted
    assert "[REDACTED_SECRET]" in redacted
    assert "[REDACTED_CPF]" in redacted


def test_run_and_capture_echo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.capture_command_evidence import run_and_capture

    test_dir = tmp_path / ".evidence" / "gemini36-v3" / "commands"
    test_dir.mkdir(parents=True)
    monkeypatch.setattr("scripts.capture_command_evidence.EVIDENCE_COMMANDS_DIR", test_dir)
    
    rec = run_and_capture("echo hello", ["G0.01"])
    assert rec["exit_code"] == 0
    assert rec["task_ids"] == ["G0.01"]
    assert len(list(test_dir.glob("*.json"))) == 1
