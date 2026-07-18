# Lesson 238 — G8.14.T4 N8N pre-commit workflow lint (2026-07-18)

## Contexto

Wave 47 candidato (lesson-236 listou): "G8.14.T4 — Automatizar export e
linting dos workflows JSON do n8n pré-commit". Rein: cartorio-n8n.

Motivação: o hook `workflow-validator` (G6.B.T1) já roda no pre-commit,
mas é global (`pass_filenames: false`) e varre TODOS os 39 WFs a cada
commit (~3–5s). Falta um gate per-file, sub-segundo, com regex anti-PII
sobre node names + parameters — exatamente os pontos onde um dev pode
acidentalmente colar um CPF num campo de teste.

## Decisões

### Por que um hook NOVO em vez de estender o `workflow-validator`?

| Aspecto | workflow-validator (existente) | n8n-workflow-lint (NOVO) |
|---------|---------------------------------|--------------------------|
| Escopo | Whole dir (3–5s) | Per-file (< 100ms) |
| LGPD check | Field-name based (`cpf`, `rg`) | Regex on values (CPF/CNPJ/PHONE-BR) |
| Onde roda | Global sanity | Pre-commit per-file fast feedback |

Ambos rodam juntos: global pega cross-WF issues (duplicate webhook paths);
per-file pega mistakes no diff antes do ship.

### Standalone CLI vs pre-commit-only

Script é **CLI-first**, depois wired no pre-commit. Razões:
1. CI pode rodar `python3 scripts/n8n_precommit_lint.py infra/n8n-workflows/*.json` sem instalar pre-commit framework
2. Local dev pode validar 1 arquivo isolado sem staging
3. Testes invocam o script via subprocess (mais próximo do real consumer)

Stdlib-only (json/re/argparse/pathlib) — zero deps, zero venv.

### Regex anti-PII: dash obrigatório

Primeiro rascunho: `\b\d{4,5}-?\d{4}\b` (dash opcional) → matchou
`31583914` (N8N assignment id, 8 dígitos sem pontuação). **False positive
crítico**: bloquearia TODO commit por causa de UUIDs internos do N8N.

Fix: dash obrigatório + parenthesized area code como segunda variante:
- `\b\d{4,5}-\d{4}\b` — `98855-1234`, `3333-4444` (mobile/landline sem DDD)
- `\(\d{2}\)\s*\d{4,5}-?\d{4}` — `(34) 98855-1234`, `(11) 3333-4444`

**Lesson**: regex PII deve casar APENAS formatos reais de produção
(portadores de telefone SEMPRE usam formatação), não formatos sintáticos
genéricos que aparecem em outros contextos.

## Implementação

### Arquivos criados

| Arquivo | LOC | Função |
|---------|-----|--------|
| `scripts/n8n_precommit_lint.py` | 180 | CLI standalone stdlib-only |
| `backend/tests/test_n8n_precommit_lint_g8.py` | 306 | 16 tests (positivos, negativos, false-positive regression, CLI surface) |
| `docs/N8N_PRECOMMIT_LINT_G8.md` | 163 | Setup, exemplos, bypass, regex catalog |

### Pre-commit config delta

```yaml
- id: n8n-workflow-lint
  name: N8N workflow lint (per-file strict + LGPD anti-PII, G8.14.T4)
  entry: python3 scripts/n8n_precommit_lint.py
  language: system
  pass_filenames: true
  files: ^infra/n8n-workflows/.*\.json$
```

`pass_filenames: true` é o que torna o hook per-file (vs `workflow-validator`
que tem `pass_filenames: false`).

### Bypass semantics

`SKIP=n8n-workflow-lint git commit ...` — convenção nativa do pre-commit
framework, sem precisar de `# noqa` em JSON (script nem lê marker).

## Test design

16 tests em 4 grupos:
- **Positivos (4)**: valid WF, empty argv, skip non-JSON, skip missing files
- **Negativos (8)**: invalid JSON, missing keys, bad nodes type, missing
  node type, PII CPF em name, PII CPF em params, PII CNPJ em params, PII
  PHONE (dashed + parens variants)
- **Anti-false-positive (1)**: 8-digit assignment IDs NÃO matcham PHONE
- **CLI surface (2)**: `--help`, `--quiet`

Anti-false-positive test é o mais valioso — ele congela a decisão de
design (dash obrigatório) e quebra imediatamente se alguém "simplificar"
o regex de volta para `\d{4,5}-?\d{4}`.

## Lições gerais (reaproveitáveis)

### 1. `pass_filenames: true` para gates per-file em pre-commit

Default do pre-commit é rodar o hook no diretório inteiro. Para gates que
só fazem sentido em arquivos modificados, use `pass_filenames: true` e o
framework passa cada arquivo staged como argumento posicional.

### 2. CLI-first scripts são test-friendly

Subprocess tests (`subprocess.run([sys.executable, str(SCRIPT), ...])`)
testam o EXATO consumer (pre-commit, CI), não uma internal API. Trade-off:
teste mais lento (process spawn) mas coverage do contrato real.

### 3. Regex PII deve mirar formatos REAIS, não sintaxe genérica

Erro clássico: `\d{4,5}-?\d{4}` (dash opcional) matchando UUIDs/IDs.
Lição: o disjuntor LGPD só vale se não bloquear fluxo normal. **Falso
positivo em produção é pior que gap conhecido** — devs aprendem a
bypassar, e o hook perde autoridade.

### 4. Re-aproveitamento do existing infra quando possível

Tentei reusar `scripts/n8n_wf_inventory.py --strict` (citado na spec da
task), mas essa flag `--strict` não existe no script real (Wave 47 G8.13.T2
ainda não tinha sido merged). Decidi escrever um CLI novo (180 LOC) em vez
de (a) esperar G8.13.T2 ou (b) extender G7.A2 com flag nova — manter o
escopo do G8.14.T4 focado.

## Coords multi-agent (lesson-236 follow-up)

Durante esta task, OUTROS 3 agents (Squad 13 G8.13.T2, Squad 17 G8.17.T1,
Squad 17 G8.17.T2) estavam ativamente fazendo `git checkout` no mesmo
worktree. Resultado: minha branch mudou 4 vezes durante a sessão
(`master → chore/g8-14-t4 → feat/g8-17-t1 → feat/g8-17-t2 → feat/g8-13-t2`).
Commit landed inicialmente na branch errada; recovery via
`git branch -f chore/g8-14-t4-n8n-precommit-lint <sha>` + `git checkout`.

**Lesson**: para waves paralelas, **sempre** rode `git checkout -b` antes
de qualquer `git add` e **sempre** verifique `git branch --show-current`
antes de `git commit`. Idealmente: ouve `git status` antes de cada commit
e re-checkout se necessário.

## Gates

| Gate | Resultado |
|------|-----------|
| `uv run ruff check scripts/n8n_precommit_lint.py backend/tests/test_n8n_precommit_lint_g8.py` | All checks passed |
| `uv run ruff format --check ...` | 2 files already formatted |
| `uv run mypy scripts/n8n_precommit_lint.py --ignore-missing-imports` | Success: no issues found |
| `uv run pytest tests/test_n8n_precommit_lint_g8.py` | 16 passed in 0.92s |
| `uv run pytest tests/test_n8n_precommit_lint_g8.py tests/test_n8n_workflow_validator.py` | 41 passed |
| Full tracked suite (excluding WIP from other agents) | 4010 passed, 0 failed |

## Honesty gate

| Check | Resultado |
|-------|-----------|
| `python3 scripts/n8n_precommit_lint.py infra/n8n-workflows/00-error-handler.json` | exit 0 OK |
| `python3 scripts/n8n_precommit_lint.py infra/n8n-workflows/*.json` (39 files) | exit 0 OK (zero false positives) |
| `python3 scripts/n8n_precommit_lint.py /tmp/wf_with_pii.json` (synthetic) | exit 1 with clear msg |
| `.pre-commit-config.yaml` válido | hook `n8n-workflow-lint` registered |

## Métricas

- Tests added: **+16**
- LOC added: **656** (180 script + 306 tests + 163 docs + 7 yaml)
- Honest count G8: **54 → 55/100**
- Branch: `chore/g8-14-t4-n8n-precommit-lint`
- Commit: `0672902`

Modified by Gustavo Almeida — 2026-07-18T13:45
