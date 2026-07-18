"""G8.19.T4 — testes do auditor de modificações em workflows N8N críticos."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "n8n_wf_audit.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("n8n_wf_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["n8n_wf_audit"] = module
    spec.loader.exec_module(module)
    module._git_log_cached.cache_clear()
    return module


@pytest.fixture
def audit_module() -> Any:
    return _load_module()


def _write_workflow(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _entry(timestamp: str, workflow: str = "critical.json") -> dict[str, str]:
    return {
        "workflow": workflow,
        "workflow_id": "wf-test",
        "workflow_hash": "a" * 64,
        "threshold": "critical",
        "commit": "b" * 40,
        "author": "Audit User",
        "email": "audit@example.invalid",
        "timestamp": timestamp,
        "subject": "test: workflow update",
    }


def test_compute_hash_deterministic(audit_module: Any, tmp_path: Path) -> None:
    first = _write_workflow(
        tmp_path / "first.json",
        {"name": "WF", "nodes": [{"type": "set", "name": "Node"}], "connections": {}},
    )
    second = tmp_path / "second.json"
    second.write_text(
        '{"connections":{},"nodes":[{"name":"Node","type":"set"}],"name":"WF"}',
        encoding="utf-8",
    )
    assert audit_module.compute_hash(first) == audit_module.compute_hash(second)


def test_compute_hash_changes_on_edit(audit_module: Any, tmp_path: Path) -> None:
    workflow = _write_workflow(
        tmp_path / "workflow.json",
        {"name": "WF", "nodes": [{"name": "Before", "type": "set"}], "connections": {}},
    )
    before = audit_module.compute_hash(workflow)
    _write_workflow(
        workflow,
        {"name": "WF", "nodes": [{"name": "After", "type": "set"}], "connections": {}},
    )
    assert audit_module.compute_hash(workflow) != before


def test_compute_hash_ignores_execution_payload(audit_module: Any, tmp_path: Path) -> None:
    workflow = _write_workflow(
        tmp_path / "workflow.json",
        {
            "name": "WF",
            "nodes": [{"name": "Node", "type": "set"}],
            "connections": {},
            "pinData": {"Node": [{"json": {"cpf": "000.000.000-00"}}]},
            "staticData": {"last_execution": "first"},
        },
    )
    first = audit_module.compute_hash(workflow)
    _write_workflow(
        workflow,
        {
            "name": "WF",
            "nodes": [{"name": "Node", "type": "set"}],
            "connections": {},
            "pinData": {"Node": [{"json": {"cpf": "111.111.111-11"}}]},
            "staticData": {"last_execution": "second"},
        },
    )
    assert audit_module.compute_hash(workflow) == first


def test_critical_wfs_listed(audit_module: Any) -> None:
    expected = {
        "template-orcamento-escritura.json",
        "02-criar-protocolo.json",
        "08-audit-verify-diario.json",
        "22-audit-verify-6h.json",
        "23-lgpd-esqueci-v2.json",
        "24-retencao-diaria.json",
    }
    assert expected <= set(audit_module.CRITICAL_WFS)
    assert all((ROOT / audit_module.WORKFLOW_DIR / name).is_file() for name in expected)


def test_main_no_args_prints_to_stdout(
    audit_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshots = [
        {"path": "critical.json", "id": "wf-test", "hash": "a" * 64, "threshold": "critical"}
    ]
    entries = [_entry("2026-07-18T12:00:00+00:00")]
    monkeypatch.setattr(
        audit_module,
        "collect_modifications",
        lambda root, workflows: (snapshots, entries),
    )
    assert audit_module.main([], root=ROOT) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["modifications_count"] == 1
    assert report["entries"][0]["workflow_id"] == "wf-test"


def test_main_with_since_filter(
    audit_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    entries = [
        _entry("2026-07-17T12:00:00+00:00"),
        _entry("2026-07-18T12:00:00+00:00"),
    ]
    monkeypatch.setattr(
        audit_module,
        "collect_modifications",
        lambda root, workflows: ([], entries),
    )
    assert audit_module.main(["--since", "2026-07-18T00:00:00Z"], root=ROOT) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["modifications_count"] == 1
    assert report["entries"][0]["timestamp"] == "2026-07-18T12:00:00+00:00"


def test_main_with_critical_only_filter(
    audit_module: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    selected: list[str] = []
    monkeypatch.setattr(
        audit_module,
        "CRITICAL_WFS",
        {"critical.json": "critical", "high.json": "high"},
    )

    def fake_collect(root: Path, workflows: tuple[str, ...]):
        selected.extend(workflows)
        return [], []

    monkeypatch.setattr(audit_module, "collect_modifications", fake_collect)
    assert audit_module.main(["--critical-only"], root=ROOT) == 0
    report = json.loads(capsys.readouterr().out)
    assert selected == ["critical.json"]
    assert report["selected_wfs"] == ["critical.json"]


def test_main_with_output_file(
    audit_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        audit_module,
        "collect_modifications",
        lambda root, workflows: ([], [_entry("2026-07-18T12:00:00+00:00")]),
    )
    output = tmp_path / "audit.json"
    assert audit_module.main(["--output", str(output)], root=ROOT) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["modifications_count"] == 1
    assert f"Report written to {output}" in capsys.readouterr().out


def test_git_log_cache_avoids_duplicate_subprocess(
    audit_module: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="commit|Author|a@example.invalid|0|subject", stderr="")

    monkeypatch.setattr(audit_module.subprocess, "run", fake_run)
    audit_module._git_log_cached.cache_clear()
    first = audit_module._git_log_cached(str(tmp_path), "critical.json", "head")
    second = audit_module._git_log_cached(str(tmp_path), "critical.json", "head")
    assert first == second
    assert len(calls) == 1
    assert calls[0][:2] == ["git", "log"]
