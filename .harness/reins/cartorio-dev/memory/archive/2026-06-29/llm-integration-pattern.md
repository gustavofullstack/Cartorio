---
description: Padrao completo de wrapper LLM (OpenAI/Anthropic/OpenClaw) — ChatError tipado + ChatResponse frozen + checklist LGPD completo (PII scrub interno, audit log, consent gate, rate limit Redis, teste de regressao). Ativa quando for criar/estender integracao LLM em app/integrations/.
---

# LLM Integration Pattern (LGPD-compliant)

Padrao testado em `backend/app/integrations/opencode_go.py` (refator + audit-fix). Aplicar para QUALQUER novo wrapper LLM (openclaw_gpt, anthropic_claude, openai_direct).

## Wrapper async com excecao tipada

```python
from dataclasses import dataclass
import asyncio
import hashlib
import time
from enum import Enum

class ErrorKind(str, Enum):
    CONFIG = "config"
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    TIMEOUT = "timeout"
    NETWORK = "network"
    PARSE = "parse"
    LGPD_BLOCKED = "lgpd_blocked"
    RATE_LIMITED = "rate_limited"

class ChatError(Exception):
    def __init__(self, msg, *, kind, status_code=None, body=None):
        super().__init__(msg)
        self.kind = kind
        self.status_code = status_code
        self.body = body

@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int

async def chat(messages, *, model, api_key, base_url,
                consent_granted: bool = False,  # LGPD art. 7 I
                session_id: str | None = None):
    # 1. CONFIG guard
    if not api_key: raise ChatError("API key ausente", kind=ErrorKind.CONFIG)
    if not base_url: raise ChatError("base_url ausente", kind=ErrorKind.CONFIG)

    # 2. Consent gate (safe-by-default)
    if not consent_granted:
        raise ChatError("Consentimento nao concedido", kind=ErrorKind.LGPD_BLOCKED)

    # 3. PII scrub INTERNO (defense-in-depth)
    scrubbed = [{"role": m["role"], "content": pii.scrub(m["content"])} for m in messages]

    # 4. Rate limit Redis (opt-in via env var)
    if session_id and settings.rate_limit_enabled:
        if not await check_rate_limit(session_id, ttl=60):
            raise ChatError("Rate limit exceeded", kind=ErrorKind.RATE_LIMITED)

    # 5. Request hash (SHA-256 do payload SCRUBBED)
    payload = {"model": model, "messages": scrubbed}
    request_hash = hashlib.sha256(json.dumps(payload).encode()).hexdigest()

    # 6. HTTP call com latency
    start = time.time()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
    except httpx.TimeoutException:
        raise ChatError("Timeout", kind=ErrorKind.TIMEOUT)
    except httpx.NetworkError as e:
        raise ChatError(str(e), kind=ErrorKind.NETWORK)

    latency_ms = int((time.time() - start) * 1000)

    if response.status_code >= 400:
        kind = ErrorKind.HTTP_4XX if 400 <= response.status_code < 500 else ErrorKind.HTTP_5XX
        raise ChatError(response.text[:500], kind=kind,
                       status_code=response.status_code, body=response.text)

    # 7. Parse
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        tokens_in = data["usage"]["prompt_tokens"]
        tokens_out = data["usage"]["completion_tokens"]
    except (KeyError, ValueError) as e:
        raise ChatError(f"Parse error: {e}", kind=ErrorKind.PARSE)

    # 8. Audit log via asyncio.to_thread (NAO bloqueia event loop)
    response_hash = hashlib.sha256(json.dumps({
        "model": model, "tokens_in": tokens_in, "tokens_out": tokens_out,
        "content_length": len(content),
    }).encode()).hexdigest()

    asyncio.create_task(asyncio.to_thread(
        audit_service.log,
        action="llm.chat", resource=model,
        request_hash=request_hash, response_hash=response_hash,
        latency_ms=latency_ms, session_id=session_id,
    ))

    return ChatResponse(content=content, model=model,
                        tokens_in=tokens_in, tokens_out=tokens_out,
                        latency_ms=latency_ms)
```

## Checklist LGPD obrigatorio (NAO pular nenhum)

1. **PII scrubbing INTERNO (defense-in-depth)** — chamar `pii.scrub()` em cada message.content ANTES de payload. Docstring "caller DEVE scrubar" NAO basta. Auditoria cartorio-lgpd pegou 8 blockers em opencode_go.py por scrub ser so externo.

2. **Audit log via AuditService** (LGPD art. 37) — SHA-256 do payload SCRUBBED (request_hash) + SHA-256 do metadata do response SEM content (response_hash com `content_length`). Hash NAO pode ser reversivel a partir do bruto.

3. **Consent gate** (LGPD art. 7 I) — param `consent_granted: bool = False` (safe-by-default). Bloqueia ANTES de chamar httpx. Falha = ChatError(kind=LGPD_BLOCKED).

4. **Rate limit por sessao** (cost guard) — Redis `INCR + EXPIRE`, chave `<provider>:ratelimit:{session_id}`, TTL 60s. Default None = desabilitado em dev. Env var opt-in pra prod.

5. **Teste de REGRESSAO dedicado** — `tests/integration/test_<provider>_no_pii.py` com mock httpx que falha se PII bruto chegar. Cobre: CPF, RG, CNPJ, email, telefone, system message, audit hash.

6. **Fallback provider scaffold** (placeholder OK) — scaffold explicito com TODO + docstring deixando claro que eh placeholder. NAO deixar TODO escondido.

7. **Docstring alinhada** — declarar o MODELO ROTEADO (deepseek-v4-flash via OpenCode-Go) e NAO o runtime IDE (MiniMax M2.7/M3 do opencode.json do Mavis). Inconsistencia entre docstring + config + RIPD gera blocker.

## Decisoes tecnicas

- **Latencia com `time.time()`** (nao httpx event hooks — menos overhead, suficiente pra P95 SLA)
- **ChatError tipado com `kind`** (CONFIG/HTTP_4XX/HTTP_5XX/TIMEOUT/NETWORK/PARSE/LGPD_BLOCKED/RATE_LIMITED) — caller decide handoff/retry sem vazar conteudo
- **ChatResponse dataclass frozen** (imutavel)
- **Raw response NAO retornado por padrao** (LGPD: pode ecoar PII)
- **Audit via `asyncio.create_task(asyncio.to_thread(...))`** — NAO bloqueia event loop. Falha no audit NAO quebra fluxo principal (try/except ao redor)
- **request_hash usa SHA-256 do payload SCRUBBED** — LGPD: hash NAO pode ser reversivel a partir do bruto

## Aplicar para

- `openclaw_gpt.py` (scaffold + LGPD checklist)
- `anthropic_claude.py` (scaffold + LGPD checklist)
- `openai_direct.py` (scaffold + LGPD checklist)

Cada um deve herdar o mesmo padrao de ChatResponse + ChatError + audit + scrub.

## Licao aprendida

Auditoria LGPD em opencode_go.py: 8 blockers = 2 criticos + 3 altos + 3 medios. Shift-the-burden ("caller faz scrub") eh falha sistematica — TODA integracao LLM precisa de scrubbing interno + audit log + consent gate como default, nao opt-in.

Referencias: cartorio-dev Sprint 1.6 (01c26df).
