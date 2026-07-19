# MCP Tools Inventory — cartorio-mcp-cabuloso (G7.09.T1)

**Source of truth:** `backend/mcp_server.py`  
**Protocol:** MCP 2025-03-26 (FastMCP)  
**Mount:** `/mcp` when `MCP_SERVER_ENABLED=true`  
**Standalone:** `make -C backend mcp-server` (default port **8100**, overridable with `MCP_SERVER_PORT`; MCP endpoint at `/`)
**Mounted:** `POST /mcp` on the API origin when `MCP_SERVER_ENABLED=true`
**Snapshot:** 2026-07-19 — inventory must be regenerated from source before release.

> **Não hardcode o número no código de produto** — o inventário muda.
> Este doc é regenerável; confira o count real no arquivo.

---

## Tools expostas (grep `@mcp.tool(`)

| # | Tool name | Finalidade | Risco / autorização necessária |
|---|-----------|------------|
| 1 | `cartorio_calcular_emolumento` | Calcula emolumento | Leitura sem PII; não decide isenção/urgência jurídica. |
| 2 | `cartorio_consultar_protocolo` | Consulta protocolo | PII mínima; cliente MCP autenticado e auditável. |
| 3 | `cartorio_criar_protocolo` | Cria protocolo em `DRAFT` | PII + escrita; consentimento e revisão humana obrigatórios. |
| 4 | `cartorio_gerar_segunda_via` | Gera segunda via | PII/documento; exigir identidade, autorização e HITL. |
| 5 | `cartorio_audit_verify` | Verifica chain no banco | Operação administrativa somente leitura; acesso de operador. |
| 6 | `cartorio_audit_hash_sequence` | Verifica amostra offline | A entrada pode conter dados auditáveis; usar somente amostras scrubbed. |
| 7 | `cartorio_saudacao` | Metadados de saúde | Leitura, sem PII. |
| 8 | `cartorio_enviar_whatsapp_reaction` | Reage a mensagem WhatsApp | Efeito externo; confirmação humana antes do envio. |
| 9 | `cartorio_enviar_whatsapp_poll` | Envia enquete WhatsApp | Efeito externo; conteúdo aprovado e confirmação humana. |
| 10 | `cartorio_enviar_whatsapp_media` | Envia mídia WhatsApp | PII/documento + efeito externo; HITL obrigatório. |
| 11 | `cartorio_enviar_telegram_reaction` | Reage a mensagem Telegram | Efeito externo; confirmação humana antes do envio. |
| 12 | `cartorio_enviar_telegram_poll` | Envia enquete Telegram | Efeito externo; conteúdo aprovado e confirmação humana. |
| 13 | `cartorio_enviar_telegram_media` | Envia mídia Telegram | PII/documento + efeito externo; HITL obrigatório. |
| 14 | `super_server_info` | Metadados e tools registradas | Leitura; não divulgar configurações ou credenciais. |

> **Gate de ativação:** tools 8–13 têm efeito externo. O inventário não prova
> allowlist, autenticação por tool ou confirmação em runtime; esses controles
> devem ser demonstrados antes de liberar um agente autônomo.

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
# O endpoint MCP exige handshake JSON-RPC; não use GET como teste de tools.
curl -sS -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
```

---

**Modified by Gustavo Almeida + cartorio-dev — G7 Wave 14 (G7.09.T1)**


## Client config example (G7.09.T2)

`scripts/mcp_config.cartorio-api.example.json` — copiar para `~/.mavis/mcp/clients/` e preencher env. **Sem secrets no git.**

**Modified by Gustavo Almeida — G7 Wave 18**
