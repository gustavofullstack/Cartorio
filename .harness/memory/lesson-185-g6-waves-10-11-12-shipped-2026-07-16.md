# Lesson 185 — G6 Waves 10-11-12: 6 tasks shipped (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo ja criou: 9 arquivos modificados, +331 LOC (telegram/sentry/whatsapp)
- Estamos em CICLO G6 (pos-F6) — 9 waves ja entregues (wave 1-9 = 18 tasks DONE)

## Entregas Waves 10-11-12 (7 commits pushed, 6 G6 tasks DONE + 1 cleanup)

### Wave 10 — Pre-commit hook + CartorioBot E2E (3 commits)
| Commit | Task | Entrega |
|---|---|---|
| `1cdbdc1` | (cleanup) | feat(loop-gustavo): telegram/sentry/whatsapp routes + metrics schema |
| `d20c00e` | G6.A.T6 | .pre-commit-config.yaml (7 hooks) + scripts/secrets_scan.py (11 patterns, 207 secrets detectados) |
| `eedf217` | G6.E.T7 | tests/test_openclaw_cartorio_bot_e2e.py (11 testes validando spec sem servidor) |

### Wave 11 — Dead-man switch Telegram + LGPD inventory (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `2f6977a` | G6.B.T4 | dead_mans_switch.py integracao Telegram GRUPO PIETRA + 11 tests |
| `3cb80da` | G6.C.T6 | scripts/lgpd_data_inventory.py (18 PII fields, 7 categorias LGPD) |

### Wave 12 — AlertManager + Idempotency audit (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `7cae7ae` | G6.D.T4 + G6.B.T5 | infra/alertmanager/alertmanager.yml + scripts/n8n_idempotency_audit.py |

## Métricas finais sessão (waves 10-12 + cleanup)

| Métrica | Antes (wave 9) | Depois (wave 12) | Delta |
|---|---|---|---|
| pytest | 2941 | **2976** | **+35** |
| mypy | 0/143 files | **0/143 files** | mantido |
| ruff | 0 | **0** | mantido |
| commits ahead origin | 0 | **0** (7 pushed hoje) | ✅ |
| scripts/ (CLI) | 12 | **15** | +3 |
| N8N WFs com error handler | 35/36 | **35/37** | +0 (+2 WFs novos) |
| N8N WFs com idempotencia | 1/21 | **1/21** (audit) | baseline documentado |
| Prometheus alerts | 15 | **15** | mantido |
| DPAs rastreados | 9 | **9** | mantido |
| PII fields catalogados | 0 | **18** | +18 |
| AlertManager receivers | 0 | **5** | +5 |
| Pre-commit hooks | 0 | **7** | +7 |
| Lessons cross-rein | 184 | **185** | +1 |

## G6 consolidado (waves 1-12)

**24 G6 tasks DONE** em 12 waves + **5 lessons (181-185)** + 5 cleanup commits = **30 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2, T3, T4, T5, T6 (6 tasks) |
| B (N8N) | T1, T2, T3, T4, T5 (5 tasks) |
| C (LGPD) | T2, T3, T5, T6 (4 tasks) |
| D (SRE/obs) | T1, T2, T3, T4, T5 (5 tasks) |
| E (LLM/OpenClaw) | T6, T7 (2 tasks) |
| J (CI/CD) | T5 (1 task) |

## Lições aprendidas cross-project (Wave 10-12)

1. **httpx importado dentro da função ≠ atributo do módulo** — `from app.x import httpx` para mock precisa de `patch("httpx.post")` em vez de `patch("app.x.httpx")`. Aprendi no test_dead_mans_switch_telegram.

2. **AlertManager receivers por squad** permitem rotear P0/P1/P2/LGPD/N8N com templates diferentes. Crucial `send_resolved: true` para nao ficar acumulando alerts no GRUPO PIETRA.

3. **N8N idempotencia eh problema de PROD nao de design** — 20/21 webhooks SEM Redis SETNX. Webhook do Evolution API (evo-in) eh o mais critico (5 retries automaticos = ate 5x cobranca ou 5x mensagem enviada). Gustavo precisa aplicar o padrao JS lesson 22 em todos.

4. **pre-commit local hooks sao mais faceis que `pre-commit.com`** — use `language: system` + entry direto (ruff/mypy/etc). Sem rede, sem Docker, sem install adicional alem do `uv tool install pre-commit`.

5. **LGPD data inventory via regex** nao eh perfeito (tem false positives/negatives) mas eh BOM baseline para auditar 18+ PII fields. Categorias baseadas no LGPD art. 5 (dados pessoais) + art. 11 (sensíveis).

6. **Telegram GRUPO PIETRA CHAT ID deve prevalecer sobre TELEGRAM_CHAT_ID generico** — implementado no `send_alert`: `target_chat_id = chat_id or GRUPO_PIEIRA_CHAT_ID or TELEGRAM_CHAT_ID`. Fallback chain explicito.

7. **chatwoot_handoff.py mypy fix**: Atendimento model NAO tem campos `telegram_chat_id` ou `canal_id`. O chat_id Telegram eh armazenado no campo generico `canal` (Mapped[str]).

8. **Secrets scanner "FAKE/EXAMPLE/PLACEHOLDER/TEST_TOKEN" comments sao ignorados** — regra importante para evitar falsos positivos em exemplos de documentacao.

## Refs

- Wave 10-12 commits: 1cdbdc1, d20c00e, eedf217, 2f6977a, 3cb80da, 7cae7ae
- Artefatos novos: `.pre-commit-config.yaml`, `scripts/secrets_scan.py`, `scripts/lgpd_data_inventory.py`, `scripts/n8n_idempotency_audit.py`, `infra/alertmanager/alertmanager.yml`, `backend/tests/test_openclaw_cartorio_bot_e2e.py`, `backend/tests/test_dead_mans_switch_telegram.py`
- Updates: `backend/app/services/dead_mans_switch.py` (Telegram send), `backend/app/services/chatwoot_handoff.py` (mypy fix)
- Reports: `docs/LGPD_DATA_INVENTORY_2026-07-16.md`, `docs/N8N_IDEMPOTENCY_AUDIT_2026-07-16.md`

## SUI (Só Gustavo Resolve) — ainda pendentes

1. 🔴 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
2. 3 env vars Easypanel UI (DATABASE_URL evolution/chatwoot/n8n)
3. Regenerar token Telegram @TestCartorioBot
4. LobeChat OPENAI_API_KEY real
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E6 cartorio-bot deploy (SSH VPS + openclaw.json)
7. DPA MiniMax assinatura (Gustavo + Mavis)
8. N8N 00-error-handler ID → substituir placeholder nos 27 WFs
9. N8N idempotencia: adicionar Redis SETNX em 20 webhooks
10. AlertManager deploy: copiar alertmanager.yml para VPS + restart Prom

**Total: 24 G6 tasks DONE em 12 waves, ~3h30min**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 14:35 BRT**