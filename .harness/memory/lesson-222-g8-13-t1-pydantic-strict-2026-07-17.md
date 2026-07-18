# Lesson 222 — G8.13.T1 Pydantic strict=True em todos schemas de request (Wave 43 / cartorio-dev 2026-07-17)

## Contexto

Task G8.13.T1 do SUPER_PLANO_G8_100_TASKS pediu `ConfigDict(strict=True)`
em TODOS os schemas Pydantic usados em routes `/api/v1/...` para recusar
coerção implicita (string "123" -> int 123 NAO aceito, float 1.0 -> int 1
NAO aceito, string "true" -> bool NAO aceito).

Pre-requisito: docs/PYDANTIC_STRICT_FUTURE_FLAGS_G7.md (G7.21.T2 Wave 27)
ja tinha habilitado `extra="forbid" + str_strip_whitespace + validate_assignment`
em schemas-chave. G8.13.T1 FORCA strict=True em TODOS schemas de request.

## Decisao

**Class-level strict=True + field-level strict=False override** para campos
com wire-format string (Decimal/datetime/enum/Literal).

Justificativa (empirica — testado em Python 3.14 + Pydantic 2.13):

1. **`model_config = ConfigDict(strict=True)` recusa coerção**:
   - str -> int (REJEITADO ✅)
   - str -> bool (REJEITADO ✅)
   - str -> float (REJEITADO ✅)
   - int -> bool (REJEITADO ✅)
   - int -> str (REJEITADO ✅)
   - int -> datetime (REJEITADO ✅)
   - str -> datetime (REJEITADO ✅)
   - str -> enum (REJEITADO ❌ — PROBLEMA para JSON wire)
   - str -> Literal (ACEITO ✅ — Literal ja aceita str nativamente)
   - int -> float (ACEITO ✅ — numeric tower: int subclass of float)

2. **JSON wire-format NAO tem tipo Decimal/datetime nativo**, entao campos
   como `valor_snapshot: Decimal` recebem string `"150.50"` do cliente.
   Solucao: `Annotated[Decimal, Field(strict=False)]` no field-level.

3. **`Field(strict=False)` funciona em Decimal/datetime/enum** (testado).
   NAO funciona em Literal (Pydantic 2.x erro: "Unable to apply constraint
   'strict' to schema of type 'literal'"). Literal aceita str nativamente,
   entao NAO precisa de override.

4. **Definição final**:
   - Schemas sem Decimal/datetime/enum: class-level `strict=True` direto.
   - Schemas com Decimal/datetime/enum: class-level `strict=True` + override
     field-level `Annotated[T, Field(strict=False)]`.
   - Literal fields: NAO precisam de override (Pydantic ja aceita str).

## Schemas impactados (15 arquivos, 17+ request models)

| Path | Schema | Campos com override |
|------|--------|---------------------|
| `app/config.py` | (setting) | `pydantic_strict_mode = True` (default) |
| `app/schemas/protocolo.py` | `ProtocoloCreateRequest` | `canal_origem` (CanalOrigem enum) |
| `app/schemas/protocolo.py` | `ProtocoloApiCreateRequest` | `ato` (AtoProtocolar enum), `valor_snapshot` (Decimal) |
| `app/schemas/agendamento.py` | `AgendamentoBase` | `tipo` (TipoAtendimento enum) |
| `app/schemas/agendamento.py` | `AgendamentoCreateRequest` | (herda override) + `data_hora` (datetime) |
| `app/schemas/lgpd_consent.py` | `LGPDConsentRequest` | (nenhum — bool/Literal ok) |
| `app/schemas/lgpd_dsar.py` | `DSARCreate` | `rights` (list[LGPDRight]) |
| `app/schemas/audit.py` | `AuditLogCreate` | (nenhum — Literal/str/dict) |
| `app/schemas/llm.py` | `LLMModelInfo`, `LLMTestRequest` | (nenhum — Literal/float/bool/str) |
| `app/api/v1/auth_login.py` | `LoginRequest`, `RefreshRequest` | (nenhum — str/bool/int) |
| `app/api/v1/bot_lgpd.py` | `CancelarRequest`, `ExportRequest`, `AccessRequest`, `RestaurarRequest` | (nenhum — Literal/str/int) |
| `app/api/v1/integrations.py` | `OpenCodeTestRequest`, `N8nErrorRequest`, `N8nDeletionRequest`, `ConsentPropagationRequest` | (nenhum — float/bool/str/int/list[str]) |
| `app/api/v1/lgpd_direitos_v2.py` | `ConsentRequest`, `CorrectionRequest`, `RevogarConsentRequest` | (nenhum — Literal/str/int) |
| `app/api/v1/brain.py` | `LessonCreate` | (nenhum — str) |

Schemas SKIPPED (intencionalmente — fora do escopo "request notarial"):
- `app/schemas/chatwoot_webhook.py` — webhook forward-compat (`extra="ignore"`)
- `app/schemas/metrics.py` — `N8nMetricsIngest` tem `extra="allow"` by design
- `app/schemas/dead_mans_switch.py` — internal frozen models
- `app/schemas/emolumento.py` — apenas response models

## Tests adicionados (23 testes em `tests/test_pydantic_strict_g8.py`)

Cobertura:
1. `test_int_field_rejects_string_coercion` — LoginRequest.ttl_minutes
2. `test_bool_field_rejects_string_coercion` — LGPDConsentRequest.accepted
3. `test_float_field_rejects_string_coercion` — LLMTestRequest.temperature (NOTA: int->float eh aceito por numeric tower)
4. `test_extra_field_rejected` — ProtocoloCreateRequest extra=forbid
5. `test_datetime_field_accepts_iso_string_wire_format` — AgendamentoCreateRequest.data_hora
6. `test_enum_field_accepts_string_wire_format` — ProtocoloCreateRequest.canal_origem
7. `test_decimal_field_accepts_string_wire_format` — ProtocoloApiCreateRequest.valor_snapshot
8. `test_audit_log_create_strict_coercion` — AuditLogCreate
9. `test_dsar_create_strict_coercion` — DSARCreate
10. `test_opencode_test_temperature_strict` — OpenCodeTestRequest
11. `test_n8n_error_request_strict_extra_forbid` — N8nErrorRequest
12. `test_n8n_deletion_deleted_count_strict_int` — N8nDeletionRequest
13. `test_consent_propagation_chatwoot_id_strict_int` — ConsentPropagationRequest
14. `test_access_request_strict` — AccessRequest
15. `test_export_request_strict` — ExportRequest
16. `test_restaurar_request_strict` — RestaurarRequest
17. `test_lgpd_v2_consent_request_strict` — ConsentRequest
18. `test_lgpd_v2_correction_request_strict` — CorrectionRequest
19. `test_lgpd_v2_revogar_consent_strict` — RevogarConsentRequest
20. `test_protocolo_api_create_strict` — ProtocoloApiCreateRequest
21. `test_settings_strict_mode_is_true_by_default` — settings invariant
22. `test_annotated_strict_per_field_pattern` — field-level override pattern
23. `test_lesson_create_strict` — LessonCreate

## Legacy tests ajustados (1)

`tests/test_lgpd_direitos_v2.py::TestCorrigirDados::test_correct_400_invalid_field`:
- Antes: esperava 400 (campo nao-whitelist era checado no handler).
- Agora: retorna 422 (Unprocessable Entity) porque `extra="forbid"` em
  CorrectionRequest recusa campo nao declarado ANTES do handler executar.
- Correção: atualizado para `assert response.status_code == 422`.
- Decisão (a) "ajustar teste legacy para tipo correto" — semanticamente
  422 vs 400 ambos validos, mas 422 eh semanticamente mais preciso
  (Unprocessable Entity = body do request tem problemas estruturais).

## Honesty Gate

```text
pytest tests/test_pydantic_strict_g8.py --no-cov -v
  -> 23 passed in 0.48s

ruff check app/schemas/ app/api/v1/auth_login.py app/api/v1/bot_lgpd.py \
  app/api/v1/integrations.py app/api/v1/lgpd_direitos_v2.py app/api/v1/brain.py \
  app/config.py tests/test_pydantic_strict_g8.py
  -> All checks passed!

mypy app/schemas/ app/api/v1/auth_login.py app/api/v1/bot_lgpd.py \
  app/api/v1/integrations.py app/api/v1/lgpd_direitos_v2.py app/api/v1/brain.py \
  app/config.py
  -> Success: no issues found in 17 source files

pytest tests/ --no-cov -q
  -> 3841 passed, 23 skipped, 49 deselected in 96.40s
```

## Cobertura real de strict (5+ garantias)

1. **string -> int**: REJEITADO em LoginRequest, ProtocoloApiCreateRequest, AgendamentoCreateRequest, N8nDeletionRequest, ConsentPropagationRequest, etc.
2. **string -> bool**: REJEITADO em LGPDConsentRequest, ProtocoloApiCreateRequest.hitl_draft, LoginRequest.dpo, OpenCodeTestRequest.consent_granted.
3. **string -> float**: REJEITADO em LLMTestRequest.temperature, OpenCodeTestRequest.temperature.
4. **campos extras**: REJEITADO em ProtocoloCreateRequest, AgendamentoCreateRequest, LoginRequest, AuditLogCreate, DSARCreate, LGPDConsentRequest, LessonCreate, etc.
5. **int -> datetime**: REJEITADO em AgendamentoCreateRequest.data_hora.
6. **string -> enum**: REJEITADO por default (aceito via field-level strict=False override).

## Pendencias conhecidas (futuras waves)

- **G8.13.T2**: validar schemas de imports JSON no n8n (squad cartorio-n8n).
- **G8.13.T3**: implementar tipos custom Pydantic (CPFStr, CNPJStr) — squad cartorio-lgpd.
- **N8nMetricsIngest** mantem `extra="allow"` por design (workflow #25 prod).
- **Chatwoot webhook** mantem `extra="ignore"` por forward-compat.
- **Settings** mantem `extra="ignore"` (env vars dinamicas).

## Modificado por Gustavo Almeida + cartorio-dev agent (Wave 43 2026-07-17)
