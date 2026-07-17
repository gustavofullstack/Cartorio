# LobeChat → OpenClaw → API — 3 intents E2E (G7.06.T4)

**Status agent:** `[x] Wave27` synthetic offline suite  
**Live chain:** HOLD until SUI (LobeChat key + OpenClaw cartorio-bot + DNS/Traefik)  
**Date:** 2026-07-17  
**Owner:** cartorio-dev / cartorio-n8n  

---

## Path (architecture)

```
User (browser)
    │
    ▼
LobeChat UI  (chat.2notasudi.com.br)
    │  OpenAI-compat proxy → OpenClaw gateway
    ▼
OpenClaw Gateway  (agent / cartorio-bot)
    │  skill registry: infra/openclaw-agent/skills/registry.json
    │  tools: consultar_emolumento | consultar/criar_protocolo | handoff_humano
    ▼
Cartorio API  (api.2notasudi.com.br)
    │  /api/v1/emolumentos/calcular-api
    │  /api/v1/protocolo/criar-api  (HITL DRAFT)
    │  /api/v1/protocolo/{YYYY-NNNNN}
    │  Chatwoot REST (handoff)
    ▼
Postgres + Redis + Audit (SHA256+HMAC)
```

Spec de tools: `docs/openclaw/E6-cartorio-bot-spec.md`  
Skills runtime: `infra/openclaw-agent/skills/registry.json`

---

## 3 intents

| # | Intent (user) | OpenClaw skill | Tool / API | HITL / LGPD |
|---|---------------|----------------|------------|-------------|
| 1 | “Quanto custa uma procuração?” | `cartorio-emolumento-calc` | `GET /api/v1/emolumentos/calcular-api?tipo=procuracao` | Publico, sem PII |
| 2 | “Status do protocolo 2026-00001” / criar ato | `cartorio-protocolo-tracker` + `criar_protocolo` | `GET /protocolo/{n}` + `POST /protocolo/criar-api` | **DRAFT always**; escrevente valida |
| 3 | “Quero falar com humano” | `cartorio-handoff-trigger` | Chatwoot macro `handoff_humano` + REST | Label `handoff-humano`, team atendimento |

### Intent 1 — Emolumento (procuração)

- Service: `app.services.emolumento.calcular("procuracao")` → total **156.40** (TABELA MG 2026).
- Endpoints: `/api/v1/emolumento/calcular` (legacy) e `/api/v1/emolumentos/calcular-api` (N8N/OpenClaw).
- Cache opcional: Redis 24h (`emolumento_cache`) — fail-open.

### Intent 2 — Protocolo / HITL draft

- **Criar:** `POST /api/v1/protocolo/criar-api` com `X-API-Key`, `hitl_draft=true` (obrigatório).
- Número gerado: `CART-YYYY-XXXXXX`, status persistido **`DRAFT`**.
- **Consultar:** `GET /api/v1/protocolo/{YYYY-NNNNN}` (formato tool OpenClaw / MCP).
- Bot **nunca** avança status sozinho (isencao/urgencia/certidão = HITL).

### Intent 3 — Handoff humano

- Macro: `app.services.chatwoot_handoff_macros.MACRO_HANDOFF_HUMANO`
  - `assign_team=atendimento`, `add_label=handoff-humano`, mensagem ao cliente.
- Runtime: `handoff_to_chatwoot()` em `app.services.chatwoot_handoff` (contact → conversation → message).
- Depende de Chatwoot UP + DNS `chatwoot.2notasudi.com.br` (ver G7.05 / G7.12).

---

## Synthetic suite (CI / local)

Arquivo: `backend/tests/test_g7_lobechat_openclaw_intents.py`

```bash
# da raiz
make test-one TEST=tests/test_g7_lobechat_openclaw_intents.py

# ou
cd backend && uv run pytest -q --no-cov tests/test_g7_lobechat_openclaw_intents.py
```

Cobre:

1. Skills registry declara as 3 intents + tools  
2. Routing de utterances sintéticas  
3. Emolumento service + HTTP (2 paths)  
4. Criar protocolo DRAFT + consulta status + rejeição `hitl_draft=false`  
5. Macro handoff + Chatwoot HTTP via **respx**  
6. Cadeia 3-turn end-to-end offline  
7. OpenAPI inclui `/api/v1/health/radar/expanded` (cross-check G7.18)

**Não** chama LobeChat/OpenClaw/Chatwoot reais. Sem secrets.

---

## Live runbook (quando SUI pronto)

Pré-requisitos:

- [ ] `G7.06.T1` OPENAI_API_KEY real no LobeChat (proxy OpenClaw/LiteLLM)  
- [ ] `G7.06.T2` agent JSON importado na UI  
- [ ] `G7.06.T3` cartorio-bot no OpenClaw (`openclaw.json`)  
- [ ] DNS + Traefik chat/agent/api verdes (`docs/DNS_TRAEFIK_SUI_PACK_G7.md`)  
- [ ] Chatwoot online se for validar handoff (`docs/CHATWOOT_HANDOFF_G7.md` se existir)

### Passo a passo live (~10 min)

1. Abrir `https://chat.2notasudi.com.br` (ou LobeChat interno) com agent Cartório.  
2. **Turno emolumento:** enviar `Quanto custa uma procuraçao?`  
   - Esperado: valor ~R$ 156,40 + breakdown; sem CPF na resposta.  
3. **Turno protocolo:** `Crie um protocolo de procuraçao` (com consent LGPD se pedido).  
   - Esperado: número `CART-…` / draft; mensagem de aguardando escrevente.  
4. **Turno status:** `Qual o status do protocolo 2026-00001?` (use número real).  
   - Esperado: status + próxima ação HITL.  
5. **Turno handoff:** `Quero falar com um humano`.  
   - Esperado: confirmação de transferência; conversa no Chatwoot com label `handoff-humano`.  
6. Validar audit: ações `protocolo.created` / `protocolo.read` na chain.  

### API smoke (sem UI)

```bash
# 1 emolumento
curl -sS 'https://api.2notasudi.com.br/api/v1/emolumentos/calcular-api?tipo=procuracao&folhas=1' \
  | python3 -m json.tool

# 2 criar draft (API key em env — NUNCA commitar)
curl -sS -X POST 'https://api.2notasudi.com.br/api/v1/protocolo/criar-api' \
  -H "X-API-Key: $CARTORIO_API_KEY" -H 'Content-Type: application/json' \
  -d '{"cliente_id":1,"ato":"procuracao","valor_snapshot":"156.40","hitl_draft":true}'

# 3 status
curl -sS 'https://api.2notasudi.com.br/api/v1/protocolo/2026-00001' | python3 -m json.tool
```

---

## Cross-refs

| Doc | Uso |
|-----|-----|
| `docs/openclaw/E6-cartorio-bot-spec.md` | 8 tools / skills / HITL |
| `infra/openclaw-agent/skills/registry.json` | Intent → tools |
| `docs/DNS_TRAEFIK_SUI_PACK_G7.md` | Edge chat/api |
| `docs/CD_EASYPANEL_HOOK_G7.md` | Redeploy API |
| Lesson 170 / 177 / 178 | LobeChat CORS, OpenClaw E8, snapshot HOLD |

---

## Definition of Done

| Check | Synthetic | Live |
|-------|-----------|------|
| 3 intents testados | [x] pytest | [ ] SUI |
| HITL draft enforced | [x] | [ ] |
| Handoff macro + mock HTTP | [x] | [ ] Chatwoot UI |
| PII not echoed in emolumento | [x] (no PII path) | [ ] |
| Docs + SUPER_PLANO checkbox | [x] | — |

**Modified by Gustavo Almeida — G7 Wave 27**
