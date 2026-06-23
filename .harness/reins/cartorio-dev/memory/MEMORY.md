
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

### LGPD wrapper LLM - checklist obrigatorio para QUALQUER integracao futura (2026-06-23)
Type: pattern

Contexto: commit 01c26df (cartorio-dev Sprint 1.6) — corrigiu 8 blockers LGPD em opencode_go.py apontados pela auditoria cartorio-lgpd. Padrao replicavel para QUALQUER wrapper de LLM provider (Anthropic, OpenAI direto, OpenClaw, etc).

Checklist obrigatorio (NAO pular nenhum):

1. **PII scrubbing INTERNO (defense-in-depth)** — chamar `pii.scrub()` em cada message.content ANTES de montar payload. Docstring "caller DEVE scrubar" NAO basta.
2. **Audit log via AuditService** (LGPD art. 37) — SHA-256 do payload SCRUBBED (request_hash) + SHA-256 do metadata do response SEM content (response_hash com content_length).
3. **Consent gate** (LGPD art. 7 I) — param `consent_granted: bool = False` (safe-by-default). Bloqueia ANTES de chamar httpx.
4. **Rate limit por sessao** (cost guard) — Redis incr+expire. Default None = desabilitado em dev. Env var opt-in.
5. **Teste de REGRESSAO dedicado** — `tests/integration/test_<provider>_no_pii.py` com mock httpx que falha se PII bruto chegar. Cobre: CPF, RG, CNPJ, email, telefone, system message, audit hash.
6. **Fallback provider** (placeholder OK) — scaffold explicito com TODO + docstring deixando claro que eh placeholder.
7. **Docstring alinhada** — declarar o MODELO ROTEADO (deepseek-v4-flash via OpenCode-Go) e NAO o runtime IDE (MiniMax M2.7/M3 do opencode.json do Mavis). Inconsistencia entre docstring + config + RIPD gera blocker.

Decisoes tecnicas:
- Auditor usa `ChatError(kind=LGPD_BLOCKED|RATE_LIMITED|CONFIG|HTTP_4XX|...)` para classificar erros sem vazar conteudo.
- Audit log via `asyncio.to_thread()` para nao bloquear event loop. Falha no audit NAO quebra fluxo principal.
- Rate limit Redis: chave `<provider>:ratelimit:{session_id}` TTL 60s.
- request_hash usa SHA-256 do payload SCRUBBED (LGPD: hash NAO pode ser reversivel a partir do bruto).

Reutilizavel para: openclaw_gpt.py, anthropic_claude.py, openai_direct.py no mesmo diretorio `app/integrations/`. Cada um deve herdar o mesmo padrao de ChatResponse + ChatError.

Licao aprendida: auditoria LGPD foi 8 itens = 2 criticos + 3 altos + 3 medios. Shift-the-burden ("caller faz scrub") eh falha sistematica — TODA integracao LLM precisa de scrubbing interno.
