# Chatwoot Agent Bot — Cartorio Assistant (G7.05.T2)

**Goal:** Agent Bot no Chatwoot para handoff + respostas assistidas.  
**Status:** HOLD-GUSTAVO (UI super_admin + API key)  
**Inbox canônica:** Telegram Inbox ID 1 (skill chatwoot) · Account 1

---

## Pré-requisitos

1. Chatwoot **UP** (hoje radar offline / 502 — fix DATABASE_URL Lesson 176 + DNS pack)
2. Super admin em `https://chat.2notasudi.com.br` (ou host EasyPanel)
3. `CHATWOOT_API_KEY` com escopo account

---

## Setup UI (~5 cliques)

1. Login **super_admin** → Agent Bots  
2. **New Agent Bot**
   - Name: `Cartorio Assistant`
   - Description: Bot HITL do 2º Notas — handoff + canned
   - Outgoing URL (webhook): `https://api.2notasudi.com.br/api/v1/webhooks/chatwoot`  
     (ou path canônico do handoff no router)
3. Copiar **Access Token** do bot → env `CHATWOOT_BOT_TOKEN` no N8N e API
4. Inbox Telegram/WhatsApp → habilitar Agent Bot
5. Labels: `lgpd`, `hitl`, `protocolo`, `emolumento`

---

## Setup API (quando Chatwoot 200)

```bash
# Listar agent bots (exemplo)
curl -sS -H "api_access_token: $CHATWOOT_API_KEY" \
  "$CHATWOOT_BASE_URL/api/v1/accounts/1/agent_bots"

# Criar (payload varia por versão 3.x)
# Preferir UI se API divergir
```

WF N8N handoff: `03-handoff-human` / webhook handoff-human — fallback inbox URL se bot token vazio.

---

## Validação

| Check | Esperado |
|-------|----------|
| Chatwoot HTTP | 200/302 login |
| Agent bot listado | sim |
| Msg “falar com humano” | cria conversation + label |
| PII no handoff | scrubbed (sem CPF raw) |

Cross-ref: `docs/CHATWOOT_HANDOFF_G7.md` · skill `.agents/skills/chatwoot/`

**Modified by Gustavo Almeida — G7 Wave 23**
