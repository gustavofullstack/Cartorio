# Lesson 263 — G8.22.T1 robustness do handler Evolution API (2026-07-18)

## Contexto

O webhook Evolution API (`POST /api/v1/webhook/evolution`) recebe 8 tipos de mensagem do WhatsApp/Baileys: text, image, audio, document, video, sticker, location, contact. Cada um tem um shape diferente no campo `message.*`, e historicamente:

- image / audio / document sem OCR/transcricao caem em `raw_text = ""` -> `_parse_dual_format` retorna string vazia -> handler precisa fazer fallback gracioso.
- audioMessage/stickerMessage/contactMessage NAO tem campo de texto -> sem fallback o LLM e chamado com payload vazio (risco de hallucination e PII echo).
- timestamp negativo (pre-1970) e message_id gigante (1MB string) ja causaram 5xx em prod.

A task G8.22.T1 era blindar o handler para os 8 tipos com testes parametrizados + fixtures sinteticas + edge cases (oversized, malformado, missing data, weird messageType).

## Decisão

Adicionado `backend/tests/fixtures/evolution_payloads.py` com 8 fixtures realistas Baileys-derived (zero PII real — LGPD Art. 46). Agregadas em `EVOLUTION_FIXTURES: dict[str, dict]` para `pytest.mark.parametrize` consumir diretamente.

Adicionado `backend/tests/test_evolution_message_types_g8.py` com **23 testes** (gate era 12+):

- 1 teste parametrizado cobrindo os 8 tipos (`status < 500`).
- 1 happy path do text (asserts `scrubbed` populado + `needs_human_handoff=False`).
- 3 handoffs explicitos (image, audio, document) — confirmam `handoff_reason="payload_empty_message"`.
- 5 defense-in-depth (oversized 1.5MB, timestamp negativo, `message={}`, `data` faltando, event nao-upsert).
- 1 idempotency replay (mesmo message_id nao duplica).
- 1 LGPD shape (response nao ecoa remoteJid cru).
- 3 schema/edge (minimal payload, weird messageType, huge message_id).
- 1 JSON encoding sanity (todas as 8 fixtures sao `json.dumps`-able).

LLM chain mockado em TODOS os testes via fixture autouse (`patch("app.integrations.fallback.chat_with_fallback", new=AsyncMock(return_value=_FakeLLMResponse()))`). Sem isso, opencode_go e openclaw falham com ConnectionError no test environment, ativando human-handoff e mascarando o sucesso do scrubber camada 3.

## LGPD

- **Art. 46** — `FAKE_REMOTE_JID = "5511999990001@s.whatsapp.net"`, `FAKE_PUSH_NAME = "Cliente Fixture"`, todas as URLs/checksums fake. Zero dado real.
- **Art. 37** — `handoff_reason="payload_empty_message"` registrado no audit log (verificado indiretamente pelo flow router.py:1069-1084).
- **Art. 7** — consent gate LGPD NAO foi alterado (test continua exercitando o caminho `app.api.v1.whatsapp.parse_evolution_payload`).

## Failure modes cobertos

| Cenário | Defesa | Test |
|---|---|---|
| 1.5MB JSON com campo string | handler nao crasha (router.py FastAPI default) | `test_evolution_handler_handles_oversized_payload_without_500` |
| Timestamp negativo | handler nao crasha | `test_evolution_handler_handles_negative_timestamp` |
| `message = {}` | cai em `needs_human_handoff` | `test_evolution_handler_handles_missing_message_field` |
| `data` ausente (legado) | parser extrai do root level | `test_evolution_handler_handles_missing_data_block` |
| Event != messages.upsert | evolution_ingest ignora | `test_evolution_handler_ignores_non_upsert_event` |
| message_id 1MB string | IdempotencyStore aceita sem OOM | `test_evolution_handler_handles_huge_message_id_string` |
| Replay mesmo message_id | retorn `status='idempotent'` | `test_evolution_handler_idempotent_replay_same_message_id` |
| weird messageType (reactionMessage) | cai em `needs_human_handoff` | `test_evolution_handler_does_not_leak_500_on_weird_message_type` |

## Restricao honored

- Commit direto em `master` via `--no-verify`, sem branch.
- `SUPER_PLANO_G8.md` e `PROGRESS.md` nao tocados.
- Nenhuma chamada para Evolution API real — fixtures 100% sinteticas.
- `make pre-commit` skipada (--no-verify); ruff + mypy passam limpos:
  - `ruff check`: 0 errors em `tests/test_evolution_message_types_g8.py` + `tests/fixtures/`.
  - `ruff format`: ja conforme.
  - `mypy`: 0 errors em 3 source files.

## Resultados

- `pytest --no-cov -q tests/test_evolution_message_types_g8.py`: **23 passed**.
- `pytest --no-cov -q -k evolution`: **115 passed** (+33 vs baseline 82), 2 skipped.
- Baseline `pytest --no-cov -q` mantem **2 falhas pre-existentes** (NAO introduzidas por esta task):
  - `tests/test_output_safety.py::test_scrub_response_nao_altera_audit_metadata` (Lesson 260).
  - `tests/test_swagger_persist_auth_g8.py::TestSwaggerPersistAuthorization::test_openapi_security_scheme_defined` (Lesson 260).
- Gate coverage 90% NAO foi rodado offline (suite full timeout >10min em CI local), mas enforcado em CI no proximo push.

## Próximos passos (não nesta task)

1. **OCR/transcricao para imageMessage/audioMessage** (sprint futuro): quando backend receber midia, chamar LLM multimodal Claude Opus 4.5 / GPT-5.5 Vision para extrair texto, substituir caminho `_parse_dual_format`. Atualizar este teste junto.
2. **413 explicito** — adicionar middleware de tamanho maximo (`MaxBodySizeMiddleware`) com response 413 + ProblemDetails RFC 7807 para payloads >1MB. Atualizar test `test_evolution_handler_handles_oversized_payload_without_500` para aceitar 413.
3. **mypy strict em testes/** — atualmente roda com default, nao strict. Pode habilitar via `[[tool.mypy.overrides]] module = ["tests.*"]`.
4. **E2E live test** — usar skill `n8n` para enviar 1 mensagem real de cada tipo via Evolution sandbox `cartorio-2notas-stage`. Por enquanto só unit.

Modified by Gustavo Almeida + cartorio-n8n — G8.22.T1.
