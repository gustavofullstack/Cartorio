# Chatwoot — Cartório 2º Ofício

> **Customer support platform** (multi-canal, multi-agente, open-source).
> Self-hosted (LGPD). Imagem: `chatwoot/chatwoot:latest`.

## Status atual (2026-06-24)

| Campo | Valor |
|---|---|
| Containers | `cartorio_chatwoot` + `chatwoot-sidekiq` |
| Up time | 16h (ambos healthy) |
| URL pública | `https://chatwoot.2notasudi.com.br` (Traefik) |
| Versão | latest |
| DB tabelas | 92 (accounts, users, conversations, messages, inboxes, etc) |
| Access tokens no DB | 2 (User id 2, AgentBot id 3) — criados 2026-06-23 |
| `CHATWOOT_API_KEY` no `.env` API | populado (User token) |
| SSL | self-signed CN=Easypanel (válido até 2036) |
| Pendência | H02 inbox Evolution, H09 DNS `chat.2notasudi.com.br` |

## Endpoints consumidos

| Método | Path | Auth | Descrição |
|---|---|---|---|
| GET | `/api/v1/accounts` | bearer api_access_token | Lista accounts |
| POST | `/api/v1/accounts/{id}/conversations` | bearer | Cria conversa |
| POST | `/api/v1/accounts/{id}/conversations/{cid}/messages` | bearer | Envia mensagem |
| GET | `/api/v1/accounts/{id}/conversations/{cid}` | bearer | Detalhes conversa |
| POST | `/api/v1/accounts/{id}/agent_bots` | bearer | Cria bot agent |
| POST | `/api/v1/webhooks` | bearer | Cria webhook subscriber |
| GET | `/api/v1/accounts/{id}/inboxes` | bearer | Lista inboxes (WhatsApp Baileys) |

**Auth**: `api_access_token` (header `api_access_token: <token>` ou `Authorization: Bearer <token>`).

## Integrações ativas

- **Evolution** → Inbox WhatsApp Baileys (independente, sem ponte)
- **N8N** → workflow `chatwoot-events` (webhook inbound) + `handoff-human` (OpenClaw→humano)
- **API FastAPI** → `chatwoot_service.py` (CRUD conversas + handoff) + webhook `/api/v1/webhook/chatwoot` (HMAC)
- **Supabase** → tabela `chatwoot_conversation_meta` (metadata persistente)
- **OpenClaw** → handoff OpenClaw↔humano via API (Squad E09, H03)
- **Redis** → session storage para contexto agente (DB 4)

## Tabelas / Schemas / Workflows

- **92 tabelas** no schema `public` do DB Chatwoot (accounts, users, conversations, messages, inboxes, contact_inboxes, etc)
- **2 access tokens** (User id 2 + AgentBot id 3) — tokens reais já no DB, prontos pra uso
- **N8N workflows**:
  - `chatwoot-events` (webhook inbound) → normaliza payload → insere Supabase
  - `handoff-human` (OpenClaw escalação) → cria conversa + atribui agente humano
  - `bot-agent` (resposta automática pré-config)
- **DB cartorio**: tabela `chatwoot_conversation_meta` (custom attributes: protocolo, emolumento_total, lgpd_consent_id, opt_out_flag)

## Problemas conhecidos + fixes aplicados

- **API `/api/v1/accounts` retornava HTML de login** (proxy/route do EasyPanel não chegava ao backend) → fix Traefik `chatwoot.2notasudi.com.br → cartorio_chatwoot-0` (validado)
- **Domínio público correto = `chatwoot.2notasudi.com.br`** (NÃO `chat.2notasudi.com.br`) → corrigido no `.env`
- **`CHATWOOT_API_KEY` VAZIO** no `.env` da API → FIX APLICADO (commit desta sessão, populado com User token do DB)
- **SSL self-signed CN=Easypanel** → aceito pelo Traefik (válido até 2036)
- **NÃO tem inbox Evolution configurada** (Squad H02) → WhatsApp chega via Baileys direto (independente)
- **Bot agent @CartorioBot** (Squad H07) → não criado ainda, precisa API Chatwoot

## Próximas tasks (Squad H do plan 2026-06-24)

- **H01** Health-check API (done)
- **H02** Inbox Evolution (whatsapp_baileys)
- **H03** Validar handoff OpenClaw↔humano
- **H04** Custom attributes: protocolo, emolumento_total, lgpd_consent_id, opt_out_flag
- **H05** Automações: keywords, opt-out, protocolos
- **H06** Reports/dashboards
- **H07** Bot agent @CartorioBot
- **H08** Testar webhooks Chatwoot
- **H09** DNS chat.2notasudi.com.br
- **H10** Documentação Chatwoot completa

Ver plano completo: `.harness/reins/cartorio-dev/tasks/2026-06-24-plan.json` (Squad H).

---

