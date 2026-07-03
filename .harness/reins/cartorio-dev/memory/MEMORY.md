# Cartorio-Dev @ Cartorio — Memória Hot

> Camada HOT (sempre injetada). Princípios canon + estado vivo + workflow canon.
> Detalhes e exemplos: ver arquivos `memory/<topic>.md` (descrições auto-injetadas).

---

## Princípios Canon (ler primeiro)

### Trust-but-verify — briefings stale em 100% dos casos (regra)

Briefings de parent/peer sobre test failures, master HEAD, branch state ou "work ja feito" estão stale em ~100% (4/4 jun-2026). Padrões: test failure phantom, master HEAD 2-5 commits atras, cherry-pick "clean" ≠ identico, regressão lateral invisivel, ZCode auto-commitando WIP mid-session.

**Protocolo ANTES de planejar fix ou aceitar review**: `git fetch origin && git log origin/master -3 --oneline` → `pytest tests/<affected> --no-cov -q` → `git rev-parse HEAD + git status --short` → `git show <hash> --stat` em CADA commit no range. Se briefing diz "X failing" e pytest diz "X passing", reportar com output literal ANTES de agir.

Custo ~30s. Benefício: não queimar 60-90min em bug-fantasma. Output literal > narrativa própria.

Detalhamento + 4 cenários + protocolo review cego: `briefing-verification.md`.

---

### Working tree NAO confiável entre sessoes (sprint ativo = rule)

ZCode/Mavis pode auto-commitar OU auto-editar WIP uncommitted mid-session.
Sprint ativo + agent paralelo = COMMITS VÃO RACING.

- `git status --short` clean NAO significa "nada pra fazer" — significa "verifique se seu trabalho ja foi commitado"
- Sempre `git log --oneline -- <file>` apos `git status` para detectar
- Se commit alheio MAS conteúdo identico ao seu = outra sessão capturou WIP → `--allow-empty` como marker formal da autoria
- NUNCA amend commit alheio. Otimize pra evitar work duplication SEM dishonesty

Detalhamento: `cross-coord-debugging.md`.

---

### LGPD compliance — toda saida/mutação toca audit + scrub (by-design)

1. Toda saída para LLM passa por PII scrubber INTERNO (defense-in-depth) — `pii.scrub()` em cada `message.content` ANTES de payload. Docstring "caller DEVE scrubar" NAO basta.
2. Toda mutação grava audit log (action + resource + request_id + ip + user_agent).
3. Consent gate safe-by-default — `consent_granted: bool = False`. Bloqueia ANTES de httpx.
4. Retenção com `expires_at` + política de purga documentada.
5. Cobertura regex documentada — CNS/CNH/etc em backlog = gap regulatorio (art. 11 = P0 imediato).

**Compliance theater detection**: pytest verde + docstring "NAO escopo" + backlog deferido (D3) = trio classico. Verificar SEMPRE: `head -50 <test_docstring>` + `grep -E "CPF|CNPJ|RG|CNH|CNS|email|telefone" app/services/pii.py` + `grep -rn "D[0-9]" app/services/ tests/`.

Detalhamento: `lgpd-compliance-theater.md` + `llm-integration-pattern.md`.

---

## Estado Vivo (atualizar a cada sprint)

### cartorio reins NAO materializados (re-verificar periodicamente)

`mavis session list` retorna APENAS `agentName=mavis` ativo. `cartorio-lgpd`/`cartorio-n8n`/`cartorio-dev` sao APENAS conceituais em agent.md.

**Implicação**: cross-rein delegation via `mavis communication send --to <sessionId>` eh INVIAVEL pra esses reins. LGPD review tem que ser INLINE pelo Pietra root (checklist manual contra git diff).

**Workflow**: implementar → reportar com diff + pytest + coverage → Pietra aplica checklist LGPD → GO merge ou devolve com fixes. Re-verificar periodicamente com `mavis session list`.

---

### API key triplet drift (3 lugares devem ter MESMO valor)

Security-critical values (CARTORIO_API_KEY, AUDIT_HMAC_KEY) devem bater em:
1. `backend/.env` local (master reference)
2. `docker service` env (`docker service update --env-add`)
3. VPS `/etc/easypanel/projects/cartorio/api/code/.env`

Validacao pos-deploy: `docker exec $(docker ps -qf name=<svc>) printenv CARTORIO_API_KEY | head -c 8` deve retornar os 8 primeiros chars identicos nos 3 lugares.

---

## Workflow Canon (testado em sprints reais)

### Easypanel rebuild ENV RESET (P0)

`docker service update --env-add` NAO persiste Easypanel webhook rebuild. Fluxo: rebuild recria task definition (RESET env vars) → container sobe SEM --env-add → Settings(strict) EXPLODE no startup.

**Workaround imediato**: `docker service update --env-add KEY=VAL svc` apos rebuild.
**Workaround durável**: env vars no Easypanel project config via UI (persiste, NAO reset pelo webhook).

**Validacao pos-rebuild OBRIGATORIA**: (1) `docker service ps <svc>` todas "Running"; (2) `docker exec printenv <KEY> | head -c 8` bate com .env local; (3) `curl https://<host>/health/radar` → 200.

---

### Cross-rein handoff — pre-built review checklist

Apos delegar cross-rein, SEMPRE entregar pre-built review checklist pro proximo reviewer. Estrutura: itens LGPD/PII/security + itens tecnicos (credenciais, logging, headers, timezone) + gaps latentes identificados (NAO scope creep, flagados) + cross-check concreto por item.

Custo 5-10min (contexto fresco). ROI 30-60min economizado pelo proximo + zero gap missed.

---

### Deliverable.md verifier retry + engine auto-redispatch vs harness hold

**Verifier retry**: quando auto-reject N vezes → `mavis-trash deliverable.md` + rewrite addressing TODOS os issues com evidencia concreta. NAO tocar code/pyproject (escopo = doc-only quando B funciona). Estrutura verifier-friendly: Summary + Changed files + Notes (verifier-specific) + Status + Cross-ref.

**Engine vs harness**: engine re-dispatcha verifier mid-hold = conflito (verifier loop automatico vs harness human-driven). Resolucao: PICK LOWEST-RISK OPTION WITHIN PARENT'S ALLOWED CHOICES. Zero code change > code change (se B funciona). Push gate SEMPRE respeitado (gate Gustavo, NAO harness, NAO engine, NAO eu).

---

### pydantic Settings strict + conftest pitfall

Shell env `AUDIT_HMAC_KEY=""` + conftest `os.environ.setdefault(KEY, val)` = setup quebrado. `setdefault` NAO sobrescreve (key ja existe, mesmo que vazia). `Field(min_length=32)` rejeita string vazia → TODOS os testes crasham.

**Workaround test files**: `unset AUDIT_HMAC_KEY CARTORIO_API_KEY` + `export AUDIT_HMAC_KEY="a" * 64` + `export CARTORIO_API_KEY="a" * 64` + `DATABASE_URL=sqlite:///:memory:` + `CHATWOOT_ACCOUNT_ID=0 CHATWOOT_INBOX_ID=0`.

**Fix canon (conftest.py)**: trocar `os.environ.setdefault(KEY, val)` por `os.environ[KEY] = val` (force).

Pre-flight: `env | grep <VAR>` antes de pytest crítico em variaveis security.

---

### Tests multi-session cache stale — `db_session.expire_all()`

SQLite in-memory + StaticPool shared entre app session (TestClient via anyio portal) e fixture session. Apos `db.delete() + commit()` NA SESSÃO DO APP, fixture session tem objeto cached → `db.get()` retorna do cache sem re-query.

**Fix**: `db_session.expire_all()` antes de cross-session reads.

Sintoma canon: "test passou primeira vez mas falhou segunda" ou `deleted_at=None` quando esperava None. NAO se aplica a Postgres.

---

### alembic upgrade heads (plural) + Swarm container atomicity

`alembic upgrade head` (singular) falha com "Multiple head revisions" em migrations paralelas. Fix: `alembic upgrade heads` (plural) ou `<branchname>@head`.

**Swarm rotation mid-task**: cada `docker exec`/`docker cp` cria NOVA instancia se Swarm rotacionou. `/tmp/<dir>` NAO persiste → copia perdida. Sintoma: "No such file or directory" em comandos subsequentes.

**Workflow canon**: TUDO dentro de UM `docker exec` (mkdir + cp + alembic + verify), refresh TID a cada comando: `CTR=$(docker ps -q -f name=cartorio_api.1 | head -1)`. OU script SSH numa unica sessao atomica.

---

### Migration DESIGN-FAIL-SILENT (P0 compliance)

Migration docstring pode ser aspiracional mas codigo pode ser NO-OP
(try/except/pass). Compliance code = zero tolerancia pra silent fail.

**Pattern canon**:
1. SEMPRE ler arquivo .py da migration COMPLETO, NAO so docstring
2. try/except + pass (silent swallow) = DESIGN-FAIL-SILENT = gap latente
3. `op.execute()` DEPOIS do silent swallow = tbm falha
4. Cross-check stamp vs ground truth (psql) — stamped mas tables vazias = partial run ou stamping manual
5. NAO aceitar DESIGN-FAIL-SILENT em compliance/audit code
6. Se extension vive em outro DB (postgres vs cartorio) = DEVE documentar ONDE cron jobs vivem, NAO so onde deveriam viver

---

### Mypy strict claim vacuous sem [tool.mypy] + naming nit cross-check

**Mypy**: claim "strict 0 errors" sem `[tool.mypy]` em pyproject = vacuo.
Default NAO pega `no-untyped-def`, `redundant-cast`, `unused-ignore`, `type-arg`.
Fix: declarar "DEFAULT config" + limite. Pra strict real, adicionar
`[tool.mypy]` section com `strict = true`.

**Naming nit**: parent/peer flag issue como "investigar depois" → ANTES de aceitar como work item, do own quick local grep/Read pra desambiguar. Naming drift = fonte #1 de falso negativo em auditoria. Offer investigation WITH diagnostic query pre-built.

**Predicted hash**: briefing pode prever commit hash sequencial mas git gera diferente (master teve commits intermediarios durante standby). SEMPRE usar `git rev-parse HEAD` pos-commit e reportar hash REAL.

---

## A18 Pattern — PostgreSQL BEFORE UPDATE trigger idempotente (LGPD art. 37)

**Licao canonica** (de 2026-07-02, A18 SQUAD A):

Toda coluna `updated_at` em cartorio DB DEVE ter trigger BEFORE UPDATE
que setta `NEW.updated_at = NOW()`. ORM `onupdate=datetime.utcnow` nao
cobre updates via SQL puro (psql, n8n direto, batch jobs). Trigger eh
defesa em profundidade (LGPD art. 37 — rastreabilidade de alteracoes).

**Pattern canonico** (ver `A18-update-at-trigger.md`):

```sql
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Para cada tabela com updated_at:
DROP TRIGGER IF EXISTS trg_set_updated_at_<tabela> ON <tabela>;
CREATE TRIGGER trg_set_updated_at_<tabela>
BEFORE UPDATE ON <tabela>
FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
```

**Migration Alembic canonica**:
- Define `TABLES_WITH_UPDATED_AT` tuple derivado de `information_schema`
  (NAO de lista hardcoded — auditar primeiro, ver A18-audit.md).
- `upgrade()` faz CREATE OR REPLACE FUNCTION + loop CREATE TRIGGER.
- `downgrade()` faz loop DROP TRIGGER + DROP FUNCTION (IF EXISTS).
- Idempotente: DROP IF EXISTS antes de CREATE.

**Licoes aprendidas**:
1. **Audit primeiro, migrar depois** — query `information_schema.columns`
   no DB prod real pode divergir de listas hardcoded em migrations
   legadas. Migration `0009` listava `webhook_events` antes da `0015`
   adicionar a coluna → falharia silenciosamente.
2. **PG nao suporta `CREATE OR REPLACE TRIGGER`** — apenas function.
   Padrao canonico = DROP IF EXISTS + CREATE.
3. **Tests PG-only com skipif sqlite** — mesmos patterns de
   `test_pgcrypto_d15.py`. 4 cenarios comportamentais (UPDATE/INSERT
   com/sem trigger, idempotencia) sao impossiveis em SQLite.
4. **Chain collision com sibling agent** — quando 2+ agentes paralelos
   editam migrations no mesmo sprint, `revision="0018"` colide. Solucao:
   re-numerar minha migration para `0019` com `down_revision="0018"`.
   Validar com `importlib.util.spec_from_file_location` antes de
   commitar.
5. **Test de migration com `op.execute(f"...")` raw SQL NAO usa regex
   no file content** — table names sao Python f-string vars, NAO aparecem
   como texto literal. Pattern canonico: load migration as module via
   `importlib.util.spec_from_file_location()` + assert em module-level
   constants (`module.TABLES_WITH_UPDATED_AT`) + assert em
   `inspect.getsource(module.upgrade)` para substrings literais
   (`"DROP TRIGGER IF EXISTS"`, `"CREATE OR REPLACE FUNCTION"`, etc).

   ```python
   import importlib.util, inspect

   spec = importlib.util.spec_from_file_location(
       "m", Path(__file__).parent / "alembic/versions/<file>.py"
   )
   m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

   # Asser em module-level constants (tabelas, etc)
   assert len(m.TABLES_WITH_UPDATED_AT) == 8
   assert set(m.TABLES_WITH_UPDATED_AT) == {...}

   # Asser em substrings literais dentro do upgrade/downgrade
   up = inspect.getsource(m.upgrade)
   assert "DROP TRIGGER IF EXISTS" in up
   assert "CREATE TRIGGER" in up
   ```

   Pitfall canonico: regex `re.findall(r"DROP TRIGGER IF EXISTS\s+\w+", content)`
   retorna 0 matches porque o table name esta dentro do f-string var
   `{trigger_name}` — texto literal NAO tem o nome da tabela.

---

## Critical Compliance Pattern — audit_verify_diario gap (FASE 4.1)

**Gap LGPD real (não compliance theater)**:
- cartorio DB: pg_cron AUSENTE → migration 0005 eh no-op → `audit_verify_diario` NAO roda
- postgres DB: 5 jobs pre-existentes (`audit-chain-verify-6h 0 */6 * * *`) conecta em postgres DB; `fn_audit_chain_verify()` vive em cartorio.public → vai falhar com "function does not exist" se executar
- VPS: crontab vazio
- **Resultado**: ninguem chama `fn_audit_chain_verify()` no cartorio DB periodicamente

**Mitigação Opção B n8n workflow**:
- Endpoint ja existe: `POST /api/v1/audit/verify` (router.py 937-960) com X-API-Key guard
- n8n Schedule Trigger cron "0 6 * * *" (03:00 BRT daily) → HTTP Request → IF chain_ok=false → Telegram GRUPO PIETRA SQUAD
- Observabilidade nativa (n8n execution history = audit trail)
- Sem credentials novos (reusa X-API-Key)
- Operabilidade via UI (não SSH)

---

## Domain Topic Files (auto-injected descriptions)

- `briefing-verification.md` — protocolo briefing stale + 4 cenários
- `cross-coord-debugging.md` — Pydantic Settings singleton, master-only hook, working tree reset
- `lgpd-compliance-theater.md` — detectar compliance fake (pytest verde + backlog deferido)
- `llm-integration-pattern.md` — wrapper LLM LGPD-compliant (ChatError + scrub + audit + consent + rate limit)
- `A13-dead-mans-switch.md` — audit dead man's switch (3-level + scheduler)
- `A14-backup-db.md` — pg_basebackup 4x/dia + WAL + S3 placeholder
- `A15-connection-pool.md` — SQLAlchemy pool tuning (20/10/3600/30 + Prometheus)
- `A18-audit.md` — auditoria DB prod: 8 tabelas com `updated_at`, 0 triggers (pre-0019)
- `A18-update-at-trigger.md` — migration `0019` idempotente + 17 tests + LGPD art. 37
### F01 mutation testing mutmut v3 (2026-07-02)
Type: workflow-tooling

Setup mutmut v3.6.0 em cartorio backend (substitui v2 do briefing, flag mudou `paths_to_mutate` -> `source_paths`).

**Setup canon**:
- `backend/setup.cfg` section `[mutmut]` com `source_paths` (newline separated), `also_copy=app/,mcp_server.py,alembic.ini` (dependencies para mutants/), `pytest_add_cli_args=--cov-fail-under=0` (override do gate 90%).
- `backend/tests/test_mutation_gate.py` smoke (4 tests): setup cfg, version, gate parse, venv.
- `backend/mutants/mutation_status.json` consumido pelo gate test (skip se ausente).
- `.github/workflows/mutation-nightly.yml` cron 03:00 UTC (inativo por default — custo).

**Baseline 2026-07-02** (1494/2121 processados, score 61.4% killed):
- PASS (gate >=80%): crypto 89.1%, emolumento 93.3%, pii 95.8%, lgpd_anonimizacao 91.4%
- FAIL com excecao: lgpd_consent 66.8%, lgpd_direito_esquecimento 51.2%, lgpd_export 40.4%, lgpd_relatorio 54.6%, redlock 61.3%
- NOT RUN: audit.py (163 queued, timeout) — F01.1 follow-up

**Pitfalls canon**:
1. coverage 90% no pyproject trava mutmut (exit 1 antes de processar mutants) — sempre passar `--cov-fail-under=0`.
2. also_copy=app/ obrigatorio (mutmut cria mutants/ isolado, sem app/ resolve).
3. `app/services/lgpd/` package SEM `__init__.py` quebra mutmut (`Path.resolve(strict=True)`). Workaround: listar arquivos individuais (`app/services/lgpd_consent.py`).
4. `tests_dir=` deprecated em v3 — usar `pytest_add_cli_args_test_selection`.
5. Run baseline ~30min single-thread, ~10-15min com `--max-children 4` (Mac M-series).

Detalhes: `.harness/reins/cartorio-dev/memory/F01-mutation-testing.md`.

---

## A20 Pattern — Redlock distributed lock (Redis SET NX EX) (2026-07-02)

**Licao canonica**: alembic `env.py` NAO pode ser loaded como modulo em tests
(depende de `alembic.context.config` que so funciona em alembic CLI). Padrao
canon para validar integracao:

1. **Source-check via regex** (nao importa env.py como modulo)
   - `assert "from app.services.redlock import" in source`
   - `assert "ALEMBIC_LOCK_NAME = "alembic:migration"" in source`
   - `assert "sys.exit(EXIT_LOCK_BUSY)" in source`

2. **Testes de comportamento** do `redlock()` em isolamento (C1-C4 cobrem)
   + source-check da integracao (C5)

**Pattern canonico de lock** (ver `A20-redlock.md`):
```python
ALEMBIC_LOCK_NAME = "alembic:migration"  # LGPD-safe

def run_migrations_online():
    try:
        with redlock(ALEMBIC_LOCK_NAME, blocking=False, timeout=0):
            _run_migrations_online_locked()
    except LockBusyError as e:
        sys.stderr.write(f"[ALEMBIC] Lock ocupado: {e}\n")
        sys.exit(EXIT_LOCK_BUSY)  # 75 = EX_TEMPFAIL
```

**Decisoes**:
- `blocking=False` (fail-fast) → Docker/swarm restart policy retenta com backoff
- `EXIT_LOCK_BUSY = 75` (BSD sysexits.h EX_TEMPFAIL)
- Lock name canonico: `alembic:migration` / `seed:<name>` (NAO expoe PII)
- Lua script atomico no release: `if redis.call('get', K) == V then del K`
  (evita race condition onde lock expira entre check e delete)

**Coverage 92% em redlock.py** (ImportError branch inacessivel).

## Working tree reset mid-session (Lesson 022 — confirmado em A20 sprint)

**Padrao observado em 2026-07-02 A20**: working tree foi REVERTIDO entre
sessoes, perdendo 5 arquivos editados (redlock.py, alembic/env.py,
seed_vault_secrets.py, test_redlock_a20_v2.py, .env.example). Git reflog
mostrou 5x "reset: moving to HEAD" entre work sessions.

**Mitigacao canonica** (validada em A20):
1. **Checkpoint `--allow-empty`** ANTES de qualquer edicao:
   ```bash
   git commit --allow-empty -m "chore(a20): checkpoint before X — lesson 022 reset observed"
   ```
2. **Commits atomicos por arquivo** (nao batching):
   ```bash
   git add file1.py && git commit -m "feat: file1 only"
   git add file2.py && git commit -m "feat: file2 only"
   ```
3. **NAO** rodar comandos broad que disparam flush (`pytest tests/` na
   raiz, `git status` repetido) entre commits.

**Detectar**:
```bash
ls -la backend/app/services/redlock.py   # timestamp estagnado > 5min = lost
git status                               # "nothing to commit" + arquivos modificados = lost
git reflog | grep "reset"                # resets nao-initiated por mim
```

---

### F05 Playwright optional-deps + mypy TYPE_CHECKING (Lesson 188)

**Padrao canonico** (Playwright = optional-deps, NAO main deps):

```toml
# pyproject.toml
[project.optional-dependencies]
e2e = ["playwright>=1.40,<2", "pytest-playwright>=0.5,<1"]

[tool.pytest.ini_options]
addopts = "-m 'not smoke and not integration and not e2e'"  # exclui E2E do CI unit
markers = ["e2e: end-to-end tests via Playwright"]
```

```python
# conftest.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from playwright.sync_api import Browser as PlaywrightBrowser  # type: ignore[import-not-found]
    from playwright.sync_api import BrowserContext as PlaywrightBrowserContext  # type: ignore[import-not-found]
    from playwright.sync_api import Page as PlaywrightPage  # type: ignore[import-not-found]
```

**Pitfalls canonicos**:
1. `import playwright  # type: ignore[import-not-found]` em runtime.
2. Generator fixtures (`yield`) devem ter `Iterator[X]`, NAO `X`.
3. Conditional `return` antes de `yield` em fixture autouse confunde mypy —
   usar `# type: ignore[return-value]` no early return.
4. Smoke test em CI unit deve SKIP (nao FAIL) quando optional-dep ausente.
   `pytest.importorskip("playwright", reason="...")`.
5. `addopts` filter `-m 'not e2e'` esconde E2E do collect. Para debug:
   `pytest tests/e2e/ -m e2e --no-cov`.

**Decisao**: E2E NAO roda em CI unit (custo + flake). Apenas nightly
skeleton (INACTIVE ate Gustavo GO). Suite full-flow ~5min + 8 tests.

Detalhes + 5 cenaros + compliance check: `F05-e2e-playwright.md`.

---

### F05 v2 — Nomenclatura canonica + smoke sem importorskip + workflow manual-only (Lesson 220)

**v1 foi rejeitada pelo verifier attempt 1** com 3 feedbacks canonicos.
**v2 corrige TODOS os 3**:

1. **Nomenclatura**: v1 `e2e_cliente` (dict) + `e2e_api_key` (string) ->
   REJEITADO. v2 `e2e_client` + `e2e_admin` (browser_contexts Playwright
   autenticados via `extra_http_headers={"X-API-Key": ...}`). Wrapper
   dataclass `E2EUserContext(context, user)` para associar user data
   ao context (Playwright NAO expoe "user state" alem de HTTP headers).

2. **Smoke SEM importorskip**: v1 `pytest.importorskip("playwright")`
   ainda exigia Playwright instalado -> REJEITADO. v2 `subprocess.run(
   ["playwright", "--version"])` puro (stdlib only) + `urllib.request.
   urlopen()` health check. Funciona mesmo com Playwright completamente
   ausente (FileNotFoundError -> skip com warning).

3. **Workflow MANUAL-ONLY**: v1 `on.schedule: cron "0 3 * * *"` mesmo
   INACTIVE -> REJEITADO. v2 APENAS `on: workflow_dispatch` (SEM
   on.schedule). Para ativar nightly no futuro: adicionar block schedule
   + secrets no repo + Gustavo GO.

**Pattern canon v2** (browser_contexts Playwright):
```python
@dataclass
class E2EUserContext:
    context: BrowserContext
    user: dict[str, Any]  # {"role", "api_key", ...cliente_data}


@pytest.fixture
def e2e_admin(browser: Browser, e2e_base_url: str) -> Iterator[E2EUserContext]:
    ctx = browser.new_context(
        base_url=e2e_base_url,
        extra_http_headers={"X-API-Key": _e2e_api_key_admin()},
    )
    try:
        yield E2EUserContext(context=ctx, user={"role": "admin", ...})
    finally:
        ctx.close()
```

**Pitfall canonico v2** (subprocess.run type narrowing):
```python
# ERRADO — mypy strict falha (List item 0 has incompatible type "str | None")
candidates = [shutil.which("playwright"), str(Path(".venv") / "bin" / "playwright")]
candidates = [c for c in candidates if c]

# CERTO — type narrowing explicito
candidates: list[str] = []
cli_path = shutil_which("playwright")
if cli_path is not None:
    candidates.append(cli_path)
candidates.append(str(Path(".venv") / "bin" / "playwright"))
```

**Decisao**: E2E v2 MANUAL-ONLY ate Gustavo GO. Suite 6 tests (~5min
chromium single-browser). Cenarios 1-5 (briefing) + 1 helper
(test_e2e_admin_context_can_request_health).

Detalhes completos: `F05-e2e-playwright.md` (atualizado v2).
