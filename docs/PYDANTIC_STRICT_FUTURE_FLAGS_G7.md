# G7.21.T2 — Pydantic v2 strict / future flags

**Task:** G7.21.T2  
**Wave:** 27  
**Owner:** cartorio-dev  
**Date:** 2026-07-17  
**Related:** ADR-024 (`docs/adr/024-pydantic-strict-future.md`)

## 1. Current state (audit)

| Área | Onde | `model_config` pré-Wave27 |
|------|------|---------------------------|
| Settings | `app/config.py` | `SettingsConfigDict(extra="ignore")` — **manter** (env vars extras) |
| Audit input | `schemas/audit.AuditLogCreate` | `extra="forbid"` ✅ |
| Audit/ORM out | `AuditLogResponse` etc. | `from_attributes=True` |
| Protocolo input | `ProtocoloCreateRequest`, `ProtocoloApiCreateRequest` | só `json_schema_extra` |
| Protocolo/ORM out | `ProtocoloResponse`, `ClienteResumo` | `from_attributes=True` |
| Agendamento | `AgendamentoBase` / Create / Response | `from_attributes` + examples |
| Metrics N8N ingest | `N8nMetricsIngest` | `extra="allow"` (payload flexível prod) |
| Metrics response | `MetricsResponse` | dict config + example |
| LGPD DSAR / Consent | `lgpd_dsar`, `lgpd_consent` | sem ConfigDict |
| LLM smoke | `schemas/llm.LLMTestRequest` | sem ConfigDict |
| Auth login | `api/v1/auth_login.LoginRequest` | sem ConfigDict |
| Inline API models | `router.py`, `bot_lgpd.py`, `brain.py`, v2 | misto; 1× `extra="forbid"` em correção cliente |
| Internal frozen | `backup_v2`, `dead_mans_switch` jobs | `{"frozen": True}` |

**Default Pydantic v2:** `extra="ignore"` (campos desconhecidos descartados).  
ADR-024 já documentou o risco LGPD de leave-as-ignore e optou por fasear.

## 2. Flags enabled (Wave 27 — KEY input only)

Progressive strictness on **request bodies** (not every model):

```python
model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
    validate_assignment=True,
)
```

| Schema | File |
|--------|------|
| `AuditLogCreate` | `app/schemas/audit.py` (+ strip + validate_assignment) |
| `ProtocoloCreateRequest` | `app/schemas/protocolo.py` |
| `ProtocoloApiCreateRequest` | `app/schemas/protocolo.py` |
| `AgendamentoCreateRequest` | `app/schemas/agendamento.py` |
| `LLMTestRequest` | `app/schemas/llm.py` |
| `DSARCreate` | `app/schemas/lgpd_dsar.py` |
| `LGPDConsentRequest` | `app/schemas/lgpd_consent.py` |
| `LoginRequest` | `app/api/v1/auth_login.py` |
| `RefreshRequest` | `app/api/v1/auth_login.py` |

### Semantics

| Flag | Effect |
|------|--------|
| `extra="forbid"` | Unknown JSON keys → **422** (blocks silent field injection) |
| `str_strip_whitespace=True` | Leading/trailing spaces stripped on `str` fields |
| `validate_assignment=True` | Re-validates on attribute assignment after construct |

## 3. Flags deferred (phased plan)

| Target | Why deferred | Next wave |
|--------|--------------|-----------|
| `Settings` (`extra="ignore"`) | Env/ops inject unknown keys; forbid would break deploy | never (or opt-in allowlist) |
| `N8nMetricsIngest` (`extra="allow"`) | Prod workflow #25 flexible payload | keep allow; document only |
| Response / ORM models (`from_attributes`) | Built from ORM/dicts with optional drift; forbid risk on internal mapping | Wave 28+ per endpoint |
| Inline models in `router.py`, `bot_lgpd.py`, `brain.py`, v2 | High surface / low review time | Wave 28: move to `schemas/` + strict |
| `strict=True` (Pydantic strict types) | Coercion break (e.g. `"150.50"` → Decimal) used by API clients | separate RFC |
| Global `model_config` on `BaseModel` subclass | One base for all would surprise half the API | prefer explicit per schema |

**Phased rollout:**

1. **Wave 27 (done):** key LGPD/auth/protocolo/LLM/agendamento **inputs**.  
2. **Wave 28:** migrate remaining request bodies from routers → `schemas/` + `extra="forbid"`.  
3. **Wave 29+:** evaluate `strict=True` only where clients already send typed JSON (no string-to-int).  
4. **Never** on Settings / intentionally flexible ingest.

## 4. How to test

```bash
cd backend

# Unit: strict flags + strip + assignment
uv run pytest -v --no-cov tests/test_pydantic_strict_g7.py tests/test_schemas_validation.py

# Related schemas still green
uv run pytest -v --no-cov tests/test_lgpd_consent_api.py tests/test_crypto.py \
  tests/test_lgpd_export.py tests/test_lgpd_privacy_policy.py

# Gates
uv run ruff check app/
uv run mypy app/ --no-error-summary
```

### Manual checks

```python
from pydantic import ValidationError
from app.schemas.protocolo import ProtocoloCreateRequest, CanalOrigem

# extra forbid
try:
    ProtocoloCreateRequest(
        cliente_cpf="12345678901",
        cliente_nome="Joao",
        tipo="certidao_negativa",
        canal_origem=CanalOrigem.WEB,
        consentimento_lgpd=True,
        evil_field=1,  # type: ignore[call-arg]
    )
except ValidationError as e:
    assert "extra" in str(e).lower() or "evil" in str(e).lower()

# strip whitespace
p = ProtocoloCreateRequest(
    cliente_cpf="12345678901",
    cliente_nome="  Joao  ",
    tipo="certidao_negativa",
    canal_origem=CanalOrigem.WEB,
    consentimento_lgpd=True,
)
assert p.cliente_nome == "Joao"
```

## 5. Risk / rollback

- **Risk:** N8N or external clients sending **unknown keys** on protocolo/consent/DSAR get 422.  
- **Mitigation:** only enable on documented contracts; metrics N8N left `allow`.  
- **Rollback:** remove `extra="forbid"` from the affected `model_config` (keep strip/validate if desired).

## 6. Status

| Item | Status |
|------|--------|
| G7.21.T2 audit | DONE |
| Key schemas strict | DONE (Wave 27) |
| Docs + tests | DONE |
| Full router migration | DEFERRED Wave 28 |

**Modified by Gustavo Almeida**
