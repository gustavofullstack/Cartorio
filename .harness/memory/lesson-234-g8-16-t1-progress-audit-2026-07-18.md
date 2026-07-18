# Lesson 234 — G8.16.T1 PROGRESS.md Upsert Automation (2026-07-18)

## Contexto

Squad 16 / Wave 46 do SUPER PLANO G8. Tarefa G8.16.T1 ("Criar automação para
persistência do progresso diário no `PROGRESS.md`") vivia sem owner claro
após Wave 45 (Squad 12). Agents vinham appendando blocos wave manualmente
no `PROGRESS.md`, com formatos divergentes (alguns com `Wave N REAL`, outros
com `Wave N G7`, alguns sem emoji). Honesty gate arriscava regressão por
falta de contrato canônico.

## Decisão arquitetural

**Script único em Python** (`scripts/progress_audit.py`) ao invés de hook
shell ou template. Justificativa:

| Opção | Pro | Contra | Decisão |
|-------|-----|--------|---------|
| Shell hook em `.git/hooks/post-commit` | trigger automático | shell syntax frágil, sem argparse, validação pobre | rejeitado |
| Template + sed | simples | não idempotente, regex frágil | rejeitado |
| Bash script com env vars | deps zero | legibilidade, sem testes unitários fáceis | rejeitado |
| **Python com argparse** | argparse nativo, dataclass, pytest-friendly, integra com `make` | precisa stdlib Python 3.11+ (já requisito do repo) | **escolhido** |

Estendi a família de helpers existente (`scripts/g7_progress_append.py` —
G7.23.T3 Wave 24), mas com **formato G8 canônico** observado em
`PROGRESS.md` linhas 3673-3736 (Wave 44/45 reais):

```
## 2026-07-18 — Wave 46 REAL COMPLETED ✅ (cartorio-sre)

- **Honest count:** 50 → **51/100** (+1)
- **G8.16.T1** descrição curta
- **Tests:** 7 passed
Modified by Gustavo Almeida — 2026-07-18T15:51:21+00:00
```

## Antes → Depois

**Antes** (manual, 4 inconsistências comuns):
1. Sem `REAL COMPLETED ✅` → agente esquecia emoji.
2. Honest count inventado (não lia `SUPER_PLANO_G8`).
3. Wave number vinha do nome do agente, não do git log.
4. Re-rodar gerava duplicata ao invés de substituir.

**Depois** (automatizado):
1. ✅ Header determinístico (`## DATE — Wave N REAL COMPLETED ✅ (cartorio-AGENT)`).
2. ✅ Honest count extraído via regex da tabela `| G8.NN.TM | ... | [x]|`.
3. ✅ Wave default = maior `Wave N` em `git log -n50`.
4. ✅ Idempotência por `wave` (regex `^## \d{4}-\d{2}-\d{2} — Wave N`).

## Implementação

- `scripts/progress_audit.py` (228 linhas, stdlib only)
  - `ProgressEntry` dataclass com `render()` puro
  - `count_honest_checkmarks()` lê tabela do `SUPER_PLANO_G8_100_TASKS.md`
  - `split_existing_blocks()` + `upsert_block()` preserva timeline
  - `--apply` persiste; `--dry-run` é no-op em disco
- `backend/tests/test_progress_audit.py` (7 testes, 0.23s)
- `docs/PROGRESS_AUDIT.md` (CLI reference + integração com `goal-loop-cron.sh`)
- Makefile: `progress-audit WAVE=N AGENT=sre PRE=X POST=Y TESTS=Z BULLET="..."`

## Métricas

- Honest count: **50 → 51/100** (+1)
- 7 unit tests PASS (formato, idempotência, count, timestamp, dry-run, apply, CLI E2E)
- Ruff: 0 errors / 0 format diffs
- Idempotência validada: 2× apply com mesmo `--wave` → 1 header no arquivo

## Integração futura

`scripts/progress_audit.py` complementa `.harness/loop-engineer/goal-loop-cron.sh`.
Enquanto o cron escreve blocos genéricos `LOOP cycle #N` com payload JSON,
este helper produz o bloco canônico `REAL COMPLETED ✅` exigido pelo squad 16.

Sugestão (próxima task, fora do escopo desta): estender `goal-loop-cron.sh`
para invocar `progress_audit.py --apply` após `RES_TEST=PASS`, com
`--wave` lido de `.brain/loop-state.json` (já tem `last_wave`).

## Anti-padrões evitados

- **NÃO** usei `# noqa: ALLOW_KEY_FALLBACK` (zero secrets envolvidos).
- **NÃO** alterei formato de entradas antigas (preservação histórica).
- **NÃO** fiz hook git (orquestrador decide quando invocar).
- **NÃO** commitei direto em master (branch `chore/g8-16-t1-progress-audit`).

## Cross-refs

- Lesson 231 — G8 Wave 45 consolidation recovery (contexto de branches stranded)
- Lesson 230 — G8 Wave 43-45 closeout (formato `REAL COMPLETED ✅` origin)
- Lesson 217 — Wave 33 G8 MCP/Idempotency (registry de waves G8)
- `scripts/g7_progress_append.py` — G7.23.T3 precursor (mesma família)

## Modified by Gustavo Almeida — cartorio-sre · G8.16.T1 Wave 46
