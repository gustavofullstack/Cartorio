# Lesson 206 — G7 Waves 13–28 consolidada (2026-07-17)

**Type:** project + reference (cross-rein)  
**Agents:** cartorio-brain / cartorio-sre hybrid (+ dev, n8n, lgpd across waves)  
**Scope:** SUPER PLANO G7 100 tasks · Waves 13→28 agent-side closeout  
**Canonical trackers:** `SUPER_PLANO_G7_100_TASKS.md` · `SUPER_GOALS_G7.md`  
**SUI residual:** `docs/SUI_CHECKLIST_G7_WAVE28.md`  
**72h window:** `docs/STABILITY_WINDOW_72H_G7.md` (tracker ready, **not started**)

---

## 1. North star recap

Meta G7 (até 2026-07-31): stack 100% integrado (API ↔ TG ↔ Chatwoot ↔ LobeChat ↔ Redis ↔
Postgres ↔ MCP ↔ WS ↔ webhooks ↔ Tailscale ↔ DNS/Traefik ↔ OpenClaw ↔ skills/brain ↔
Postman/Swagger ↔ radar) com SOLID/DRY, tipagem, CI verde e MVP operacional — **HITL +
PII + audit chain** inegociáveis.

---

## 2. Progresso (snapshot Wave 28 — 2026-07-17)

| Métrica | Valor |
|---------|-------|
| Tasks G7 total | **100** |
| `[x]` done (agent ou closed-with-SUI-runbook) | **~92** |
| `[~]` partial (doc/code ready, live HOLD) | **~8** |
| `[ ]` open | **0** unmarked (residual is [~]/[x]-with-HOLD notes) |
| % done strict (`[x]` only) | **~92%** |
| % progress weighted (`[x]` + 0.5×`[~]`) | **~96%** |
| Waves agent-side | **W13–W27 shipped**; **W28 go-live pack** (SUI checklist + 72h tracker + this lesson + A4/SRE packs lesson-207) |
| Gates locais típicos | ruff 0 · mypy 0 · pytest green · coverage gate ≥90% |
| Alembic | single head **0020** |
| Composite gate | local **exit 0** · prod **exit 2 HOLD** (DNS/SUI) |
| Lessons G7 dedicadas | **186–206** (ver índice) |

### Open residual (agent cannot close alone — live HOLD)

1. **DNS A×3** Cloudflare chatwoot/n8n/supabase (G7.12.T1; soft dns-check may exit 0 with snapshot [~])  
2. **OpenClaw operator token scopes** non-empty + cartorio-bot create (G7.14.T4 / G7.06.T3)  
3. **Env DATABASE_URL** Evolution/Chatwoot/N8N (Lesson 176) + WA QR + TG token  
4. **DPA sign + Privacy publish + AlertManager secrets + Tailscale online**  
5. **72h window start** + git tag `v0.7.0-g7-mvp` push (G7.25.T2 live / T4 tag HOLD)  
6. Partials: WA real msg, Chatwoot handoff prod, mutmut re-run report  

Full checkbox SUI: **`docs/SUI_CHECKLIST_G7_WAVE28.md`** · packs A4: **lesson-207**.

---

## 3. Wave map (o que cada wave entregou)

| Wave | Foco | Lesson(s) | Resultado-chave |
|------|------|-----------|-----------------|
| **13** | Mutation killers audit, D5 IP, RIPD v1.4, health matrix, radar fallback | 186 | Super plano G7 nasce; matriz canais live |
| **14** | g7_super_validator, MCP inventory, SUI checklist Wave14 | — / 187 start | Validator + inventário tools |
| **15** | openclaw.json, catalog/postman, skills index, Redis ops | 187 | Integration matrix + Redis maxmemory doc |
| **16** | HMAC PREV, CI gates, DoR/DoD, paperclip board | 188 | CI openapi+n8n+coverage+secrets |
| **17** | Evolution dual-format, WS50, Postman gen, Tailscale offline fallback | 189 | Dual webhook + orchestrator % |
| **18** | rate_limit metrics, DLQ drill, TG think-strip, MCP example, domain typo | 190 | Prometheus 3-tier + MiniMax badge coord |
| **19** | PII pre-LLM 8/8, OpenAPI 126, Chatwoot handoff doc, redlock peer skip | 191 | Handoff checklist (prod HOLD) |
| **20** | TG multi-turn Redis hist, HMAC drill, Evolution QR/DB checklist, STATUS | 192 | SUI checklists Evo/QR |
| **21** | TG setWebhook helper, smoke inv 26, LobeChat apiKey scrub, mutmut status | 193 | Token HOLD documentado |
| **22** | coverage gap, canned v4, WA synthetic E2E, DNS/Traefik SUI pack | 194 | One-pager DNS pack |
| **23** | cov tests DMS/evo, Chatwoot agent bot runbook, LobeChat key, dashboard | 195 | G7_PROGRESS_DASHBOARD |
| **24** | Alembic 0020, backup dry-run, 502 playbook, mypy 154, composite 0/1/2, 18 cov | 196 | Gate prod HOLD = exit 2 |
| **25** | RLS audit, pool report, skills 6/6, SOLID dead-code, Mapped 100%, CD, MVP cut, LE | 197 | MVP cut-line WhatsApp consult |
| **26** | MCP 13 + coding-vps 63, WS ping, Tailscale runbook, OpenClaw skills/1M, LGPD inv 25, N8N KISS, pre-commit, TG1000 31/31 | 198, 199 | Metrics cov 94%; idempotency notice |
| **27** | Pydantic strict inputs, service DRY masks, Traefik access/edge, DPA READY, Privacy v3, Loki sample, AlertManager TG, 3 intents synth, routers-merged, radar redeploy runbook | 200–203 | Sign/publish/deploy still SUI |
| **28** | SUI consolidado 100% tick form, 72h stability tracker, MEMORY consolidada | **206** | Go-live residual pack |

---

## 4. HOLD-GUSTAVO consolidado (lista mestra)

Ordem de execução recomendada (detalhe em Wave28 SUI doc):

1. **DNS ×3** — `chatwoot` / `n8n` / `supabase` → `187.77.236.77`  
2. **Env DATABASE_URL** — evolution + chatwoot + n8n (Lesson **176**: não force-restart sem fix env)  
3. **Redeploy API** — `/radar/expanded` 200  
4. **Traefik merge** — `routers-merged-g7.yaml` live  
5. **Telegram** — BotFather token + webhook secret + setWebhook  
6. **LobeChat** — `OPENAI_API_KEY` real + proxy OpenClaw  
7. **WhatsApp QR** — instance `open`  
8. **OpenClaw** — operator token com scopes + create `cartorio-bot`  
9. **Tailscale** — restore admin path (não P0 se API pública UP)  
10. **AlertManager** — secrets + live fire  
11. **DPA MiniMax** — assinar (READY_TO_SIGN)  
12. **Privacy v3** — publicar site  
13. **Start 72h window** — `docs/STABILITY_WINDOW_72H_G7.md`  
14. **Tag** `v0.7.0-g7-mvp` após PASS  

### Anti-padrões gravados (não repetir)

| # | Anti-padrão | Lesson |
|---|-------------|--------|
| 1 | `docker service update --force` sem corrigir env | 176 |
| 2 | Tratar Traefik 502 como “Traefik down” sem ler access log backend | 176, 172 |
| 3 | Commitar tokens / `sk-*` / BotFather | STANDARDS + secrets_scan |
| 4 | Echo CPF raw / mandar PII a LLM pública | pii 3-camadas |
| 5 | Bot decidir isenção/urgência/certidão sozinho | HITL DRAFT |
| 6 | 4 agents paralelos pesados em SSH/CPU limitado — preferir 1–2 reais | 185 |
| 7 | Contar LobeChat/OpenClaw “done” só com JSON no git (live SUI) | 170, 177, 178 |
| 8 | Assumir DNS Hostinger eterno — Cloudflare migration deixou 3 NXDOMAIN | 179 |
| 9 | `parse_mode=HTML` com `<think>` da LLM → 502 silencioso TG | 152/TG fix |
| 10 | Iniciar 72h com DNS NXDOMAIN ou DB down | Wave 28 |

---

## 5. Métricas de qualidade (agent-side, estáveis)

| Gate | Estado típico Wave 28 |
|------|------------------------|
| ruff | 0 |
| mypy strict `app/` | 0 (154 files report Wave 24) |
| pytest | full suite green local (markers smoke/integration excluded default) |
| coverage CI | `--cov-fail-under=90` |
| mutmut audit+pii | status tracked; full ≥75% target ainda parcial G7.02.T1 |
| MCP cartorio | 13 tools inventariados (não hardcodar contagem eternamente) |
| coding-vps MCP | 63 ≥ 62 |
| TG 1000 subset | 31/31 auto |
| Idempotency webhooks | 22 green (Wave 24) |
| OpenAPI catalog | 73+ / baseline 126 paths (waves) |
| Pydantic | strict flags em key **input** schemas (Wave 27); Settings permanece `extra=ignore` |

---

## 6. Arquitetura / decisões que sobreviveram G7

1. **HITL obrigatório** — protocolo `DRAFT`; bot nunca fecha ato jurídico sozinho.  
2. **Audit append-only** — SHA256 chain + HMAC; DMS a cada 15 min; rotação drill documentado.  
3. **PII 3 camadas** — validators → Sentry `before_send` → log `MaskingFilter` + pre-LLM scrub.  
4. **Evolution dual payload** — root `message` **e** `data.message`.  
5. **Domain typo `supbase`** — ACEITO como canônico; `supabase` alias via DNS novo.  
6. **Composite exit codes** — 0 OK / 1 local fail / 2 prod HOLD (não mascarar SUI como fail de código).  
7. **MVP cut-line** — WhatsApp consult-only primeiro (Wave 25) antes de escritura full auto.  
8. **Secrets** — never commit; `check_no_literal_keys` + secrets_scan CI.  
9. **Conventional Commits** + trailer `Modified by Gustavo Almeida`.  
10. **Memory dual** — `.harness/memory/` (git) vs session Claude dir (não misturar).

---

## 7. Goals G7.1–G7.12 (aprox. Wave 28)

| Goal | ~% | Bloqueio residual |
|------|----|-------------------|
| G7.1 API production-grade | 99% | polish |
| G7.2 Telegram live E2E | 70% | token SUI |
| G7.3 Chatwoot handoff | 42% | DNS + 502 env |
| G7.4 LobeChat agent | 62% | key + OpenClaw live |
| G7.5 Redis/PG 72h | 90% | 72h window not started |
| G7.6 MCP sync | 90% | live mount smoke prod |
| G7.7 WS + webhooks dual | 95% | — |
| G7.8 Tailscale/Traefik/DNS | 60% | DNS×3 + merge + TS |
| G7.9 OpenClaw bot | 50% | token scopes + create |
| G7.10 Postman/Swagger/radar | 90% | expanded prod redeploy |
| G7.11 SOLID/typing | 94% | Any hotspots optional |
| G7.12 CI/CD + obs | 94% | AM secrets live |

**Média ponderada ~82–88%** dependendo do peso SUI. Meta ≥95% após SUI + 72h.

---

## 8. Lessons index 200–206 (Wave 27–28)

| # | Arquivo | Resumo |
|---|---------|--------|
| 200 | `lesson-200-g7-wave27-a1-pydantic-dry-2026-07-17.md` | Pydantic forbid em inputs-chave + DRY mask_nome/email |
| 201 | `lesson-201-g7-wave27-a2-traefik-obs-2026-07-17.md` | Traefik access log debug + edge rate-limit (deploy HOLD) |
| 202 | `lesson-202-g7-wave27-a3-lgpd-2026-07-17.md` | DPA MiniMax READY_TO_SIGN + Privacy v3 draft |
| 203 | `lesson-203-g7-wave27-a4-intents-radar-2026-07-17.md` | 3 intents synth + routers-merged + radar redeploy runbook |
| 204 | *(reservado se slot A paralelo gravou outro id — checar memory dir)* | — |
| 205 | *(idem)* | — |
| **206** | **este arquivo** | **Consolidação Waves 13–28 + HOLD + métricas** |

Waves 13–26: lessons **186–199** (e paralelas G6 181–185 / 192 dual numbering — preferir prefixo `g7-wave` no filename).

---

## 9. Wave 28 entregáveis (esta sessão)

| Task | Entrega | Status |
|------|---------|--------|
| G7.25.T1 | `docs/SUI_CHECKLIST_G7_WAVE28.md` | **[~]** agent complete; ticks prod SUI |
| G7.25.T2 | `docs/STABILITY_WINDOW_72H_G7.md` | **[x]** tracker ready; window not started |
| G7.25.T3 | this lesson + MEMORY.md index | **[x]** |
| G7.25.T4 | tag release | **[ ]** after 72h PASS |

---

## 10. Próximos passos (humano + agent)

1. Gustavo executa `docs/SUI_CHECKLIST_G7_WAVE28.md` §2 na ordem.  
2. `make dns-check` + radar green → preencher T0 em stability doc → **start 72h**.  
3. Agent: não abrir PRs de “fake green” prod; manter composite exit 2 honesto até DNS.  
4. Após 72h PASS: G7.25.T4 tag + release notes; atualizar SUPER_GOALS média ≥95%.  
5. cartorio-lgpd: assinar DPA + publish Privacy (pode ser paralelo à stability se PII paths estáveis).

---

## 11. Cross-refs essenciais

- Lessons SRE/prod: **172, 176, 179, 180**  
- Telegram: **152, 160, 161, 178, 192, 193**  
- OpenClaw/Lobe: **170, 177, 178, 203**  
- LGPD: **171, 202**, RIPD v1.4, DPA pack  
- G6→G7 bridge: **186**  

---

**Modified by Gustavo Almeida + cartorio-brain/sre hybrid — G7 Wave 28 (G7.25.T3)**
