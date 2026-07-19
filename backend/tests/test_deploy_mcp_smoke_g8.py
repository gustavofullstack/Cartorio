"""Deployment smoke must verify that the public MCP transport is mounted."""

from __future__ import annotations

from pathlib import Path


def test_deploy_smoke_rejects_missing_mcp_mount() -> None:
    """A successful deploy cannot silently leave ``/mcp/`` returning 404."""
    deploy_workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml"
    ).read_text(encoding="utf-8")

    assert "MCP mount (must fail closed, never 404)" in deploy_workflow
    assert "https://api.2notasudi.com.br/mcp/" in deploy_workflow
    assert 'test "$mcp_status" = "401" || test "$mcp_status" = "503"' in deploy_workflow
