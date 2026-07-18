# Lesson 258 — G8.19.T2 HMAC Key Rotation Router (2026-07-18)

## Contexto

Tarefa G8.19.T2 — criar roteador de chaves HMAC para permitir
rotação do `AUDIT_HMAC_KEY` sem invalidar entries antigos do audit
log. LGPD Art. 37 (rastreabilidade), Art. 46 (segurança — NIST SP
800-57 recomenda rotação periódica), Art. 50 (governança).

Wave 50, Squad 19 (Cryptography). Master ahead 38 commits. Tarefa
pega no fluxo crítico de HITL/A13 com T025 do v22 já marcando o
problema como hipótese a ser tratada.

## Decisões arquiteturais

1. **Registry singleton thread-safe em memória.** `HmacKeyRouter`
   mantem `dict[kid] → {secret, status, created_at, rotated_at}` +
   `_active_kid`. `threading.RLock` interno protege todas as
   mutações. Singleton via `_ROUTER` + helper `get_router()`.

2. **Estados: active | rotating | deprecated.** Apenas uma `active`
   por vez; rotação automaticamente promove a antiga para `rotating`
   com `rotated_at=now`. Cleanup após grace (default 30 dias)
   promove para `deprecated` (não verifica mais).

3. **Lazy bootstrap a partir de `settings.audit_hmac_key` como kid
   `legacy`.** Compat 100% retroativa: entries pre-rotation têm
   `hmac_kid IS NULL`, verify cai automaticamente em `legacy`.
   `bootstrap_legacy()` é idempotente (chamadas duplicadas com
   mesma secret não corrompem).

4. **`_compute_hmac` retorna `tuple[str, str]` em vez de `str`.** Nova
   API `sign_audit_entry(payload) -> (kid, sig)` exposta no módulo.
   `AuditService.log()` armazena `hmac_signature=sig` (continua hex
   puro 64 chars) E `hmac_kid=kid` na nova coluna. Compat com
   `verify_chain()` que só olha SHA256, não HMAC.

5. **Coluna `audit_log.hmac_kid VARCHAR(64) NULL` via migration Alembic
   0021.** Index `ix_audit_log_hmac_kid` para forensic queries.
   Migration idempotente (checa `information_schema.columns` antes de
   criar). Downgrade: drop column (entries perdem kid mas SHA256 chain
   intacta).

6. **`verify_audit_entry` falha silenciosa (`False`) em kid
   desconhecido / deprecated.** Não crash em produção: entry suspeito
   = entry suspeito, mas o processo continua. Outras violações
   (secret inválido, kid duplicado) ainda explodem para misuse
   detection em CI.

## Padrões / Snippets reaproveitáveis

```python
# HmacKeyRouter singleton thread-safe (inspiração para futuros registries)
class HmacKeyRouter:
    def __init__(self):
        self._lock = threading.RLock()
        self._keys = {}
        self._active_kid = ""

    def register_key(self, kid, secret, status):
        with self._lock:
            if kid in self._keys:
                raise ValueError(f"kid duplicado: {kid!r}")
            self._keys[kid] = {...}
```

```python
# Migration Alembic idempotente (checa information_schema)
def _column_exists(table, column):
    conn = op.get_bind()
    q = sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    )
    return conn.execute(q, {"t": table, "c": column}).scalar() is not None
```

## Pegadinhas / Notas de cuidado

- **`_compute_hmac` mudou de `str` para `tuple[str, str]`.** Quebrou
  4 mutmut killers que assumiam string. **Tivemos que adaptá-los** —
  isso é parte legítima do ciclo (testes de mutação precisam cobrir
  a implementação real). Nomes `_kid, sig = ...` mostram o unpack
  corretamente.

- **`bootstrap_legacy` precisa ser idempotente** porque `main.py`
  lifespan + `TestClient` + scheduler podem chamar várias vezes. Se
  secret for a mesma, noop; se for diferente, também noop (defesa
  contra tampering de settings — preserva audit chain).

- **`threading.RLock` (não Lock)**: permite que `cleanup_rotated_keys`
  chame métodos internos que pegam o mesmo lock, sem deadlock.

- **`rotated_at` é resetado a cada rotação**, então testar cleanup
  requer artificially aging do timestamp ou criar key direto como
  rotating. Teste `test_cleanup_rotated_keys_after_grace_period`
  usa o pattern `with router._lock: router._keys[kid]["rotated_at"] = ...`.

- **3 testes pré-existentes quebrados NÃO relacionados a esta task**
  (`test_audit_integrity_g8.py` — `AttributeError` no
  `audit_integrity.SessionLocal`). São arquivos untracked de outra
  squad em andamento. Verificado via git stash que falham em master
  puro antes da minha mudança.

- **Tests de mutation killers** (`test_audit_mutmut_killers_g6.py`)
  usam `hmac_mod` alias — já é um padrão para `import hmac as hmac_mod`
  dentro do test em vez do nome builtin (escopo local, evita shadow).

## Próximos passos

- Adicionar `cleanup_rotated_keys_thunk()` ao scheduler lifespan (target
  horário: 03:00 BRT junto com `AUDIT_VERIFY_CRON`).
- Adicionar endpoint admin `POST /admin/audit/rotate-hmac-key` com
  X-API-Key (mesmo pattern do `/admin/audit/check-now`).
- Persistir o registry em Redis para sobreviver a restart do processo
  (hoje é in-memory; restart perde rotação).
- Métrica Prometheus `audit_hmac_key_age_hours` (alerta após N dias
  sem rotação).

## Métricas

- 18 testes novos (`test_audit_keys_g8.py`) — todos PASS
- 4 mutmut killers adaptados — todos PASS
- Migration Alembic 0021 — gerada idempotente
- Ruff: 0 issues
- Mypy: 0 errors
- 125 tests totais do escopo G8.19.T2 PASS em 2.71s

Modified by Gustavo Almeida
