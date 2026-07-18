# HMAC Key Rotation — Cartório (G8.19.T2)

**Status:** implementado 2026-07-18 | **Cartório:** 2º Serviço Notarial de Uberlândia
**Wave:** 50 (Squad 19 — Cryptography) | **Tasks:** G8.19.T2 | **Review:** cartorio-lgpd pendente
**LGPD Art.** 37 (rastreabilidade) + Art. 46 (segurança) + Art. 50 (governança)

---

## TL;DR

Permite **rotacionar `AUDIT_HMAC_KEY` sem invalidar entries antigos** do
audit log. Cada entry referencia qual `kid` (key id) assinou; entries
pre-rotação continuam verificáveis através do kid `legacy` registrado
no bootstrap do `app.services.audit_keys`.

Operação **zero-downtime**: novas entries assinadas com a kid ativa,
entries antigas ainda verificáveis com sua kid de origem (enquanto a
chave existir no registry).

---

## Motivação

- **LGPD Art. 37** exige cadeia de auditoria íntegra e contínua.
- **LGPD Art. 46** exige medidas de segurança adequadas — rotação
  periódica de chaves criptográficas é boa prática (NIST SP 800-57).
- **LGPD Art. 50** exige governança e planos de resposta a incidentes
  — chave comprometida precisa ser rotacionada sem perder audit
  histórico.

Antes desta task, `settings.audit_hmac_key` era **string única lida do
env** (`AUDIT_HMAC_KEY`); qualquer rotação invalidaria entries antigos.
T025 (regression v22) já detectava o problema como scenario hipotético.

---

## Arquitetura

### Registry singleton thread-safe

`app/services/audit_keys.py` define `HmacKeyRouter`, singleton mantido
em memória (init de processo). Toda mutação passa por
`threading.RLock` interno — segura em ambiente multi-thread
(uvicorn workers, scheduler, dead-man's-switch).

```
                +-----------------------+
                |   HmacKeyRouter       |
                |   (_lock: RLock)      |
                +-----------------------+
                  | kid=legacy (active)  |
                  | kid=k_2026_07_18     | ← ativa (sign)
                  | kid=k_old (rotating) | ← grace 30d
                  | kid=k_very_old       | ← deprecated (sem verify)
                +-----------------------+
                            |
                +-----------+-----------+
                |                       |
        sign_audit_entry()    verify_audit_entry()
        (usa kid ativa)       (usa kid da entry)
```

### Estados de uma key

| Estado      | Quem assina | Quem verifica | Como sai desse estado  |
|-------------|-------------|---------------|------------------------|
| `active`    | sim         | sim           | `rotate_to_new_key()`  |
| `rotating`  | não         | sim           | grace 30 dias → `deprecated` |
| `deprecated`| não         | não (KeyError)| cleanup manual         |

### Compatibilidade retroativa

- **Entries pre-rotação** (`hmac_kid IS NULL`) verificam contra a kid
  `legacy` registrada no bootstrap a partir de `settings.audit_hmac_key`.
- **Entries novas** (criadas após esta task) têm `hmac_kid` preenchido.
- `verify_chain()` continua funcionando sem mudança (verifica só a
  cadeia SHA256, recalcula hash sem depender da HMAC).

---

## Schema

Migration `0021-add-audit-hmac-kid.py` (alembic) adiciona:

```sql
ALTER TABLE audit_log
  ADD COLUMN hmac_kid VARCHAR(64) NULL;

CREATE INDEX ix_audit_log_hmac_kid ON audit_log (hmac_kid);
```

Índice para forensic queries (e.g., "quantas entries foram assinadas
com a kid `k_2026_06_01`?").

---

## API pública

### `audit_keys.HmacKeyRouter` (singleton via `get_router()`)

| Método                            | Uso                                  |
|-----------------------------------|--------------------------------------|
| `bootstrap_legacy(secret, kid)`   | Inicializa com chave do settings     |
| `register_key(kid, secret, status)`| Adiciona nova key ao registry        |
| `rotate_to_new_key(kid, secret)`  | Promove nova active; antiga rotating |
| `get_key_for_signing()`           | Retorna (kid, secret) ativo          |
| `get_key_by_kid(kid)`             | Retorna secret por kid               |
| `cleanup_rotated_keys(grace_days)`| Marca chaves antigas como deprecated |
| `snapshot()`                      | Estado do registry (debug/health)    |

### Helpers de alto nível

```python
from app.services.audit_keys import sign_audit_entry, verify_audit_entry

# Assinar entry novo
kid, sig = sign_audit_entry(canonical_payload_bytes)

# Verificar entry (passar kid correto; None → legacy)
ok = verify_audit_entry(canonical_payload_bytes, kid, sig)
```

### Integração com `AuditService.log()`

```python
class AuditService:
    @staticmethod
    def _compute_hmac(message: str) -> tuple[str, str]:
        """Returns (kid, sig). Substituiu implementação direta por registry."""
        kid, sig = sign_audit_entry(message.encode("utf-8"))
        return kid, sig

    def log(...):
        hmac_kid, hmac_sig = self._compute_hmac(...)
        entry = AuditLog(..., hmac_signature=hmac_sig, hmac_kid=hmac_kid)
```

---

## Operação

### Rotação manual (one-shot)

```python
# Em qualquer modulo com acesso ao router:
from app.services.audit_keys import get_router, generate_new_secret

new_secret = generate_new_secret(nbytes=32)  # 256 bits
old_kid = get_router().rotate_to_new_key("k_2026_07_18", new_secret)
print(f"Rotated: old={old_kid} -> new=k_2026_07_18")
```

Após 30 dias (ou grace configurado), chamar
`cleanup_rotated_keys_thunk()` no scheduler.

### Rotação automatizada via scheduler (recomendado)

`cleanuup_rotated_keys_thunk` deve ser chamado diariamente (sugestão:
junto com `AUDIT_VERIFY_CRON` que roda às 03:00 BRT). Adicionar ao
`app/jobs/cron_audit_verify.py` ou similar.

```python
# Sugestao de integracao no scheduler lifespan
from app.services.audit_keys import cleanup_rotated_keys_thunk
deprecated = cleanup_rotated_keys_thunk(grace_period_days=30)
if deprecated:
    logger.warning("audit_keys: deprecated kids=%s", deprecated)
```

### Adicionar nova key sem rotacionar a atual

```python
get_router().register_key("k_2026_07_18_a", secret_a, status=KeyStatus.ROTATING)
get_router().register_key("k_2026_07_18_b", secret_b, status=KeyStatus.ROTATING)
# Apenas UMA pode ser ACTIVE por vez — usar rotate_to_new_key para promover
```

---

## Garantias

- **Zero-downtime** em rotação: chave antiga continua verificável
  enquanto key existir.
- **Audit chain preservada** (SHA256) — rotação de HMAC **NÃO** altera
  os hashes armazenados.
- **Entries antigas preservadas** — entradas pré-rotação têm
  `hmac_kid IS NULL`; verify usa fallback `legacy`.
- **Thread-safe** — `RLock` interno; 50 threads concorrentes em teste
  dedic (`test_concurrent_rotate_thread_safe`).
- **Falha explícita** em misuse:
  - `kid duplicado` → `ValueError`
  - `secret < 16 bytes` → `ValueError`
  - `rotate sem active key` → sem erro (no-op gracioso)
  - `verify de kid deprecated` → `False` (não crash)
  - `get_key_for_signing sem active` → `RuntimeError`

---

## Tests

`tests/test_audit_keys_g8.py` — 18 testes cobrindo:

1. `test_register_key_first_becomes_active`
2. `test_register_two_active_keys_raises`
3. `test_register_key_rejects_short_secret`
4. `test_register_key_rejects_duplicate_kid`
5. `test_rotate_to_new_key_old_marked_rotating`
6. `test_rotate_with_no_prior_active_no_error`
7. `test_get_key_for_signing_returns_active_only`
8. `test_get_key_by_kid_returns_correct_secret`
9. `test_get_key_by_kid_unknown_raises`
10. `test_verify_old_entry_with_old_key_succeeds`
11. `test_verify_old_entry_with_new_key_fails_gracefully`
12. `test_verify_legacy_kid_used_when_kid_is_none`
13. `test_verify_unknown_kid_fails_silently`
14. `test_cleanup_rotated_keys_after_grace_period`
15. `test_cleanup_rotated_keys_within_grace_period_noop`
16. `test_audit_chain_integrity_preserved_across_rotation`
17. `test_concurrent_rotate_thread_safe`
18. `test_generate_new_secret_minimum_length`

Mais os 4 mutmut killers atualizados em
`tests/test_audit_mutation_killers_g6.py` e
`tests/test_audit_mutmut_killers_g6.py` para o novo retorno tuple de
`AuditService._compute_hmac()`.

Regression tests existentes (`test_audit.py`,
`test_audit_regression_v22_t024_t025.py`) continuam passando.

---

## LGPD-by-design

| Art. LGPD | Como é atendido                                          |
|-----------|-----------------------------------------------------------|
| Art. 37   | Cadeia de auditoria íntegra após rotação (chain preservada) |
| Art. 46   | Rotação periódica sem invalidar histórico (boa prática NIST) |
| Art. 50   | Grace period documentado; cleanup automático via scheduler |
| Art. 52   | Medidas de segurança técnicas adequadas (NIST SP 800-57)   |

DPO/Cartorio-LGPD review pendente (Wave 50 LGPD-REVIEW-PENDING).

---

## Possíveis evoluções

- Persistir o registry em Redis (`SADD audit_keys:active ...`) para
  sobreviver a restart do processo.
- API admin `POST /admin/audit/rotate-hmac-key` com X-API-Key (mesmo
  pattern do `/admin/audit/check-now`).
- Métrica Prometheus `audit_hmac_key_age_hours` para alertar
  automaticamente após N dias sem rotação.
- Auditoria da própria rotação: cada `rotate_to_new_key` deve
  registrar entrada de audit com `action=audit.key_rotated`.

---

## Referências

- NIST SP 800-57 Part 1 — Recommendation for Key Management
- OWASP Cryptographic Storage Cheat Sheet
- LGPD Art. 37, 46, 50
- T025 (test_audit_regression_v22_t024_t025.py) — regression original
- PR anterior: docs/HMAC_KEY_ROTATION_G8.md (este arquivo)

---

Modified by Gustavo Almeida
