
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

### Briefing vs evidencia: SEMPRE rodar pytest antes de agir (2026-06-23)
Type: anti-pattern

Cenario: root session me mandou briefing urgente "246 passed, 4 FAILED no master d030e9c" com lista de 4 testes (test_payload_com_pii_bloqueia_e_marca_pii_blocked, test_payload_extremo_50_pii_simultaneos, test_webhook_evolution_sem_pii, test_chat_with_fallback_delegates_to_opencode_go) e pediu plano de fix. O briefing parecia detalhado, com causa raiz e nivel de risco por falha. Parecia legitimo.

Quando rodei \`cd backend && .venv/bin/pytest tests/ --no-cov -q 2>&1 | tail -5\`:
- 263 passed, 2 skipped, 37 deselected, 0 failed
- Os 4 testes listados: 4/4 PASSED (rodei individual tambem)

Causa provavel: Gustavo (root) estava olhando pra state stale (output de console antigo, ou branch diferente). O briefing herdado propagou pra mim.

Regra:
1. **EVidencia > briefing.** Se o briefing diz "X failing" e meu pytest diz "X passing", o briefing esta errado. NAO inventar fix pra bug-fantasma — gastar quota em code que ja funciona eh a forma mais rapida de quebrar.
2. **Reportar a discrepancia com output literal.** Copia/cola do pytest no relatorio. Sem output proprio, sem acao.
3. **Sprint 3 #4.2 e #4.3 ja estao em master.** DELETE /cliente/{id} em app/api/v1/router.py:1273. Job retencao em app/jobs/retencao.py. Nao recriar o que existe — checar primeiro.
4. **Deselect ≠ fail.** "37 deselected" no output do pytest NAO significa 37 fails — sao testes com marker excluido (no caso, @pytest.mark.smoke filtrado por \`-m 'not smoke'\` no addopts). Saber a diferenca evita report falso.

Reutilizavel: toda vez que um briefing vier com "tem N fails", rodar \`pytest --no-cov -q 2>&1 | tail -5\` ANTES de planejar fix. Custo: 5s. Beneficio: nao queimar 60-90min em bug-fantasma.

### Briefing stale anti-pattern - 2o caso (2026-06-23 19:22 BRT)
Type: anti-pattern

Briefing do parent session (mvs_840ea91043b6447ba0d4d215927d6c46) dizia:
- master HEAD = 3b85746 (LGPD audit workflows)  <- ERRADO, real era 6d6d608
- /tmp/cartorio-build/ NAO EXISTE - T19 WS ja merged  <- VERDADE
- test_endpoint_registered_in_app PASSANDO (12/12)  <- VERDADE
- 9 FAILURES REAIS em tests/integration/test_llm_output_scrub.py  <- ERRADO

Realidade verificada:
- master HEAD = 6d6d608 (working tree CLEAN)
- test_llm_output_scrub.py: 14/14 PASSED em 0.57s
- pytest tests/ completo: 345 passed, 2 skipped, 37 deselected, 0 failed

A "feature" ja tinha sido entregue em 2 commits durante a janela do briefing:
- 60a715f "feat: implement output PII scrubbing for LLM responses and add IP address truncation to audit logs for LGPD compliance."
- 6d6d608 "feat: add output PII scrubbing tracking to integration models and propagate request context to OpenCode-Go, while updating RIPD documentation."

Confirmado: parent session estava olhando para state STALE (provavelmente copy-paste de briefing anterior, ou memoria de contexto desatualizada). O briefing 60a715f ja entrega exatamente o que foi pedido.

Licao:
1. Briefing pode estar 2-3 commits atras. SEMPRE rodar `git log master -3 --oneline` e `pytest tests/<file> --no-cov -q` ANTES de qualquer acao.
2. Working tree state pode mudar DURANTE a janela do briefing - parent pode ter commit feito enquanto eu lia. Re-verificar antes de reportar.
3. Quando briefing pedir "fix de 9 fails em X" e master tem commit "feat: implement X", o briefing esta obsoleto.
4. Reportar discrepancia com output literal do pytest e git log master. NUNCA inventar fix pra bug-fantasma.

Reforco da regra anterior: este e o 2o caso em <24h. Padrao recorrente, NAO eh excecao.

### Pydantic Settings singleton trap em testes (2026-06-23)
Type: anti-pattern

Contexto: test_cliente_historico.py (criado por mim/ZCode) tinha 5 fails, dos quais 4 eram "401 == 200" (esperava 200, recebia 401). Causa raiz: o test setava `os.environ.setdefault("CARTORIO_API_KEY", "test-key-12345")` mas `app/config.py` tem `settings = get_settings()` no module level. Esse singleton foi criado quando conftest.py carregou (ANTES do test file), e nesse momento CARTORIO_API_KEY NAO estava no env, entao `settings.cartorio_api_key = None`. O setdefault do test NAO recriava o singleton. `get_settings.cache_clear()` NAO ajuda — so afeta chamadas futuras de get_settings(), nao a variavel `settings` ja criada.

Sintoma: tests que dependem de env vars que afetam `settings` recebem 401/403 mesmo passando o header/credencial certa.

Fix correto: setar a env var em `tests/conftest.py` ANTES de `from app.config import get_settings`. O conftest carrega antes do test file, entao o singleton `settings` e criado com o valor correto. Outras opcoes: (a) `importlib.reload(app.config)` no test (hacky), (b) `pytest.MonkeyPatch.setattr(app.config.settings, "cartorio_api_key", ...)` (mais isolado mas verboso).

Reutilizavel: QUALQUER projeto FastAPI + Pydantic Settings v2 com `settings = get_settings()` no module level. Verificar SEMPRE antes de debugar "auth 401 misteriosos" em tests.

Licao: o conftest.py NAO e' so pra fixtures — e' tambem o unico lugar garantido de rodar antes do singleton ser criado. Trate conftest.py como bootstrap de env state.

### "Theater of compliance" - tests verde != compliance real (2026-06-23)
Type: anti-pattern

Contexto: cartorio-dev Sprint 1.7 — output LLM scrub foi shipped em 60a715f + 6d6d608. Tests 14/14 verde em test_llm_output_scrub.py. POREM o test docstring documenta LIMITACOES explicitamente:

  test_llm_output_scrub.py linhas 19-22:
  'Limites documentados (NAO escopo desta entrega):
   - CNH sem regex -> nao eh redacted (D3 backlog)
   - CNS sem regex -> nao eh redacted (D3 backlog)'

  Linhas 16-17:
  'correcoes virao em D3 CNS-anchored'

Realidade verificada:
- scrub() em app/services/pii.py NAO tem CNS nem CNH (grep vazio)
- output scrubber novo USA scrub() — portanto tambem nao pega CNS/CNH
- LGPD art. 11 (dado sensivel saude) violado na boundary 2 (output do LLM)
- Passa tests, falha na vida real = "theater of compliance"

Sintoma: pytest verde + docstring dizendo "NAO escopo desta entrega" + backlog itemizado (D3). Trio classico de "compliance fake".

Licao:
1. **Pytest verde NAO garante compliance.** Test docstring pode DOCUMENTAR gaps explicitos ("NAO escopo desta entrega"). Antes de fechar ticket LGPD, ler docstring E backlog.
2. **Procurar "TODO backlog" / "D3" / "NAO escopo" / "limitation" / "futura entrega"** em test docstrings. Saida de compliance theater quase sempre tem marker textual.
3. **Verificar regex no scrub() ANTES de assumir cobertura.** `grep -E "CNH|CNS" app/services/pii.py` deve retornar matches. Se vazio = gap real.
4. **Compliance gap != bug-fantasma.** Bug-fantasma eh "teste diz fail mas passa". Compliance gap eh "teste passa mas coverage eh intencionalmente incompleto e documentado". Ambos precisam ser reportados, mas o segundo NAO pode ser silenciado como "ja feito".

Acao recomendada:
- Antes de dar "LGPD-XXX done", SEMPRE: (a) ler test docstring, (b) grep regex do scrub(), (c) verificar backlog items referenciados, (d) confirmar com cartorio-lgpd se o gap esta aprovado formalmente.
- Se gap for ART. 11 (saude) ou ART. 7 (consentimento) → P0 imediato, NAO deferir.
- Documentar gaps em RIPD/MEMORY para que proxima sprint pegue.

Reutilizavel: qualquer projeto com pipeline LGPD/HIPAA/PCI onde tests tem docstring "limitation" ou backlog deferido. Buscar marcadores: "NAO escopo", "D<X> backlog", "limitation", "future work", "will be addressed in", "TODO backlog".
