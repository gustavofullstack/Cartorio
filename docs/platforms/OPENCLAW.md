# OpenClaw Gateway — Cartório 2º Ofício

> **AI Agent Gateway** (LLM router + skills + tools + channels).
> Container: `cartorio_openclaw-gateway`. Endpoint interno: `:18789`.

## Status atual (2026-06-24)

| Campo | Valor |
|---|---|
| Container | `cartorio_openclaw-gateway` |
| Up time | 36s (healthy, recém-restart) |
| URL interna | `http://100.99.172.84:18789/` (HTML UI 200 OK) |
| Versão | `2026.6.10` |
| Agent | `CartórioBot` |
| Modelos | `minimax-m3` (1M context), `deepseek-v4-flash` (131k), `minimax-m2.7` (131k) |
| Provider | Opencode-Go (nova key `sk-xcRwExjQ`) |
| Skills | 38 totais (todos com hash, todos `enabled=false` exceto `healthcheck`) |
| Channels | 7 declarados (whatsapp, telegram, web) |
| Tools | 5 (evolution-api, supabase, calendar, audit-log, n8n) |
| Pendência | OpenClaw M3 fix (temperature=0.0 + model=minimax-m3 no `agent.json`) |

## Endpoints consumidos

| Método | Path | Auth | Descrição |
|---|---|---|---|
| GET | `/` | none | HTML UI gateway |
| POST | `/v1/chat/completions` | bearer | Chat completion (compat OpenAI) |
| GET | `/health` | none | Healthcheck |
| WS | `/ws/chat` | none | WebSocket streaming |
| POST | `/v1/skills/invoke` | bearer | Invoca skill por nome |
| GET | `/v1/models` | bearer | Lista modelos disponíveis |

**Auth**: bearer token (`OPENCLAW_API_KEY` em `/etc/easypanel/projects/cartorio/api/code/.env`).

## Integrações ativas

- **N8N** → workflow `openclaw-bridge` chama `/v1/chat/completions` para fallback LLM
- **Telegram bot** `@test_cartorio_bot` → `bot ↔ OpenClaw` (com thinking ON, Squad F05)
- **API FastAPI** → wrapper LLM (`backend/app/services/llm.py`) com fallback chain OpenClaw→Opencode-Go→OpenAI→Anthropic
- **Supabase** → tools `supabase` (queries RLS) + `audit-log` (RPC `registrar_auditoria`)
- **Redis** → cache responses + session storage (DB 5)
- **Evolution/Chatwoot** → tool `evolution-api` (send_message) + integração via API FastAPI

## Tabelas / Schemas / Workflows

- **OpenClaw config** (`openclaw.json`):
  - 3 models: `minimax-m3` (1M), `deepseek-v4-flash` (131k), `minimax-m2.7` (131k)
  - 1 provider: `opencode-go` (key `sk-xcRwExjQ`)
  - 7 channels: whatsapp, telegram, web
  - 5 tools: evolution-api, supabase, calendar, audit-log, n8n
  - 38 skills (todos com hash, todos `enabled=false` exceto `healthcheck`)
- **N8N workflow** `openclaw-fallback` (fallback LLM) + `openclaw-bridge` (bridge LLM)
- **DB cartorio**: tabela `agent_session` (state persistente cross-session) + `agent_skill_invocation` (log de skills chamadas)

## Problemas conhecidos + fixes aplicados

- **OpenClaw M3 fix pendente** → aplicar `temperature=0.0` + `model=minimax-m3` no `agent.json` (Mavis/Pietra trabalhando)
- **Skills todas `enabled=false` exceto `healthcheck`** → habilitação gradual conforme demanda
- **Memory persistente cross-session** (Squad E07) → RAG em `docs/leads`, `docs/platforms`, `.harness/memory`
- **Latency budget** (Squad E06) → p50<1s, p95<3s, p99<5s + métricas prometheus (pendente)
- **Crash-loop check** (Squad E08) → restart + healthcheck + log rotation + sentry (pendente)
- **Telegram bot @CartorioBot** (Squad E09) → webhook setado, last_error era "Read timeout" (N8N reiniciou)

## Próximas tasks (Squad E do plan 2026-06-24)

- **E01** Verificar runtime: gateway responde, THINKING_ENABLED, modelo, fallback
- **E02** Auditar persona workspace (remover emojis, sério/direto/curto)
- **E03** Criar/atualizar skills: 7 + 6 direitos LGPD = 13
- **E04** Harness fortíssimo: usar SEMPRE {MCPs,tools,plugins,skills,hooks}, contexto preso, funções fortes
- **E05** Fallback chain: OpenClaw→Opencode-Go→OpenAI→Anthropic
- **E06** Latency budget p50<1s, p95<3s, p99<5s + métricas prometheus
- **E07** Memory persistente cross-session (RAG docs/leads, docs/platforms, .harness/memory)
- **E08** Crash-loop check: restart, healthcheck, log rotation, sentry
- **E09** Telegram bot @CartorioBot responde comandos
- **E10** Documentação OpenClaw completa

Ver plano completo: `.harness/reins/cartorio-dev/tasks/2026-06-24-plan.json` (Squad E).

