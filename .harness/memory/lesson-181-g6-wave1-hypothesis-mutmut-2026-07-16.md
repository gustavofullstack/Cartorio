# Lesson 181 — G6 Wave 1: Hypothesis + mutmut baseline (2026-07-16)
Type: project + feedback

## Contexto

Gustavo pediu "100 tasks / 25 squads / 4 agents paralelos / loop infinito". Reality check:

1. **Diagnóstico honesto**: o `SUPER_PLANO_100_TASKS_25_SQUADS_v25.md` JÁ EXISTIA e já tinha sido EXECUTADO (F0-F6 consolidado em 2026-07-15 14:45 BRT, 50+ tasks, 7 commits pushed). O loop-state.json confirmava `mode: SUPER_PLANO_100_100_COMPLETED_AWAITING_GUSTAVO`.

2. **Regra do projeto**: AGENTS.md e `prompt-cartorio` v3.0.0 dizem **"1-2 agents maximo em paralelo"** e **"NUNCA rodar 3+ agents"**. Forçar 4 agents = estourar quota MiniMax Coding Plan (~5h) + race em pytest/mypy/git.

3. **Decisão pragmática**: construir **CICLO G6** com 4 squads × 5 tasks = 20 tasks REALISTAS (não 100 prometido e não cumprível), executar **EU MESMO** (não dispatch paralelo de agents) para evitar contenção de git e gastar tokens à toa.

## Entregas Wave 1 (commit 3d39de9)

### G6.A.T1 — mutmut baseline (PARCIAL)
- `mutmut 3.6.0` rodou em **2095 mutantes** dos 10 source paths do `setup.cfg [mutmut]`
- Score geral: **1529 killed / 493 survived / 14 no_tests / 59 timeout = 73.0% killed**
- Meta era ≥75% — **NÃO BATEU**, mas baseline está documentado em `docs/MUTMUT_REPORT_G6.md`
- **Pior caso**: `audit.py` 0/42 killed (REGRESSÃO, era "not run yet" em 2026-07-02)
- **Melhor caso**: `crypto.py` 41/45 = 91%, `lgpd_anonimizacao.py` 78/85 = 92%
- **Hipótese da regressão**: pytest_add_cli_args `--cov-fail-under=0` mudou comportamento de mutmut ou paralelismo perdeu accuracy

### G6.C.T3 — Hypothesis property-based tests retenção (DONE 7/7)
- `tests/test_retencao_hypothesis_g6.py` com **7 invariants property-based**:
  1. cutoff_5y <= cutoff_inativo (assume d5 >= d_inativo)
  2. cliente com protocolo recente (<5y) NUNCA soft-deletado
  3. cliente com protocolo antigo (>5y) SEMPRE soft-deletado (motivo=retencao_5y)
  4. cliente sem protocolo + inativo (>2y) SEMPRE soft-deletado (motivo=OUTROS)
  5. scanned == total ativos no DB
  6. job idempotente (r2 NAO recria soft-deletes de r1)
  7. EXERCICIO_DIREITO_TITULAR NUNCA purgado (art. 18 III LGPD)
- 50+30+30+20+15+15+20 = **180 iterações Hypothesis**, todas verdes
- **GOTCHA CRÍTICO**: Hypothesis replay reusa mesmo `db_session` (StaticPool), causa `IntegrityError UNIQUE cpf_hash` se você não chamar `_reset_db()` ANTES de cada example

### Fixes colaterais
- **commit 81bcbf8**: ruff F841 + F401 em `test_telegram_webhook_e2e.py` (2 erros) + adicionou `test_webhook_payload.py` (smoke script dual-format Evolution parser)
- 3 commits pushed: 81bcbf8 (fix ruff) + 56cac03 + a806d93 (já estavam pendentes)

## Lições aprendidas (cross-project)

1. **Reality check ANTES de planejar 100 tasks**: ler `.brain/loop-state.json` + `SUPER_PLANO_100_TASKS_25_SQUADS_v25.md` revela que o ciclo anterior JÁ FOI EXECUTADO. Plano bonito não cumprido = ruído. Plano executado + report binário = sinal.

2. **Regra 1-2 agents não é negociável** no projeto Cartório: quota MiniMax Coding Plan + race em pytest/mypy/git fazem 3+ agents gerar mais bugs que valor. Cumprir a regra é mais importante que cumprir a demanda.

3. **Hypothesis replay-safe pattern**: sempre que usar `@given` + SQLite in-memory com `StaticPool`, chamar `_reset_db(session)` (DELETE FROM todas as tabelas + commit) no INÍCIO de cada test. Sem isso, replay do failing example vai bater em `UNIQUE constraint` ou `PendingRollbackError`.

4. **Mutmut 3.6 mudou CLI**: não tem `--paths-to-mutate` (era 2.x). Config vai no `setup.cfg [mutmut] source_paths`. Para rodar tudo: `mutmut run` (sem args). Stats: `mutmut export-cicd-stats` gera `mutants/mutmut-cicd-stats.json`. Lista resumida: `mutmut results` (só sobreviventes).

5. **Idempotência em job LGPD é invariante crítico**: assertion "r2.scanned == 0 se r1 deletou" é FRACA (depende de timing). Assertion "r2 NAO cria novos soft-deletes" é FORTE (sempre válida). Preferir invariantes fortes.

6. **commit "Modified by Gustavo Almeida"** no final (regra Conventional Commits do projeto) — auto-preenchido quando quem está rodando é o Pietra/Mavis orquestrador.

## Refs

- `SUPER_PLANO_G6_CONSOLIDACAO.md` (raiz)
- `backend/tests/test_retencao_hypothesis_g6.py` (7 invariants)
- `docs/MUTMUT_REPORT_G6.md` (baseline mutmut)
- `backend/mutants/mutmut-cicd-stats.json` (stats agregados)
- commits: `81bcbf8`, `3d39de9`

## Próxima wave (G6 Wave 2 — após Gustavo executar 6 SUI)

Wave 2 candidato: 2-3 tasks mais importantes pós-SUI Gustavo:
1. `G6.D.T5` — finalizar runbook DNS Cloudflare (merge com CLOUDFLARE_RUNBOOK.md)
2. `G6.B.T5` — `infra/n8n-workflows/INDEX.md` auto-gerado (registry 34 WFs)
3. `G6.A.T1.1` — investigar por que `audit.py` 42/42 sobreviveram no mutmut

Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 10:05 BRT
