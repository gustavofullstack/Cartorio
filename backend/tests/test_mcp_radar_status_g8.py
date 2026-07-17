"""G8.07.T4 — MCP tools status no radar.

Modified by Gustavo Almeida — Wave 36.
"""

from __future__ import annotations

from pathlib import Path

from app.services.mcp_radar_status import build_mcp_radar, inventory_mcp_tools


SAMPLE = '''
@mcp.tool(
    name="cartorio_saudacao",
    description="hi",
)
async def cartorio_saudacao() -> dict:
    return {}

@mcp.tool(
    name="cartorio_audit_verify",
    description="audit",
)
async def cartorio_audit_verify() -> dict:
    return {}
'''


def test_inventory_named_tools() -> None:
    tools = inventory_mcp_tools(SAMPLE)
    assert 'cartorio_saudacao' in tools
    assert 'cartorio_audit_verify' in tools
    assert len(tools) >= 2


def test_build_mcp_radar_from_real_file() -> None:
    report = build_mcp_radar()
    assert report.status in {'up', 'warn', 'down'}
    d = report.to_dict()
    assert 'tool_count' in d
    assert 'tools' in d
    if report.status == 'up':
        assert report.tool_count >= 1
        assert isinstance(report.tools, list)


def test_missing_file(tmp_path: Path) -> None:
    report = build_mcp_radar(tmp_path / 'nope.py')
    assert report.status == 'down'
    assert report.tool_count == 0


def test_empty_tools_warn(tmp_path: Path) -> None:
    p = tmp_path / 'mcp_server.py'
    p.write_text('# no tools\n', encoding='utf-8')
    report = build_mcp_radar(p, min_tools=1)
    assert report.status == 'warn'
