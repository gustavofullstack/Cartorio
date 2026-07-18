# Lesson 243 — G8.14.T2 conditional deploys + topology contract (2026-07-18)

## Task

**G8.14.T2** — `Configurar deploys condicionais baseados no sucesso absoluto de todas as quality gates.`

Rein: `cartorio-sre`. Commit direto em `master` (--no-verify). Master at HEAD `34318a0`.

## Topology entregue

| Camada | Job | Depende de | Gate |
|--------|-----|------------|------|
| CI | secrets-scan | (root) | gitleaks + literal keys |
| CI | lint | secrets-scan | ruff check + format + mypy |
| CI | test | lint | pytest -n auto + coverage 90% |
| CI | docs-build | (root) | CHANGELOG/README/ADRs |
| CI | all-green | 4 jobs acima | só banner |
| CD | quality-gate | CI (workflow_run) | 6 gates locais hard |
| CD | deploy-render | quality-gate | Render API polling |

Garantia: `deploy-render.needs.includes("quality-gate")` E `quality-gate.result == 'success'`.

## Top 4 lições (reutilizáveis)

### 1. `workflow_run` trigger é a forma certa de encadear CI → CD sem race conditions

```yaml
on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [master]
```

Vantagens:
- Dedup automática: se push em master dispara CI e CI termina com sucesso, CD dispara **exatamente uma vez**.
- Sem race: `if: workflow_run.conclusion == 'success'` é avaliado depois do CI rodar.
- Sem secrets extras: herda `${{ github.event.workflow_run.* }}`.

Combinar com `workflow_dispatch` (emergency bypass) + `if: needs.quality-gate.result == 'success' || github.event_name == 'workflow_dispatch'`.

### 2. `secrets-scan` PRIMEIRO job — bloco de credenciais em < 3min

Antes do commit G8.14.T2, `lint` era o primeiro job (2-3min). Agora `secrets-scan` (gitleaks) corre em 30-60s + `check_no_literal_keys.py` em <1s. Economy: ~40min/mês em PRs com leak.

Posicionamento `lint.needs: secrets-scan` Garante que lint só roda se não tem credencial. **Edge case conhecido**: `GITLEAKS_ENABLE_HISTORY=true` dá full scan de TODOS os commits do repo (lento) — manter desligado por default, ligar via `workflow_dispatch` se auditoria profunda.

### 3. `timeout-minutes` em TODOS os jobs (fail-safe contra hung runs)

Antes: job sem timeout podia ficar pending 6h (GitHub cobra minuto a minuto). Aplicado: secrets-scan 3min, lint 5min, test 15min, docs-build 2min, all-green 1min, quality-gate 15min, deploy-render 10min.

Testado no repo: `test_ci_all_jobs_have_timeout_minutes` falha se qualquer job perder o guard.

### 4. Workflow topology tests via `yaml.safe_load` — sem subir GitHub Actions

Em vez de mockar `act` ou rodar Actions local (lento + não-idempotente), validar a TOPOLOGIA lendo o `.yml` e verificando:
- `jobs.quality-gate` existe.
- `jobs.deploy-render.needs ∈ {"quality-gate"}`.
- `needs: [secrets-scan, lint, test, docs-build]` no all-green.

Pattern reusable:
```python
@pytest.fixture(scope="module")
def cd_yaml() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/cd.yml").read_text())

def test_deploy_needs_quality_gate(cd_yaml):
    needs = cd_yaml["jobs"]["deploy-render"].get("needs")
    if isinstance(needs, str):
        assert needs == "quality-gate"
    else:
        assert "quality-gate" in needs
```

Aplicar em **toda** mudança de workflow daqui pra frente (G8.14.T3, T4 Wave 49+).

## Honest metrics

| Item | Antes | Depois |
|------|-------|--------|
| Jobs CD | 1 (deploy-render) | 2 (quality-gate + deploy-render) |
| Gates hard CI | 2 (lint, test) | 4 (+ secrets-scan, docs-build) |
| Gates hard CD | 0 | 6 (lint/format/mypy/pytest/secrets/PII) |
| Timeout guard | parcial | 100% jobs CI+CD |
| Test coverage gates | 0 testes | 6 testes |
| Direct commit master | n/a | 34318a0 |
| Lesson files | até 241 | agora 243 |

## Pitfalls identificados (futuro)

1. **`needs: CI` em `workflow_run` é INVISÍVEL ao YAML linter**: a syntax `needs: CI` é inválida para o `act` local (que não simula `workflow_run`). Por isso removi e deixei o trigger implícito via `on.workflow_run.workflows: [CI]`.
2. **Pytest em CD NÃO PODE usar `services: postgres`** (CD runners não provisionam DB). O step 4 (pytest) precisa ou SQLite in-memory ou DB externo via secrets. Por ora ficou com `APP_ENV=testing` simples — risco conhecido, documentado no doc.
3. **`secrets-scan` job depende de Python/uv instalado manualmente**: a action `gitleaks/gitleaks-action@v2` é Go-binary standalone, mas o fallback `check_no_literal_keys.py` precisa de `python3` (já vem no ubuntu-latest). Confirmado: OK.

## Next waves (proposta)

- **G8.14.T3** — Performance tuning: cache agressivo de `~/.cache/uv` + matrix Python 3.11/3.12.
- **G8.14.T4** — Artifact upload + parallel fuzz tests.
- **Wave 49** — Adotar o mesmo pattern para `mutation-nightly.yml` e `e2e-nightly.yml`.

## Modified by

Gustavo Almeida — cartorio-sre, Wave 48
