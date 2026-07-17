# MCP Tools Inventory — cartorio-mcp-cabuloso (G7.09.T1)

**Source of truth:** `backend/mcp_server.py`  
**Protocol:** MCP 2025-03-26 (FastMCP)  
**Mount:** `/mcp` when `MCP_SERVER_ENABLED=true`  
**Standalone:** `make -C backend mcp-server` (default port 8765 / 8100)  
**Snapshot:** 2026-07-16 Wave 14 — count via `rg -c '@mcp.tool' backend/mcp_server.py`

> **Não hardcode o número no código de produto** — o inventário muda.
> Este doc é regenerável; confira o count real no arquivo.

---

## Tools expostas (grep `@mcp.tool(`)

| # | Tool name | Finalidade | PII? | HITL |
|---|-----------|------------|------|------|
| 1 | `cartorio_calcular_emolumento` | Emolumento MG 2026 | Não | N/A |
| 2 | `cartorio_consultar_protocolo` | Status protocolo | Mínimo (nº) | Read |
| 3 | `cartorio_criar_protocolo` | Cria protocolo DRAFT | Sim (consent) | **Obrigatório** |
| 4 | `cartorio_gerar_segunda_via` | Link PDF 2ª via | Sim | HITL |
| 5 | `cartorio_audit_verify` | Integridade chain | Não | Admin |
| 6 | `cartorio_saudacao` | Health check MCP | Não | N/A |
| 7 | `super_server_info` | Meta server | Não | N/A |
| 8+ | (demais no arquivo) | radar / LGPD / etc. | ver source | ver source |

Regenerar lista completa:

```bash
rg -n '@mcp.tool\(' backend/mcp_server.py -A 3
python3 scripts/g7_super_validator.py --skip-pytest --skip-ruff
```

---

## Clients MCP (config paths)

| Client | Config |
|--------|--------|
| Global cartorio | `~/.mavis/mcp/clients/cartorio-mcp-config.json` |
| Cursor / Claude / TRAE | `scripts/mcp_config.*.json` |
| Skills repo | `.agents/skills/api/SKILL.md` |

---

## Skills relacionadas (`.agents/skills/`)

| Skill | Uso |
|-------|-----|
| `api` | REST + WS + MCP cartorio |
| `chatwoot` | CRM handoff |
| `n8n` | workflows |
| `supabase` | PG/Auth/Storage |
| `easypanel` | deploy Swarm |
| `hostinger` | VPS SSH/Tailscale |
| `minimax-m3` | LLM coding plan |
| `coding-vps-*` | orchestrator / 62 tools / deploy / monitor |

---

## Smoke

```bash
# Local
cd backend && uv run python mcp_server.py
# Prod (se mount ativo)
curl -sS https://api.2notasudi.com.br/mcp | head -c 400
```

---

**Modified by Gustavo Almeida + cartorio-dev — G7 Wave 14 (G7.09.T1)**


## Client config example (G7.09.T2)

`scripts/mcp_config.cartorio-api.example.json` — copiar para `~/.mavis/mcp/clients/` e preencher env. **Sem secrets no git.**

**Modified by Gustavo Almeida — G7 Wave 18**
