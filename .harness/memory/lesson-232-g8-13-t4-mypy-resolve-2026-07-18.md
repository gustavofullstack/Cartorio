# Lesson 232 — G8.13.T4: Resolver mypy warnings restantes (Wave 45 baseline → 2 errors → 0) — 2026-07-18

## TL;DR

Wave 45 consolidada (`f2aac13` / `3c453d0`) deixou **2 mypy errors residuais**
no backend (190 source files). G8.13.T4 eliminou ambos com fixes corretos
(**zero `# type: ignore` adicionado**):

| Path | Line | Category | Fix |
|------|------|----------|-----|
| `app/services/emolumento.py` | 119 | **C-Real** (dead code / drift risk) | Removeu redefinição local de `isencao_aplicavel()` — já vem de `emolumento_validacao.py` (G8.11.T3 SOLID split). |
| `app/services/traefik_lobechat_routing.py` | 27 | **C-External** (lib sem stubs) | Adicionou `types-PyYAML>=6.0.12.20260518` ao dev dep group. |

**Final**: `uv run mypy app/` → `Success: no issues found in 190 source files`.
**Pytest**: `test_emolumento.py` + `test_emolumento_validacao.py` +
`test_traefik_lobechat_routing_g8.py` = **58 passed**.
**Ruff**: clean.

## Contexto

Tarefa do SUPER_PLANO_G8 (item G8.13.T4):
**"Resolver quaisquer advertências remanescentes do mypy strict no
backend."** Escopo definido:

1. Rodar `mypy app/` como baseline.
2. Para cada warning/error: avaliar bug-real vs ruído, fix correto,
   regression test se possível.
3. Re-rodar mypy → zero.

Lesson 164 (Wave 38) já tinha zerado 7 erros. Após Wave 45 consolidado
(commit `f2aac13`) + lessons 226-231, estes 2 persistiam.

## Workflow executado

### 1. Analisar

- Lido `AGENTS.md` (P0 rules + HITL).
- Lido `lesson-164-mypy-7-errors-resolved-2026-07-13.md` (decisão chave:
  **mypy default config + per-line annotations > global strict mode
  for legacy projects**. Mantém `[tool.mypy]` vazio).
- Confirmado: o gate do projeto é `mypy app/` (default), NÃO strict.

### 2. Baseline (testar)

```
$ uv run mypy app/ 2>&1 | tail -5
app/services/traefik_lobechat_routing.py:27: error: Library stubs not installed for "yaml"  [import-untyped]
app/services/traefik_lobechat_routing.py:27: note: Hint: "python3 -m pip install types-PyYAML"
...
app/services/emolumento.py:119: error: Name "isencao_aplicavel" already defined (possibly by an import)  [no-redef]
Found 2 errors in 2 files (checked 190 source files)
```

**Baseline**: 2 errors / 0 warnings / 2 arquivos afetados.

### 3. Corrigir

#### Fix #1 — `app/services/emolumento.py:119` [no-redef]

**Category**: C-Real (dead code / drift risk).

**Root cause**: Wave 43 (G8.11.T3) promoveu `isencao_aplicavel` para o módulo
puro `app/services/emolumento_validacao.py` (SOLID SRP). O `emolumento.py`
original ainda tinha uma **definição local duplicada** com constantes inline
(`gratuítos`, `motivos_validos`) — mas o mesmo símbolo já era importado
no topo. mypy detectou a colisão como `no-redef`.

**Avaliação**: definição local é **dead code** que pode drift da versão
canônica. Os 22 callers (tests + `app/api/v1/router.py:181`) já importam
via `from app.services.emolumento import isencao_aplicavel` — vão pegar
o símbolo canônico automaticamente.

**Fix**: deletar o bloco de 17 linhas (function local + constante `gratuítos`
+ constante `motivos_validos` inline). O `from app.services.emolumento_validacao
import isencao_aplicavel` no topo já provê o símbolo. `__all__` mantém
referência ao nome (back-compat preservada). Docstring adicional no
`__all__` aponta a razão da remoção (SOLID SRP).

#### Fix #2 — `app/services/traefik_lobechat_routing.py:27` [import-untyped]

**Category**: C-External (lib externa sem stubs no projeto).

**Root cause**: `try: import yaml` levanta `[import-untyped]` porque PyYAML
(`pyyaml==6.0.3`, já no `uv.lock`) **não bundle type stubs**. mypy hint:
`Hint: "python3 -m pip install types-PyYAML"`.

**Avaliação**: dois caminhos possíveis:

| Opção | Prós | Contras |
|-------|------|---------|
| (A) `uv add --group dev types-PyYAML` | Canonical fix, type-check completo em `yaml.safe_load(text)` | Lockfile churn (11 linhas) |
| (B) `# type: ignore[import-untyped]` | 1 linha | Cobre o sintoma mas mantém `yaml.safe_load` como `Any` |

**Fix escolhido: (A)** — `types-PyYAML==6.0.12.20260518` adicionado ao
`[dependency-groups] dev` em `pyproject.toml`. Lockfile regerado.
Imediatamente mypy começou a checar `yaml.safe_load(text)` com tipos
precisos (sem novos warnings).

### 4. Melhorar

- **Tests existentes continuam PASS** sem mudança alguma. Função
  `isencao_aplicavel` continua exportada com a mesma assinatura
  `(tipo: str, *, motivo: str) -> bool`. Tests em `test_emolumento.py`
  e `test_emolumento_validacao.py` passam (58 tests total).
- **Não adicionei regression test novo** porque (a) o fix #2 é puramente
  infra (stubs lib) — sem mudança comportamental; (b) o fix #1 é remoção
  de código morto, e os 22 callers já existentes exercitam
  consistentemente o símbolo re-exportado. Adicionar um teste
  que verifica `emolumento.isencao_aplicavel is emolumento_validacao.isencao_aplicavel`
  seria frágil (testaria implementação, não contrato).

### 5. Otimizar

- `.mypy_cache` regenera incremental — zero overhead para re-runs.
- `pyproject.toml` `dev` dep group: `types-PyYAML>=6.0.12.20260518` (lock).
- Nenhuma anotação deprecada, nenhum `# type: ignore`.

### 6. Documentar

- Esta lesson 232 (registro do trabalho).
- Docstring adicional em `app/services/emolumento.py` apontando o
  motivo da remoção (SOLID SRP).
- `__all__` mantido com comentário explicativo no `emolumento.py`.

### 7. Comentar

- Branch `chore/g8-13-t4-mypy-resolve` off `3c453d0` (Wave 45 consolidada).
- Commit com mensagem Conventional Commits — termina com
  `Modified by Gustavo Almeida`.

### 8. Memória (este arquivo)

Persistir a receita de fix canônico (types-PyYAML em vez de `# type: ignore`)
para reuso futuro.

## Honesty gate (estado pós-fix)

```
$ uv run mypy app/ 2>&1 | tail -3
Success: no issues found in 190 source files
$ uv run ruff check app/
All checks passed!
$ uv run pytest --no-cov -q tests/test_emolumento.py tests/test_emolumento_validacao.py tests/test_traefik_lobechat_routing_g8.py
58 passed in 0.43s
```

**Caveat de ambiente**: durante a execução da task, existia um arquivo
**UNTRACKED** em `app/api/v1/alertmanager.py` (G8.15.T2 — AlertManager
webhook router, WIP de outro agente em squad paralela Wave 47). Este
arquivo não está no escopo de G8.13.T4 (wave 45 baseline) e não foi
tocado por esta task — pertence ao agente responsável pela G8.15.T2.
Em meio à corrida multi-agent, o arquivo foi subsequentemente refinado
pelo agente G8.15.T2 que eliminou o erro de tipo independentemente.

## Anti-padrões evitados

1. **Não usei `# type: ignore` genérico** — e onde o tipo da categoria era
   stubs (`types-PyYAML`), instalei o pacote canônico em vez de silenciar.
   Diferente de fix #1 (lesson 164, `bot_metrics.py:183`), usei `cast()` +
   Literal shrinking — aqui a solução limpa é prover stubs.
2. **Não toquei `.venv` ou libs externas** — só adicionei dep em
   `[dependency-groups] dev` e lockfile.
3. **Não fiz merge** — só commit local em branch `chore/g8-13-t4-mypy-resolve`.
4. **Não modifiquei arquivos WIP de outras squads** (`alertmanager.py`,
   etc.) — política multi-agent: cada squad zela pelos seus próprios
   arquivos untracked.

## Refs

- [[lesson-164-mypy-7-errors-resolved-2026-07-13]] — política "default +
  per-line > strict"; precedente do `cast()` legítimo em `bot_metrics.py`.
- [[lesson-231-g8-wave-45-consolidation-recovery-2026-07-18]] — Wave 45
  consolidada (commit `f2aac13`) que criou o estado pós-fix com 2
  erros remanescentes.
- [[lesson-225-g8-11-t3-emolumento-validation-retry-2026-07-18]] — split
  SOLID SRP de `emolumento.py` → `emolumento_validacao.py` que motivou
  o dead code.
- Modified by Gustavo Almeida — G8.13.T4 / cartorio-dev — 2026-07-18.
