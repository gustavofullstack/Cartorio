# OpenClaw cartorio-bot deploy SUI (G7.06.T3)

| Campo | Valor |
|-------|--------|
| **Task** | G7.06.T3 — criar agent `cartorio-bot` no OpenClaw (E8) |
| **Wave pack** | **Wave28 SUI pack refreshed** (2026-07-17) |
| **Agent-side** | JSON + spec + synthetic intents **DONE** |
| **Live** | **[~] HOLD-GUSTAVO** — SSH/EasyPanel + operator token scopes |
| **Rein** | cartorio-n8n / cartorio-sre |

**Não marcar `[x]` até `agents.list` incluir `cartorio-bot` em prod.**

---

## Artefatos canônicos (repo)

| Item | Path |
|------|------|
| Bot config | `infra/openclaw/cartorio-bot.openclaw.json` |
| Spec E6 | `docs/openclaw/E6-cartorio-bot-spec.md` |
| LobeChat import | `infra/lobechat/agent_cartorio_import.json` |
| Import checklist | `docs/LOBCHAT_OPENCLAW_IMPORT_G7.md` |
| 3 intents E2E synth | `docs/LOBECHAT_OPENCLAW_3INTENTS_E2E_G7.md` + `backend/tests/test_g7_lobechat_openclaw_intents.py` |
| Skills registry | `docs/OPENCLAW_SKILLS_REGISTRY_G7.md` |
| Context guards | `docs/OPENCLAW_CONTEXT_GUARDS_G7.md` |
| TS HTTPS notes | `infra/traefik/TAILSCALE_OPENCLAW.md` |

Slug oficial: **`cartorio-bot`**  
Endpoint: `wss://agent.2notasudi.com.br/v1/chat` · HTTP compat `https://agent.2notasudi.com.br/v1`  
API tools base: `https://api.2notasudi.com.br`

---

## Pré-requisitos

1. OpenClaw gateway **UP** (`agent.2notasudi.com.br` — radar openclaw online).  
2. **Operator token** com scopes `operator.read` **e** `operator.write`.  
   - Lesson 177: token health-only com `scopes=[]` **bloqueia** `agents.create`.  
3. Secrets **só** em EasyPanel/UI — nunca commitar `apiKey`/password.  
4. CORS já aceita `.2notasudi.com.br` (Lesson 170) — não reabrir issue CORS sem evidência.  
5. (Opcional mesh) Tailscale restore: `docs/TAILSCALE_RESTORE_G7.md` + one-pager `docs/TAILSCALE_SSH_RADAR_LIVE_G7.md`.

```bash
curl -sS -o /dev/null -w 'agent:%{http_code}\n' https://agent.2notasudi.com.br/health
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | jq .services.openclaw
# meta: 200 + online
```

Validação local de artefatos (sem deploy):

```bash
python3 -c "import json; d=json.load(open('infra/openclaw/cartorio-bot.openclaw.json')); assert d['name']=='cartorio-bot'"
python3 -c "import json; json.load(open('infra/lobechat/agent_cartorio_import.json'))"
# sem secrets literais
rg -n 'sk-|gAAAAA|password.*=.*[A-Za-z0-9]{16}' infra/openclaw/ infra/lobechat/ || true
```

---

## Deploy steps (SUI ~7–15 min)

### Opção A — Volume / arquivo no container (preferido)

1. SSH (Tailscale `100.99.172.84` ou público `187.77.236.77`):

```bash
# Do laptop (após restore TS preferível)
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84
# fallback:
# ssh -i ~/.ssh/id_ed25519_cartorio root@187.77.236.77
```

2. Copiar JSON do bot para path documentado:

```bash
# Ajuste container/serviço EasyPanel se o path diferir
DEST=/home/node/.openclaw/openclaw.json
# Backup
cp "$DEST" "${DEST}.bak-$(date +%Y%m%d%H%M)" 2>/dev/null || true

# Copiar conteúdo de infra/openclaw/cartorio-bot.openclaw.json
# (scp do laptop ou cat via heredoc — SEM colar tokens no histórico git)
```

3. Control UI: password/operator settings (SUI).  
4. Restart:

```bash
# Nome do serviço varia no Swarm/EasyPanel
docker service update --force cartorio_openclaw 2>/dev/null \
  || systemctl restart openclaw 2>/dev/null \
  || docker restart openclaw
```

### Opção B — EasyPanel UI

1. `https://easypanel.2notasudi.com.br` → serviço OpenClaw / agent.  
2. Volume mount: montar `cartorio-bot.openclaw.json` → `/home/node/.openclaw/openclaw.json`.  
3. Env: operator token com scopes read+write; **não** usar placeholder `sk-xxxx`.  
4. Redeploy serviço.

### Opção C — API create (se Control API exposta)

```bash
# Pseudocódigo — headers/paths conforme versão OpenClaw em prod
export OPENCLAW_OPERATOR_TOKEN='…'  # scopes operator.read|write
curl -sS -X POST "https://agent.2notasudi.com.br/v1/agents" \
  -H "Authorization: Bearer $OPENCLAW_OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @infra/openclaw/cartorio-bot.openclaw.json | jq .
```

Se 401/403: recriar token com scopes (Lesson 177).

---

## Contrato do agent (resumo)

| Dimensão | Valor |
|----------|--------|
| Tools | emolumento, protocolo, agendar, 2ª via, LGPD, audit_verify, handoff |
| HITL | `criar_protocolo` / atos jurídicos → sempre DRAFT |
| PII | hooks `on_message_in` scrub + `on_response_out` |
| Providers | primary MiniMax-M3; fallbacks no JSON (só com DPA) |
| Channels | telegram/whatsapp/lobechat flags no JSON (`HOLD_*` até SUI canal) |

System prompt P0 no JSON: **nunca inventar emolumento** — chamar API; nunca decidir isenção sozinho.

---

## Validação pós-deploy

```bash
# Health
curl -sS https://agent.2notasudi.com.br/health | jq .

# Lista agents (path pode variar — Control UI se API divergir)
curl -sS -H "Authorization: Bearer $OPENCLAW_OPERATOR_TOKEN" \
  https://agent.2notasudi.com.br/v1/agents | jq '.[].name // .agents'

# Esperado: cartorio-bot presente
```

| Check | Esperado |
|-------|----------|
| `/health` | 200 |
| `agents.list` | contém `cartorio-bot` |
| WS `connect.challenge` → hello-ok | bot listado |
| Tool emolumento | total 156.40 p/ procuração (via API) |
| LobeChat import (G7.06.T2) | baseURL OpenClaw + key real (G7.06.T1) |

Synthetic (já verde, não prova deploy):

```bash
cd backend && uv run pytest -q --no-cov tests/test_g7_lobechat_openclaw_intents.py
```

3 intents live (G7.06.T4 synth DONE; live ainda SUI):  
`quanto custa procuração` · consulta protocolo · criar protocolo → **DRAFT** + HITL.

---

## Rollback

```bash
cp /home/node/.openclaw/openclaw.json.bak-YYYYMMDDHHMM \
   /home/node/.openclaw/openclaw.json
# restart serviço OpenClaw
```

LobeChat: reverter import / desligar agent se respostas ruins.

---

## Definition of Done

| Item | Status |
|------|--------|
| JSON + E6 spec no repo | [x] |
| Deploy one-pager Wave28 | [x] |
| Operator token scoped | [~] |
| openclaw.json montado / agent create | [~] |
| agents.list tem cartorio-bot | [~] |
| Smoke tool emolumento live | [~] |

---

## Cross-refs

- Lesson 170 (LobeChat CORS) · 177 (E8 scopes) · 178 (snapshot canais)  
- `docs/G7_SUI_WAVE14_CHECKLIST.md` §7  
- `docs/LOBCHAT_OPENCLAW_IMPORT_G7.md`

**Modified by Gustavo Almeida — G7 Wave28 SUI pack refreshed**
