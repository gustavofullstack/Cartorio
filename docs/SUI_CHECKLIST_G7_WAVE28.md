# SUI Checklist Consolidado — G7 Wave 28 (Go-Live residual)

**Status agent-side:** **[~] COMPLETE** — checklist 100% materializado; **ticks de produção = SUI-only**  
**Data:** 2026-07-17 · Wave 28 · tasks **G7.25.T1**  
**Owner humano:** Gustavo Almeida  
**Owners técnicos (docs/code):** cartorio-sre + cartorio-n8n + cartorio-lgpd + cartorio-dev  
**Tempo total estimado (humano):** ~60–90 min (DNS+env+tokens) + assinaturas LGPD (paralelo)

> **Regra de ouro:** agent **não** executa UI Cloudflare, EasyPanel secrets, BotFather, QR WhatsApp,
> assinatura DPA, publish de Privacy Policy, `tailscale up`, ou merge Traefik live no VPS.
> Agent entrega runbook + validadores + checkboxes. Gustavo tica após executar.

---

## 0. Legenda

| Símbolo | Significado |
|---------|-------------|
| `[x]` | Feito (agent-side ou verificado) |
| `[ ]` | **HOLD-GUSTAVO** — ação humana pendente |
| `[~]` | Parcial (doc/code ready; live ainda HOLD) |
| **SUI** | Single-User Interface / ação humana no painel |

### Fontes consolidadas

| Fonte | Path |
|-------|------|
| SUI original (Turn 50) | `.harness/SUI_CHECKLIST.md` |
| Wave 14 executável | `docs/G7_SUI_WAVE14_CHECKLIST.md` |
| DNS + Traefik pack | `docs/DNS_TRAEFIK_SUI_PACK_G7.md` |
| Evolution DB + QR | `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md` |
| Telegram webhook | `docs/TELEGRAM_WEBHOOK_REREGISTER_G7.md` |
| LobeChat key | `docs/LOBECHAT_OPENAI_KEY_G7.md` |
| OpenClaw E8 / 3 intents | `docs/LOBECHAT_OPENCLAW_3INTENTS_E2E_G7.md` · Lesson 177 |
| Traefik merge | `docs/TRAEFIK_ROUTERS_MERGE_G7.md` · `infra/traefik/routers-merged-g7.yaml` |
| Radar expanded redeploy | `docs/RADAR_EXPANDED_REDEPLOY_G7.md` |
| AlertManager → TG | `docs/ALERTMANAGER_TELEGRAM_G7.md` |
| Tailscale restore | `docs/TAILSCALE_RESTORE_G7.md` |
| DPA MiniMax | `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md` |
| Privacy v3 publish | `docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md` |
| 72h stability (após SUI) | `docs/STABILITY_WINDOW_72H_G7.md` |
| Super plano | `SUPER_PLANO_G7_100_TASKS.md` |

---

## 1. Agent-side DONE (não exige Gustavo para “fechar doc”)

Estes itens já estão no repositório e **contam como ticked agent-side** em Wave 28:

- [x] Runbooks DNS Cloudflare (`infra/dns/CLOUDFLARE_RUNBOOK.md`) + `scripts/check_dns_health.sh` + `make dns-check`
- [x] Typo `supbase` ratificado (`infra/dns/DOMAIN_TYPO_DECISION.md`)
- [x] Traefik merge artifact `infra/traefik/routers-merged-g7.yaml` + `ROUTERS_PENDENTES.yaml`
- [x] Evolution dual-format webhook parse + QR helper WF export
- [x] Telegram setWebhook helper (`scripts/telegram_set_webhook.py`) + docs re-register
- [x] LobeChat agent JSON scrub + OPENAI_API_KEY runbook
- [x] OpenClaw `openclaw.json` cartorio-bot + skills registry + context 1M guards
- [x] `/api/v1/health/radar` + `/radar/expanded` **código** + pytest
- [x] AlertManager Telegram route YAML + live-fire procedure (secrets não no git)
- [x] Loki/Promtail sample query script
- [x] DPA MiniMax **READY_TO_SIGN** package
- [x] Privacy Policy v3 **draft** + publish checklist
- [x] RIPD v1.4 addendum + data inventory 25 PII fields
- [x] Composite gate `scripts/g7_composite_gate.py` (exit 0/1/2)
- [x] Super validator `scripts/g7_super_validator.py`
- [x] Alembic single head 0020 + backup dry-run local WORK
- [x] Coverage/mypy/ruff gates documentados; mutmut status tracked
- [x] 72h stability tracker doc (`docs/STABILITY_WINDOW_72H_G7.md`) — janela **não** iniciada
- [x] Este consolidado Wave 28 (`docs/SUI_CHECKLIST_G7_WAVE28.md`)

---

## 2. HOLD-GUSTAVO — checklist residual (produção)

### Ordem obrigatória (não pular)

```
1 DNS ×3  →  2 env DATABASE_URL (Evo/CW/N8N)  →  3 scale 0→1 se host-mode
→  4 Redeploy API (radar/expanded)  →  5 Traefik merge
→  6 Telegram token+webhook  →  7 LobeChat key  →  8 WA QR
→  9 OpenClaw token + cartorio-bot  →  10 Tailscale (opcional admin)
→  11 AlertManager secrets + fire  →  12 DPA sign  →  13 Privacy publish
→  14 start 72h window
```

---

### §1 DNS Cloudflare ×3 — G7.12.T1 / G7.05.T1

**Tempo:** ~5 min · **Painel:** https://dash.cloudflare.com/ · zona `2notasudi.com.br`

- [ ] A record `chatwoot` → `187.77.236.77` (Proxy **ON** 🔵)
- [ ] A record `n8n` → `187.77.236.77` (Proxy ON 🔵 — se Traefik edge; OFF se conflito histórico)
- [ ] A record `supabase` → `187.77.236.77` (Proxy ON 🔵; canônico typo `supbase` permanece)
- [ ] `dig +short chatwoot.2notasudi.com.br A` ≠ vazio / NXDOMAIN
- [ ] `dig +short n8n.2notasudi.com.br A` ≠ vazio / NXDOMAIN
- [ ] `dig +short supabase.2notasudi.com.br A` ≠ vazio / NXDOMAIN
- [ ] `make dns-check` → exit 0 (G7.12.T2)

**Validação:**
```bash
for sub in chatwoot n8n supabase; do dig +short "$sub.2notasudi.com.br" A; done
bash scripts/check_dns_health.sh
make dns-check
```

---

### §2 Env vars Easypanel — DATABASE_URL (Evolution / Chatwoot / N8N) — Lesson 176

**Tempo:** ~10–15 min · **Painel:** EasyPanel `cartorio_*`

- [ ] `evolution-api`: `DATABASE_URL` com **DNS Swarm interno** + user/pass **atuais** (`admin` / DB real) — **remover** `10.11.211.12` e `supabase_admin:e999…`
- [ ] `chatwoot`: mesma correção de host/creds Postgres
- [ ] `n8n`: mesma correção de host/creds Postgres
- [ ] Redis URL dos 3 serviços ok se aplicável
- [ ] Se port conflict host-mode: scale **0 → 1** (nunca 1→1 force-only)
- [ ] Chatwoot `ENABLE_ACCOUNT_SIGNUP=false` (se ainda `true` — ver `.harness/SUI_CHECKLIST.md` SUI3)
- [ ] Radar classic: evolution / chatwoot / n8n → **online** (não 502)

```bash
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool
curl -sS -o /dev/null -w '%{http_code}\n' https://whatsapp.2notasudi.com.br/
curl -sS -o /dev/null -w '%{http_code}\n' https://chat.2notasudi.com.br/   # ou chatwoot. após DNS
curl -sS -o /dev/null -w '%{http_code}\n' https://flow.2notasudi.com.br/
```

---

### §3 Redeploy API — `/radar/expanded` — G7.18.T1

**Tempo:** ~5–10 min · Doc: `docs/RADAR_EXPANDED_REDEPLOY_G7.md`

- [ ] EasyPanel → serviço **api** → rebuild/deploy a partir de `master` com `health_radar_expanded`
- [ ] `curl -sS -o /dev/null -w '%{http_code}\n' https://api.2notasudi.com.br/api/v1/health/radar/expanded` → **200**
- [ ] `make radar-smoke` (se target apontar prod)

---

### §4 Traefik merge routers — G7.12.T3

**Tempo:** ~5–10 min · Doc: `docs/TRAEFIK_ROUTERS_MERGE_G7.md`

- [ ] Backup dynamic config Traefik na VPS
- [ ] Merge `infra/traefik/routers-merged-g7.yaml` (ou `ROUTERS_PENDENTES.yaml`) no dynamic file EasyPanel/Traefik
- [ ] Reload Traefik / confirmar routers `chatwoot` / `n8n` / `supabase` (se FQDNs novos)
- [ ] Opcional edge rate-limit: `docs/TRAEFIK_EDGE_RATE_LIMIT_G7.md` (middleware HOLD se não mergeado)

---

### §5 Telegram bot token + webhook — G7.03.T1

**Tempo:** ~5 min · Doc: `docs/TELEGRAM_WEBHOOK_REREGISTER_G7.md`

- [ ] @BotFather: `/token` (ou revoke + novo) — **nunca** commitar
- [ ] Atualizar Easypanel API: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_WEBHOOK_SECRET`
- [ ] Redeploy API **antes** do setWebhook
- [ ] `python3 scripts/telegram_set_webhook.py --apply` (ou curl documentado)
- [ ] `getWebhookInfo`: url canônica, `last_error_message` null
- [ ] Smoke humano: `/start` no bot → resposta 200 (sem 502 HTML/`<think>`)

---

### §6 LobeChat OPENAI_API_KEY — G7.06.T1

**Tempo:** ~3 min · Doc: `docs/LOBECHAT_OPENAI_KEY_G7.md`

- [ ] Substituir placeholder `sk-xxxx` por bearer real do proxy OpenClaw/LiteLLM
- [ ] `OPENAI_PROXY_URL=https://agent.2notasudi.com.br/v1` (ou canônico atual)
- [ ] `OPENAI_MODEL_LIST` coerente com OpenClaw
- [ ] Import agent JSON (se ainda não): scrub checklist Wave 21
- [ ] Smoke UI: 1 pergunta FAQ → resposta

---

### §7 WhatsApp QR Evolution — G7.04.T2

**Tempo:** ~5 min · Doc: `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md`  
**Pré:** §2 Evolution UP (não 502)

- [ ] Abrir `https://whatsapp.2notasudi.com.br/manager`
- [ ] Login com `AUTHENTICATION_API_KEY` (secret store / env — **não** re-commit)
- [ ] Instância `cartorio-2notas` (ou canônica): state `close` → escanear QR
- [ ] State `open` / `connected`
- [ ] 1 msg real WA → webhook → resposta (emolumento / FAQ) — fecha G7.04.T4 residual

```bash
# Exemplo de checagem state (token só no host):
# GET /instance/connectionState/<instance>  →  {"instance":{"state":"open"}}
```

---

### §8 OpenClaw operator token + cartorio-bot — G7.06.T3 / G7.14.T4

**Tempo:** ~10–15 min · Lessons 177 / 203 · E6/E8 specs

- [ ] Operator token com **scopes não-vazios** (não health-only `scopes=[]`) — G7.14.T4
- [ ] Token em secret store / env OpenClaw (nunca git)
- [ ] Criar agent `cartorio-bot` conforme `docs/openclaw/E6-cartorio-bot-spec.md` / openclaw.json Wave 15
- [ ] Skills registry alinhado (`docs/OPENCLAW_SKILLS_REGISTRY_G7.md`)
- [ ] Live E2E 3 intents (synthetic já verde Wave 27; live fecha residual G7.06.T4)

---

### §9 Tailscale restore (admin path) — G7.11.T1 / T2

**Tempo:** ~10–20 min · Doc: `docs/TAILSCALE_RESTORE_G7.md`  
**Nota:** **não P0** se API pública UP — bypass SSH seguro.

- [ ] Console Hostinger ou SSH público fallback `187.77.236.77`
- [ ] `tailscale up` no VPS; node `vps-cartorio` online
- [ ] MagicDNS `vps-cartorio.tail2fe279.ts.net` resolve no admin laptop
- [ ] SSH `:22` via CGNAT `100.99.172.84` OK
- [ ] Radar expanded check `tailscale` / `ssh` green (após §3 redeploy)
- [ ] ACL least-privilege apply (matriz no doc T4 — admin console)

---

### §10 AlertManager → Telegram live — G7.18.T3

**Tempo:** ~15 min · Doc: `docs/ALERTMANAGER_TELEGRAM_G7.md` §7

- [ ] Bot de alertas criado; token **só** secret store (não git)
- [ ] Chat ids Pietra (+ LGPD/N8N se rotas)
- [ ] Files montados nos paths do YAML no host
- [ ] `amtool check-config` OK
- [ ] Prometheus → AlertManager connectivity OK
- [ ] Live fire em janela acordada (avisar grupo)
- [ ] Confirmar P0 + resolved messages
- [ ] Remover alerta de teste / silence residual

---

### §11 DPA MiniMax assinar — G7.19.T2

**Tempo:** due diligence + assinatura (humano/jurídico) · Doc: `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md`

- [ ] Preencher placeholders cartório (CNPJ, tabelião, DPO nominal/telefone)
- [ ] Due diligence MiniMax (sede, residency, ISO/SOC)
- [ ] Assinatura bilateral (PDF)
- [ ] Arquivar `docs/lgpd/dpa_minimax.pdf` (ou vault + pointer)
- [ ] Flag `LGPD_DPA_MINIMAX_SIGNED=true` em prod (se aplicável)
- [ ] Audit log `dpa.minimax.signed`
- [ ] Atualizar `docs/LLM_DPA_MATRIX.md` status → **SIGNED**
- [ ] Tracker: `python3 scripts/dpa_sign_flow.py` (se disponível)

---

### §12 Privacy Policy v3 publish — G7.19.T3

**Tempo:** ~45–90 min conteúdo+site · Doc: `docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md`

- [ ] A1–A4: DPO/tabelião dados + aprovação escrita
- [ ] A5–A6: HTML/PDF público + SHA-256 do texto
- [ ] B1: publicar https://2notasudi.com.br/privacidade → **200**
- [ ] B2–B3: footer + página DPO
- [ ] B7: purge Cloudflare `/privacidade`
- [ ] C1–C5: bot welcome / consent hash / LobeChat banner → v3
- [ ] D4: audit `privacy_policy.v3.published`
- [ ] Critérios §F do publish checklist todos verdes

---

### §13 Observabilidade / backup / RLS (HOLD residual prod)

- [ ] Backup dry-run em `/var/backups` prod (sample local já WORK Wave 24)
- [ ] RLS audit sample em Postgres **prod** (report local Wave 25)
- [ ] Connection pool load test 25 sob carga real (report lab Wave 25)
- [ ] Cert LE expiry monitor ativo no host (doc Wave 25)
- [ ] Loki/Promtail ingest query real na VPS (script Wave 27)

---

### §14 Pós-SUI validação composta + 72h

- [ ] `make g7-validate` / `python3 scripts/g7_super_validator.py` → WORK (não HOLD dns)
- [ ] `python3 scripts/g7_composite_gate.py` → **exit 0** (prod)
- [ ] Radar classic: 7/7 ou 9/9 services online conforme matrix
- [ ] Preencher log-zero em `docs/STABILITY_WINDOW_72H_G7.md` e **iniciar** janela 72h
- [ ] Após 72h sem P0: candidatar tag `v0.7.0-g7-mvp` (G7.25.T4)

---

## 3. Matriz rápida HOLD (single glance)

| # | Item | Squad/Task | Status |
|---|------|------------|--------|
| 1 | DNS A×3 chatwoot/n8n/supabase | G7.12.T1 | [ ] SUI |
| 2 | `make dns-check` exit 0 | G7.12.T2 | [ ] SUI (depends 1) |
| 3 | DATABASE_URL Evo/CW/N8N | G7.04.T1 / Lesson 176 | [ ] SUI |
| 4 | Redeploy API radar/expanded | G7.18.T1 | [ ] SUI |
| 5 | Traefik routers merge live | G7.12.T3 | [ ] SUI (artifact [x]) |
| 6 | Telegram token + webhook | G7.03.T1 | [ ] SUI |
| 7 | LobeChat OPENAI_API_KEY | G7.06.T1 | [ ] SUI (runbook [x]) |
| 8 | WhatsApp QR open | G7.04.T2 | [ ] SUI |
| 9 | 1 msg real WA E2E | G7.04.T4 | [~] synth [x] / real [ ] |
| 10 | OpenClaw scopes + cartorio-bot | G7.14.T4 / G7.06.T3 | [ ] SUI |
| 11 | Tailscale online + MagicDNS | G7.11.T1/T2 | [ ] SUI |
| 12 | AlertManager secrets + fire | G7.18.T3 | [ ] SUI (YAML [x]) |
| 13 | DPA MiniMax signed | G7.19.T2 | [ ] SUI (READY [x]) |
| 14 | Privacy v3 published | G7.19.T3 | [ ] SUI (draft [x]) |
| 15 | Chatwoot handoff live | G7.05.T3 | [~] doc [x] / prod [ ] |
| 16 | 72h stability window **start** | G7.25.T2 | [x] tracker / [ ] started |
| 17 | Tag v0.7.0-g7-mvp | G7.25.T4 | [ ] após 72h |

---

## 4. Definition of Done — G7.25.T1 (agent)

| Critério | Estado |
|----------|--------|
| Consolidado único com **todos** residual HOLD-GUSTAVO em checkbox | **[x]** este doc |
| Agent-side items explicitamente ticked §1 | **[x]** |
| Residual claramente em seção SUI-only §2–§3 | **[x]** |
| Cross-links Wave 14 / DNS pack / Evolution / TG / Lobe / OpenClaw / AM / DPA / Privacy | **[x]** |
| Ticks de produção por Gustavo | **[ ]** (impossível ao agent) |

**Marcação SUPER_PLANO:** `G7.25.T1` → **[~] Wave28 checklist complete (ticks SUI)**

---

## 5. Comandos de verificação (copiar/colar)

```bash
# Local agent gates (já verdes tipicamente)
make pre-commit   # ou: make lint && make test-fast

# DNS
make dns-check
bash scripts/check_dns_health.sh

# Radar
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://api.2notasudi.com.br/api/v1/health/radar/expanded

# Composite / super validator
python3 scripts/g7_composite_gate.py --report docs/G7_COMPOSITE_GATE_WAVE24.md
python3 scripts/g7_super_validator.py --report docs/G7_VALIDATOR_REPORT.md

# Smoke backend
make -C backend smoke
```

---

**Modified by Gustavo Almeida + cartorio-brain/sre hybrid — G7 Wave 28 (G7.25.T1)**
