# Lesson 187 — G6 Waves 16-17-18: 6 tasks shipped + cleanup (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo criou: 15 arquivos modificados (skills INDEX + brain catalog + radar + RIPD + Postman + LGPD docs + canal health matrix)
- Estamos em CICLO G6 (pos-F6) — 15 waves ja entregues (wave 1-15 = 30 tasks DONE)

## Entregas Waves 16-17-18 (7 commits pushed, 6 G6 tasks DONE + 1 cleanup)

### Wave 16 — Coverage badge + N8N backup (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `f3b0286` | (cleanup) | feat(loop-gustavo): skills INDEX + brain catalog + radar expanded + LGPD docs |
| `d9690a3` | G6.A.T8 | scripts/coverage_badge.py + 8 badges shields.io + mypy fix whatsapp |
| `6bee457` | G6.B.T7 | scripts/n8n_workflow_backup.py (tar.gz + SHA256 + manifest + prune 30) |

### Wave 17 — LGPD consent banner + SLO rules (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `ee8099f` | G6.C.T8 + G6.D.T6 | docs/lgpd/CONSENT_BANNER_WIDGET.html + infra/prometheus/slo_rules.yml (12 rules) |

### Wave 18 — CartorioBot CLI + super-prompt v3.1.0 (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `563b0d9` | G6.E.T9 + G6.J.T7 | scripts/cartorio_bot_chat.py + docs/SUPER_PROMPT_v3.1.0_RELEASE_NOTES.md |

## Métricas finais sessão (waves 16-18 + cleanup)

| Métrica | Antes (wave 15) | Depois (wave 18) | Delta |
|---|---|---|---|
| pytest | 3003 | **3025** | **+22** |
| mypy | 0/143 files | **0/143 files** | mantido |
| ruff | 0 | **0** | mantido |
| commits ahead origin | 0 | **0** (7 pushed hoje) | ✅ |
| scripts/ (CLI) | 18 | **20** | +2 |
| N8N WFs com idempotency | 21/21 | **21/21** | mantido |
| Prometheus SLO rules | 0 | **12** (4 SLOs) | +12 |
| Backup snapshots N8N | 0 | **1** (37 WFs, 0.05 MB) | +1 |
| Coverage badges | 0 | **8** | +8 |
| Lessons cross-rein | 186 | **187** | +1 |

## G6 consolidado (waves 1-18)

**36 G6 tasks DONE** em 18 waves + **7 lessons (181-187)** + 7 cleanup commits = **43 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2, T3, T4, T5, T6, T7, T8 (8 tasks) |
| B (N8N) | T1, T2, T3, T4, T5, T6, T7 (7 tasks) |
| C (LGPD) | T2, T3, T5, T6, T7, T8 (6 tasks) |
| D (SRE/obs) | T1, T2, T3, T4, T5, T6 (6 tasks) |
| E (LLM/OpenClaw) | T6, T7, T8, T9 (4 tasks) |
| J (CI/CD) | T5, T6, T7 (3 tasks) |

## Lições aprendidas cross-project (Wave 16-18)

1. **mypy [union-attr] fix em dict.get().get() chain**: padrao `data.get(key) if isinstance(data.get(key), dict) else {}` causa mypy reclamar. Solucao: `# type: ignore[union-attr]` direto + isinstance() guard separado.

2. **shields.io badges URLs**: `-` vira `--`, `_` vira `__`, espaco vira `_`. Para URL badge funcional: substituir em label E value antes de montar URL.

3. **N8N backup como tar.gz + SHA256 sidecar + manifest.json**: padrao classico Unix. Prune 30 snapshots = ~10 anos (1x/semana). Restore cria safety backup ANTES de sobrescrever.

4. **Consent banner LGPD v3 storage key**: versionado (`cartorio_lgpd_consent_v3`) para invalidar consentimentos v2 expirados (1 ano). Banner com `role=dialog`, `aria-live=polite`, `aria-label` para acessibilidade (WCAG 2.1).

5. **Prometheus SLO multi-window burn-rate** (Google SRE workbook cap. 5):
   - Fast burn: 1h window, 14.4x rate (budget exhausto em ~2 dias)
   - Slow burn: 6h window, 6x rate (budget exhausto em ~5 dias)
   - Composite SLO: media ponderada de 4 SLIs

6. **OpenClaw WebSocket handshake**: `connect.challenge` com nonce → bot precisa responder `auth.challenge` para continuar. Sem bot deployado, fica em challenge loop. Connection funcional prova que endpoint ta UP.

7. **OpenClaw payload v1 format**: `type/agent/session_id/message.{role,content,timestamp}`. Response pode vir em `response.message.content` OU `response.content` OU `response.response` (implementacao defensiva).

8. **Release notes v3.1.0 reflete estado real**: 75% tasks done, 3025 pytest (vs 952 v3.0.0), 18 scripts CLI novos, 9 docs/infra novos. Breaking change documentado: LGPD retencao 365d→90d.

## Refs

- Wave 16-18 commits: f3b0286, d9690a3, 6bee457, ee8099f, 563b0d9
- Artefatos novos: `scripts/{coverage_badge,n8n_workflow_backup,cartorio_bot_chat}.py`, `docs/lgpd/CONSENT_BANNER_WIDGET.html`, `infra/prometheus/slo_rules.yml`, `docs/SUPER_PROMPT_v3.1.0_RELEASE_NOTES.md`
- Updates: `backend/app/api/v1/whatsapp.py` (mypy fix), `.gitignore` (backups/)

## SUI (Só Gustavo Resolve) — ainda pendentes

1. 🔴 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
2. 3 env vars Easypanel UI (DATABASE_URL evolution/chatwoot/n8n)
3. Regenerar token Telegram @TestCartorioBot
4. LobeChat OPENAI_API_KEY real
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E6 cartorio-bot deploy (SSH VPS + openclaw.json)
7. DPA MiniMax assinatura (Gustavo + Mavis)
8. N8N 00-error-handler ID → substituir placeholder nos 27 WFs
9. GitHub Secrets: VPS_HOST/VPS_USER/VPS_SSH_KEY/TELEGRAM_*
10. Loki stack deploy (docker compose up)
11. Prometheus SLO rules deploy (Prometheus reload)
12. SLOs Grafana dashboard (composite SLO panel)

**Total: 36 G6 tasks DONE em 18 waves, ~5h30min**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 17:50 BRT**