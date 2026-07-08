# Skills Index — Cartório 2º Notas Uberlândia

> **Catálogo central** de todas as skills em `.agents/skills/`.
> **Status**: ✅ ativo · 🟡 parcial · ❌ quebrado
> **Última atualização**: 2026-07-08 (Squad 3)

## Legenda de categorias

| Tag | Categoria | Tools MCP relacionadas |
|---|---|---|
| `LLM` | LLMs, agentes de IA, modelos | LLM (17 tools) |
| `INFRA` | VPS, Docker Swarm, deploy | STATUS, DOCKER, EASYPANEL, UTILITY |
| `DATABASE` | Postgres, Redis, Clickhouse, Mongo | DB (10 tools) |
| `MONITORING` | Prometheus, Sentry, Grafana, SSL | MONITORING (8 tools) |
| `NETWORKING` | Tailscale, mesh VPN | NETWORKING (3 tools) |
| `SECURITY` | LGPD, PII, audit | (audit/pii internos) |
| `WORKFLOW` | Temporal, Paperclip, Langflow | WORKFLOW (4 tools) |
| `INTEGRATION` | WhatsApp, Telegram, Chatwoot, n8n | (in integrações dedicadas) |
| `OPS` | Operação, runbooks, backup | UTILITY (15 tools) |
| `AGENT` | Multi-agent, orquestração | LLM + WORKFLOW |
| `DOCS` | Documentação, ADRs | — |
| `SEARCH` | RAG, scraping, web | RAG, SEARCH |

---

## Catálogo

| Skill | Categoria | Status | Descrição | Path |
|---|---|---|---|---|
| `api` | INTEGRATION | ✅ | Endpoints REST do Cartório API (50+ rotas, LGPD, Telegram, auth) | [api/SKILL.md](api/SKILL.md) |
| `chatwoot` | INTEGRATION | ✅ | CRM Chatwoot (REST + MCP, 30 tools, handoff humano) | [chatwoot/SKILL.md](chatwoot/SKILL.md) |
| `coding-vps-21` | INFRA / LLM | ✅ | 21+ coding agents + MiniMax-M3 XMax Thinking (Lesson 159/160) | [coding-vps-21/SKILL.md](coding-vps-21/SKILL.md) |
| `coding-vps-tools-100` | INFRA | ✅ | Catálogo 100+ tools MCP do coding-vps_apenas_para_auxilio | [coding-vps-tools-100/SKILL.md](coding-vps-tools-100/SKILL.md) |
| `coding-vps-orchestrator` | INFRA | ✅ | Como usar o MCP orchestrator (CLI/HTTP/stdio) | [coding-vps-orchestrator/SKILL.md](coding-vps-orchestrator/SKILL.md) |
| `coding-vps-deploy` | INFRA | ✅ | Como deployar novos agents (Dockerfile + swarm + .env) | [coding-vps-deploy/SKILL.md](coding-vps-deploy/SKILL.md) |
| `coding-vps-monitor` | MONITORING | ✅ | Como monitorar 89 serviços (docker stats, port scan, health checks) | [coding-vps-monitor/SKILL.md](coding-vps-monitor/SKILL.md) |
| `easypanel` | INFRA | ✅ | EasyPanel API REST (deploy, env, logs, snapshots) | [easypanel/SKILL.md](easypanel/SKILL.md) |
| `hostinger` | INFRA | ✅ | VPS Hostinger (SSH, Tailscale, API, firewall) | [hostinger/SKILL.md](hostinger/SKILL.md) |
| `minimax-m3` | LLM | ✅ | MiniMax-M3 XMax Thinking via LiteLLM proxy | [minimax-m3/SKILL.md](minimax-m3/SKILL.md) |
| `n8n` | WORKFLOW | ✅ | N8N Workflow Engine (REST + MCP, 50 tools, 34 workflows ativos) | [n8n/SKILL.md](n8n/SKILL.md) |
| `supabase` | DATABASE | ✅ | Supabase auto-hospedado (REST, Auth, Storage, Edge Functions) | [supabase/SKILL.md](supabase/SKILL.md) |

---

## Resumo por categoria

| Categoria | # Skills | Tools MCP |
|---|---|---|
| LLM | 2 | 17 (chat_minimax + 16 agents) |
| INFRA | 6 | 39 (STATUS+DOCKER+EASYPANEL+UTILITY+NETWORKING) |
| INTEGRATION | 3 | (api, chatwoot, n8n) |
| MONITORING | 1 | 8 (Prometheus, Sentry, Grafana, SSL, Hostinger) |
| DATABASE | 1 | 10 (postgres, redis, clickhouse, mongo, etc.) |
| WORKFLOW | 1 | 4 (Temporal, Paperclip, Langflow) |
| **TOTAL** | **12** | **100+** |

---

## Como adicionar nova skill

1. Criar pasta: `mkdir -p .agents/skills/<name>`
2. Criar `SKILL.md` com YAML frontmatter (`name`, `description`, `type`, `created`).
3. Atualizar este INDEX.md (1 linha na tabela).
4. (Opcional) Adicionar hook de auto-regeneração em `.hooks/`.

## Como adicionar nova tool ao MCP orchestrator

Ver [coding-vps-orchestrator/SKILL.md](coding-vps-orchestrator/SKILL.md) e [coding-vps-tools-100/SKILL.md](coding-vps-tools-100/SKILL.md).

```python
# Em scripts/coding_vps_mcp_orchestrator.py
def my_tool(arg1: str) -> dict:
    """Descrição curta."""
    return {"result": "ok", "arg1": arg1}

# Em _register_xxx() соответствующей categoria
"my_tool": {"func": my_tool, "args": ["arg1"], "category": "xxx", "desc": "..."}
```

## Hooks ativos

- `.hooks/post-commit.sh` — syntax check do orchestrator + alerta de skills não indexadas.
- Ativar: `git config core.hooksPath .hooks`

## MCP config

- `.trae/mcp-servers/coding-vps.json` — server MCP stdio para TRAE IDE.
- Ver [docs/integrations/TRAE-coding-vps.md](../../docs/integrations/TRAE-coding-vps.md) para setup completo.

---

**Modified by Gustavo Almeida**
