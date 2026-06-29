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