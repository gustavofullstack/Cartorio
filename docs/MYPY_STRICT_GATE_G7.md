# G7.21.T1 — mypy strict: zero regressions confirmation

**Task:** G7.21.T1  
**Agent:** cartorio-dev (A1)  
**Data verificação:** 2026-07-17  
**Status:** **DONE**

---

## Comando

```bash
cd backend && uv run mypy app/
```

Equivalentes no projeto:

```bash
# Makefile backend
make -C backend typecheck

# Lint gate local (ruff + mypy — ver Makefile / make lint na raiz)
make lint
```

CI (fresh cache — Lesson 64):

```bash
cd backend && rm -rf .mypy_cache && uv run mypy app/
```

---

## Resultado (verificado nesta sessão)

| Item | Valor |
|------|--------|
| **mypy version** | 2.1.0 (compiled: yes) |
| **Escopo** | `app/` (154 source files) |
| **Fresh cache** | Sim (`rm -rf .mypy_cache` antes da 2ª corrida) |
| **Erros** | **0** |
| **Exit code** | **0** |
| **Stdout** | `Success: no issues found in 154 source files` |

Regressão: **nenhuma** — gate mypy limpo no estado atual do branch de trabalho.

---

## Referência do CI gate

Arquivo: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

- Job de lint/typecheck roda em `working-directory: backend`
- Step: **Mypy typecheck (fresh, no cache — Lesson 64)**
- Comando CI:

```yaml
- name: Mypy typecheck (fresh, no cache — Lesson 64)
  working-directory: backend
  run: rm -rf .mypy_cache && uv run mypy app/
```

Também referenciado em:

| Artefato | Uso |
|----------|-----|
| `.github/workflows/deploy.yml` | Gate pré-deploy: mesmo padrão `rm -rf .mypy_cache && uv run mypy app/` |
| `.github/pull_request_template.md` | Checklist: `make lint` passa (ruff + mypy) |
| `backend/Makefile` | Target `typecheck` → `uv run mypy app/` |
| Root `AGENTS.md` / `Claude.md` | mypy strict em `app/`; gate 0 errors |

**Política do projeto:** 0 errors em `app/`. mypy é gate de CI e de `make qa` / pre-push (manual stage quando via pre-commit).

---

## Escopo e limites

- **In scope:** `backend/app/**/*.py` (154 arquivos na corrida de 2026-07-17).
- **Fora do gate habitual:** `tests/`, `alembic/versions/`, `mcp_server.py` (não cobertos por `mypy app/` a menos que o comando mude).
- Configuração: sem bloco `[tool.mypy]` explícito em `pyproject.toml` no momento da verificação — mypy usa defaults + o que o ambiente/projeto já aceita; o **contrato operacional** é o comando CI acima e **zero erros**.

---

## Status task

| Campo | Valor |
|-------|--------|
| **G7.21.T1** | **DONE** |
| Regressões | 0 |
| Commit | **Não** (pedido explícito da wave) |

Modified by Gustavo Almeida
