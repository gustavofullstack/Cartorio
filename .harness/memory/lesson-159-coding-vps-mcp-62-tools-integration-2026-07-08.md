---
name: coding-vps-mcp-62-tools-integration-2026-07-08
description: >
  Squad 5: orchestrator real = 62 tools/13 cats (not 100). Register redis_ping +
  health_check_all. MCP configs TRAE/SOLO/Antigravity/Cursor/Claude without secrets.
  Smoke: scripts/validate_coding_vps_tools_60.sh
type: project
date: 2026-07-08
agent: squad5-integration
priority: P1
status: active
---

# Lesson 159 — coding-vps MCP 62 tools + TRAE/Antigravity integration

## Resumo

1. CLI real: `MCP orchestrator: 62 tools in 13 categories`
2. Docs/skills que dizem 100/92/85 estão stale
3. Integração canônica: `python …/coding_vps_mcp_orchestrator.py mcp`
4. `redis_ping` existia mas não estava em `_register_db()` — gap clássico
5. `health_check_all` adicionado como thin wrapper de `list_services`
6. Templates JSON em `scripts/mcp_config.{trae,antigravity,cursor,claude_desktop}.json` **sem** keys em plain text
7. Doc: `docs/platforms/coding-vps/INTEGRATION_TRAE_ANTIGRAVITY.md`
8. Memory espelho: `docs/platforms/coding-vps/MEMORY_2026-07-08.md`
9. Smoke: `bash scripts/validate_coding_vps_tools_60.sh`

## Regra operacional

> Antes de documentar tool count: rodar `list`. Antes de commitar mcp_config: grepar `sk-` / API keys.

## Ver também

- Lesson 158 (estado VPS services / MiniMax)
- Skill `.agents/skills/coding-vps-tools-100/SKILL.md`

Modified by Gustavo Almeida
