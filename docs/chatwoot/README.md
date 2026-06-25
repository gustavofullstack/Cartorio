# Chatwoot — Documentação Consolidada

> **Fonte**: chatwoot.com/docs + nossa experiência operacional
> **Versão**: Latest (Docker Swarm via Easypanel)
> **URL**: https://chat.2notasudi.com.br
> **Porta**: 3000 (interno)
> **Admin**: admin@2notasudi.com.br

---

## 🎯 Para que serve no Cartório

| # | Função | Uso |
|---|--------|-----|
| 1 | **CRM** | Gerenciar todas as conversas dos clientes |
| 2 | **Integrar WhatsApp** | Via Evolution API + webhooks |
| 3 | **Integrar Agent AI** | OpenClaw (Pietra) aparece como agente |
| 4 | **HITL** | Pausar o agent em qualquer conversa manualmente |
| 5 | **Automações** | Regras automáticas baseadas em condições |
| 6 | **Macros** | Ações predefinidas para atendentes |
| 7 | **Canned Responses** | Respostas prontas para FAQ |
| 8 | **Labels/Tags** | Categorização de conversas |
| 9 | **Teams** | Equipes de atendimento |
| 10 | **Reports** | Relatórios de atendimento e SLA |
| 11 | **Contacts** | Base de contatos integrada |
| 12 | **Inbox** | Canal WhatsApp conectado |

---

## 🔐 Autenticação

| Tipo | Como |
|------|------|
| **API v1** | Header `api_access_token: <token>` |
| **API v2** | OAuth 2.0 + Bearer token |
| **Web login** | Email + senha (admin@2notasudi.com.br) |

**Nossas tokens**:
- 2 access tokens reais configurados
- Token armazenado em `.env` da API

---

## 📡 Endpoints Principais (API v1)

| Endpoint | Método | Função |
|----------|--------|--------|
| `/api/v1/accounts` | GET | Lista contas |
| `/api/v1/accounts/:id/conversations` | GET | Lista conversas |
| `/api/v1/accounts/:id/conversations/:id` | GET | Detalhe conversa |
| `/api/v1/accounts/:id/conversations/:id/messages` | POST | Enviar mensagem |
| `/api/v1/accounts/:id/contacts` | GET/POST | Listar/criar contatos |
| `/api/v1/accounts/:id/agents` | GET | Lista agentes |
| `/api/v1/accounts/:id/labels` | GET/POST | Labels |
| `/api/v1/accounts/:id/canned_responses` | GET/POST | Canned responses |
| `/api/v1/accounts/:id/teams` | GET/POST | Teams |
| `/api/v1/accounts/:id/inboxes` | GET | Inboxes |

---

## 🔌 Webhooks (Recebidos pela API)

Eventos que o Chatwoot envia para nossa API:

| Evento | Quando | Endpoint |
|--------|--------|----------|
| `conversation_created` | Nova conversa | `/api/v1/webhook/chatwoot` |
| `conversation_updated` | Status muda | `/api/v1/webhook/chatwoot` |
| `message_created` | Nova mensagem | `/api/v1/webhook/chatwoot` |
| `message_updated` | Mensagem editada | `/api/v1/webhook/chatwoot` |
| `contact_created` | Novo contato | `/api/v1/webhook/chatwoot` |
| `contact_updated` | Contato editado | `/api/v1/webhook/chatwoot` |

---

## 👥 Estrutura Multi-Tenant

```
Chatwoot Account (1)
├── Inbox (WhatsApp)
├── Agents
│   ├── Humano (André, Gustavo, etc)
│   └── Bot (Pietra = OpenClaw)
├── Teams
├── Labels (tags)
├── Canned Responses (FAQ)
└── Conversations
    ├── Status: open/pending/resolved/snoozed
    └── Assignee: agent/team
```

---

## 🤖 HITL (Human In The Loop)

Para pausar o agent em qualquer conversa:

```
1. Atendente vê conversa no Chatwoot
2. Clica "Pausar Agent" (custom action)
3. API recebe webhook → pausa OpenClaw
4. Atendente assume (typing indicator + reply)
5. Quando terminar: "Retomar Agent"
6. Pietra retoma com contexto preservado
```

---

## ✅ Squad H — DONE 100% (8/8)

| H | Task | Status |
|---|------|--------|
| H01 | Configuração inicial | ✅ |
| H02 | Inbox WhatsApp | ✅ |
| H03 | Integração OpenClaw | ✅ |
| H04 | HITL (Human In The Loop) | ✅ |
| H05 | Labels e tags | ✅ |
| H06 | Canned responses FAQ | ✅ |
| H07 | Teams de atendimento | ✅ |
| H08 | Script helper criar API key | ✅ |

---

## ⚠️ INC-005b — HOLD Gustavo/CI

**Problema**: container `cartorio_chatwoot` está sem Networks no Docker Swarm.

**Sintoma**: API tenta chamar Chatwoot e falha (network error).

**Fix necessário**: Adicionar network `cartorio_supabase_default` no Easypanel UI.

**Ação**: Gustavo/CI manual via Easypanel UI.

---

## 🔗 Links Úteis

| Recurso | URL |
|---------|-----|
| Docs oficial | https://www.chatwoot.com/docs/ |
| Developer docs | https://www.chatwoot.com/developers/api/ |
| GitHub | https://github.com/chatwoot/chatwoot |
| Webhooks | https://www.chatwoot.com/developers/api/webhooks/ |
| API reference | https://www.chatwoot.com/developers/api/ |
| Docker Hub | https://hub.docker.com/r/chatwoot/chatwoot |

---

## 🎯 Integração com nosso Sistema

```
Cliente (WhatsApp)
    ↓
Evolution API
    ↓ webhook
N8N (workflow #03-handoff-human-chatwoot)
    ↓ REST
API (FastAPI) → Supabase (audit_log + cliente)
    ↓
Chatwoot (cria/atualiza conversa)
    ↓
Atendente humano assume se HITL ON
```

---

## 📊 Squad Status Atual

- H01-H08: ✅ **DONE 100%**
- Squad H é a única com **100% completo** entre todas as squads!
- 8/8 tasks implementadas, testadas e em produção

---

## 📁 Arquivos relacionados no repo

- `canned-responses-chatwoot.json` — 50+ respostas prontas para FAQ
- `chatwoot-setup-2026-06-25.json` — Setup completo exportado
- `scripts/diagnose_chatwoot_crashloop.sh` — Diagnóstico INC-005b
- `scripts/fix_chatwoot_url.sh` — Fix URL FQDN público
- `scripts/create_chatwoot_api_key.sh` — Helper para criar API key