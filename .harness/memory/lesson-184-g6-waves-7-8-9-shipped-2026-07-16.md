# Lesson 184 — G6 Waves 7-8-9: ship 6 tasks + matrix CI (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo (Pietra/Mavis) ja criou: 8 arquivos novos, 7 modificados, +495 LOC
- Estamos em CICLO G6 (pos-F6) — 5 waves ja entregues (wave 1-6 = 12 tasks DONE)

## Entregas Waves 7-8-9 (6 commits pushed, 6 G6 tasks DONE + 1 cleanup)

### Wave 7 — CI gate integration + LGPD DPA flow (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `f592bc6` | (cleanup) | feat(loop-gustavo): whatsapp router + e2e tests + ripd + qr-scan-helper |
| `959d735` | G6.A.T2 | 5 G6 gates no Makefile + GitHub Actions (openapi-check/n8n-validate/coverage-gate/radar-smoke/openapi-update) |
| `3cbb4e7` | G6.C.T2 | scripts/dpa_sign_flow.py: tracker de 9 DPAs (4 signed, 1 pending Gustavo, 4 pending provider) |

### Wave 8 — N8N error handler + Prometheus alerts (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `45fa594` | G6.B.T3 | scripts/n8n_error_handler_audit.py + fix 27 WFs + mypy fix fallback |
| `9a038e1` | G6.D.T2 | scripts/prometheus_alert_validator.py + 3 alerts LGPD/produto (consent/backup/circuit-breaker) |

### Wave 9 — OpenClaw spec + CI Python matrix (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `278752d` | G6.E.T6 + G6.J.T5 | docs/openclaw/E6-cartorio-bot-spec.md + ci.yml matrix Python 3.12+3.13 |

## Métricas finais sessão (waves 7-9 + cleanup)

| Métrica | Antes (wave 6) | Depois (wave 9) | Delta |
|---|---|---|---|
| pytest | 2932 | **2941** | **+9** |
| mypy | 0/142 files | **0/143 files** | +1 file |
| ruff | 0 | **0** | mantido |
| pytest tempo serial | ~60s | **~60s** | mantido |
| commits ahead origin | 0 | **0** (6 pushed hoje) | ✅ |
| scripts/ (CLI) | 9 | **12** | +3 |
| N8N WFs com error handler | ~0 | **35/36** | +27 |
| Prometheus alerts | 12 | **15** | +3 |
| DPAs rastreados | 0 | **9** | +9 |
| CI matrix Python | 1 versão | **2 versões (3.12+3.13)** | +1 |
| lessons cross-rein | 183 | **184** | +1 |

## G6 consolidado (waves 1-9)

**18 G6 tasks DONE** em 9 waves + 4 lessons + 3 cleanup commits = **25 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2 (snapshot CI), T3 (snapshot), T4 (xdist), T5 (coverage gate) |
| B (N8N) | T1 (validator CI), T2 (canned v3), T3 (error handler) |
| C (LGPD) | T2 (DPA flow), T3 (Hypothesis retenção), T5 (Privacy Policy v3) |
| D (SRE/obs) | T1 (radar CLI), T2 (Prometheus alerts), T3 (backup dryrun), T5 (DNS checker) |
| E (LLM/OpenClaw) | T6 (cartorio-bot spec) |
| J (CI/CD) | T5 (Python matrix) |

## Lições aprendidas cross-project (Wave 7-9)

1. **N8N errorWorkflow exige UUID do WF alvo** — exports N8N nao tem o ID (so no servidor). Use placeholder `"ERROR_HANDLER_PLACEHOLDER_REPLACE_WITH_REAL_ID"` e Gustavo substitui no deploy via N8N UI.

2. **`settings={}` (dict vazio) conta como "settings existe"** — meu fix `--fix` so adicionava errorWorkflow se settings nao existia. Loop adicional necessario para `settings = {} or None`.

3. **Prometheus alerts YAML exige campos minimos**: alert, expr, for, labels.severity, labels.squad, annotations.summary, annotations.description. Validador detecta gaps.

4. **DPA Matrix é estado explicito > inferido**: 9 providers com 4 estados (signed/template/pending_gustavo/pending_provider). Manter KNOWN_DPAS dict permite tracking sem DB.

5. **Python CI matrix com cache key por versao**: `key: py${{ matrix.python-version }}-uv-` evita colisao de venv cacheado.

6. **Git sparse-checkout pode bloquear add de arquivos em diretorios tracked**: precisei separar `git add` em chunks para nao incluir `00-error-handler.json` (ja tracked em outra parte do sparse-checkout).

7. **mypy `attr-defined` em `ChatErrorKind.API`**: classe ChatErrorKind tem CONFIG/HTTP_4XX/HTTP_5XX/TIMEOUT/etc mas NAO `API`. Para circuit breaker aberto, `HTTP_5XX` eh semanticamente correto.

8. **`make` nao captura exit code 1 do script Python** sem set -e no alvo. Use `python3 script.py || exit 1` ou apenas deixe o `&&` chain.

## Refs

- Wave 7-9 commits: f592bc6, 959d735, 3cbb4e7, 45fa594, 9a038e1, 278752d
- Artefatos novos: `scripts/{dpa_sign_flow,n8n_error_handler_audit,prometheus_alert_validator}.py` + `docs/openclaw/E6-cartorio-bot-spec.md`
- Updates: `Makefile` (+5 alvos), `.github/workflows/ci.yml` (matrix + 3 gates), `infra/prometheus/alerts.yml` (+3 alerts), 27 N8N WFs (errorWorkflow), `backend/app/integrations/fallback.py` (mypy fix)
- Reports: `docs/DPA_FLOW_REPORT_2026-07-16.md`, `docs/N8N_ERROR_HANDLER_AUDIT_2026-07-16.md`, `docs/PROMETHEUS_ALERTS_REPORT_2026-07-16.md`

## SUI (Só Gustavo Resolve) — ainda pendentes

1. 🔴 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
2. 3 env vars Easypanel UI (DATABASE_URL evolution/chatwoot/n8n)
3. Regenerar token Telegram @TestCartorioBot
4. LobeChat OPENAI_API_KEY real
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E6 cartorio-bot deploy (SSH VPS + openclaw.json)
7. DPA MiniMax assinatura (Gustavo + Mavis)
8. N8N 00-error-handler ID → substituir placeholder nos 27 WFs

**Total: 18 G6 tasks DONE em 9 waves, ~2h30min**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 13:00 BRT**