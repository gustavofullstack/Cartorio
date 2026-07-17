# 72h Stability Window — G7 (G7.25.T2)

**Status:** **[x] TRACKER READY** — janela **não iniciada**  
**Task:** G7.25.T2 · Wave 28  
**Owner start:** Gustavo (após SUI DNS+env mínimos)  
**Owner monitor:** cartorio-sre + Gustavo  
**Depends-on:** `docs/SUI_CHECKLIST_G7_WAVE28.md` §1–§2 (DNS×3 + DATABASE_URL + API healthy)

---

## 1. Objetivo

Provar **72 horas contínuas** de operação estável em produção antes de:

- declarar G7 go-live MVP fechado;
- tag `v0.7.0-g7-mvp` (G7.25.T4);
- elevar compliance ANPD / radar 9/9 como “produção estável”.

Não é load test sintético: é **observação real** com critérios de abort e log horário/turno.

---

## 2. Critérios para **START** (gate de entrada)

A janela **só** inicia quando **todos** os itens abaixo estiverem verdes.  
Registrar `T0` (timestamp BRT) no log §6.

### 2.1 Obrigatórios (P0 gate)

| # | Critério | Como verificar | OK? |
|---|----------|----------------|-----|
| S1 | DNS chatwoot/n8n/supabase **não** NXDOMAIN | `make dns-check` exit 0 | [ ] |
| S2 | API `/health` e `/ready` **200** | `curl -sS -o /dev/null -w '%{http_code}\n' https://api.2notasudi.com.br/ready` | [ ] |
| S3 | Radar classic: serviços críticos **online** (api, redis, db no mínimo; ideal n8n/evolution/chatwoot) | `GET /api/v1/health/radar` | [ ] |
| S4 | Sem P0 aberto (502 massivo, DB down, audit chain broken) | status + Sentry | [ ] |
| S5 | `DATABASE_URL` Evo/CW/N8N corrigidos (Lesson 176) **ou** canais offline **explicitamente fora de escopo** da janela (documentar) | EasyPanel + radar | [ ] |

### 2.2 Fortemente recomendados (fecham mais G7 goals)

| # | Critério | OK? |
|---|----------|-----|
| R1 | `/api/v1/health/radar/expanded` → **200** (redeploy API) | [ ] |
| R2 | Telegram webhook vivo (`getWebhookInfo` ok + 1 `/start`) | [ ] |
| R3 | WhatsApp instance `open` **ou** WA marcado out-of-scope na janela | [ ] |
| R4 | Composite gate prod **exit 0** (não exit 2 HOLD) | [ ] |
| R5 | AlertManager ou Uptime Kuma com pelo menos 1 canal de alerta vivo | [ ] |

### 2.3 Quando **não** iniciar

- API em 502/000 intermitente;
- Postgres/Redis vermelho no radar;
- Deploy experimental em andamento sem freeze;
- Rotação de secrets planejada nas próximas 24h sem janela de manutenção.

---

## 3. Métricas a observar (72h)

### 3.1 Radar / health

| Métrica | Fonte | Alvo | Abort se |
|---------|-------|------|----------|
| Radar classic overall | `GET /api/v1/health/radar` | green / yellow aceitável com nota | red crítico ≥15 min |
| Radar expanded categories | `GET .../radar/expanded` | health/dns/disk ok | health red |
| `/ready` | HTTP | 200 | 5xx ou timeout > 5s sustentado |
| `/metrics` scrape | Prometheus | scrape ok | target down > 30 min |

### 3.2 Error rate / app

| Métrica | Fonte | Alvo | Abort se |
|---------|-------|------|----------|
| HTTP 5xx rate API | Traefik access log / Prom | < 1% req (janela 15m) | > 5% por 15m **ou** spike P0 |
| Sentry events (scrubbed) | Sentry | tendência flat/down | burst novo sem owner |
| Telegram webhook errors | `getWebhookInfo` + logs | `last_error_message` null | erros repetidos > 1h |
| Evolution/WA disconnect | Evolution state | `open` se no escopo | flapping close/open > 3×/h |

### 3.3 Audit chain (imutável)

| Métrica | Fonte | Alvo | Abort se |
|---------|-------|------|----------|
| Dead-man's-switch audit | logs API lifespan (15 min) | check OK | chain break / HMAC fail |
| Manual sample | `verify` audit endpoint/script se exposto | last N entries valid | qualquer invalid chain |
| Retenção LGPD job | scheduler 03:00 BRT | job roda sem crash | crash 2 noites seguidas |

### 3.4 Infra

| Métrica | Fonte | Alvo | Abort se |
|---------|-------|------|----------|
| Disco VPS | radar expanded `disk` / `df` | < 85% | ≥ 90% |
| Redis memory | `INFO memory` / radar | abaixo maxmemory sem thrash | OOM / eviction storm |
| Postgres connections | pool / pg_stat | < pool max | saturation + 5xx |
| Cert LE | monitor Wave 25 | > 14d para expiry | < 7d sem renew plan |
| Tailscale (se no escopo) | `tailscale status` | online | offline **não** abort se SSH público ok |

### 3.5 Negócio / HITL (amostra)

| Check | Frequência | Alvo |
|-------|------------|------|
| 1 protocolo DRAFT criado (HITL) sem auto-approve | 1×/dia | status `DRAFT` |
| PII não vaza em logs Sentry sample | 1×/dia | mask ok |
| 1 smoke emolumento (TG ou WA se live) | 1×/dia | resposta coerente |

---

## 4. Cadência de amostragem

| Cadência | O quê |
|----------|--------|
| **T0** | Preencher header do log; freeze deploys não-emergenciais |
| **A cada 4h** (ou turno) | Radar + `/ready` + nota 5xx + 1 linha no log |
| **1×/dia (manhã)** | Audit DMS sample, disco, Sentry digest, webhook TG |
| **1×/dia (noite 03:30 BRT)** | Confirmar retenção LGPD se job enabled |
| **T+72h** | Close-out: PASS / FAIL / EXTEND |

### Freeze de deploy

Durante a janela: **somente** hotfixes P0 com:

1. entry no log §6;
2. rollback plan escrito;
3. re-baseline de métricas após 30 min.

---

## 5. Critérios de **PASS** / **FAIL** / **EXTEND**

### PASS (fecha G7.25.T2 live)

- 72h sem incidente **P0**;
- no máximo **1 P1** resolvido < 2h com root cause notada;
- radar critical path green/yellow documentado;
- audit chain sem break;
- log §6 completo (mínimo 6 amostras + close-out).

### FAIL (reinicia contagem)

- P0 (API down > 15 min, data loss, audit break, PII leak raw);
- 2+ P1 correlacionados (mesmo root cause);
- restore incompleto pós-incidente sem validação.

### EXTEND (+24h ou +72h)

- 1 P1 isolado com fix e observação;
- mudança de escopo (ex.: WA entrou no meio da janela);
- deploy emergencial com re-baselining.

---

## 6. Template de log (copiar para cada janela)

> Preencher abaixo **quando iniciar**. Não apagar template em branco — duplicar seção “Janela N”.

### Janela 1 — (não iniciada)

```
WINDOW_ID:     G7-72H-001
STATUS:        NOT_STARTED
T0_BRT:        YYYY-MM-DD HH:MM BRT
T_END_PLANNED: T0 + 72h
OPERATOR:      Gustavo / …
SCOPE_IN:      api, redis, postgres, [telegram?], [whatsapp?], [n8n?], [chatwoot?]
SCOPE_OUT:     (listar canais offline intencionais)
BASELINE_RADAR: (colar JSON resumido ou link)
BASELINE_COMMIT/IMAGE: …
NOTES:         Started after SUI: DNS×3 [ ] env [ ] …
```

#### Amostras (4h / turno)

| # | Timestamp BRT | Radar | /ready | 5xx note | Audit DMS | Incidents | Initials |
|---|---------------|-------|--------|----------|-----------|-----------|----------|
| 0 | T0 | | 200 | | OK/NA | none | |
| 1 | T0+4h | | | | | | |
| 2 | T0+8h | | | | | | |
| 3 | T0+12h | | | | | | |
| 4 | T0+24h | | | | | | |
| 5 | T0+36h | | | | | | |
| 6 | T0+48h | | | | | | |
| 7 | T0+60h | | | | | | |
| 8 | T0+72h | | | | | | CLOSE |

#### Incidentes (se houver)

| Time | Sev | Symptom | Action | Resolved | Root cause |
|------|-----|---------|--------|----------|------------|
| | P0/P1/P2 | | | | |

#### Close-out

```
RESULT:     PASS | FAIL | EXTEND
T_END_BRT:  …
SUMMARY:    …
NEXT:       tag v0.7.0-g7-mvp | reopen SUI | new window G7-72H-002
MEMORY:     append lesson short entry if non-obvious
```

---

## 7. Comandos de amostragem rápida

```bash
# Health
curl -sS -o /dev/null -w 'ready %{http_code}\n' https://api.2notasudi.com.br/ready
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool | head -80
curl -sS -o /dev/null -w 'expanded %{http_code}\n' \
  https://api.2notasudi.com.br/api/v1/health/radar/expanded

# DNS
make dns-check

# Composite (prod HOLD = exit 2 ainda conta como “não start” se S1–S3 falham)
python3 scripts/g7_composite_gate.py --report /tmp/g7-composite-72h.md || true

# Telegram (token só no env local — nunca echo em issue)
# curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
```

---

## 8. Relação com outros docs

| Doc | Papel |
|-----|--------|
| `docs/SUI_CHECKLIST_G7_WAVE28.md` | Gate de entrada (o que ticar antes do T0) |
| `docs/CANAL_HEALTH_MATRIX.md` | Baseline de canais |
| `docs/OUTAGE_RECOVERY_RUNBOOK.md` | Se FAIL/P0 |
| `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md` | Diagnóstico 502 vs DNS |
| `.harness/SUI_CHECKLIST.md` | SUI histórico Turn 50 |
| `SUPER_PLANO_G7_100_TASKS.md` G7.25.T2 | Checkbox tracker |

---

## 9. Status G7.25.T2

| Entrega agent Wave 28 | Estado |
|------------------------|--------|
| Doc com start criteria | **[x]** |
| Métricas (radar, error rate, audit) | **[x]** |
| Template de log 72h | **[x]** |
| When to start (após SUI DNS+env) | **[x]** |
| Janela live iniciada | **[ ]** NOT_STARTED |

**SUPER_PLANO:** `G7.25.T2` → **[x] Wave28 tracker ready (window not started)**

---

**Modified by Gustavo Almeida + cartorio-sre/brain hybrid — G7 Wave 28 (G7.25.T2)**
