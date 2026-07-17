# G7.08.T1 — Alembic heads: single head + pending migrations report

**Task:** G7.08.T1  
**Agent:** cartorio-dev (A1)  
**Data verificação (repo local):** 2026-07-17  
**Status:** **DONE agent-side**

---

## Resultado executivo

| Check | Resultado |
|-------|-----------|
| Heads no graph de migrations | **1 head** (`0020`) |
| Multiple heads? | **Não** |
| Merge pending no repo? | **Não** (histórico linear a partir de `0015` → `0020`) |
| DB prod no head? | **HOLD** — não verificado nesta sessão (sem `alembic current` em DB live) |

---

## Head atual

| Campo | Valor |
|-------|--------|
| **Revision ID** | `0020` |
| **Arquivo** | `backend/alembic/versions/2026_07_09_0020-fix-fn-auto-audit-hash-hmac.py` |
| **Parent** | `0019` |
| **Resumo** | Fix `fn_auto_audit`: preencher `hash` + `hmac_signature` (NOT NULL) — P0 Telegram HITL / IntegrityError em `audit_log` |

Confirmação (stdout):

```text
0020 (head)
```

Contagem de linhas de `alembic heads` = **1** → single head.

---

## Cadeia (últimas 8 revisões, do head para trás)

Ordem: **mais recente → mais antiga**.

| # | Revision | Parent | Resumo |
|---|----------|--------|--------|
| 1 (head) | `0020` | `0019` | Fix `fn_auto_audit` hash + HMAC (pgcrypto) |
| 2 | `0019` | `0018` | A18 COMPLETE: `fn_set_updated_at` em 8 tabelas |
| 3 | `0018` | `0017` | A19 soft delete extended (`atendimentos`, `webhook_events`) |
| 4 | `0017` | `0016` | LGPD `reversivel_ate` + `audit_encerramento_id` em `clientes` |
| 5 | `0016` | `0015` | Colunas de notificação do cliente (telegram/whatsapp/etc.) |
| 6 | `0015` | `2026_06_25_0014` | A18+A19 TimestampMixin + soft delete estendido |
| 7 | `2026_06_25_0014` | `2026_06_25_0013` | pgcrypto encryption at-rest (D15) |
| 8 | `2026_06_25_0013` | `2026_06_25_0012` | create supabase applied tables (A1) |

**Nota histórica:** o grafo mais antigo tem merge points (`2026_06_24_0003`, `2026_06_25_0010`, `2026_06_25_0012`). Isso é esperado e **já resolvido** — o head único atual é `0020`. Multiple heads *no passado* ≠ multiple heads *agora*.

---

## Confirmação de single head

Comandos executados em `backend/`:

```bash
uv run alembic heads
# → 0020 (head)

uv run alembic history
# → cadeia linear 0019 -> 0020 (head), ...
```

Gate opcional (repo root, offline — não precisa de Postgres):

```bash
python scripts/check_alembic_single_head.py
# exit 0 = single head; exit 1 = multiple heads
```

---

## Como checar (runbook)

Da **raiz do repo**:

```bash
# Histórico verbose (Makefile → backend)
make -C backend alembic-history

# Heads (precisa cwd backend ou: make -C backend ...)
cd backend && uv run alembic heads

# Equivalent via uv a partir de backend/
uv run alembic heads -v
uv run alembic history --verbose
```

Aplicar / reverter (só com GO explícito em prod — Lesson 110):

```bash
make -C backend alembic-up      # alembic upgrade head
make -C backend alembic-down    # alembic downgrade -1
```

**Prod (dentro do container API, referência `alembic.ini`):**

```bash
docker exec -it cartorio_api alembic current
docker exec -it cartorio_api alembic heads
docker exec -it cartorio_api alembic upgrade head   # SOMENTE com autorização
```

---

## Risco de migrations não aplicadas em prod — **HOLD**

| Item | Estado |
|------|--------|
| Graph no repositório | Single head `0020` — **OK** |
| `alembic current` vs head no **DB de produção** | **HOLD** — não executado nesta task |
| Motivo do HOLD | `alembic current` exige DB + settings válidos; checagem live não faz parte do escopo agent-side sem credenciais/rede VPS |

**Ação recomendada (SRE / deploy window):**

1. No container/API prod: `alembic current` e comparar com `0020`.
2. Se `current < 0020`: planejar `upgrade head` com GO Gustavo (migrations `0018`/`0019`/`0020` tocam soft-delete, triggers `updated_at` e função de audit — impacto operacional).
3. Se `current == 0020`: sem pending no graph; fechar HOLD.
4. Se `current` em revision desconhecida / heads divergentes no DB: **não** forçar upgrade — investigar `alembic_version` e merge history.

Migrations recentes com risco se **não** aplicadas em prod:

- **`0020`**: sem ela, INSERT em `atendimentos` via trigger `fn_auto_audit` pode 500 (IntegrityError hash/HMAC) — P0 Telegram HITL.
- **`0019`**: sem triggers `updated_at`, timestamps stale em updates SQL puros.
- **`0018`**: colunas `deleted_at` em `webhook_events` (e model alignment).

---

## Inventário rápido de versions (repo)

Diretório: `backend/alembic/versions/`  
Total de arquivos de revision (aprox.): **25** (inclui merges históricos).  
Head lógico: **somente `0020`**.

---

## Status task

| Campo | Valor |
|-------|--------|
| **G7.08.T1** | **DONE** (agent-side) |
| Entregáveis | Este report + `scripts/check_alembic_single_head.py` |
| Commit | **Não** (pedido explícito da wave) |
| Prod DB apply | **HOLD** para check live |

Modified by Gustavo Almeida
