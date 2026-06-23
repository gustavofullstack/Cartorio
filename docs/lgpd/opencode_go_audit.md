# Auditoria LGPD — Integração OpenCode-Go / MiniMax

> **Auditoria realizada pelo Rein `cartorio-lgpd`** em 23/06/2026 às 13:52 BRT.
> **STATUS:** 🔴 **BLOQUEIO ATIVO** — código aceito mas **NÃO CONFORME** LGPD. Ver §7.

**Auditor:** Rein `cartorio-lgpd` (sessão `mvs_f7a29511daec40b7995718801be1a2c5`)
**Data:** 23/06/2026
**Versão RIPD:** 1.2 (Tratamento 7)
**Arquivo auditado:** `backend/app/integrations/opencode_go.py` (250 linhas, criado em 23/06/2026 13:51)

---

## 1. Escopo da auditoria

Validar que toda chamada ao sub-processor **OpenCode-Go / MiniMax** (provider configurado em `.harness/reins/*/opencode/opencode.json` como `minimax`, baseURL `https://agent.minimax.io/mavis/api/v1/llm/v1`) **não exponha dados pessoais brutos** (LGPD art. 46 + art. 50).

> **Observação:** O módulo auditado diz usar `deepseek-v4-flash` (linha 6 do docstring), enquanto o provider configurado em `opencode.json` referencia MiniMax-M2.7/M3. **Inconsistência** que precisa ser resolvida (ver §8).

---

## 2. Veredito consolidado

| Item | Status | Severidade |
|------|--------|------------|
| Bearer auth via header (não URL) | ✅ OK | — |
| Timeout 30s | ✅ OK | — |
| Não loga payload bruto | ✅ OK | — |
| `raw=None` por padrão | ✅ OK | — |
| Erros tipados sem leak | ✅ OK | — |
| **PII scrubbing interno (defense-in-depth)** | ❌ **AUSENTE** | **CRÍTICO** |
| **Chamada a `pii.scrub()` ou `pii.hash_pii()`** | ❌ **AUSENTE** | **CRÍTICO** |
| **Audit log (LGPD art. 37)** | ❌ **AUSENTE** | **ALTO** |
| **Consent gate (`consent.granted=true`)** | ❌ **AUSENTE** | **ALTO** |
| **Fallback para LiteLLM** | ❌ **AUSENTE** | **MÉDIO** |
| **Rate limit por sessão** | ❌ **AUSENTE** | **MÉDIO** |
| **Teste de regressão sem PII bruto** | ❌ **AUSENTE** | **ALTO** |
| **Consistência modelo (deepseek vs MiniMax)** | ❌ **DIVERGENTE** | **MÉDIO** |
| **DPA com MiniMax assinado** | ❌ **PENDENTE** | **CRÍTICO** |

**Veredito final:** 🔴 **NÃO AUTORIZADO MERGE** até correção de TODOS os itens CRÍTICOS e ALTO.

---

## 3. O que está BOM (defense-in-depth existente)

- ✅ **Bearer auth no header**, não em query string (linha 148) — token não vai para log de proxy/HTTPS
- ✅ **Timeout 30s** (linha 100) — evita dangling request com dado em memória
- ✅ **Não loga payload bruto** — nenhum `print()`, `logger.debug()`, `logger.info()` com `messages` ou `payload`
- ✅ **`raw=None` por padrão** (linha 219) — comentário explícito "NAO retornar raw por padrao (LGPD: response pode ter PII eco)"
- ✅ **Erros tipados** (`ChatErrorKind.*`) sem vazar conteúdo da response — `body_text[:500]` é truncado
- ✅ **Validação de config** antes da chamada (api_key, base_url, messages não vazias)
- ✅ **Docstring na função `chat()`** explicitamente diz "Toda saida DEVE passar pelo PII scrubber antes de chegar aqui" (linha 121) — boa intenção, mas **não basta**, precisa ser aplicado internamente

---

## 4. O que está FALTANDO (bloqueios)

### 4.1. 🔴 CRÍTICO — PII scrubbing interno ausente

O módulo aceita `messages: list[dict[str, str]]` e envia **diretamente** sem chamar `pii.scrub()` (de `backend/app/services/pii.py`). Isso é **shift the burden** — se o caller esquecer (e vai esquecer, em algum momento), LGPD art. 46 (medidas de segurança) é violada.

**Correção exigida:**
```python
from app.services.pii import scrub

async def chat(messages, *, model, api_key, base_url, temperature=0.2, timeout_seconds=30.0):
    # ... validação ...
    
    # LGPD art. 46 — PII scrubbing ANTES de enviar (defense-in-depth)
    scrubbed_messages = []
    for msg in messages:
        result = scrub(msg.get("content", ""))
        scrubbed_messages.append({
            "role": msg["role"],
            "content": result.text,  # scrubbed
        })
        if result.redaction_count > 0:
            # log estruturado para audit
            audit_logger.info(
                "pii_redacted",
                role=msg["role"],
                findings=result.findings,
                total=result.redaction_count,
            )
    
    payload = {
        "model": model,
        "messages": scrubbed_messages,  # SEMPRE scrubbed
        "temperature": temperature,
    }
    # ... resto ...
```

### 4.2. 🔴 CRÍTICO — DPA com Mini/OpenCode não assinado

O RIPD v1.2 Tratamento 7 lista isso como **BLOQUEIO ATIVO**. Sem DPA, ambiente é **STAGING ONLY**. Sem isso, **PROIBIDO** enviar dado real (mesmo anonimizado) — `deepseek-v4-flash` e MiniMax podem usar input para treinar modelo conforme termos padrão.

**Ação:** Gustavo + DPO fechar DPA. Armazenar em `docs/lgpd/dpa_minimax.pdf`. Status atual: **NÃO EXISTE**.

### 4.3. 🟠 ALTO — Audit log ausente (LGPD art. 37)

Toda chamada a OpenCode-Go **DEVE** ser registrada em `audit_log` (imutável, hash chain) com:
- `actor_id` (cliente ou operador)
- `request_hash` (SHA-256 do payload enviado)
- `response_hash` (SHA-256 do payload recebido)
- `model` (`deepseek-v4-flash` ou similar)
- `tokens_in`, `tokens_out`
- `latency_ms`
- `timestamp`
- `consent_granted` (boolean)
- `pii_redacted_count` (quantos campos foram scrubbed)

**Código atual NÃO chama** `AuditService.log()` em nenhum momento. **Bloqueio.**

### 4.4. 🟠 ALTO — Consent gate ausente

Antes de chamar OpenCode-Go, o módulo **DEVE** verificar `consent.granted=true` para o cliente. Caso contrário, viola LGPD art. 7º I (consentimento). Atualmente, função recebe `messages` direto — caller precisa passar contexto de consent.

**Correção:** parâmetro `consent_token: str` na função `chat()`, validado contra `consent_log` no Supabase antes de enviar.

### 4.5. 🟠 ALTO — Teste de regressão ausente

Não há `tests/integration/test_opencode_go_no_pii.py` no repo (verificado por `glob`). Sem teste que falha se payload bruto chegar, qualquer refactor futuro pode regredir.

**Teste exigido:**
```python
async def test_opencode_go_does_not_send_raw_cpf(monkeypatch):
    """Garante que CPF bruto no input NAO chega ao provider."""
    captured_payloads = []
    
    async def mock_post(self, url, **kwargs):
        captured_payloads.append(kwargs.get("json", {}))
        return MockResponse(...)
    
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    
    messages = [{"role": "user", "content": "Meu CPF e 123.456.789-09"}]
    await chat(messages, model="deepseek-v4-flash", api_key="test", base_url="http://test")
    
    sent_text = json.dumps(captured_payloads[0])
    assert "123.456.789-09" not in sent_text  # CPF foi scrubbed
    assert "[CPF_REDACTED]" in sent_text
```

### 4.6. 🟡 MÉDIO — Fallback LiteLLM ausente

Se OpenCode-Go falhar (timeout, 5xx, network), o sistema **deve** ter fallback para LiteLLM (OpenAI/Anthropic) com **mesmo scrubbing**. Atualmente, qualquer falha → `ChatError` → caller decide. Sem fallback, o chatbot fica fora do ar durante incidentes do OpenCode.

**Ação:** implementar `chat_with_fallback()` que tenta OpenCode-Go primeiro, depois LiteLLM.

### 4.7. 🟡 MÉDIO — Rate limit por sessão ausente

Sem rate limit, um atacante pode esgotar a cota do provider e inflar custo. Sugestão: 60 chamadas/min/sessão.

### 4.8. 🟡 MÉDIO — Inconsistência modelo (deepseek vs MiniMax)

O docstring do módulo diz `deepseek-v4-flash` (linha 6) mas o `opencode.json` configura MiniMax-M2.7/M3 como `whitelist`. **Qual é o modelo real?** Se for `deepseek-v4-flash`, o RIPD v1.2 está errado. Se for MiniMax, o código está errado.

**Ação:** alinhar — `deepseek-v4-flash` se for real, atualizar RIPD. Caso contrário, mudar código para MiniMax.

---

## 5. Dados que **PODEM** ser enviados (campo permitido)

| Dado | Formato | Por quê |
|------|---------|---------|
| Texto livre da mensagem do cliente | PII-scrubbed (CPF/RG/CNPJ/telefone/email/cartão/CEP/PIS/título/placa/data mascarados) | Necessário para o LLM raciocinar |
| Intenção classificada | `"consulta_emolumento"`, `"criar_protocolo"`, etc. | Necessário para roteamento |
| Contexto da conversa (resumido) | PII-scrubbed | Necessário para continuidade |
| Hash do cliente (segue o dado pelo sistema) | `pii.hash_pii(cliente.cpf, salt)` | Permite correlacionar logs sem expor CPF |
| Idioma detectado | `"pt-BR"` | Necessário para resposta |
| Timestamp aproximado | granularidade hora, não segundo | Contexto temporal |

## 6. Dados que **NUNCA** podem ser enviados (campo-branco/negativo)

| Dado | Motivo | Sanção |
|------|--------|--------|
| **CPF bruto** | Identifica pessoa (LGPD art. 5º I); basta hash irreversível | Bloqueio de merge + remoção do trecho |
| **RG bruto** | Mesmo | Bloqueio de merge |
| **CNPJ bruto** | Mesmo | Bloqueio de merge |
| **Telefone bruto** | Mesmo | Bloqueio de merge |
| **Email bruto** | Mesmo | Bloqueio de merge |
| **Endereço residencial** | Dado pessoal + alto risco de re-identificação | Bloqueio de merge |
| **Nome completo** | Identifica pessoa | Substituir por primeiro nome ou token genérico `[NOME]` |
| **Data de nascimento** | Identifica pessoa | Substituir por `[DATA_NASC]` ou faixa etária |
| **Número de protocolo** | Não é pessoal, mas vinculável — manter apenas se necessário para LLM referenciar | Avaliar caso a caso |
| **Conteúdo de documento jurídico** (escritura, procuração) | Contém múltiplos PII | Nunca enviar o documento inteiro; só resumo scrubbed |
| **Imagem / áudio bruto do cliente** | Pode conter rosto, voz (LGPD art. 5º II — dado biométrico/sensível) | Nunca enviar — só descrição textual scrubbed |

---

## 7. Decisão do auditor

🚫 **BLOQUEIO ATIVO — MERGE NÃO AUTORIZADO**

`cartorio-dev` deve:
1. Implementar PII scrubbing interno em `chat()` (chamar `pii.scrub()` em cada `message["content"]`)
2. Adicionar audit log via `AuditService.log()` com hash do payload
3. Adicionar consent gate (parâmetro `consent_token` validado contra Supabase)
4. Criar `tests/integration/test_opencode_go_no_pii.py` com mock de httpx
5. Implementar fallback `chat_with_fallback()` para LiteLLM
6. Resolver inconsistência de modelo (deepseek vs MiniMax)
7. Aguardar DPA com MiniMax assinado por Gustavo + DPO

Após correções, abrir novo PR e solicitar re-review.

---

## 8. Inconsistência de modelo — exige alinhamento

| Fonte | Modelo declarado |
|-------|-----------------|
| `backend/app/integrations/opencode_go.py:6` (docstring) | `deepseek-v4-flash` |
| `.harness/reins/*/opencode/opencode.json` (provider config) | MiniMax-M2.7 / MiniMax-M2.7-highspeed / MiniMax-M3 |
| `docs/ripd.md` v1.2 (Tratamento 7) | MiniMax-M2.7 / MiniMax-M3 |

**Ação:** confirmar com `cartorio-dev` qual é o modelo real. Se for MiniMax, atualizar docstring. Se for deepseek, atualizar `opencode.json` e RIPD.

---

## 9. Histórico

| Versão | Data | Mudança | Autor |
|--------|------|---------|-------|
| 0.1 (template) | 23/06/2026 13:49 | Template preparado, aguardando código de `cartorio-dev` | Rein `cartorio-lgpd` |
| 1.0 (auditoria) | 23/06/2026 13:53 | Auditoria concluída — 8 blockers identificados (2 críticos, 3 altos, 3 médios) | Rein `cartorio-lgpd` (sessão `mvs_f7a29511daec40b7995718801be1a2c5`) |

Modified by Gustavo Almeida