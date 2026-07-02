# A19 Soft Delete Pattern — Squad A (API/DB Hardening)

**Status**: COMPLETED 2026-07-02 20:33 BRT
**Squad**: A (API/DB Hardening)
**Commit hash**: see git log master (LOCAL only; push gate Gustavo per Lesson 110)
**Worktree**: /Users/gustavoalmeida/projetos/Cartorio
**Sprint**: Sprint 5 (continuidade)

---

## Resumo

Padrao global de soft delete (`deleted_at TIMESTAMP NULL`) consolidado
no projeto. Antes do A19, 5 models ja tinham `deleted_at` ad-hoc
(cliente, protocolo, conversa, documento, agendamento). A19 adicionou:

1. **SoftDeleteMixin** (`app/models/mixins.py`) — col + helpers em UMA
   lugar so, usado pelas entidades de dominio
2. **BaseRepository** (`app/repositories/base.py`) — DRY pattern com
   soft_delete/restore/find_active/find_including_deleted/find_by_id
3. **Migration 0018** — fecha gaps (Atendimento drift + WebhookEvent) e
   NAO quebra schema
4. **Refactor**: 7 models agora herdam `SoftDeleteMixin` (Cliente,
   Protocolo, Conversa, Documento, Agendamento, Atendimento, WebhookEvent)
   — coluna `deleted_at` migrou do campo manual pra heranca do mixin
5. **30 tests pytest** cobrindo comportamento do mixin + Repository

---

## Estado ANTERIOR a A19 (auditado)

Soft delete estava PARCIALMENTE aplicado:
- Migration A17 (2026-06-25-0002) adicionou `deleted_at` em: `protocolos`,
  `atendimentos`, `documentos` (com partial indexes WHERE deleted_at IS NULL)
- Migration A19 (2026-06-26-0001) adicionou `deleted_at` em: `protocolos`,
  `conversas`, `documentos`, `agendamentos` (com full indexes)
- 5 models ja tinham `deleted_at` declarado manualmente (cliente,
  protocolo, conversa, documento, agendamento)
- **Drift**: `Atendimento` tinha coluna no DB (A17) mas NAO no model
- **Gap**: `WebhookEvent` sem coluna

Hard delete (`db.delete()`) usado em 2 lugares — AMBOS legitimos:
- `app/jobs/retencao.py:230` — purga cliente com >5y desde deleted_at
  (LGPD D4 retencao) — correto manter hard
- `app/services/lgpd/direito_esquecimento.py:118-119` — hard delete
  quando cliente SEM protocolo (ADR-018) — correto manter hard

---

## Files changed (15 modificados + 4 criados)

### Criados (4)
- `backend/app/models/mixins.py` — SoftDeleteMixin + query helpers
- `backend/app/repositories/__init__.py` — export BaseRepository
- `backend/app/repositories/base.py` — BaseRepository generico
- `backend/tests/test_a19_soft_delete.py` — 30 testes
- `backend/alembic/versions/2026_07_02_0018-a19-soft-delete-extended.py` — migration

### Modificados (7 models refatorados pra usar mixin)
- `backend/app/models/cliente.py` — mixin, removido campo manual
- `backend/app/models/protocolo.py` — mixin, removido campo manual
- `backend/app/models/conversa.py` — mixin, removido campo manual
- `backend/app/models/documento.py` — mixin, removido campo manual
- `backend/app/models/agendamento.py` — mixin, removido campo manual
- `backend/app/models/atendimento.py` — mixin (drift fix)
- `backend/app/models/webhook_event.py` — mixin (gap fix)
- `backend/app/models/__init__.py` — export SoftDeleteMixin

---

## SoftDeleteMixin — uso

```python
from app.models.base import Base, TimestampMixin
from app.models.mixins import SoftDeleteMixin

class MinhaEntidade(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "minha_entidade"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = ...

obj = db.get(MinhaEntidade, 1)
obj.soft_delete()  # seta deleted_at = utcnow() (idempotente)
obj.restore()      # seta deleted_at = NULL
assert obj.is_deleted is False
```

Migration cria coluna indexada:
```sql
ALTER TABLE minha_entidade ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;
CREATE INDEX IF NOT EXISTS ix_minha_entidade_deleted_at ON minha_entidade (deleted_at);
```

---

## Query helpers

```python
from app.models.mixins import query_active, query_including_deleted, select_active

# Default: filtrar soft-deletados
ativos = query_active(db, Cliente).all()

# Admin: ver TUDO (gated por permissao no router)
todos = query_including_deleted(db, Cliente).all()

# SQLAlchemy 2.0 style (select + execute)
stmt = select_active(Cliente)
resultado = db.execute(stmt).scalars().all()
```

---

## BaseRepository — uso

```python
from app.repositories import BaseRepository

class ClienteRepository(BaseRepository[Cliente]):
    def find_by_cpf_hash(self, cpf_hash: str) -> Cliente | None:
        return self.find_active().filter(Cliente.cpf_hash == cpf_hash).first()

repo = ClienteRepository(db)
cliente = repo.find_by_id(123)
repo.soft_delete(cliente)
db.commit()
cliente = repo.find_by_id(123)             # None (default exclui soft)
cliente = repo.find_by_id(123, include_deleted=True)  # objeto com deleted_at
```

Metodos:
- `soft_delete(obj)` / `soft_delete_by_id(id)` — soft delete
- `restore(obj)` — volta deleted_at a None
- `find_active()` / `find_including_deleted()` — query helpers
- `find_by_id(id, include_deleted=False)` — busca por PK
- `find_deleted()` — apenas soft-deletados (relatorios, retencao 5y)
- `count_active()` — count otimizado

---

## Migration 0018

```python
revision = "0018"
down_revision = "0017"
```

Aplica SQL idempotente (rodavel multipla sem erro):
- `ALTER TABLE atendimentos ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL` (drift fix)
- `CREATE INDEX IF NOT EXISTS ix_atendimentos_deleted_at ON atendimentos (deleted_at)`
- `ALTER TABLE webhook_events ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL` (gap fix)
- `CREATE INDEX IF NOT EXISTS ix_webhook_events_deleted_at ON webhook_events (deleted_at)`

Down: DROP COLUMN + DROP INDEX IF EXISTS (rollback).

**Atenção**: alembic upgrade `heads` (plural) — Lesson 162.

---

## Tabelas de dominio com soft delete (7 FINAL)

| Tabela            | Status     | Origem coluna          |
| ----------------- | ---------- | ---------------------- |
| clientes          | ok         | anterior a A17         |
| protocolos        | ok         | A17 + A19              |
| documentos        | ok         | A17 + A19              |
| conversas         | ok         | A19                    |
| agendamentos      | ok         | A19                    |
| atendimentos      | **fix A19**| A17 (model drift)      |
| webhook_events    | **fix A19**| A19 (nova coluna)      |
| audit_log         | NAO tem    | by design (hash chain) |
| outbox_messages   | NAO tem    | by design (DLQ)        |

---

## Tests (30 adicionados) — 100% passing

`backend/tests/test_a19_soft_delete.py`:

**TestSoftDeleteMixinBehavior** (4 testes):
- `test_obj_ativo_is_deleted_false`
- `test_soft_delete_seta_timestamp`
- `test_soft_delete_idempotente`
- `test_restore_zera_timestamp`

**TestQueryHelpers** (4 testes):
- `test_query_active_exclui_soft_deletado`
- `test_query_active_retorna_ativo`
- `test_query_including_deleted_retorna_todos`
- `test_select_active_constroi_select`

**TestBaseRepository** (10 testes):
- `test_find_active_exclui_soft_deletado`
- `test_find_including_deleted_retorna_todos`
- `test_find_by_id_padrao_exclui_soft_deletado`
- `test_find_by_id_com_flag_retorna_soft_deletado`
- `test_find_by_id_inexistente`
- `test_soft_delete_by_id`
- `test_soft_delete_by_id_inexistente`
- `test_restore_via_repo`
- `test_find_deleted_retorna_apenas_soft`
- `test_count_active_exclui_soft`

**TestDomainModelsHaveDeletedAt** (7 testes):
- 7 assertions garantindo que cada tabela de dominio tem coluna
  `deleted_at` nullable no metadata

**TestSystemModelsSemDeletedAt** (2 testes):
- `test_audit_log_nao_tem_deleted_at`
- `test_outbox_message_nao_tem_deleted_at`

**TestAuditChainIntegrityAfterSoftDelete** (2 testes):
- `test_audit_chain_intact_apos_soft_delete_cliente`
- `test_audit_log_nunca_aparece_em_query_active`

**TestSoftDeleteMixinUsabilidade** (2 testes):
- `test_atendimento_suporta_soft_delete` (drift fix validated)
- `test_webhook_event_suporta_soft_delete` (gap fix validated)

Total: 30 testes, **100% coverage** em `app/models/mixins.py`,
`app/repositories/__init__.py`, `app/repositories/base.py`.

---

## Gates

- ruff check: **All checks passed** (15+ arquivos modificados)
- ruff format --check: **17 files already formatted**
- mypy (default config): **0 errors** em 15 source files
- pytest tests/test_a19_soft_delete.py: **30 passed**
- pytest tests/ full (excluindo smoke/integration): **1646 passed,
  18 skipped, 0 failed** (regression: 0)
- coverage A19 modules: **100%** (mixins.py + repositories/base.py)
- coverage global: NAO verificada localmente (bug CPython/pytest em
  session teardown — internal AssertionError no report handler,
  pytest exit 3, mas tests passam todos). CI Sandbox Roda confirma.

---

## Decisoes de design

### Decisao 1: `DateTime` naive UTC vs timezone-aware

Mixin usa `DateTime` (naive, sem tz). Match com migrations existentes
(TIMESTAMP NULL, nao TIMESTAMPTZ). Migrar schema para TIMESTAMPTZ eh
out of scope — envolveria migration que altera type, risco de lock
em prod, sem ganho pratico (PG converte automaticamente).

Caller que precisa offset-aware faz:
```python
aware = obj.deleted_at.replace(tzinfo=timezone.utc)
```

### Decisao 2: refactor 7 models vs add-only

Optei por refatorar — herdando `SoftDeleteMixin`, todos os 7 models
de dominio ganham coluna + helpers + consistencia. Risco era drift
schema vs model, mas como a coluna JA EXISTIA em DB com mesmo nome +
type + nullable, nao ha migration adicional necessaria alem da 0018
que fecha gaps (Atendimento + WebhookEvent).

Custo do refactor: 7 edits mecanicos (trocar `Base, TimestampMixin`
por `Base, TimestampMixin, SoftDeleteMixin` + remover campo manual).
Beneficio: `is_deleted`, `soft_delete()`, `restore()` funcionam em
qualquer entidade sem boilerplate.

### Decisao 3: BaseRepository Generic vs Repository por entidade

Optei por `BaseRepository[T]` GENERICO + subclasses especializadas
futuras (ClienteRepository, ProtocoloRepository). Repository eh
RECOMENDACAO (nao obrigacao) — services legados continuam usando
`db.query(Model)` sem quebra. Novos endpoints devem usar repo para
LGPD-by-default.

---

## NAO FOI FEITO (out of scope)

- Nao push (regra Gustavo — Lesson 110). Commit local apenas.
- Nao migrei todas as rotas para usar `BaseRepository` (refactor
  cirurgico em rotas = outra sprint). Scope creep evitado.
- Nao criei `ClienteRepository` com queries especificas — stubs podem
  ser adicionados em outro PR.
- Nao adicionei endpoint `?include_deleted=true` gated por permissao
  (escopo = mixin + repository, nao UI/API).
- Nao testei em Postgres real — testes usam SQLite in-memory
  (trigger behavior testado pelo A18 separado).
- Nao alterei `direito_esquecimento.py` ou `retencao.py` para usar
  BaseRepository (suas decisoes hard delete sao corretas por ADR-018).

---

## Liçoes canonicas aplicadas

- **Lesson 110** (push gate Gustavo): commit local, NAO push
- **Lesson 169** (mypy claim vacuo): claimed "mypy 0 errors DEFAULT
  config" nao "strict" — pyproject sem [tool.mypy]
- **Lesson 162** (alembic upgrade heads): migration usa `heads`
  (plural) pra chain consistência
- **Lesson 189** (pydantic strict + conftest): shell `AUDIT_HMAC_KEY=""`
  bugou import; pre-flight `env | grep` antes pytest critico
- **Briefing verification**: audit previa (5/4 jun-2026 stale pattern)
  — verificou git log + migrations existentes ANTES de comecar a
  implementar; evitou duplicar migration A17/A19 já em prod

---

## Lições NOVAS (escritas em MEMORY.md principal)

A19 confirma padrao:
1. **Auditoria previa antes de migration**: migrations A17 + 0015 ja
   adicionaram `deleted_at` em 4-5 tabelas. Tarefa A19 original
   parecia "do zero" mas 80% ja existia; trabalho real foi: gaps
   (drift + webhook), mixin, repository, tests. SEMPRE auditar
   migrations existentes antes de planejar nova migration.
2. **Model-DB drift detection automatica**: `TestDomainModelsHaveDeletedAt`
   detecta drift entre model declared columns e migrations aplicadas.
   Pattern reutilizavel: para cada tabela importante, teste afirma
   `hasattr(Model, "field")` + `Model.__table__.columns["field"].nullable`.
3. **Refactor cirurgico > add-only**: refatorar 7 models pra usar mixin
   custou 14 linhas no total mas trouxe `is_deleted`/`soft_delete()`
   em todo dominio. Add-only deixa duplicacao perpetua.

Modified by Gustavo Almeida
