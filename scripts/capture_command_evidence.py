#!/usr/bin/env python3
"""Wrapper de execução para registro imutável de evidências de comandos (V3)."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_COMMANDS_DIR = PROJECT_ROOT / ".evidence" / "gemini36-v3" / "commands"


def redact_sensitive(text: str) -> str:
    """Redige chaves, tokens e PII de outputs."""
    import re
    text = re.sub(r"(sk-[a-zA-Z0-9]{20,})", "[REDACTED_SECRET]", text)
    text = re.sub(r"(lin_api_[a-zA-Z0-9]{20,})", "[REDACTED_SECRET]", text)
    text = re.sub(r"(\b\d{3}\.\d{3}\.\d{3}-\d{2}\b)", "[REDACTED_CPF]", text)
    return text


def run_and_capture(cmd: str, task_ids: list[str], cwd: str | None = None) -> dict:
    EVIDENCE_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    start_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.time()
    
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd or str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    t1 = time.time()
    end_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    duration = t1 - t0
    
    stdout_redacted = redact_sensitive(proc.stdout)
    stderr_redacted = redact_sensitive(proc.stderr)
    
    stdout_hash = hashlib.sha256(stdout_redacted.encode("utf-8")).hexdigest()
    stderr_hash = hashlib.sha256(stderr_redacted.encode("utf-8")).hexdigest()
    
    cmd_id = f"cmd_{int(t0*1000)}_{proc.returncode}"
    
    stdout_file = EVIDENCE_COMMANDS_DIR / f"{cmd_id}.stdout.redacted.txt"
    stderr_file = EVIDENCE_COMMANDS_DIR / f"{cmd_id}.stderr.redacted.txt"
    json_file = EVIDENCE_COMMANDS_DIR / f"{cmd_id}.json"
    
    stdout_file.write_text(stdout_redacted, encoding="utf-8")
    stderr_file.write_text(stderr_redacted, encoding="utf-8")
    
    record = {
        "command_id": cmd_id,
        "task_ids": task_ids,
        "cwd": cwd or str(PROJECT_ROOT),
        "start_utc": start_utc,
        "end_utc": end_utc,
        "duration_seconds": duration,
        "command_redacted": redact_sensitive(cmd),
        "exit_code": proc.returncode,
        "stdout_sha256": stdout_hash,
        "stderr_sha256": stderr_hash,
        "environment": "local_execution",
        "has_network": False,
        "captured_by": "FLASH-V3-DEEP-REMEDIATION-ORCHESTRATOR"
    }
    
    json_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture command evidence")
    parser.add_argument("--cmd", required=True, help="Command to execute")
    parser.add_argument("--tasks", nargs="+", default=[], help="Task IDs associated")
    args = parser.parse_args()
    
    rec = run_and_capture(args.cmd, args.tasks)
    print(f"[EVIDENCE CAPTURED] Command ID: {rec["command_id"]} Exit Code: {rec["exit_code"]}")
    return rec["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
