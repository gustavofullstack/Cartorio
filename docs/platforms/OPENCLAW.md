# OpenClaw Gateway — Cartório 2º Ofício

> **AI Agent Gateway** — Gerencia agents, skills, tools, sessões e channels.
> Container: `cartorio_openclaw-gateway` (porta interna 18789, externa 18790).

## Status atual (2026-06-25 10:25 BRT)

| Campo | Valor |
|---|---|
| Container | `cartorio_openclaw-gateway.1.vpibdx7ecjnaz81mz7z1ou739` |
| Up time | 18h+ (healthy) |
| URL interna | `http://100.99.172.84:18789/` |
| URL externa | `https://agent.2notasudi.com.br/` |
| Versão | `2026.6.10` (ghcr.io/openclaw/openclaw:latest) |
| Agent | `main` (Pietra Cartório) |
| Provider LLM | Opencode-Go (`sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ`) |
| Modelo primário | `minimax-m3` (1M context) |
| Temperature | 0.0 |
| Thinking | ON (adaptive) |
| Skills | 38 declaradas (todas `enabled=false` exceto `healthcheck`) |
| Tools | 5 (evolution-api, supabase, calendar, audit-log, n8n) |

## Arquitetura (Lesson 152 — OpenClaw é AGENT RUNTIME, não LLM proxy)

```
Cliente (N8N/API/Telegram)
    │
    ▼
OpenClaw Gateway ───→ opencode_go (LLM real, HTTP /v1/chat/completions)
    │                        │
    ├── Skills (38)          └── Model: minimax-m3 (1M context, thinking)
    ├── Tools (5)
    ├── Sessions/WebSocket
    └── Config hot-reload
```

**Importante**: OpenClaw serve como **runtime de agent** (skills, tools, sessões, WebSocket).
O LLM real é chamado via **opencode_go direto**. OpenClaw NÃO é um proxy LLM REST.

## Endpoints

| Método | Path | Auth | Descrição |
|---|---|---|---|
| GET | `/health` | none | Healthcheck → `{"ok":true,"status":"live"}` |
| GET | `/v1/agents` | - | Lista agents configurados |
| WS | `/v1/chat` | - | WebSocket chat streaming (FUNCIONANDO) |
| POST | `/v1/chat` | bearer | Chat REST (HTTP 404 — gateway schema rejeitado, WS workaround) |
| POST | `/v1/messages` | bearer | Envio de mensagens |

**Nota**: `/v1/chat` via HTTP retorna 404 (gateway.http schema rejeitado desde versão 2026.6.10).
O WebSocket `/v1/chat` funciona normalmente e é usado por N8N, Telegram e UI.

## Integrações ativas

| Serviço | Tipo | Detalhes |
|---|---|---|
| **N8N** | Workflow | `13-openclaw-chat-bridge.json` + `14-opencode-go-fallback.json` |
| **API FastAPI** | Backend | Wrapper LLM em `backend/app/services/llm.py` com fallback chain |
| **Telegram** | Bot | `@test_cartorio_bot` via N8N workflow 31 |
| **Supabase** | Tool | Tools `supabase` (queries RLS) + `audit-log` (RPC) |
| **Redis** | Cache | Cache responses + session storage (DB 5) |
| **Evolution API** | Tool | Tool `evolution-api` (send_message) + integração via API |

## Configuração

**Config path**: `/home/node/.openclaw/agents/main/agent/`

Arquivos:
- `agent.json` — Persona, modelo, temperatura, thinking
- `models.json` — Provedores e modelos disponíveis
- `openclaw-agent.sqlite` — Estado persistente do agent
- `codex-home/` — Workspace do agent
- `plugins/` — Plugins carregados

**Config hot-reload**: OpenClaw detecta mudanças nos arquivos de config automaticamente
(logs: `config change detected; evaluating reload` + `config hot reload applied`).

## Problemas corrigidos (2026-06-25 07:41 BRT)

| # | Problema | Correção | Status |
|---|---|---|---|
| 1 | Modelo `qwen3.7-max` quebrado (401 `not supported for format oa-compat`) | Patch para `minimax-m3` via hot reload | ✅ |
| 2 | Contexto limitado a 131.1k | Configurado 1M via `contextTokens=1048576` | ✅ |
| 3 | Thinking desativado | `thinkingDefault=adaptive` no provider config | ✅ |
| 4 | API em loop de restart (CARTORIO_API_KEY faltando) | 33 env-add + force restart | ✅ |

## Problemas conhecidos ainda pendentes

| # | Problema | Impacto | Plano |
|---|---|---|---|
| 1 | Skills todas `enabled=false` exceto `healthcheck` | Agent sem skills ativas | Habilitação gradual conforme demanda |
| 2 | HTTP `/v1/chat` 404 | Não pode usar como proxy REST puro | WS funciona, workaround via API direta |
| 3 | Sem métricas Prometheus | Sem visibilidade de performance | Sprint futuro (E06) |

## Fallback chain

Quando OpenClaw falha, a API tenta (em ordem):
1. OpenClaw Gateway (primary)
2. Opencode-Go direto (fallback via N8N WF 14)
3. OpenAI (se configurado)
4. Anthropic (se configurado)

## Skills (por habilitar)

38 skills declaradas no gateway, todas com hash SHA256.
Nenhuma está ativa (`enabled=false`) exceto `healthcheck`.
A habilitação será gradual conforme demanda dos workflows N8N.

Skills planejadas para ativar:
- `saudacoes` — Boas-vindas + menu inicial
- `protocolo-tracker` — Status de protocolo
- `emolumento-calc` — Cálculo de emolumentos
- `handoff-trigger` — Transferência para humano
- `agendamento` — Agendamento de atendimento
- `segunda-via` — Segunda via de documentos
- `pesquisa-satisfacao` — Pesquisa de satisfação

## Troubleshooting

**Problema**: Gateway não responde
```
curl -s https://agent.2notasudi.com.br/health
# Esperado: {"ok":true,"status":"live"}
```

**Problema**: Modelo 401 (formato não suportado)
```bash
# Verificar modelo configurado
docker exec cartorio_openclaw-gateway sh -c "cat /home/node/.openclaw/agents/main/agent/agent.json" | grep model
```

**Problema**: Hot reload não funciona
```bash
# Forçar restart do container
docker service update --force cartorio_openclaw-gateway
```

## Referências

- Workflows N8N: `infra/n8n-workflows/13-openclaw-chat-bridge.json`, `14-opencode-go-fallback.json`
- Provider key: `.env` → `OPENCODE_GO_API_KEY`, `OPENCLAW_API_KEY`
- Config VPS: `/var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/openclaw.json`
- Lesson 152: "OpenClaw é AGENT RUNTIME, não LLM proxy" — `.harness/memory/MEMORY.md`
