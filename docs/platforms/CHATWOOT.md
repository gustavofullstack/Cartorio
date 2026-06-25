# Chatwoot — Cartório 2º Ofício

> **CRM open-source** (multi-canal, multi-agente, inbox unificado).
> Self-hosted (LGPD art. 33 — dado não sai do VPS). Container: `cartorio_chatwoot`.

## Status atual (2026-06-25 10:40 BRT)

| Campo | Valor |
|---|---|
| Containers | `cartorio_chatwoot.1` (11h UP) + `cartorio_chatwoot-sidekiq.1` (19h UP) |
| URL pública | `https://chat.2notasudi.com.br` (Traefik SSL) |
| Versão | `chatwoot/chatwoot:latest` |
| DB tabelas | 92 (accounts, users, conversations, messages, inboxes, etc) |
| Access tokens | 2 reais (User id 2 + AgentBot id 3) |
| Health API | `GET /api/v1/accounts` → 200 OK (9ms via health/integracoes) |
| Sidekiq | Background jobs ativo |

## Arquitetura

```
Cliente (WhatsApp/Web/Telegram)
    │
    ▼
Chatwoot Inbox ───→ Agente humano (HITL via Chatwoot UI)
    │
    ├── Webhook → N8N → API → Supabase/Redis
    ├── Agent Bot (pendente criar via UI Super Admin)
    └── Macros/Automações (pendente configurar)
```

## Endpoints da API

| Método | Path | Descrição |
|---|---|---|
| GET | `/api/v1/accounts` | Lista accounts |
| POST | `/api/v1/accounts/{id}/conversations` | Cria conversa |
| POST | `/api/v1/accounts/{id}/conversations/{cid}/messages` | Envia mensagem |
| GET | `/api/v1/accounts/{id}/conversations/{cid}` | Detalhes conversa |
| POST | `/api/v1/accounts/{id}/agent_bots` | Cria bot agent |
| POST | `/api/v1/webhooks` | Cria webhook subscriber |
| GET | `/api/v1/accounts/{id}/inboxes` | Lista inboxes |

**Auth**: `api_access_token` (header `api_access_token: <token>` ou `Authorization: Bearer <token>`).

## Funções do Chatwoot no Ecossistema

| Função | Status | Detalhes |
|---|---|---|
| **Integrar WhatsApp** | 🔶 Parcial | Inbox Baileys independente (sem Evolution). Pendente: canal oficial |
| **Agent AI (Pietra)** | 🔶 Parcial | Pendente criar Agent Bot no Super Admin |
| **HITL** | 🔶 Parcial | WF `handoff-human` existe, falta Agent Bot criado |
| **Macros** | ⬜ Pendente | 10 macros a criar |
| **Canned Responses** | ⬜ Pendente | 50+ templates jurídicos |
| **Automações** | ⬜ Pendente | Keywords, opt-out, protocolos |

## Integrações ativas

| Serviço | Tipo | Detalhes |
|---|---|---|
| **N8N** | Workflow | `handoff-human` (OpenClaw→humano) + webhook inbound |
| **API FastAPI** | Service | `chatwoot_service.py` (CRUD conversas + handoff) + webhook `/api/v1/webhook/chatwoot` (HMAC) |
| **Supabase** | DB | Tabela `chatwoot_conversation_meta` (custom attributes) |
| **OpenClaw** | Handoff | Bot→humano via API FastAPI |
| **Redis** | Cache | Session storage para contexto agente (DB 4) |

## Fluxo de Handoff (N8N → Chatwoot)

```
OpenClaw detecta confidence < 0.85
    → POST /api/v1/atendimento (handoff=true)
    → N8N workflow handoff-human
    → Chatwoot API createConversation + sendMessage
    → Agente humano assume via Chatwoot UI
```

## Problemas conhecidos

| # | Problema | Status |
|---|---|---|
| 1 | `chatwoot.2notasudi.com.br` DNS NXDOMAIN (precisa A record) | ⚠️ Gustavo |
| 2 | CHATWOOT_API_KEY no .env — placeholder pendente | ⚠️ Gustavo |
| 3 | Agent Bot @CartorioBot — precisa Super Admin UI | ⚠️ Gustavo |
| 4 | Inbox Evolution não configurada (WhatsApp via Baileys direto) | 🔶 Parcial |
| 5 | SSL self-signed CN=Easypanel (válido até 2036, funcional) | ✅ OK |

## Troubleshooting

### API retorna HTML de login
**Causa**: Rota do Traefik não chega no backend Chatwoot.
**Fix**: Verificar Traefik router `chat.2notasudi.com.br → cartorio_chatwoot:3000`

### Health check
```bash
curl -s https://chat.2notasudi.com.br/api/v1/accounts
# 200 OK = funcionando. 401 = API key errada.
```

## Recursos do Chatwoot a configurar

- [ ] **Inbox WhatsApp** (Evolution via Baileys)
- [ ] **Agent Bot** "Cartório Assistant" (criar via Super Admin UI)
- [ ] **Canned Responses** — 50+ templates (FAQ cartorário)
- [ ] **Macros** — 10 macros (identificar/transferir/resumir)
- [ ] **Automações** — Keywords, opt-out LGPD, protocolos
- [ ] **Labels/Tags** — Categorização de conversas
- [ ] **Reports** — Métricas de atendimento

## Referências

- Container: `cartorio_chatwoot` (porta 3000) + `cartorio_chatwoot-sidekiq`
- URL: `https://chat.2notasudi.com.br`
- DB: PostgreSQL database `chatwoot` no Supabase
- Workflows N8N: `handoff-human`, `chatwoot-events`, `bot-agent`
- Documentação oficial: `docs/platforms/CHATWOOT_QUICK.md` (197 linhas)
- Doc oficial auto-gerada: `docs/platforms/Chatwoot.md` (78 linhas — legado)
