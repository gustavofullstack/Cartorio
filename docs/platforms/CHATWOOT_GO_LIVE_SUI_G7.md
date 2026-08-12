# Chatwoot Go-Live SUI Master (G7.05.T1 + G7.05.T3)

| Campo | Valor |
|-------|--------|
| **Tasks** | G7.05.T1 DNS+Traefik · G7.05.T3 Handoff WF3 + labels LGPD |
| **Wave pack** | **Wave28 SUI pack refreshed** (2026-07-17) |
| **Agent-side docs** | DONE (parcials + merge artifact) |
| **Live** | **[~] HOLD-GUSTAVO** — DNS, merge Traefik, env DB, UI bot, WF ativo |
| **Rein** | cartorio-n8n + cartorio-sre + cartorio-lgpd (labels) |

**Canônicos URL:**  
- Preferido cliente: `https://chat.2notasudi.com.br`  
- Alias pack: `https://chatwoot.2notasudi.com.br` (A record + router pendente)

Este arquivo é o **master one-pager**. Detalhes ficam nos docs linkados — não duplicar runbooks longos.

---

## Mapa de dependências

```
Cloudflare A (chatwoot)     G7.05.T1 / G7.12.T1
        ↓
Traefik router merge        G7.05.T1 / G7.12.T3  → docs/TRAEFIK_ROUTERS_MERGE_G7.md
        ↓
Chatwoot UP (DATABASE_URL)  Lesson 176           → 200/302 login
        ↓
Agent Bot Cartorio          G7.05.T2             → docs/CHATWOOT_AGENT_BOT_SETUP_G7.md
        ↓
Handoff WF3 + labels LGPD   G7.05.T3             → §3 deste doc
        ↓
Canned jurídicas 20+        G7.05.T4 DONE Wave22
```

| Doc filho | Escopo |
|-----------|--------|
| [`DNS_TRAEFIK_SUI_PACK_G7.md`](DNS_TRAEFIK_SUI_PACK_G7.md) | dig + 3 A records + ordem edge |
| [`TRAEFIK_ROUTERS_MERGE_G7.md`](TRAEFIK_ROUTERS_MERGE_G7.md) | `routers-merged-g7.yaml` copy-paste |
| [`CHATWOOT_HANDOFF_G7.md`](CHATWOOT_HANDOFF_G7.md) | checklist env + contrato `handoff_to_chatwoot` |
| [`CHATWOOT_AGENT_BOT_SETUP_G7.md`](CHATWOOT_AGENT_BOT_SETUP_G7.md) | Agent Bot UI/API |
| [`CHATWOOT_HANDOVER.md`](CHATWOOT_HANDOVER.md) | fluxo escrevente |
| [`PLAYBOOK_502_VS_NXDOMAIN_G7.md`](PLAYBOOK_502_VS_NXDOMAIN_G7.md) | 502 vs DNS |

---

## 1. DNS (G7.05.T1) — ~5 min

Cloudflare zona `2notasudi.com.br`:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `chatwoot` | `187.77.236.77` | Proxied |
| A | `n8n` | `187.77.236.77` | Proxied (opcional pack) |
| A | `supabase` | `187.77.236.77` | Proxied (opcional; typo `supbase` canônico) |

```bash
dig +short chatwoot.2notasudi.com.br A @1.1.1.1
bash scripts/check_dns_health.sh
# meta: IP Cloudflare/proxy, não NXDOMAIN
```

Runbook: `infra/dns/CLOUDFLARE_RUNBOOK.md`

---

## 2. Traefik merge (G7.05.T1 / G7.12.T3) — ~10 min

Artifact: `infra/traefik/routers-merged-g7.yaml`  
Passos: `docs/TRAEFIK_ROUTERS_MERGE_G7.md`

```bash
# Pós-merge (no laptop)
for h in chatwoot.2notasudi.com.br chat.2notasudi.com.br; do
  code=$(curl -sk -o /dev/null -m 15 -w '%{http_code}' "https://$h/")
  echo "$h → $code"
done
# 200/301/302 = edge OK | 502 = router OK, upstream DB/env | 000 = DNS
```

Se **502** após DNS: corrigir `DATABASE_URL` Chatwoot (Lesson 176) → scale 0→1 se host-mode.

```bash
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | jq .services.chatwoot
# meta: online
```

---

## 3. Agent Bot (G7.05.T2) — pré-req handoff

One-pager: `docs/CHATWOOT_AGENT_BOT_SETUP_G7.md`

- Name: **Cartorio Assistant**  
- Outgoing webhook: `https://api.2notasudi.com.br/api/v1/webhooks/chatwoot` (ou path canônico prod)  
- Token → env `CHATWOOT_BOT_TOKEN` (N8N + API)  
- Inbox Telegram/WhatsApp com bot habilitado  

---

## 4. Handoff WF3 + labels LGPD (G7.05.T3)

### 4.1 Código API

- Service: `backend/app/services/chatwoot_handoff.py`  
- Fluxo: user → pipeline → `handoff_to_chatwoot()` → conversation + label → escrevente  
- **LGPD:** body **sem** CPF/RG/protocolo raw — `pii.scrub` antes do post  

Checklist env: `docs/CHATWOOT_HANDOFF_G7.md`

| Var | Uso |
|-----|-----|
| `CHATWOOT_BASE_URL` | interno Swarm preferível (`http://cartorio_chatwoot:3000`) |
| `CHATWOOT_API_KEY` | account token |
| `CHATWOOT_ACCOUNT_ID` | tip. `1` |
| `CHATWOOT_INBOX_ID` | tip. Telegram inbox `1` (skill) |
| `CHATWOOT_BOT_TOKEN` | agent bot |
| `CHATWOOT_WEBHOOK_SECRET` | HMAC opcional |

### 4.2 Workflow N8N WF3

| Item | Path / valor |
|------|----------------|
| Export staging | `infra/n8n-workflows/03-handoff-human-chatwoot-v3-staging.json` |
| Webhook path | `handoff-human` / id `handoff-human-v2` |
| Nodes | Webhook → Normalizar → Chatwoot Create Conversation → Send Message |
| Fallback inbox | `https://chatwoot.2notasudi.com.br/app/accounts/1/conversations?search=…` |

Ativar no N8N (`flow.2notasudi.com.br`) quando N8N + Chatwoot UP. Credencial `chatwoot-api` no UI — **não** commitar tokens.

### 4.3 Labels LGPD (obrigatórias no go-live)

Criar no Chatwoot (Settings → Labels) e aplicar no handoff / bot:

| Label | Uso |
|-------|-----|
| `lgpd` | direito de titular / menção LGPD |
| `hitl` | exige escrevente (ato jurídico) |
| `protocolo` | protocolo DRAFT / consulta |
| `emolumento` | dúvida de custas |
| `pii-scrubbed` | payload já mascarado (auditoria) |
| `whatsapp` / `telegram` / `web` | canal origem |

**Regras P0:**

1. HITL: protocolo nasce **DRAFT** — bot não conclui certidão/escritura.  
2. Nunca postar CPF raw no Chatwoot.  
3. Audit append-only na API quando handoff partir do backend.  
4. Canned: v3+v4 ≥20 jurídicas (`chatwoot_canned_responses_v*`, JSON `docs/canned-responses-chatwoot.json`).

### 4.4 Smoke handoff (pós-UP)

```bash
# Edge
curl -sS -o /dev/null -w '%{http_code}\n' https://chat.2notasudi.com.br

# Unit (local, sem PII)
cd backend && uv run pytest -q --no-cov -k chatwoot

# Mensagem de teste no canal: "quero falar com um atendente"
# Esperado: conversation no Chatwoot + labels hitl (+ canal) + sem CPF no body
```

---

## 5. Definition of Done (live ainda [~])

| # | Check | Status |
|---|-------|--------|
| 1 | dig `chatwoot` ≠ NXDOMAIN | [~] |
| 2 | Traefik router merged | [~] |
| 3 | Chatwoot HTTP 200/302 + radar online | [~] |
| 4 | Agent bot listado | [~] |
| 5 | WF3 ativo + labels LGPD | [~] |
| 6 | 1 handoff real scrubbed | [~] |
| — | Master one-pager consolidado | [x] Wave28 |

Só promover G7.05.T1 / T3 para `[x]` no SUPER_PLANO após checks live.

---

## Ordem SUI sugerida (~25–40 min)

1. DNS A `chatwoot` (+ n8n se for o mesmo bloco)  
2. Traefik merge  
3. Fix DATABASE_URL Chatwoot se 502  
4. Agent bot + labels  
5. Ativar WF3 + testar “falar com humano”  
6. Re-probe `CANAL_HEALTH_MATRIX` / `make radar-smoke`

**Modified by Gustavo Almeida — G7 Wave28 SUI pack refreshed**
