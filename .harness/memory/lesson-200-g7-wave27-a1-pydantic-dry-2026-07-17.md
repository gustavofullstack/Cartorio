# Lesson 200 — G7 Wave 27 A1: Pydantic strict + service DRY

**Date:** 2026-07-17  
**Tasks:** G7.21.T2, G7.20.T2  
**Agent:** cartorio-dev

## What we did

1. **G7.21.T2** — Progressive Pydantic v2 strictness on KEY **input** schemas only:
   - `extra="forbid"`, `str_strip_whitespace=True`, `validate_assignment=True`
   - Targets: AuditLogCreate, ProtocoloCreate/ApiCreate, AgendamentoCreate, LLMTestRequest, DSARCreate, LGPDConsentRequest, Login/Refresh
   - Deferred: Settings (`extra=ignore`), N8nMetricsIngest (`extra=allow`), ORM response models, router-inline models, global `strict=True`
   - Doc: `docs/PYDANTIC_STRICT_FUTURE_FLAGS_G7.md`
   - Tests: `backend/tests/test_pydantic_strict_g7.py`

2. **G7.20.T2** — Real DRY: unified nome/email display masks used by `lgpd_export` + `lgpd_privacy_policy` into `crypto.mask_nome` / `crypto.mask_email_display` (parameterize `empty` + `domain_mode`). Thin wrappers keep test imports.
   - Doc: `docs/SERVICE_LAYER_DRY_G7.md`
   - Inventory also notes Redis sync `_get_redis_client` x3 and httpx ad-hoc clusters as deferred.

## Lessons

- **Do not** set `extra=forbid` on Settings or flexible N8N ingest — will break ops/prod silently-looking 422s.
- **Mask DRY:** differences are usually placeholders (`[titular anonimizado]` vs `[nome indisponivel]`) and domain truncation (TLD-only export) — parameterize, don’t fork full functions.
- **Keep thin wrappers** when private helpers are exported in tests/`__all__` — zero churn on call sites.
- ADR-024 already chose phased forbid; Wave 27 is the first concrete enablement on LGPD/auth-critical bodies.

## Commands

```bash
cd backend && uv run ruff check app/ && uv run mypy app/ --no-error-summary
uv run pytest -v --no-cov tests/test_pydantic_strict_g7.py tests/test_crypto.py \
  tests/test_lgpd_export.py tests/test_lgpd_privacy_policy.py tests/test_schemas_validation.py
```

Modified by Gustavo Almeida
