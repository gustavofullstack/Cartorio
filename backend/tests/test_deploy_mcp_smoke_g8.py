"""Deployment smoke must verify that the public MCP transport is mounted."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_deploy_smoke_rejects_missing_mcp_mount() -> None:
    """A successful deploy cannot silently leave ``/mcp/`` returning 404."""
    deploy_workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml"
    ).read_text(encoding="utf-8")

    assert "MCP mount (must fail closed, never 404)" in deploy_workflow
    assert "https://api.2notasudi.com.br/mcp/" in deploy_workflow
    assert 'test "$mcp_status" = "401" || test "$mcp_status" = "503"' in deploy_workflow


def test_legacy_vps_deploy_is_manual_and_fail_closed() -> None:
    """VPS restarts require explicit human confirmation and SUI approval."""
    path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    # PyYAML 1.1 parses the YAML 1.2 boolean-like key ``on`` as ``True``.
    trigger = config.get("on", config.get(True))
    assert isinstance(trigger, dict)
    assert "push" not in trigger
    assert "workflow_dispatch" in trigger
    inputs = trigger["workflow_dispatch"]["inputs"]
    assert inputs["confirm_deploy"]["type"] == "boolean"
    deploy = config["jobs"]["deploy"]
    guard = str(deploy["if"])
    assert "inputs.confirm_deploy == true" in guard
    assert "vars.VPS_DEPLOY_ENABLED == 'true'" in guard
    assert "vars.SUI_CHECKLIST_APPROVED == 'true'" in guard
