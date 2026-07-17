# G7.20.T2 — Service layer extract duplicates

**Task:** G7.20.T2  
**Wave:** 27  
**Owner:** cartorio-dev  
**Date:** 2026-07-17  
**Principle:** KISS / SOLID — surgical only

## 1. Inventory (duplicates found)

| Cluster | Locations | Nature | Action Wave 27 |
|---------|-----------|--------|----------------|
| **Nome / email display masks** | `lgpd_export._mask_nome` / `_mask_email` **vs** `lgpd_privacy_policy._mask_nome_personalizado` / `_mask_email_personalizado` | Near-identical PII display masking; comment already said “mesmo padrao” | **EXTRACTED** → `crypto.mask_nome` + `crypto.mask_email_display` |
| CPF/CNPJ mask | `services/crypto.mask_cpf` **vs** `models/cpf_cnpj_validator.mask_cpf` | Same mask format; **different** invalid handling (`""` vs `[MASKED:cpf]`) | **DEFERRED** — semantic fork intentional |
| Sync Redis client | `emolumento_cache`, `agendamento_cache`, `atendimento_cache` `_get_redis_client()` | Identical 8-line factory | Documented; extract later to `app.core` (see ADR-026 dual async/sync) |
| Async Redis `_get_client` | `rate_limit`, `sliding_window`, `idempotency_store`, `redis_bus`, `slow_queries` | Similar lazy async get | Prefer `app.core.redis_client` over time |
| httpx.AsyncClient ad-hoc | `notificacao`, `chatwoot_handoff`, `cartorio_agent`, `dead_mans_switch` | Timeout + status_code checks | High risk rewrite; leave + thin helpers later |
| Status HTTP parsing | multiple services `r.status_code in (200, 201)` | Trivial | Not worth abstraction |

## 2. What was extracted

### Shared helpers in `app/services/crypto.py`

```python
def mask_nome(nome: str | None, *, empty: str = "[nome indisponivel]") -> str:
    """G*** A*** style; `empty` customiza placeholder."""

def mask_email_display(
    email: str | None,
    *,
    empty: str = "[email indisponivel]",
    domain_mode: Literal["full", "tld"] = "full",
) -> str:
    """f***@domain or f***@tld (export D29)."""
```

### Call sites (thin wrappers keep test imports stable)

| Service | Wrapper | Shared call |
|---------|---------|-------------|
| `lgpd_export` | `_mask_nome` | `mask_nome(..., empty="[nome indisponivel]")` |
| `lgpd_export` | `_mask_email` | `mask_email_display(..., domain_mode="tld")` |
| `lgpd_privacy_policy` | `_mask_nome_personalizado` | `mask_nome(..., empty="[titular anonimizado]")` |
| `lgpd_privacy_policy` | `_mask_email_personalizado` | `mask_email_display(..., domain_mode="full")` |

**Why keep wrappers:** tests import private helpers (`test_lgpd_export`, `test_lgpd_privacy_policy`); `__all__` re-exports privacy helpers. Behavior unchanged.

### Design notes

- **Single source of truth** for display masks under crypto (already home of `mask_cpf` / `mask_email`).
- **Parameterize differences** (`empty`, `domain_mode`) instead of copy-paste.
- Did **not** change `mask_email` (logs/UI empty → `""`) — different contract from LGPD display placeholders.

## 3. Intentionally not extracted (risk)

1. **httpx pools** — agent/LLM timeouts differ (8s–60s); shared client needs lifecycle + tests.  
2. **Redis sync factory** — easy win later; blocked only by time + need for fake-redis parity tests.  
3. **cpf_cnpj_validator masks** — invalid path used by A10 validators; merging would alter security logging.

## 4. How to test

```bash
cd backend
uv run pytest -v --no-cov \
  tests/test_crypto.py \
  tests/test_lgpd_export.py \
  tests/test_lgpd_privacy_policy.py \
  tests/test_pydantic_strict_g7.py
```

## 5. Status

| Item | Status |
|------|--------|
| Inventory | DONE |
| ≥1 real DRY (2+ call sites) | DONE (`mask_nome` / `mask_email_display`) |
| Docs | DONE |
| Redis/httpx extract | DEFERRED (documented) |

**Modified by Gustavo Almeida**
