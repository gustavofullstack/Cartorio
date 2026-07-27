# `.brain/agents/` — Agent registry

Catálogo dos agents ativos no projeto Cartório. Cada agent tem papel, plataforma e responsabilidade clara.

**Regra absoluta:** Todo o runtime roda na VPS Hostinger (`187.77.236.77` / Tailscale `100.99.172.84`). MacBook = cliente SSH apenas. Nenhuma máquina local é parte do projeto.

## Agents ativos (2026-07-27)

| Agent | Plataforma | Modelo | Role | Status |
|---|---|---|---|---|
| **Hermes Cartório Gateway** | VPS Docker Swarm | MiniMax-M3 (via `hermes_llm_api_key`) | Agent AI runtime — orquestra conversas, chama MCP tools, responde via Photon/API | 🔴 NOT_DEPLOYED (stack pronto em `infra/hermes/`) |
| **FastAPI Backend** | VPS Docker Swarm (`cartorio_api`) | — | API REST 220+ endpoints, MCP Server 15 tools, Dashboard, Webhooks | 🟢 OPERATIONAL |
| **Cartório Agent (Brain)** | VPS via FastAPI | MiniMax-M3 / LiteLLM | `cartorio_agent.py` (58KB) — agente IA principal, chat pipeline, PII scrub | 🟢 OPERATIONAL |
| **OpenClaw Gateway** | VPS Docker Swarm | deepseek-v4-flash | Agent AI runtime alternativo (Pietra Cartório) | 🟢 OPERATIONAL |
| **N8N Workflow Engine** | VPS Docker Swarm | — | 32 workflows, automação de processos, triggers | 🟡 PARTIALLY_INTEGRATED |

## Integrações de Canal (VPS)

| Canal | Serviço VPS | Status |
|---|---|---|
| Telegram | `@test_cartorio_bot` via webhook | 🟢 CONNECTED |
| WhatsApp | Evolution API 2.3.7 | 🔴 DEGRADED (sessão close — QR pendente) |
| iMessage | Photon sidecar (Hermes) | 🔴 NOT_DEPLOYED |
| Web Chat | Chatwoot CRM | 🟡 DEGRADED (API 401) |
| MCP | FastMCP em `/mcp` | 🟢 OPERATIONAL (15 tools) |

## Times de agentes (desenvolvimento)

| Agent | Papel | Escopo |
|---|---|---|
| **cartorio-dev** | Backend FastAPI / SQLAlchemy / audit / PII | Implementação + testes |
| **cartorio-n8n** | Workflows n8n / Evolution / OpenClaw / multi-canal / deploy | Integração + deploy |
| **cartorio-lgpd** | LGPD / RIPD / retenção / privacy policy / erasure rights | Review + sign-off |

## Atualizado em 2026-07-27 — Stage 9 Limpeza VAIO + Diagnóstico VPS Master

Próximo: Resolver 5 bloqueios P0 (Hermes deploy, WhatsApp QR, Chatwoot credencial, N8N chave, iMessage/Photon).