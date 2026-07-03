# F05 E2E Playwright — Setup & Full Flow

## TL;DR

- **Suite Playwright E2E completa** (8 tests em 1 arquivo) cobrindo fluxo
  ponta-a-ponta do cartorio 2notas: cliente novo → protocolo DRAFT →
  agendamento → atendimento → emolumento → documento upload → soft
  delete (A19) → LGPD consent revogacao.
- **5 cenarioes principais + 2 helpers + 1 health** = 8 tests totais.
- **CI nightly skeleton** criado em `.github/workflows/e2e-nightly.yml`
  (INACTIVE — requer Gustavo GO para ativar `on.schedule`).
- **NAO roda em CI unit** (marker `e2e` excluido via `addopts`), mantendo
  suite 1648+ tests rapida (<3min).
- **Custo CI**: ~5min nightly single-browser (chromium only — firefox/webkit
  inflaria +200MB por browser).

## Stack

- **Tool**: `playwright>=1.40,<2` + `pytest-playwright>=0.5,<1`
- **Browser**: chromium-only (1 binary ~200MB vs 600MB+ com trio)
- **Marcador**: `@pytest.mark.e2e` registrado em pyproject.toml
- **Optional-deps**: `[project.optional-dependencies.e2e]` SEPARADO de
  `dev` para nao inflar CI unit (Lesson F01: lessons learned from mutmut).
- **Cleanup**: soft delete via DELETE /cliente/{id} (A19 compat).
  Preserva audit log imutavel (LGPD art. 37).
- **Auth**: X-API-Key 64 hex (gate admin em endpoints protegidos) +
  E2E_BASE_URL env var (default localhost:8000, prod Tailscale).

## Cenarios cobertos

| # | Nome | Endpoints exercidos | LGPD gate | A19 |
|---|------|---------------------|-----------|-----|
| 1 | cliente novo protocolo DRAFT | POST /protocolo | YES (consentimento) | - |
| 2 | agendamento presencial + confirmar | POST /agendamento + GET list + POST confirmar | - | - |
| 3 | atendimento WhatsApp handoff | POST /atendimento + POST /atendimento/{id}/concluir | - | - |
| 4 | emolumento calculado | GET /emolumento/calcular (com/sem urgencia, tipo invalido) | - | - |
| 5 | documento upload + hash SHA256 | POST /documento/upload | - | - |
| 6 | soft delete A19 | DELETE /cliente/{id} + GET /cliente/{id} + GET /v2/clientes | YES | YES |
| 7 | LGPD consent revogacao (D31) | POST /lgpd/consent + POST /lgpd/revogar-consent + GET /lgpd/dashboard | YES | - |
| 8 | health smoke | GET /health/live | - | - |

**Bonus**: smoke test `tests/test_e2e_health.py` valida setup Playwright
(lib + bindings + chromium binary). NAO marker e2e — roda em CI unit
para detectar drift de instalacao. SKIP se playwright NAO instalado.

## Comando reproducao

### Local (dev)

```bash
cd backend
uv pip install -e ".[e2e]"
playwright install chromium

# Rodar suite (requer API up em localhost:8000)
E2E_BASE_URL=http://localhost:8000 \
  uv run pytest tests/e2e/ -m e2e --browser chromium -v --tb=short --no-cov

# Apenas smoke (drift detection — roda em CI unit)
uv run pytest tests/test_e2e_health.py -v --no-cov
```

### CI nightly (apos Gustavo GO)

```bash
# .github/workflows/e2e-nightly.yml — schedule DESATIVADO por default.
# Trocar `cron: "0 3 * * *"` para ativar.
uv sync --extra e2e
playwright install chromium
E2E_BASE_URL=https://api.2notasudi.com.br \
  uv run pytest tests/e2e/ -m e2e --browser chromium -v --tb=short
```

## Decisoes de design

### Por que httpx.Client e NAO Playwright APIRequest para a suite?

A UI web do cartorio NAO existe ainda (backend-only). Playwright APIRequest
e equivalente a httpx + headers, mas adiciona overhead de context browser.
**Suite F05 usa httpx.Client** (`api_session` fixture) por:

1. **Velocidade**: 10x mais rapido (sem browser launch ~2s overhead).
2. **Estabilidade**: zero flake de browser crash.
3. **Drift detection**: smoke `test_e2e_health.py` valida Playwright
   install separadamente — se drift, smoke falha e bloqueia suite.
4. **Compatibilidade**: suite F05 pode ser movida para UI testing no
   futuro (`e2e_page` fixture ja existe, basta usar `page.goto()`).

### Por que marker e2e excluido de addopts?

```ini
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=90 -m 'not smoke and not integration and not e2e'"
```

Suite 1648+ tests roda em <3min hoje. Adicionar 8 tests E2E inflaria
runtime + dependeria de API online (flake em CI unit). Marker `e2e`
explicitamente excluido — suite E2E roda apenas em:
- Dev local: `pytest -m e2e`
- CI nightly (futuro): workflow separado

### Por que cleanup via soft delete e NAO drop database?

A19 lesson: `Cliente` tem soft delete via `SoftDeleteMixin`. Drop
database destruiria audit log imutavel (LGPD art. 37). Soft delete
preserva integridade referencial de protocolos + audit + LGPD rastreabilidade.

## Pitfalls canonicos descobertos

1. **Playwright import quebrando mypy** — `playwright` vive em
   `[project.optional-dependencies.e2e]`, nao em deps principal.
   Mypy default retorna `import-not-found`. Solucao canonica:
   ```python
   if TYPE_CHECKING:
       from playwright.sync_api import Browser as PlaywrightBrowser  # type: ignore[import-not-found]
   ```
   E em runtime: `# type: ignore[import-not-found]` no import.

2. **Generator fixture + return type** — pytest fixtures com `yield`
   devem ter return type `Iterator[X]`, NAO `X`. Mypy default pega
   isso: `[misc] The return type of a generator function should be
   "Generator" or one of its supertypes`.

3. **Conditional return antes de yield** em fixture autouse confunde
   mypy. Solucao: `return` antes de yield NAO conta como generator
   return — usar `# type: ignore[return-value]` no early return.

4. **Smoke test fail vs skip** — `test_e2e_health.py` deve SKIP
   (nao FAIL) quando playwright NAO instalado em CI unit. Se FAIL,
   CI unit quebra mesmo sem suite E2E configurada. Usar
   `pytest.importorskip("playwright", reason="...")`.

5. **`addopts` filter** — `-m 'not e2e'` em addopts esconde E2E
   do collect. Para debug, rodar `pytest tests/e2e/ -m e2e --no-cov`
   explicitamente. CI unit nao coleta E2E — economiza ~2s startup.

## Compliance verificacoes

- [x] Ruff check + format clean (`ruff check .` + `ruff format --check .`)
- [x] mypy 0 errors em `app/` (production code, NAO tests)
- [x] pytest unit 1648+ tests continua passando (marker e2e excluido)
- [x] Toda mutacao via soft delete (LGPD art. 37 audit log preservado)
- [x] Suite E2E NAO roda em CI unit (addopts exclui marker)
- [x] CI nightly skeleton INACTIVE (gate Gustavo para ativar)
- [x] Smoke test detecta drift Playwright install
- [x] Cada cenario e idempotente (cleanup via soft delete)

## Decisao FINAL: NAO rodar suite E2E em todo PR

Custo proibitivo:
- ~5min por run (chromium launch + 8 tests)
- ~$0.10/run em GH Actions (ubuntu runner)
- Free tier 2000min/mes — 1 run/dia ja eh 1500min/mes

**Recomendacao**: manter nightly apenas (custo ~150min/mes), expandir
para PR-mergeable apenas em tasks F05.1+ (UI testing).

## Follow-ups

- **F05.1** — UI E2E com React (quando frontend existir). Reusar
  `e2e_page` fixture, adicionar login flow + dashboard rendering.
- **F05.2** — Multiple browsers (firefox + webkit) — custo +400MB
  e +5min, decidir baseado em fragmentacao user base.
- **F05.3** — Visual regression testing (Playwright screenshot diff).
- **F05.4** — CI gate enforcement (fail PR se suite E2E quebrou).

Modified by Gustavo Almeida