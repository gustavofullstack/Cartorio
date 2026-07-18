"""Tests for `scripts/n8n_precommit_lint.py` (G8.14.T4).

These tests invoke the script as a subprocess (it lives in `scripts/`,
outside the `backend/` package) to validate the exact CLI behavior a
pre-commit hook consumer would see. All PII fixtures use FICTITIOUS
zeroed/identical digits (`000.000.000-00`, `11.111.111/0001-11`) — never
real personal data — to keep LGPD-by-design.

Modified by Gustavo Almeida — G8.14.T4 (cartorio-n8n).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "n8n_precommit_lint.py"


def _run_lint(*paths: Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke the lint CLI as a subprocess (same way pre-commit does)."""
    cmd = [sys.executable, str(SCRIPT), *[str(p) for p in paths]]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=30,
    )


def _write_wf(tmp_path: Path, name: str, payload: dict | str) -> Path:
    p = tmp_path / name
    if isinstance(payload, str):
        p.write_text(payload, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Positives: workflows that MUST pass
# ---------------------------------------------------------------------------


def test_lint_valid_workflow_passes(tmp_path: Path) -> None:
    """A canonical minimal WF with no PII exits 0 with no errors."""
    wf = {
        "name": "valid_wf",
        "nodes": [
            {"name": "Start", "type": "n8n-nodes-base.start"},
            {
                "name": "CallAPI",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {
                    "url": "={{$env.CARTORIO_API_URL}}/foo",
                    "method": "POST",
                },
            },
        ],
        "connections": {"Start": {"main": [[{"node": "CallAPI", "type": "main", "index": 0}]]}},
    }
    p = _write_wf(tmp_path, "valid.json", wf)
    result = _run_lint(p)
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "OK" in result.stderr


def test_lint_empty_argv_no_op(tmp_path: Path) -> None:
    """No positional args → exit 0, no files checked."""
    result = _run_lint()  # zero files
    assert result.returncode == 0
    assert "0 file(s) checked" in result.stderr


def test_lint_skips_non_json_silently(tmp_path: Path) -> None:
    """Non-JSON files are skipped (not an error)."""
    txt = tmp_path / "readme.txt"
    txt.write_text("hello world")
    md = tmp_path / "NOTES.md"
    md.write_text("# notes")
    result = _run_lint(txt, md)
    assert result.returncode == 0


def test_lint_skips_missing_files_silently(tmp_path: Path) -> None:
    """Non-existent paths are skipped (pre-commit may pass deleted files)."""
    ghost = tmp_path / "does-not-exist.json"
    result = _run_lint(ghost)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Negatives: workflows that MUST fail
# ---------------------------------------------------------------------------


def test_lint_invalid_json_fails(tmp_path: Path) -> None:
    """Malformed JSON → exit 1 with descriptive error."""
    p = _write_wf(tmp_path, "bad.json", "{ not valid json")
    result = _run_lint(p)
    assert result.returncode == 1
    assert "JSON invalid" in result.stderr
    assert str(p) in result.stderr


def test_lint_missing_required_keys_fails(tmp_path: Path) -> None:
    """Top-level missing `name` and `connections` → exit 1 listing each."""
    p = _write_wf(tmp_path, "no-keys.json", {"nodes": []})
    result = _run_lint(p)
    assert result.returncode == 1
    assert "missing required top-level key 'name'" in result.stderr
    assert "missing required top-level key 'connections'" in result.stderr


def test_lint_nodes_not_a_list_fails(tmp_path: Path) -> None:
    """`nodes` not a list → exit 1."""
    p = _write_wf(tmp_path, "bad-nodes.json", {"name": "x", "nodes": "oops", "connections": {}})
    result = _run_lint(p)
    assert result.returncode == 1
    assert "'nodes' must be a list" in result.stderr


def test_lint_node_missing_type_fails(tmp_path: Path) -> None:
    """Node without `type` → exit 1."""
    p = _write_wf(
        tmp_path,
        "no-type.json",
        {"name": "wf", "nodes": [{"name": "n1"}], "connections": {}},
    )
    result = _run_lint(p)
    assert result.returncode == 1
    assert "nodes[0] missing 'type'" in result.stderr


def test_lint_pii_cpf_in_node_name_fails(tmp_path: Path) -> None:
    """Fictitious CPF in node name → exit 1 with PII label."""
    p = _write_wf(
        tmp_path,
        "pii-name.json",
        {
            "name": "wf",
            "nodes": [{"name": "Send to 000.000.000-00", "type": "t"}],
            "connections": {},
        },
    )
    result = _run_lint(p)
    assert result.returncode == 1
    assert "contains PII (CPF)" in result.stderr
    assert "000.000.000-00" in result.stderr


def test_lint_pii_cpf_in_parameters_fails(tmp_path: Path) -> None:
    """Fictitious CPF in node parameters → exit 1 with PII label."""
    p = _write_wf(
        tmp_path,
        "pii-params.json",
        {
            "name": "wf",
            "nodes": [
                {
                    "name": "Send",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"body": {"cpf": "111.111.111-11"}},
                }
            ],
            "connections": {},
        },
    )
    result = _run_lint(p)
    assert result.returncode == 1
    assert "parameters contains PII (CPF)" in result.stderr


def test_lint_pii_cnpj_in_parameters_fails(tmp_path: Path) -> None:
    """Fictitious CNPJ in node parameters → exit 1 with PII label."""
    p = _write_wf(
        tmp_path,
        "pii-cnpj.json",
        {
            "name": "wf",
            "nodes": [
                {
                    "name": "Send",
                    "type": "t",
                    "parameters": {"cnpj": "11.111.111/0001-11"},
                }
            ],
            "connections": {},
        },
    )
    result = _run_lint(p)
    assert result.returncode == 1
    assert "contains PII (CNPJ)" in result.stderr


def test_lint_pii_phone_dashed_in_parameters_fails(tmp_path: Path) -> None:
    """Realistic dashed BR phone in parameters → exit 1 with PHONE label.

    BR mobile format (without DDD): 9XXXX-XXXX (9 digits, dashed).
    """
    p = _write_wf(
        tmp_path,
        "pii-phone.json",
        {
            "name": "wf",
            "nodes": [
                {
                    "name": "Send",
                    "type": "t",
                    "parameters": {"phone": "98855-1234"},
                }
            ],
            "connections": {},
        },
    )
    result = _run_lint(p)
    assert result.returncode == 1
    assert "PHONE-BR" in result.stderr


def test_lint_pii_phone_parens_in_parameters_fails(tmp_path: Path) -> None:
    """Parens-formatted BR phone → exit 1 with PHONE label."""
    p = _write_wf(
        tmp_path,
        "pii-phone-parens.json",
        {
            "name": "wf",
            "nodes": [
                {
                    "name": "Send",
                    "type": "t",
                    "parameters": {"phone": "(34) 98855-1234"},
                }
            ],
            "connections": {},
        },
    )
    result = _run_lint(p)
    assert result.returncode == 1
    assert "PHONE-BR" in result.stderr


# ---------------------------------------------------------------------------
# Anti-false-positive: real BR-ish data that MUST NOT match
# ---------------------------------------------------------------------------


def test_lint_8digit_assignment_id_does_not_trigger_phone_match(tmp_path: Path) -> None:
    """8-digit N8N assignment ids (e.g. '31583914') must NOT match PHONE-BR.

    Regression for the initial bug where optional dash caused false positives
    on numeric IDs that have nothing to do with phone numbers.
    """
    wf = {
        "name": "wf",
        "nodes": [
            {
                "name": "Init Correlation",
                "type": "n8n-nodes-base.set",
                "parameters": {
                    "assignments": {
                        "assignments": [
                            {"id": "78c215f6", "name": "a", "value": "x", "type": "string"},
                            {"id": "31583914", "name": "b", "value": "y", "type": "string"},
                        ]
                    }
                },
            }
        ],
        "connections": {},
    }
    p = _write_wf(tmp_path, "ids.json", wf)
    result = _run_lint(p)
    assert result.returncode == 0, f"false-positive PHONE-BR match: {result.stderr}"


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_cli_help_exits_zero() -> None:
    """`--help` exits 0 and shows usage."""
    cmd = [sys.executable, str(SCRIPT), "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "Pre-commit lint" in result.stdout


def test_quiet_flag_suppresses_ok_line(tmp_path: Path) -> None:
    """`--quiet` suppresses the OK summary on stderr (errors still print)."""
    wf = {"name": "ok", "nodes": [{"name": "n", "type": "t"}], "connections": {}}
    p = _write_wf(tmp_path, "ok.json", wf)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--quiet", str(p)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "OK" not in result.stderr
