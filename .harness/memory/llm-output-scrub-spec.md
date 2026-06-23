# LGPD-015 — LLM Output Scrub Patch + Test Suite Spec

> Origin: mvs_3c841fe (cartorio-lgpd) → mvs_c2508947 (Pietra root)
> Captured: 2026-06-23 18:51 BRT
> Status: **BACKLOG** (aguarda jump queue / override HOLD decisão Gustavo 19:18 BRT)
> Closes: Blocker #10 + #13 + #14 (3 gaps de output scrub no cartório 2notasudi)

## Contexto

Toda chamada LLM tem 2 boundaries de PII scrubbing:
- B1 INPUT: text → scrub() → LLM request [implementado em 6/6 chamadas]
- B2 OUTPUT: LLM response → ??? → caller [GAP em 3 sites]

Output echo é gap crônico. Docstrings dizem "caller DEVE scrubar" (shift-the-burden) — ninguém scrubba.

## Sites afetados

| Site | Arquivo | Linha | Risco | Blocker |
|------|---------|-------|-------|---------|
| A | backend/app/integrations/opencode_go.py | 390 | LGPD geral | #10 P0 |
| B | backend/app/api/v1/router.py | 553 | WhatsApp webhook + CNS art. 11 | #13 P0 |
| C | backend/app/api/v1/integrations.py | 190 | Smoke test interno | #14 P1 |

## Spec #1 — Patch mínimo scrub() no output

### Decisão de design (cartorio-dev escolhe)

**Opção 1 — wrapper novo** (semantica explicita boundary 2):
```python
def scrub_llm_output(content: str) -> ScrubResult:
    """Scrub especifico para output de LLM (defense-in-depth).
    Idempotente (se caller ja fez, no-op).
    """
```

**Opção 2 — reusar scrub() direto** (mais simples, sem helper novo):
```python
result = scrub(content)
```

Recomendação cartorio-lgpd: opção 2 (YAGNI, mesmo código). Pietra concorda.

### Aplicação nos 3 call sites

**SITE A — opencode_go.py:390**
```python
# ATUAL
content = choice['message']['content']

# PROPOSTO
raw_content = choice['message']['content']
result = scrub(raw_content)
content = result.text
output_pii_redacted_count = result.redaction_count  # NOVO campo em ChatResponse
```

**SITE B — router.py:553**
```python
# ATUAL
bot_response = llm_resp.content

# PROPOSTO
result = scrub(llm_resp.content)
bot_response = result.text
output_pii_redacted_count = result.redaction_count
```

**SITE C — integrations.py:190**
```python
# ATUAL
response=resp.content,

# PROPOSTO
_scrub_out = scrub(resp.content)
response=_scrub_out.text,
output_pii_redacted_count=_scrub_out.redaction_count,
```

### Contrato (3 invariantes)

1. `scrub()` no output NUNCA quebra o fluxo principal — se falhar (impossível mas defense-in-depth), usar conteúdo original + `log.error` para forense.
2. `output_pii_redacted_count > 0` DEVE disparar audit log separado (`action='llm.output_scrubbed'`) com payload completo (sender, count, output_length). Pattern espelha existing audit de input.
3. `output_pii_redacted_count` DEVE aparecer em TODA response ao cliente/operador. Não pode ser silenciado.

### Adicionar campo em ChatResponse (opencode_go.py:76-99)

```python
class ChatResponse(BaseModel):
    content: str
    # ... existing fields ...
    output_pii_redacted_count: int = 0  # NOVO
```

## Spec #2 — Suite de testes (pytest)

### Arquivo NOVO: `backend/tests/integration/test_llm_output_scrub.py`

```python
# Suite A: opencode_go.py boundary
async def test_opencode_go_scrubs_pii_in_output():
    '''LLM ecoa CPF no output. Assert que ChatResponse.content NAO contem CPF.'''
    with mock_httpx_response(content='Seu CPF e 123.456.789-09'):
        resp = await chat(messages=[{'role':'user','content':'Qual meu CPF?'}],
                          consent_granted=True, ...)
    assert '123.456.789-09' not in resp.content
    assert resp.output_pii_redacted_count >= 1

async def test_opencode_go_scrubs_cns_in_output():
    '''LLM ecoa CNS (dado sensivel art. 11) no output. Assert redacted.'''
    with mock_httpx_response(content='Seu CNS e 1234 5678 9012 3456'):
        resp = await chat(...)
    assert '1234 5678 9012 3456' not in resp.content
    assert resp.output_pii_redacted_count >= 1

async def test_opencode_go_scrubs_cnh_in_output():
    with mock_httpx_response(content='CNH 123456789-01'):
        resp = await chat(...)
    assert '123456789-01' not in resp.content

async def test_opencode_go_output_clean_when_no_echo():
    with mock_httpx_response(content='Bom dia, em que posso ajudar?'):
        resp = await chat(...)
    assert resp.output_pii_redacted_count == 0
```

```python
# Suite B: router.py boundary (webhook WhatsApp)
def test_webhook_evolution_response_scrubs_llm_echo(client):
    '''Cliente envia mensagem, LLM ecoa CNS, response do webhook NAO contem CNS.'''
    payload = _make_evolution_payload('Ola')
    with mock_opencode_go_chat(content='Seu CNS e 1234 5678 9012 3456'):
        resp = client.post('/api/v1/webhook/evolution', json=payload)
    body_str = str(resp.json())
    assert '1234 5678 9012 3456' not in body_str, \
        f'CNS ECOADO PELO LLM VAZOU NO RESPONSE: {body_str[:500]}'

def test_webhook_evolution_response_scrubs_cpf_echo(client):
    with mock_opencode_go_chat(content='Seu CPF e 123.456.789-09'):
        resp = client.post('/api/v1/webhook/evolution', json=payload)
    assert '123.456.789-09' not in str(resp.json())
```

```python
# Suite C: integrations.py boundary (smoke test)
def test_opencode_test_endpoint_scrubs_output(client):
    payload = {'message': 'meu CNS e 1234 5678 9012 3456', 'consent_granted': True}
    with mock_opencode_go_chat(content='CNS detectado: 1234 5678 9012 3456'):
        resp = client.post('/integrations/opencode/test', json=payload)
    assert '1234 5678 9012 3456' not in str(resp.json())
```

```python
# Suite D: audit log do output scrub
def test_output_scrub_creates_audit_log(db_session):
    '''output_pii_redacted_count > 0 DEVE gravar audit log separado.'''
    # ... assert que AuditService.log(action='llm.output_scrubbed', ...)
    # ... foi chamado com payload contendo count + sender + length
```

```python
# Suite E: integracao CNS anchored (cobre gap P0.4)
def test_cns_anchored_scrubs_echo():
    '''CNS anchored regex pega CNS mesmo sem keyword (anchor contextual).'''
    from app.services.pii import detect_only
    text = 'CNS 123456789012345'  # sem keyword 'CNS'/'sus'/'saude'
    # SEM anchored: NAO detecta
    # COM anchored (proposto): detecta porque contexto
    assert 'cns' in detect_only(text)  # so passa apos implementar P0.4
```

### Arquivo MODIFICADO: `backend/tests/test_webhook_evolution_e2e.py`

Adicionar 1 test de Suite B (integração E2E do webhook).

## Checklist para cartorio-dev (ordem de execução)

```
[ ] Adicionar campo output_pii_redacted_count em ChatResponse (opencode_go.py:76-99)
[ ] Modificar SITE A (opencode_go.py:390) para scrub() no output
[ ] Modificar SITE B (router.py:553) para scrub() no output
[ ] Modificar SITE C (integrations.py:190) para scrub() no output
[ ] Adicionar test_llm_output_scrub.py (Suite A-E acima)
[ ] Adicionar 1 test em test_webhook_evolution_e2e.py (Suite B)
[ ] Adicionar audit log action='llm.output_scrubbed' quando output_pii_redacted_count > 0
[ ] Rodar pytest --cov — coverage gate 90% NAO pode baixar
[ ] Atualizar docs/ripd.md para refletir 3a camada (output scrub) implementada
[ ] Review cartorio-lgpd antes de merge v0.6.0
```

## Estimativa cartorio-lgpd

- 3 fixes + suite testes: ~2-3h
- Auditoria + merge: ~30min (cartorio-lgpd)
- **TOTAL: ~3h para fechar Blocker #10 + #13 + #14 de uma vez**

## Decisão de orquestração Pietra

- mvs_a3ed3f0b (cartorio-dev) em HOLD até 19:18 BRT (cron reviver-4.1 TTL 19:40)
- Quando Gustavo escolher (a) jump queue ou (b) override HOLD, eu mando o brief consolidado pra cartorio-dev
- Se (a) ou (b) não sair: HOLD até segunda ordem (cartorio-dev segue em 4.1 + 4.2 + 4.3 que já estão em master)
- cartorio-lgpd (mvs_3c841fe): standby 19:18+ pra review pós-fix

## Cross-project lesson (já salva em agent memory)

Ver MEMORY.md: "LLM output scrub gap pattern — Blocker #13 + #14"

## Refs

- `.harness/memory/LGPD-AUDIT-2026-06-23.md` (auditoria original)
- `.harness/TASKS.md` (LGPD-015 backlog item)
- `docs/ripd.md` (atualizar pós-merge)
- MEMORY.md do agent mavis (lesson reusável cross-project)
