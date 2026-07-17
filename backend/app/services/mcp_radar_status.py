"""G8.07.T4 — Status de tools MCP para o painel de radar.

Inventário estático + contagem dinâmica via AST/regex do `mcp_server.py`
sem importar FastMCP (evita side-effects em health checks).

Retorna payload pronto para `/api/v1/health/radar/expanded`.

Modified by Gustavo Almeida — G8.07.T4 Wave 36.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Caminho default relativo ao backend/
DEFAULT_MCP_SERVER = Path(__file__).resolve().parents[2] / 'mcp_server.py'

_TOOL_NAME_RE = re.compile(
    r'@mcp\.tool\s*\(\s*(?:name\s*=\s*[\'"]([\w\-]+)[\'"])?',
    re.MULTILINE,
)
_DEF_AFTER_TOOL_RE = re.compile(
    r'@mcp\.tool\b[^\n]*\n(?:async\s+)?def\s+(\w+)\s*\(',
    re.MULTILINE,
)


@dataclass(slots=True)
class McpToolStatus:
    name: str
    source: str = 'mcp_server.py'


@dataclass(slots=True)
class McpRadarReport:
    status: str  # up | down | warn
    tool_count: int
    tools: list[str] = field(default_factory=list)
    latency_ms: int = 0
    detail: str = ''
    path: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'latency_ms': self.latency_ms,
            'detail': self.detail,
            'tool_count': self.tool_count,
            'tools': self.tools,
            'path': self.path,
        }


def inventory_mcp_tools(source: str) -> list[str]:
    """Extrai nomes de tools do source do mcp_server.

    Preferência: name= no decorator; fallback: nome da def.
    """
    names: list[str] = []
    for m in _DEF_AFTER_TOOL_RE.finditer(source):
        names.append(m.group(1))
    # Se decorator usa name= explícito diferente da def, preferir name=
    named = [m.group(1) for m in _TOOL_NAME_RE.finditer(source) if m.group(1)]
    if named and len(named) >= len(names):
        return named
    # merge unique preserving order
    seen: set[str] = set()
    out: list[str] = []
    for n in names + named:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def build_mcp_radar(
    mcp_path: Path | None = None,
    *,
    min_tools: int = 1,
) -> McpRadarReport:
    """Lê mcp_server.py e monta report de radar."""
    start = time.perf_counter()
    path = mcp_path or DEFAULT_MCP_SERVER
    if not path.exists():
        return McpRadarReport(
            status='down',
            tool_count=0,
            latency_ms=int((time.perf_counter() - start) * 1000),
            detail=f'mcp_server missing: {path.name}',
            path=str(path),
        )
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
        tools = inventory_mcp_tools(text)
        elapsed = int((time.perf_counter() - start) * 1000)
        if len(tools) < min_tools:
            return McpRadarReport(
                status='warn',
                tool_count=len(tools),
                tools=tools,
                latency_ms=elapsed,
                detail=f'only {len(tools)} tools (min={min_tools})',
                path=str(path),
            )
        return McpRadarReport(
            status='up',
            tool_count=len(tools),
            tools=tools,
            latency_ms=elapsed,
            detail=f'{len(tools)} MCP tools inventoried',
            path=str(path),
        )
    except OSError as exc:
        return McpRadarReport(
            status='down',
            tool_count=0,
            latency_ms=int((time.perf_counter() - start) * 1000),
            detail=f'read error: {type(exc).__name__}',
            path=str(path),
        )


__all__ = [
    'DEFAULT_MCP_SERVER',
    'McpRadarReport',
    'McpToolStatus',
    'build_mcp_radar',
    'inventory_mcp_tools',
]
