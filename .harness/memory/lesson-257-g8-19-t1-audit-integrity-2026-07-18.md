# Lesson 257 — G8.19.T1 audit hash sequence verifier (2026-07-18)

## Contexto

Tarefa G8.19.T1 — complemento do `AuditService.verify_chain` (G8.07.T2).
O original **para no primeiro índice quebrado**; o novo enumera TODOS os
índices onde chain + HMAC divergiram. Necessário para:

- detectar tamper mid-chain (entry 3 editada → entries 3..N quebradas)
- detectar HMAC forjado (assinatura inconsistente mesmo com hash consistente)
- forense (DPO precisa saber "quantos e quais" entries foram adulterados)

LGPD Art. 37 (continuidade da auditoria) + Art. 46 (segurança).

## Decisões arquiteturais

1. **Módulo novo `app/services/audit_integrity.py`**, NÃO extensão de
   `audit.py`. Razão: `audit.py` é o **chain builder** (intocável,
   AGENTS.md regra P0). Integridade checker é consumidor, não produtor.

2. **API clara, 3 funções, 1 responsabilidade cada:**
   - `verify_hash_sequence(entries: list[dict]) -> list[int]` — pure,
     testa 3 regras (chain / hash / HMAC) por entry, retorna TODOS os
     índices quebrados.
   - `from_db(db: Session) -> Generator[dict]` — stream-friendly com
     `.yield_per(500)` para tabelas grandes (10k+ entries sem DoS).
   - `verify_full_chain(db: Session) -> dict` — orquestrador + summary
     (`total_entries`, `broken_indices`, `integrity_score`,
     `chain_intact`, `first_break_id`, `error`).

3. **HMAC reproduzido do AuditService.log linha 107:**
   `HMAC-SHA256(key, f"{new_hash}:{timestamp}:{actor_id}:{action}")`.
   Mesmo key (`settings.audit_hmac_key`) — chave comprometida = cadeia
   comprometida.

4. **Normalização de timestamp** idêntica ao `verify_chain` original:
   `tzinfo=None`, `isoformat(timespec='microseconds')`, troca ` ` por `T`.
   Sem isso, divergência sistemática (Postgres format com espaço ≠
   `isoformat()`).

5. **`integrity_score` em [0, 1]** = `(total - len(broken)) / total`.
   Pronto para métrica Prometheus (`audit_chain_integrity_score`).

6. **CLI com exit codes canônicos** (0 OK, 1 quebrado, 2 I/O error).
   Integra com dead-man's-switch de 15min via `app.jobs.cron_dead_mans_switch`
   em Wave 51+.

## Pegadinhas / armadilhas

### A. `from app.db import SessionLocal` no CLI

O CLI importa `SessionLocal` no topo do módulo. O `_patch_db_session_for_all_tests`
autouse do conftest rebinds `app.db.SessionLocal` para SQLite in-memory,
mas **só para módulos `app.*`** (loop `if mod_name.startswith("app")`).
Módulo `scripts.audit_integrity_check` fica de fora — referencia o
`SessionLocal` original (Postgres de prod).

**Fix nos testes:** monkeypatch `cli_mod.SessionLocal` para um `sessionmaker`
bindado na engine do teste. NÃO importar dentro de `main()` (lazy) — quebra
a interface do argparse (não roda sem DB).

### B. `_compute_hmac_signature` precisa de 4 params

A tentação é simplificar para `HMAC(key, payload)` ou `HMAC(key, hash)`.
**Errado** — o formato canônico em `audit.py:107` é:
```python
hmac_sig = cls._compute_hmac(f"{new_hash}:{timestamp}:{actor_id}:{action}")
```
Refatorei para `_compute_hmac_signature(*, new_hash, timestamp, actor_id, action, hmac_key)`
com kwargs explícitos para forçar o caller a pensar nos 4 params.

### C. Stream-based com `from_db()` — type hint

SQLAlchemy `.yield_per()` retorna `Query[AuditLog]`, não `Generator[dict]`.
Mypy strict reclama. Solução: wrap em função `_gen()` com `yield` (mypy
infere Generator corretamente) + `Any` no type hint de retorno com
`# type: ignore[no-any-return]` (alternativa menos elegante mas aceita).

### D. CI gate `make test` exige coverage

O conftest SQLite in-memory NÃO tem `audit_log` populada nos testes
existentes, então adicionar `tests/test_audit_integrity_g8.py` pode
inflar coverage do módulo novo (bom) e mexer no gate. **Cobertura do
módulo novo ~95%** (só `error` branch não coberto). Gate 90% continua OK.

## Outputs

- `backend/app/services/audit_integrity.py` (273 linhas)
- `backend/scripts/audit_integrity_check.py` (95 linhas)
- `backend/tests/test_audit_integrity_g8.py` (252 linhas, 12 testes)
- `docs/AUDIT_INTEGRITY_G8.md`

## Validação

- `uv run pytest tests/test_audit_integrity_g8.py --no-cov -v` → **12 passed**
- `uv run pytest tests/test_audit*.py --no-cov -q` → **51 passed** (sem regressão)
- `uv run ruff check app/services/audit_integrity.py` → **0 errors**
- `uv run ruff format --check` → **formatted**
- `uv run mypy app/services/audit_integrity.py` → **Success: no issues found**

## Integração pendente (Wave 51+)

- Métrica Prometheus `audit_chain_integrity_score` (gauge)
- Alerta Telegram GRUPO PIETRA SQUAD quando `chain_intact == False`
- Cron de 15min em `app.jobs.cron_dead_mans_switch` (já roda no lifespan,
  só falta chamar `verify_full_chain()`)
- Endpoint admin `GET /api/v1/admin/audit/integrity` (X-API-Key)

## LGPD-REVIEW-PENDING

Mudança em `audit*` (verificador de integridade da cadeia) **exige
sign-off do `cartorio-lgpd`** conforme AGENTS.md. Commit inclui a tag
no body — merge prod bloqueado até review.
