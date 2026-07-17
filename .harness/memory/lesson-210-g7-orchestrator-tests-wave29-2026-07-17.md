# Lesson 210 — Testes do g7_orchestrator (15 PASSED) Wave 29 A1 (2026-07-17)

Type: project + reference

## Contexto

Lesson 209 (Wave 29 closeout) já consolidou:
- orquestrador G7 default (scripts/super_loop_orchestrator.py → g7_orchestrator.py)
- N8N inventário 38 WFs
- LGPD dashboard go-live
- Canal health matrix

**Gap identificado**: `scripts/g7_orchestrator.py` (canônico) NÃO tinha testes unitários.
Risco: regressão silenciosa em `parse_tasks()` regex / `next_cmd()` diversity / `main()` dispatch.

## Entrega (Wave 29 A1)

`backend/tests/test_g7_orchestrator.py` — **15 testes, 100% PASS em 0.19s**.

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestParseTasks | 6 | done / mixed / empty / missing file / malformed / partial precedence |
| TestStatusCmd | 2 | progress pct + loop-state JSON integration |
| TestNextCmd | 2 | squad diversity + fallback <4 squads |
| TestMain | 3 | default status / validate dispatch / unknown command |
| TestIntegrationWithRealPlan | 2 | ≥100 tasks parsed + ≥85% progress (Wave 28 ~92%) |

### Por que esses testes importam

1. **parse_tasks()** — regex `\[[ x~X]\]` é frágil. Se alguém mudar formato da tabela no
   `SUPER_PLANO_G7_100_TASKS.md`, status fica silenciosamente errado.
2. **next_cmd()** — diversity por squad evita que 4 agents peguem 4 tasks do mesmo squad.
3. **Integration tests** — guard contra regressão de progresso (se alguém marcar `[x]`
   sem realmente fazer).

## Validação gates pós-wave

| Gate | Antes | Depois |
|------|-------|--------|
| pytest | 3176 | **3191** (+15) |
| mypy strict | 0/155 | 0/155 |
| ruff | 0 | 0 |

## Decisão de versionamento

- Lesson 209 já existia (Wave 29 closeout criada pelo loop G7 em paralelo)
- Minha contribuição ficou como **Lesson 210** (não duplica 209)
- MEMORY.md index atualizado (próxima seção)

## Próxima wave (Wave 30?)

8 [~] abertas no G7 plano = **TODAS SUI Gustavo** (DNS UI, QR scan, env vars, tokens).
**NÃO há wave de código** a rodar sem antes Gustavo resolver SUI.

Opções Wave 30 (todas opcionais):
1. Mega-commit dos 148 untracked (SUI #14) → working tree 100% clean
2. Mais 1-2 testes em módulos <90% coverage (se houver)
3. SUI específico Gustavo autoriza (ex: rotear DNS via script)

## Cross-refs

- lesson-209 (Wave 29 closeout, paralelo)
- lesson-208 (push-first-analyze-second)
- lesson-185 (1-2 agents max)
- scripts/g7_orchestrator.py (canônico)
- scripts/super_loop_orchestrator.py (wrapper G7 default)

Modified by Gustavo Almeida