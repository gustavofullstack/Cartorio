# Lesson 240 — G8.17.T2 Detailed Webhook Schemas in Swagger (2026-07-18)

## Contexto

Task G8.17.T2 do SUPER_PLANO_G8_100_TASKS: "Documentar schemas de payload
detalhados para todos os webhooks no Swagger". Antes desta task, os schemas
de webhook (Telegram, Evolution, Chatwoot, N8N, AlertManager) tinham pouquíssima
documentação no `/openapi.json` — devs tinham que olhar no código fonte para
entender o payload esperado.

## Implementation

### 1. `app/services/pii_marker.py` (novo)

Helper centralizado para marcação LGPD:

- `PIIField(...)` — wrapper sobre `pydantic.Field` que injeta `**LGPD PII**` no
  prefixo da description + `x-pii: True` no `json_schema_extra` (exportado
  como OpenAPI extension).
- `is_pii_field(description)` — bool check para tools/scanners.
- `collect_pii_paths(model)` — retorna lista de paths JSON pointer-like dos
  campos PII (ex: `['message.from.id', 'chat.id']`).
- `PII` constante string `"**LGPD PII**"` para reuso em outros lugares.

### 2. `app/schemas/webhook_payloads.py` (novo, 756 LOC)

Schemas completos para:
- `TelegramUpdate` / `TelegramMessage` / `TelegramUser` / `TelegramChat` / `TelegramCallbackQuery`
- `EvolutionPayload` / `EvolutionKey` / `EvolutionMessage` (dual-format)
- `N8nErrorRequest` / `N8nDeletionRequest` / `N8nMetricsIngest`
- `OutboxDispatchRequest` (Supabase outbox)
- Re-exports: `ChatwootWebhookModel`, `AlertManagerPayload`

Cada schema:
- `ConfigDict(strict=True, extra="ignore")` (forward-compat vendor changes)
- 100% dos campos com `Field(description=...)` em PT-BR
- `examples=[...]` em pelo menos 1 campo por schema
- Defaults explícitos onde útil (chat_id, edit_date, etc)
- `Annotated[T, Field(...)]` type-safe pattern

### 3. `app/schemas/webhook_alertmanager.py` (novo, 264 LOC)

Schemas AlertManager re-encapsulados com 100% descriptions. G8.15.T2 já tinha
os schemas mas sem descriptions detalhadas.

### 4. `app/schemas/chatwoot_webhook.py` (modified)

Estendi com `Annotated[X, Field(description=...)]` mantendo compat 100% com
`parse_chatwoot_payload` e tests existentes.

### 5. Endpoints webhook (modified)

- `app/api/v1/telegram.py` — `openapi_extra` com 3 examples (text/cb/group)
- `app/api/v1/whatsapp.py` — `openapi_extra` com 2 examples (nested/legacy)
- `app/api/v1/router.py` — `Body(examples=)` webhook/evolution +
  `openapi_extra` webhook/chatwoot
- `app/api/v1/alertmanager.py` — reusa schemas de `webhook_alertmanager`
  (mesmo shape, +description)

### 6. `app/middleware/openapi_enhancer.py` (modified)

Adicionei `_register_webhook_schemas(components)` — hook que **force-register**
todos os schemas webhook em `components.schemas`, mesmo os que não são
referenciados via `Annotated[..., Body(...)]` (Telegram/WhatsApp webhooks
continuam usando `request.json()` para backward compat, então FastAPI não
auto-registra).

## Pattern emergente: `Annotated[..., PIIField(...)]`

```python
class TelegramMessage(BaseModel):
    text: Annotated[str | None, PIIField(
        default=None,
        description="Texto plain-text (LGPD PII: pode conter CPF/RG/nome).",
        max_length=4096,
    )] = None

    chat_id: Annotated[int, PIIField(
        description="ID do chat no Telegram (LGPD PII).",
        examples=[123456789],
    )]
```

Beneficios:
- Type-safe (mypy strict passa)
- `description` aparece em `/openapi.json` → Swagger UI mostra tooltip
- `examples` aparecem no Swagger UI como dropdown
- `**LGPD PII**` marker aparece automaticamente em toda description de campo PII
- `x-pii: True` no JSON schema → LGPD scanners podem filtrar/redatar
- Defaults explícitos → Pydantic aceita `Field(default=None)` corretamente

## Tests (18 testes, todos passando)

`backend/tests/test_webhook_schemas_g8.py`:

1. `test_telegram_payload_serialization` — roundtrip JSON
2. `test_telegram_payload_realistic_example` — payload real com CPF
3. `test_pii_fields_marked_in_schema_description` — marker `**LGPD PII**` presente
4. `test_schema_has_examples` — examples em cada webhook schema
5. `test_openapi_includes_enhanced_descriptions` — 100% campos documentados
6. `test_extra_ignore_does_not_break_real_data` — vendor fields ignorados
7. `test_unknown_webhook_returns_validation_error` — payloads inválidos 422
8. `test_evolution_dual_format_compatibility` — nested + legacy
9. `test_pii_field_helper_marker` — PIIField injeta prefixo + x-pii
10. `test_collect_pii_paths_nested` — paths PII nested detectados
11. `test_response_payload_examples_in_openapi` — 3+ examples por endpoint
12. `test_field_descriptions_portuguese` — descriptions PT-BR
13. `test_alertmanager_schema_accepts_real_payload` — payload Prometheus real
14. `test_chatwoot_message_created_full` — todos campos PII marcados
15. `test_outbox_dispatch_required_fields` — canal literal validado
16. `test_n8n_error_request_required` — execution_id required
17. `test_n8n_deletion_request` — LGPD Art. 18 / Art. 37 purga
18. `test_realistic_json_dump_telegram` — serialização JSON

## Honesty Gate (todos cumpridos)

- `uv run pytest tests/test_webhook_schemas_g8.py --no-cov -v` → **18 passed**
- `uv run pytest --no-cov` (full suite) → **4028 passed**, 0 failed
- `uv run ruff check app/schemas/ app/api/v1/...` → **0 errors**
- `uv run mypy app/schemas/...` → **0 errors**
- Para cada schema Pydantic: `Field(description=...)` em 100% dos campos ✓
- `app.openapi()` mostra descriptions em todos os campos ✓
- Lesson criada ✓
- PROGRESS.md append ✓ (next step)
- SUPER_PLANO_G8 G8.17.T2 [x] ✓ (next step)

## Métricas

- Schemas criados: **2** (webhook_payloads, webhook_alertmanager)
- Schemas estendidos: **1** (chatwoot_webhook)
- Endpoints com openapi_extra: **4** (telegram, whatsapp, chatwoot, outbox)
- Fields com description: **~80 campos** (todos com `Field(description=...)`)
- PII fields marcados: **~30 campos** com `**LGPD PII**`
- Tests adicionados: **+18**
- Honest count G8: **54 → 55/100** (+1)

## Gotcha: schemas não-referenciados não auto-registram

FastAPI só auto-registra schemas que aparecem em route handlers (via
`Annotated[Schema, Body(...)]` ou `response_model=Schema`). Os webhooks
Telegram/WhatsApp usam `request.json()` (raw body) por causa da lógica
complexa de multi-step parsing, então seus schemas não eram auto-registrados.

**Solução**: hook `_register_webhook_schemas()` em `openapi_enhancer.py`
que adiciona manualmente os schemas em `components.schemas`. Sem isso, os
`$ref` em `openapi_extra` ficam dangling e o Swagger UI não renderiza.

## Cross-review LGPD pendente

Mudança em `app/schemas/` e `app/services/pii_marker.py` toca PII/LGPD.
**AGUARDANDO cross-review do `cartorio-lgpd`** antes de merge público
(padrão estabelecido em lesson 236 para Wave 46).

Pontos de review sugeridos:
1. Marker `**LGPD PII**` é suficiente ou precisa de algo mais formal?
2. `x-pii: True` extension é compatível com specs OpenAPI?
3. `collect_pii_paths` retorna paths suficientes para LGPD scanner?

## Modified by Gustavo Almeida + super orquestrador (Wave 47 prep)
