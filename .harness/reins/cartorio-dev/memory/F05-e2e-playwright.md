# F05 E2E Playwright — v2 (Feedback Verifier Attempt 1)

## TL;DR v2

Suite Playwright E2E completa (6 tests em 1 arquivo) cobrindo fluxo
ponta-a-ponta do cartorio 2notas: cliente novo → agendamento →
atendimento → emolumento → documento (SHA256) → soft delete (A19) →
LGPD consent revogacao.

**Diffs vs v1 (rejeitada por verifier attempt 1)**:

1. **Nomenclatura canonica**: `e2e_client` e `e2e_admin` (browser_contexts
   Playwright autenticados). v1 usava `e2e_cliente` e `e2e_api_key`
   (string X-API-Key) — REJEITADO.
2. **Smoke test SEM importorskip**: v2 usa `subprocess.run(['playwright',
   '--version'])` puro (stdlib only) + `urllib.request.urlopen()` health
   check. v1 usava `pytest.importorskip("playwright")` que AINDA exigia
   Playwright instalado — REJEITADO.
3. **Workflow MANUAL-ONLY**: v2 `e2e-nightly.yml` tem APENAS
   `on: workflow_dispatch` (SEM `on.schedule`). v1 tinha
   `schedule: cron "0 3 * * *"` mesmo INACTIVE — REJEITADO.

## Nomenclatura canonica v2

| Fixture v1 (REJEITADO) | Fixture v2 (ACEITO) | Tipo |
|------------------------|---------------------|------|
| `e2e_api_key` (string) | `e2e_admin` (BrowserContext autenticado) | admin |
| `e2e_cliente` (dict de dados) | `e2e_client` (BrowserContext + cliente criado on-the-fly) | cliente |
| `e2e_context` (Playwright ctx) | `e2e_admin.context` (acessar via attribute) | helper |
| `e2e_page` (Playwright page) | `e2e_page` (unchanged, mas usa `e2e_admin` como base) | page |
| `api_session` (httpx) | `api_session` (unchanged) | httpx shortcut |

Helper class `E2EUserContext`:
```python
@dataclass
class E2EUserContext:
    context: PlaywrightBrowserContext
    user: dict[str, Any]  # {"role": "admin|cliente", "api_key", ...cliente_data}
```

Uso:
```python
def test_x(e2e_admin: E2EUserContext, e2e_client: E2EUserContext):
    # admin context (X-API-Key admin header injetado)
    e2e_admin.context.request.get("/api/v1/health/live")
    # cliente context (X-API-Key client + cliente_id em e2e_client.user)
    cliente_id = e2e_client.user["id"]
```

## Stack (mesma v1)

- **Tool**: `playwright>=1.40,<2` + `pytest-playwright>=0.5,<1`
- **Browser**: chromium-only (1 binary ~200MB vs 600MB+ com trio)
- **Marcador**: `@pytest.mark.e2e` registrado em pyproject.toml
- **Optional-deps**: `[project.optional-dependencies.e2e]` SEPARADO de
  `dev` para nao inflar CI unit.
- **Cleanup**: soft delete via DELETE /cliente/{id} (A19 compat).
  Preserva audit log imutavel (LGPD art. 37).
- **Auth**: X-API-Key 64 hex (gate admin) +
  `E2E_BASE_URL` env var (default localhost:8000, prod Tailscale).

## Cenarios cobertos (6 tests)

| # | Nome | Endpoints exercidos | LGPD gate | A19 |
|---|------|---------------------|-----------|-----|
| 1 | cliente agenda consulta | POST /protocolo + POST /agendamento + GET /agendamento/cliente/{id} + POST /confirmar | YES | - |
| 2 | comparecimento + emolumento | POST /atendimento + POST /concluir + GET /emolumento/calcular | - | - |
| 3 | documento/recibo + hash | POST /documento/upload + SHA256 verify | - | - |
| 4 | soft delete (A19) | DELETE /cliente + GET /cliente + GET /v2/clientes | - | YES |
| 5 | LGPD consent + revogacao | POST /lgpd/consent + POST /lgpd/revogar-consent + GET /lgpd/dashboard | YES | - |
| 6 | health via Playwright ctx | GET /health/live via `e2e_admin.context.request` | - | - |

Bonus: `tests/test_e2e_health.py` (3 tests, NAO marker e2e — roda em
CI unit para detectar drift de setup):
- `test_playwright_cli_via_subprocess`: SKIP+warning se Playwright
  ausente (NAO fail, NAO importorskip).
- `test_api_health_via_urllib`: SKIP+warning se API offline.
- `test_chromium_browser_cache_via_filesystem`: SKIP+warning se cache
  ausente.

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

### CI manual (v2 — workflow_dispatch only)

```bash
# Apos Gustavo GO para adicionar secrets (E2E_API_KEY_ADMIN etc):
gh workflow run e2e-nightly.yml \
  -f e2e_base_url=https://api.2notasudi.com.br \
  -f branch=master
```

## Decisoes de design v2

### Por que browser_context em fixtures e NAO httpx apenas?

v1 usava `api_session` (httpx) para todas chamadas — mais rapido mas
NAO usa Playwright de verdade. v2 adiciona `e2e_admin` / `e2e_client`
como browser_contexts Playwright (X-API-Key header injetado via
`extra_http_headers`):

1. **Drift detection real**: o fixture `e2e_admin` falha LOUD se
   Playwright NAO estiver instalado (vs httpx que funciona sem).
2. **F05.1 ready**: quando UI React existir, basta usar `e2e_page`
   (que ja existe em v1) sem reescrever fixtures.
3. **Demonstra pattern**: `test_e2e_admin_context_can_request_health`
   prova que `context.request` funciona para futuros tests.
4. **api_session preservado**: tests API-only continuam usando httpx
   (10x mais rapido, sem browser launch overhead).

### Por que 5 cenarios no briefing mas 6 tests na suite?

Briefing pediu 5 cenarios de negocio. v2 adiciona 1 test extra
(`test_e2e_admin_context_can_request_health`) que NAO e cenario de
negocio — apenas demonstra que o pattern Playwright context.request
funciona. E util como smoke para F05.1 (UI testing futuro).

### Por que `/documento/upload` no lugar de `/recibo` (Cenario 3)?

Briefing pediu "POST /recibo emite recibo com hash SHA256" — esse
endpoint NAO EXISTE no backend atual. Adaptacao: `POST /documento/upload`
faz exatamente isso (emite doc com SHA256, vinculado a protocolo_id).
Equivalente em termos de hash chain + integridade juridica.

Decisao documentada em docstring do cenario 3 + reportada no
deliverable.md.

### Por que smoke test SEM importorskip?

v1 usou `pytest.importorskip("playwright")` no smoke test. Verifier
rejeitou: importorskip AINDA exige Playwright instalado (apenas skipa
execucao, NAO a verificacao). Em CI unit, se Playwright NAO foi
instalado, importorskip ainda chama `importlib.import_module("playwright")`
que falha com ImportError → skip. Mas o spirit do briefing era:
"NAO falhar em CI unit se Playwright ausente". v2 usa subprocess.run
+ urllib stdlib puro — funciona mesmo com Playwright completamente
ausente (FileNotFoundError -> skip).

### Por que workflow SEM on.schedule?

v1 tinha `on.schedule: cron "0 3 * * *"` mesmo com INACTIVE — verifier
rejeitou (workflow deve ser draft/disabled OU manual-only). v2 remove
`on.schedule` completamente — apenas `workflow_dispatch`. Para ativar
schedule no futuro: adicionar `on.schedule` block + secrets no repo +
Gustavo GO.

## Pitfalls canonicos descobertos (v1 + v2)

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

4. **Smoke test fail vs skip** (v1) — `pytest.importorskip` ainda
   exige Playwright instalado para verificar. v2 usa subprocess.run
   puro + urllib stdlib — funciona mesmo com Playwright ausente.

5. **`addopts` filter** — `-m 'not e2e'` em addopts esconde E2E
   do collect. Para debug, rodar `pytest tests/e2e/ -m e2e --no-cov`
   explicitamente. CI unit nao coleta E2E — economiza ~2s startup.

6. **subprocess.run type narrowing (v2)** — `subprocess.run(cmd)`
   espera `str | bytes | PathLike` (NAO `str | None`). Pattern canon:
   ```python
   candidates: list[str] = []
   cli_path = shutil_which("playwright")
   if cli_path is not None:
       candidates.append(cli_path)
   ```
   Em vez de `[c for c in candidates if c]` que deixa None no list.

7. **BrowserContext dataclass wrapper (v2)** — Playwright NAO expoe
   "user state" alem de HTTP headers. Para associar cliente_id ao
   context, wrappear em dataclass:
   ```python
   @dataclass
   class E2EUserContext:
       context: BrowserContext
       user: dict[str, Any]
   ```
   Tests acessam via `e2e_client.user["id"]`.

## Compliance verificacoes

- [x] Ruff check + format clean (`ruff check .` + `ruff format --check .`)
- [x] mypy 0 errors em codigo NOVO (`mypy tests/e2e/ tests/test_e2e_health.py`)
- [x] pytest unit 1713+ tests continua passando (marker e2e excluido)
- [x] Toda mutacao via soft delete (LGPD art. 37 audit log preservado)
- [x] Suite E2E NAO roda em CI unit (addopts exclui marker `e2e`)
- [x] CI workflow MANUAL-ONLY (apenas workflow_dispatch, SEM on.schedule)
- [x] Smoke test SEM importorskip (subprocess.run + urllib stdlib)
- [x] Cada cenario e idempotente (cleanup via soft delete)
- [x] Nomenclatura canonica v2 (`e2e_client` + `e2e_admin`)

## Decisao FINAL: NAO rodar suite E2E em todo PR

Custo proibitivo:
- ~5min por run (chromium launch + 6 tests)
- ~$0.10/run em GH Actions (ubuntu runner)
- Free tier 2000min/mes — 1 run/dia ja eh 1500min/mes

**Recomendacao**: manter manual-only via workflow_dispatch ate Gustavo
GO explicito. Decidir depois entre nightly (custo ~150min/mes) vs
PR-mergeable (custo ~2500min/mes — esgotaria Free Tier).

## Follow-ups

- **F05.1** — UI E2E com React (quando frontend existir). Reusar
  `e2e_page` fixture + adicionar login flow + dashboard rendering.
- **F05.2** — Multiple browsers (firefox + webkit) — custo +400MB
  e +5min, decidir baseado em fragmentacao user base.
- **F05.3** — Visual regression testing (Playwright screenshot diff).
- **F05.4** — CI gate enforcement (fail PR se suite E2E quebrou).
- **F05.5** — Migrar smoke test de volta para pytest.importorskip SE
  Playwright passar a ser dev dep (decisao separada de Gustavo).

Modified by Gustavo Almeida