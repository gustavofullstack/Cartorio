# G7.20.T1 — Auditoria de dead code (follow-ups ADR-027)

**Data:** 2026-07-17  
**Autor:** cartorio-dev (Wave 25 slot A3)  
**Escopo:** `backend/app/` — inventário conservador de funções/módulos sem referência  
**Vínculo:** [ADR-027](adr/ADR-027-codebase-analysis-solid-dry-kiss.md) (SOLID/DRY/KISS)  
**Política:** preferir **reportar** a deletar. Delete só com **zero refs** comprovadas (AST + grep textual + testes). Máx. 1–2 deletes seguros nesta wave.

---

## 1. Método

1. **AST walk** em `backend/app/**/*.py` — 827 defs (`def`/`async def`).
2. Contagem de **Name/Attribute loads** + **ocorrências textuais** (`rg`) em `app/`, `tests/`, `scripts/`, `alembic/`.
3. Filtro de **falsos positivos**:
   - Handlers FastAPI (`@router.get/...`) — nunca chamados por nome.
   - Validadores Pydantic (`@field_validator`) — registrados via decorator.
   - Métodos/patches referenciados só em testes por string path.
4. Cruzamento com follow-ups ADR-027 (god-files, helpers extraídos, DRY audit).

**Ferramentas:** `rg`, script AST local (sem vulture/dead para evitar mass-delete).

---

## 2. Contexto ADR-027 (já feito vs follow-up)

| Item ADR-027 | Status em 2026-07-17 |
|---|---|
| T073/T074 — `_helpers.py` (`serialize_orm_with_pii_mask`, `list_with_pagination`) | **Vivo** — import em `router.py` + suite `tests/test_helpers_unit.py` |
| T075/T076 — `audit_helper.log_mutation` | **Vivo** — `lgpd_consent`, `lgpd_direito_esquecimento` + unit tests |
| HOLD: `telegram.py`, `cartorio_agent.py`, `webhook_evolution`, `pii.py`, `audit*` | Mantido — **não** refactor nesta task |
| Delete de código | ADR-027: zero deletes. Esta task: **2 deletes seguros** (abaixo) |

### Top arquivos por LOC (atual)

| LOC | Path | Nota ADR-027 |
|---:|---|---|
| 5383 | `app/api/v1/router.py` | God-route; helpers parciais |
| 2315 | `app/api/v1/telegram.py` | HOLD (webhook crítico) |
| 1379 | `app/services/cartorio_agent.py` | HOLD (LLM agent) |
| 1097 | `app/api/v1/integrations.py` | Integrações externas |
| 911 | `app/services/chat_pipeline.py` | Debounce / multi-canal |

---

## 3. Dead code **deletado** nesta wave (2 itens, 100% unused)

| # | Símbolo | Arquivo | Prova | Risco |
|---|---|---|---|---|
| 1 | `_interval_sql(days)` | `app/api/v1/lgpd_dpo_dashboard.py` | Zero refs; supersedido por `_interval_days_sqlite` / `_interval_days_postgres` via `_now_minus_days_expr` | Baixo |
| 2 | `_menu_kb()` | `app/services/cartorio_agent.py` | Zero refs; docstring DEPRECATED 2026-07-12; retornava `[]`. `_servicos_kb()` **permanece** (ainda referenciado ~L1093) | Baixo |

**Não commitado** (pedido da wave). Diff local apenas.

---

## 4. Candidatos fortes — **report only** (não deletar ainda)

### 4.1 Helpers com zero call-site de produção

| Símbolo | Arquivo | Evidência | Por que NÃO deletar agora |
|---|---|---|---|
| `_db_check` / `_redis_check` (nested) | `app/api/v1/router.py` ~L1745–1755 (health_radar) | Definidos e **nunca chamados**; DB/Redis checks estão **inline** no mesmo handler | God-file de alto tráfego; limpar em PR dedicado + smoke `/health/radar` |
| `_FakeResp` | `app/api/v1/router.py` ~L1842 | Só usado pelos nested mortos acima | Deletar **junto** com `_db_check`/`_redis_check` (cluster) |
| `_clear_queue` | `app/api/v1/telegram.py` ~L468 | Def only; zero callers | Caminho Telegram HOLD; possível reintrodução de debounce queue |
| `_send_extra_messages` | `app/api/v1/telegram.py` ~L1303 | Def only; zero callers | Ligado a `AgentReply.extra_messages` — pode ser wiring incompleto, não lixo |
| `_last_bot_from_history` | `app/services/cartorio_agent.py` ~L883 | Def only; zero callers | Comentários em `_offline_reply` sugerem uso anti-loop planejado |
| `_call_fast_llm` | `app/api/v1/telegram.py` ~L1594 | **Sem caller de prod**; só patch string em `tests/test_telegram_debounce_regression.py` | Remover exige ajustar teste de regressão |

### 4.2 Módulo órfão (scaffold, não lixo cego)

| Módulo | Refs em `app/` | Notas |
|---|---|---|
| `app/services/materialized_views.py` | **Nenhuma** import | DDL G6.A.T12 (`VIEWS_DDL`, `INDEXES_DDL`, `render_*_sql`). Cron referenciado no docstring (`jobs/cron_refresh_views.py`) **não existe**. Manter como spec SQL até job/migração; **não** apagar sem decisão de produto DPO |

### 4.3 “UNIMPORTED-FROM-APP” que **não** são dead

Muitos services só são puxados por routers/main/tests. Exemplos vivos via outro path:

| Módulo | Consumidor real |
|---|---|
| `dist_lock` | `tests/test_dist_lock.py` (+ potencial runtime futuro) |
| `redlock` | `main.py`, `alembic/env.py`, `router.py`, scripts |
| `idempotency_store_fake` | só testes (proposital) |
| `chatwoot_canned_responses_v3/v4` | testes + chain v4→v3→v2 |
| `log_masker`, `crypto`, `brain_*` | main/API/jobs conforme wiring |

**Regra:** ausência de import em outro service ≠ morto se router/test/script importa.

---

## 5. Falsos positivos (NÃO listar como dead)

| Padrão | Exemplo | Motivo |
|---|---|---|
| `@field_validator` | `_strip_cpf`, `_strip_tipo`, `_hitl_deve_ser_true` em `schemas/protocolo.py` | Pydantic registra por decorator |
| Endpoints FastAPI | `login`, `list_tasks`, `direito_acesso_v2`, … | Wire via `APIRouter` |
| Private helpers com call local | `_send_typing`, `_get_queued_messages`, `_sender_to_remote_jid` | Refs no mesmo arquivo (AST Attribute/Name) |

---

## 6. Follow-ups recomendados (próximas waves)

| Prioridade | Ação | Critério de aceite |
|---|---|---|
| P2 | Remover cluster `_db_check`/`_redis_check`/`_FakeResp` em `health_radar` | Smoke radar verde; 0 refs |
| P2 | Decidir destino de `_send_extra_messages` + `extra_messages` do agent | Wire completo **ou** delete + teste |
| P3 | Conectar `materialized_views.py` a job/Alembic **ou** marcar `deprecated` no módulo | DPO dashboard latency |
| P3 | Avaliar `_call_fast_llm` vs patch de teste | Sem dead code “fantasma” só para mock |
| P1 (ADR-027 HOLD) | **Não** fatiar `telegram.py` / `cartorio_agent` sem E2E + multi-rein | AGENTS.md + guia Telegram |

---

## 7. O que **não** fazer

- Mass-delete com vulture/autoflake sem review humano.
- Apagar validators Pydantic / rotas FastAPI por “zero call”.
- Tocar `audit*`, `pii*`, cadeia LGPD rights (P0).
- Refactor god-files nesta task (fora de escopo).

---

## 8. Resumo executivo

| Métrica | Valor |
|---|---|
| Defs escaneadas | 827 |
| Candidatos fortes (helpers) | 8 + 1 módulo scaffold |
| Deletes aplicados | **2** (`_interval_sql`, `_menu_kb`) |
| Mass refactor | **0** |
| Commit | **não** (pedido da wave) |

**Conclusão:** codebase relativamente limpa de dead code “óbvio”; o grosso do bulk ADR-027 continua sendo **complexidade viva** (god-files HOLD), não funções órfãs. Follow-ups de delete restantes são micro e isoláveis.

---

Modified by Gustavo Almeida  
cartorio-dev · G7.20.T1 · Wave 25
