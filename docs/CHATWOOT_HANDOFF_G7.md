# Chatwoot Handoff — G7 Integration Checklist (G7.05.T3)

**Service:** `backend/app/services/chatwoot_handoff.py`  
**Public URL (desired):** `https://chat.2notasudi.com.br` (canonical) / `chatwoot.*` NXDOMAIN HOLD  
**Status prod 2026-07-16:** 🔴 502 + radar offline (env DATABASE_URL + DNS)

---

## Fluxo HITL

```
User (TG/WA/Web)
  → API / chat_pipeline / agent
  → handoff_to_chatwoot()  [HITL obrigatório em ato jurídico]
  → Chatwoot conversation + label
  → Escrevente responde no CRM
```

---

## Pré-requisitos (SUI + config)

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | DNS `chatwoot` A record **ou** usar `chat.*` canônico | Gustavo | HOLD |
| 2 | `CHATWOOT_API_KEY` | Easypanel | verify |
| 3 | `CHATWOOT_ACCOUNT_ID` / `CHATWOOT_INBOX_ID` | Easypanel | verify |
| 4 | `CHATWOOT_BASE_URL` interno Swarm (`http://cartorio_chatwoot:3000`) | sre | verify |
| 5 | `CHATWOOT_WEBHOOK_SECRET` HMAC | security | optional |
| 6 | Agent Bot Cartorio Assistant | Gustavo UI | HOLD |
| 7 | DATABASE_URL Chatwoot → Postgres atual | Gustavo Lesson 176 | HOLD |

---

## Código de handoff (contrato)

```python
# chatwoot_handoff.handoff_to_chatwoot(...)
# - cria/busca contact
# - cria conversation na inbox
# - post message com resumo (sem CPF raw)
# - retorna public_url para escrevente
```

**LGPD:** nunca colocar CPF/RG raw no body Chatwoot; usar mask de `pii.scrub`.

---

## Canned responses

| Fonte | Path | Contagem |
|-------|------|----------|
| JSON export | `docs/canned-responses-chatwoot.json` | ver script |
| v3 service | `app/services/chatwoot_canned_responses_v3.py` | tags handoff/protesto/inventario |

Meta G7.05.T4: 20/50 jurídicas — continuar em wave futura.

---

## Validação

```bash
# Service up?
curl -sS -o /dev/null -w '%{http_code}\n' https://chat.2notasudi.com.br

# Radar
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | jq .services.chatwoot

# Unit (local)
cd backend && uv run pytest -q --no-cov -k chatwoot
```

---

## Cross-refs

- Lesson 176 (502 DATABASE_URL) · 178 (Telegram/LobeChat) · 179 (DNS)
- `docs/CHATWOOT_HANDOVER.md` · skill `.agents/skills/chatwoot/`

**Modified by Gustavo Almeida + cartorio-n8n — G7 Wave 19**
