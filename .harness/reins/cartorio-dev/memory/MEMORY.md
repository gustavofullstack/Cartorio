
### Wrapper LLM async com excecao tipada (2026-06-23)
Type: pattern

Padrao testado em cartorio-backend/app/integrations/opencode_go.py (refator commit 20036bb):

```python
async def chat(messages, *, model, api_key, base_url, ...) -> ChatResponse:
    if not api_key: raise ChatError('API key ausente', kind=CONFIG)
    if not base_url: raise ChatError('base_url ausente', kind=CONFIG)
    # ... httpx post ...
    if response.status_code >= 400:
        kind = HTTP_4XX if 400 <= status < 500 else HTTP_5XX
        raise ChatError(msg, kind=kind, status_code=status, body=body_text)
    # ... parse ...
    return ChatResponse(content, model, tokens_in, tokens_out, latency_ms, ...)
```

Decisoes:
- API key + base_url injetados por param (testavel sem settings)
- Latencia medida com time.time() (nao httpx event hooks)
- ChatError tipado com `kind` (CONFIG/HTTP_4XX/HTTP_5XX/TIMEOUT/NETWORK/PARSE) para caller decidir handoff/retry
- ChatResponse dataclass frozen (imutavel)
- raw response NAO retornado por padrao (LGPD: pode ecoar PII)

Reutilizavel para qualquer LLM provider (OpenAI, Anthropic, OpenClaw).
Aplicar mesmo padrao ao adicionar openclaw_gpt.py ou openai.py no mesmo diretorio.
