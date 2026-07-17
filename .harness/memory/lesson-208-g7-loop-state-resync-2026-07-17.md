# Lesson 208 — G7 loop state resync após sessão interrompida (2026-07-17)

Type: project + feedback

## Caso

Sessão TRAE recarregada após Gustavo pedir `CONTINUE!!` em 2026-07-17 ~17:30 BRT.
Estado na entrada:

| Item | Esperado (loop state) | Real (disco + git) |
|------|----------------------|--------------------|
| G7 tasks | ~92/100 [x] | **92/100 [x]** ✅ |
| G6 tasks | 57/100 [x] | 57/100 [x] ✅ |
| master ahead origin | 0 | **2 commits ahead** (da176f9, 67d7a53) |
| Working tree modified | 0 | 0 ✅ (só `trae-agent` executável + 148 untracked novo) |
| pytest | ~3128 | **3176** (+48 desde Wave 27) |
| mypy strict | 0 | **0 / 155 files** (+1 file desde W24) |
| ruff | 0 | **0** ✅ |

**Achado crítico #1:** O orquestrador `scripts/super_loop_orchestrator.py` está lendo o
arquivo **antigo** `SUPER_PLANO_100_TASKS_25_SQUADS_v25.md` e reporta `20/100` (5 waves).
**O trabalho real migrou para `SUPER_PLANO_G7_100_TASKS.md`** (Wave 13-28, 92/100).

**Achado crítico #2:** O `.brain/loop-state.json` ainda reporta S4 como última wave do v25.
O arquivo novo `.brain/loop-state-v25.json` foi criado pelo super-loop recente mas é
**state shadow** (não canônico).

## Decisão

1. **Push dos 2 commits ahead** antes de qualquer operação destrutiva (FEITO: `b7ae85f..6720d10`).
2. **Não re-empacotar Wave 30 G6** — tarefas G6.A.T13/G6.D.T11 já entregues como G7 squads.
3. **Manter 148 untracked files** (são artifacts G7 Wave 13-28 que não foram commitados na sessão
   anterior). Devem ser commitados em **1 mega-commit** `chore(loop-gustavo): commit G7 wave 13-28 artifacts`
   para limpar working tree, **NÃO** individualmente (risco de perder contexto).
4. **Não tocar `loop-state.json`** — Gustavo controla quando sincronizar com G7 (script gap conhecido).
5. **Atualizar PROGRESS.md + SUPER_GOALS_G7.md** com snapshot real pós-sessão.

## Anti-padrão detectado (Lesson 208 reinforce)

> Quando Gustavo envia `CONTINUE!!` o agente NÃO DEVE imediatamente empacotar novas tasks.
> **PRIMEIRO** rodar `git status -sb` + `git log --oneline -10` + orchestrator status para
> entender em qual loop/plano o estado real está. Em G7-loop o ciclo já passou por 28 waves
> e muitas tasks da "Wave 30 G6" já viraram tasks de G7 squads equivalentes.

## Ação tomada nesta sessão

1. `git push origin master` ✅ (3 commits sincronizados: da176f9, 67d7a53, 6720d10)
2. `make lint` (ruff + mypy) ✅ all green
3. `pytest -q --no-cov` ✅ 3176 passed / 20 skipped / 49 deselected
4. Diagnóstico de working tree (0 modified, 148 untracked) ✅
5. Orquestrador status ✅ (revela gap de leitura: v25 vs G7)

## Pendente (não crítico, não bloqueia)

- Commit consolidado dos 148 untracked (1 mega-commit `chore(loop-gustavo)`)
- Atualizar `scripts/super_loop_orchestrator.py` para ler G7 (substituir path v25 → G7)
- Atualizar `loop-state.json` canônico para refletir Wave 28 G7 (não v25 S4)
- Tag `v0.7.0-g7-mvp` (lesson 207 + 206 já tem notes ready, tag é HOLD-GUSTAVO)

## Cross-refs

- lesson-206 (G7 W13-28 consolidada) — status real 92% / 96% weighted
- lesson-207 (G7 W28 A4 SUI packs)
- lesson-185 (1-2 agents max em paralelo, regra Gustavo)
- lesson-180 (F0-F6 SUPER PLANO 100/100 cycle — predecessor)
- SUPER_GOALS_G7.md (canônico)
- SUPER_PLANO_G7_100_TASKS.md (canônico G7)
- docs/SUI_CHECKLIST_G7_WAVE28.md (HOLD mestra — DNS×3, env, tokens, QR, DPA, Privacy, AM, TS)

## Cross-project

Vale para QUALQUER projeto com multi-loop engine (lesson 141): sempre validar
`loop-state.json` vs `git log` antes de empacotar nova wave. Divergência = sessão
interrompida ou sync race. **Push first, analyze second** (lesson 142 — YOLO mode).

Modified by Gustavo Almeida