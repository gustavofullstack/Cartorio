# Pre-commit install — all devs (G7.22.T3)

| Campo | Valor |
|-------|--------|
| **Task** | G7.22.T3 — pre-commit install all devs |
| **Wave** | G7 Wave 26 |
| **Rein** | cartorio-n8n / cartorio-brain (docs) · cartorio-dev (hooks) |
| **Config** | [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) (raiz do repo) |
| **Regra** | Instalar em **toda** máquina de desenvolvimento. Hooks não substituem `make qa` no CI. |

---

## 0. TL;DR (2 minutos)

```bash
# Na raiz do repo Cartorio
cd /path/to/Cartorio

# 1) Tool pre-commit (recomendado: uv tool, alinhado ao stack)
uv tool install pre-commit
# fallback: pipx install pre-commit  |  pip install pre-commit

# 2) Instalar hooks no .git desta clone
pre-commit install

# 3) (Opcional) smoke uma vez em tudo
pre-commit run --all-files
```

Pronto: cada `git commit` dispara os hooks definidos em `.pre-commit-config.yaml`.

---

## 1. Pré-requisitos

| Req | Como checar | Notas |
|-----|-------------|--------|
| Git clone do repo | `git rev-parse --show-toplevel` | Hooks vivem em `.git/hooks/` |
| Python 3.11+ | `python3 --version` | Backend target py311 |
| `uv` | `uv --version` | `make install` / `cd backend && uv sync` |
| Deps backend | `cd backend && uv sync` | ruff + mypy via `uv run` |
| Rede (1ª vez) | — | Só se baixar plugins externos; **este repo usa `repo: local`** (sem download de hooks GitHub) |

> **Makefile vs framework pre-commit**  
> `make pre-commit` = lint + pytest-fast (atalho humano).  
> `pre-commit install` = framework que roda hooks no **git commit**.  
> São complementares — instale os dois.

---

## 2. Instalação detalhada

### 2.1 Instalar o CLI

```bash
# Preferido (mesmo gerenciador do backend)
uv tool install pre-commit

# Verificar
pre-commit --version
```

Alternativas aceitas:

```bash
pipx install pre-commit
# ou, se não houver uv/pipx:
python3 -m pip install --user pre-commit
```

### 2.2 Registrar hooks na clone

```bash
cd "$(git rev-parse --show-toplevel)"
pre-commit install
```

Isso cria/atualiza `.git/hooks/pre-commit` apontando para o framework.

### 2.3 (Opcional) commit-msg / pre-push

O YAML atual **não** define `default_stages` extras nem hooks `commit-msg` / `pre-push`.  
Política do projeto (AGENTS.md / CLAUDE.md):

- **mypy full** e **pytest coverage** são lentos → CI + `make qa` / pre-push **manual** quando existir.
- Conventional Commits (`feat:`/`fix:`/… + `Modified by Gustavo Almeida`) é **convenção humana** + review; não está no YAML atual.

Se no futuro adicionarem stage manual:

```bash
pre-commit install --hook-stage pre-push
pre-commit run --hook-stage manual --all-files
```

---

## 3. Inventário de hooks (source: `.pre-commit-config.yaml`)

Todos são `repo: local` + `language: system` (usam ferramentas já no PATH / `uv run`).

| id | Nome | Quando dispara | Comando |
|----|------|----------------|---------|
| `ruff-check` | ruff (lint backend) | `backend/**/*.py` | `cd backend && uv run ruff check . --fix --exit-non-zero-on-fix` |
| `ruff-format` | ruff format (backend) | `backend/**/*.py` | `cd backend && uv run ruff format --check .` |
| `mypy-selective` | mypy (changed files only) | `backend/app/**/*.py` | `cd backend && uv run mypy app/ --follow-imports silent` |
| `workflow-validator` | N8N workflow validator | `infra/n8n-workflows/**/*.json` | `python3 scripts/n8n_workflow_validator.py` |
| `openapi-snapshot` | OpenAPI snapshot check | `backend/app/**/*.py` | `python3 scripts/openapi_snapshot.py --check` |
| `dns-check` | DNS checker | **todo commit** (sem `files:`) | `python3 scripts/dns_health_check.py` |
| `secrets-scan` | secrets scan | **todo commit** (sem `files:`) | `python3 scripts/secrets_scan.py` |

Notas:

- **Speed target** no header do YAML: &lt; 5s por arquivo (ruff ms; mypy selective em s).
- `ruff-check` usa `--fix` → pode **reescrever** arquivos no working tree; re-stage se o hook formatar.
- `ruff-format` é `--check` (não reescreve; falha se desalinhado) → rode `make format` antes se falhar.
- `dns-check` pode ser HOLD/ruído offline — se bloquear commit sem rede, ver §5.

---

## 4. Uso diário

```bash
# Commit normal (hooks automáticos)
git add -A
git commit -m "feat: minha mudanca

Modified by Gustavo Almeida"

# Rodar todos os hooks sem commitar
pre-commit run --all-files

# Rodar um hook só
pre-commit run ruff-check --all-files
pre-commit run secrets-scan --all-files
pre-commit run workflow-validator --all-files

# Atalho Makefile (NÃO é o framework git)
make pre-commit     # lint + pytest -x --no-cov
make qa             # lint + test com coverage gate (igual CI)
```

### Checklist onboarding novo dev

1. [ ] `uv tool install pre-commit && pre-commit install`
2. [ ] `cd backend && uv sync`
3. [ ] `cp backend/.env.example backend/.env` (sem secrets reais no git)
4. [ ] `pre-commit run --all-files` (primeira vez pode falhar em format — `make format`)
5. [ ] `make test-fast` smoke local
6. [ ] Confirmar: `ls -la .git/hooks/pre-commit` existe e não é só `.sample`

---

## 5. Skip / troubleshooting

| Sintoma | Fix |
|---------|-----|
| `pre-commit: command not found` | `uv tool install pre-commit` e garanta `~/.local/bin` no `PATH` |
| `uv: command not found` nos hooks | Instale uv; ou use shell onde `backend` já tem venv |
| ruff format check falha | `make format` → `git add` de novo |
| mypy falha | Corrija types em `backend/app/`; gate é 0 errors |
| openapi snapshot drift | `python3 scripts/openapi_snapshot.py` (gerar) e revisar diff em `snapshots/` |
| N8N validator bloqueia | Ver `infra/n8n-workflows/VALIDATION_REPORT.md`; não commitar cred hard-coded |
| secrets_scan falha | Remova literal keys; opt-out pontual só com `# noqa: ALLOW_KEY_FALLBACK` (scripts) |
| dns-check ruído offline | Não use `--no-verify` por hábito. Se **emergência**: `SKIP=dns-check git commit ...` (pre-commit env) ou `git commit --no-verify` **com justificativa no PR** |
| Hooks não rodam | `pre-commit install` de novo; confira não estar em worktree sem hooks |

```bash
# Skip seletivo (framework pre-commit)
SKIP=dns-check,openapi-snapshot git commit -m "..."

# Nuke + reinstall hooks
pre-commit uninstall
pre-commit install
pre-commit clean   # limpa caches do framework
```

> **Proibido como hábito:** `git commit --no-verify` para contornar secrets-scan ou ruff. Review rejeita.

---

## 6. Relação com CI

| Camada | O que roda |
|--------|------------|
| Local pre-commit | Subset rápido (tabela §3) |
| `make pre-commit` | ruff/mypy-ish via lint + pytest-fast |
| `make qa` / `make ci` | Gate completo (= GitHub Actions) |
| GHA `ci.yml` | ruff, mypy, pytest cov≥90, secrets, etc. |

Pre-commit **não** garante coverage 90% nem mutation. Sempre `make qa` antes de abrir PR (template em `.github/pull_request_template.md`).

---

## 7. Verificação “all devs installed”

Para o time / lead:

```bash
# Em cada máquina
pre-commit --version && test -x .git/hooks/pre-commit && echo "HOOK_OK"
```

PR checklist sugerido (onboarding):

- [ ] Li este doc (`docs/PRECOMMIT_INSTALL_G7.md`)
- [ ] `pre-commit install` executado nesta clone
- [ ] `pre-commit run secrets-scan --all-files` exit 0

---

## 8. Evolução do YAML (fora de escopo T3)

Possíveis melhorias futuras (não implementadas aqui):

1. Filtrar `dns-check` com `files:` ou stage `manual` (evita falha offline).
2. Hook `check_no_literal_keys.py` / `check_no_bare_exception.py` alinhados ao CI.
3. `commit-msg` conventional commits.
4. `pass_filenames: true` seletivo para mypy só em arquivos staged (mais rápido).

---

## 9. Referências

- Config: `.pre-commit-config.yaml`
- AGENTS.md / CLAUDE.md — seção lint + pre-commit
- `scripts/n8n_workflow_validator.py`, `scripts/secrets_scan.py`, `scripts/dns_health_check.py`, `scripts/openapi_snapshot.py`
- `docs/CD_EASYPANEL_HOOK_G7.md` — CD ≠ pre-commit

---

**Modified by Gustavo Almeida** — G7 Wave 26 (G7.22.T3) · cartorio-n8n/brain
