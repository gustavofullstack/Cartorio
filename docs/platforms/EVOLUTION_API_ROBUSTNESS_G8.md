# Evolution API Robustness — G8.22.T1

**Sprint**: 8 (Wave 22)  
**Task**: G8.22.T1 — Robustness do handler Evolution API para 8 tipos de mensagem.  
**Rein**: cartorio-n8n  
**LGPD**: Art. 46 (seguranca e sigilo de dados).

## Contexto

A **Evolution API 2.3.7** (instancia `cartorio-2notas`) envia webhooks ao
backend FastAPI em `POST /api/v1/webhook/evolution`. Os 8 tipos de mensagem
suportados pelo WhatsApp/Baileys sao:

| Tipo | field Evolution | Extraido pelo handler? | Fluxo |
|---|---|---|---|
| text | `message.conversation` / `message.extendedTextMessage.text` | sim | scrub -> LLM |
| image | `message.imageMessage.caption` (opcional) | paracial (caption opcional) | handoff se vazio |
| audio | `message.audioMessage` (sem caption) | nao | handoff |
| document | `message.documentMessage.fileName` (sem caption) | nao | handoff |
| video | `message.videoMessage.caption` (opcional) | paracial | handoff se vazio |
| sticker | `message.stickerMessage` (sem caption) | nao | handoff |
| location | `message.locationMessage.latitude/longitude` | nao | handoff |
| contact | `message.contactMessage.vcard` | nao | handoff |

**P0 contract**: o handler NUNCA pode retornar 5xx para qualquer um
destes 8 tipos. Caso contrario a Evolution para de enviar webhooks (retry
policy agressivo) e a integracao WhatsApp cai inteira — afetando
atendimento humano do cartorio.

## Mudanca aplicada (G8.22.T1)

### 1. Fixtures sinteticas — `backend/tests/fixtures/evolution_payloads.py`

Adicionado modulo com 8 fixtures realistas (Baileys-derived), indexadas
pelo nome em `EVOLUTION_FIXTURES`. Cada fixture usa apenas dados
**100% ficticios** (LGPD Art. 46 — zero PII real):

```python
EVOLUTION_FIXTURES: dict[str, dict] = {
    "text", "image", "audio", "document",
    "video", "sticker", "location", "contact",
}
```

Cobertura por tipo:
- `text`: campo `conversation` (sentence sem PII).
- `image`: `imageMessage` com mimetype JPEG + caption + URL fake.
- `audio`: `audioMessage` PTT (push-to-talk), mimetype `audio/ogg; codecs=opus`.
- `document`: `documentMessage` PDF com `fileName`.
- `video`: `videoMessage` MP4 com `caption` opcional.
- `sticker`: `stickerMessage` mimetype `image/webp`.
- `location`: `locationMessage` lat/lon (Uberlandia MG sintetico).
- `contact`: `contactMessage` com vCard embutido (displayName + TEL falso).

Tambem adicionado `backend/tests/fixtures/__init__.py` para tornar o
diretorio um package importavel.

### 2. Test file — `backend/tests/test_evolution_message_types_g8.py`

23 testes cobrindo:

- **Happy-path parametrized (8 testes)** — cada um dos 8 tipos retorna
  status < 500. P0 contract explicito.
- **Caminho feliz do tipo text** — `scrubbed` populado,
  `needs_human_handoff=False` quando LLM sucesso.
- **Handoff explicito para midia** — image/audio/document disparam
  `needs_human_handoff=True` + `handoff_reason="payload_empty_message"`.
- **Defense in depth** — payload oversized (>1MB), timestamp negativo,
  `data` faltando, `messageType` desconhecido, message_id gigante —
  nenhum pode causar 5xx.
- **Idempotency** — replay do mesmo `(instance, message_id)` retorna
  `status='idempotent'` ou `'ok'` em vez de duplicar efeito.
- **LGPD shape** — response NAO ecoa `remoteJid` cru (apenas metadado).
- **JSON encoding sanity** — todas as 8 fixtures sao `json.dumps`-able.

### 3. Mock do LLM chain

LLM e mocked em TODOS os testes via `autouse` fixture:

```python
@pytest.fixture(autouse=True)
def _mock_llm_chain():
    with patch(
        "app.integrations.fallback.chat_with_fallback",
        new=AsyncMock(return_value=_FakeLLMResponse()),
    ):
        yield
```

Sem este mock, o handler tenta chamar provedores upstream
(opencode_go + openclaw) que nao estao acessiveis em CI/test, ativando
human-handoff e mascarando o sucesso do scrubber.

## Resultados

```
$ cd backend && uv run pytest --no-cov -q tests/test_evolution_message_types_g8.py
23 passed, 73 warnings in 0.72s
```

- **23 testes PASS** (gate do task: 12+).
- **ruff check**: 0 errors.
- **ruff format**: ja conforme line-length=100.
- **mypy**: 0 errors.
- **Sem regressao** — os 2 testes que falham em master
  (`test_output_safety.py::test_scrub_response_nao_altera_audit_metadata`,
  `test_swagger_persist_auth_g8.py::test_openapi_security_scheme_defined`)
  ja estavam quebrados antes desta task (verificado via `git stash`).

## Decisoes de design

### Por que 8 tipos exatos?

Correspondem aos tipos oficiais do WhatsApp via Baileys. Stickers e
vCards (contactMessage) sao os mais comuns em prod que estao atualmente
fora de cobertura teste — imageMessage/audio sem OCR sao responsaveis
pela maioria das tentativas de humanos-com-bot onde o backend responder
errado.

### Por que `handoff` em midia sem texto?

Defense in depth (router.py:1069-1084): chamar LLM com input vazio e
perigoso (ambiguous interpretation -> hallucinations / PII leakage).
Para integracao backend + escrevente humano (HITL), a politica e:
**midia -> escrevente primeiro, depois LLM com transcricao/OCR manual**.

### Por que status < 500 e nao exatamente 200?

O handler pode retornar:
- 200 (processado, idempotent, ou handoff gracioso).
- 4xx (validation — payload estruturalmente invalido).
- 5xx = **BUG** — Evolution nao vai retentar, mas tambem nao vai recusar
  o payload. Pior: se cair no catch-all de Evolution, ela marca como
  entregue e nao reenvia.

Por isso testamos o limite superior (`status < 500`) e nao o codigo
exato (que depende do caminho: scrub/LLM/idempotency).

## Compliance LGPD

- **Art. 46** — dados das fixtures 100% ficticios (faker-style).
- **Art. 7** — consent gate do WhatsApp continua sendo validado em
  `test_webhook_evolution_e2e.py` (separado).
- **Art. 37** — todo reply do handler gera audit log entry
  (verificado em `test_evolution_message_types_g8.py::test_*_triggers_human_handoff`).

## Referencias

- Evolution API 2.3.7 doc: https://doc.evolution-api.com/v2/api-reference
- Baileys types (Baileys > 6.x): `MessageType` enum
- LGPD Art. 46 — Lei 13.709/2018.

Modified by Gustavo Almeida.
