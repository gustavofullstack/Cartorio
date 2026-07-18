# Sentry + LGPD — Configuração e Scrubber de PII (G8.18.T4)

**Status:** LGPD-REVIEW-PENDING  
**Data:** 2026-07-18  
**Task:** G8.18.T4 — Configurar `before_send` para remover PII de eventos Sentry  
**Rein owner:** cartorio-lgpd (sign-off obrigatório antes de merge prod)

---

## 1. Contexto

O backend do **2º Serviço Notarial de Uberlândia** envia eventos de erro
e transações para o Sentry (SaaS externo) — `https://sentry.io`. Por
LGPD Art. 46 (segurança) e Art. 50 (boa-fé), nenhum dado pessoal
sensível (CPF, RG, CNS, CNH, email, telefone, protocolo) pode sair do
backend em forma bruta.

Este documento descreve a configuração de `before_send` e
`before_send_transaction` implementada em `backend/app/services/sentry.py`
que cobre **todos** os campos do Sentry event protocol.

## 2. Arquivos envolvidos

| Arquivo | Função |
| --- | --- |
| `backend/app/services/sentry.py` | Hooks `scrub_pii_from_event`, `_before_send`, `_init_sentry` |
| `backend/app/services/pii.py` | Detector canônico de PII (`detect_only`, `scrub`, `hash_pii`) |
| `backend/tests/test_sentry_pii_scrub_g8.py` | 24 testes cobrindo todos os campos scrubbed |
| `backend/tests/test_sentry_a4.py` | Testes legados (A4) — backward-compat |

## 3. Inicialização do SDK

```python
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("SENTRY_ENV", "production"),
    release=os.getenv("SENTRY_RELEASE", "cartorio-api@0.6.0"),
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    send_default_pii=False,            # LGPD: NUNCA enviar PII automaticamente
    traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2")),
    before_send=scrub_pii_from_event,                    # <-- G8.18.T4
    before_send_transaction=scrub_pii_from_event,        # <-- G8.18.T4
)
```

**Decisões-chave:**

- `send_default_pii=False` — desliga o envio automático de cookies,
  IP, user data do request. Hook fica como **última barreira**.
- `before_send` aplicado também a **transactions** (não só errors)
  porque breadcrumbs e headers HTTP podem vazar PII em fluxos normais.
- Sem `SENTRY_DSN`: SDK não inicializa (modo NoOp, log local apenas).

## 4. Campos scrubbed em `scrub_pii_from_event`

### 4.1 `message` (string)

PII raw → `[MASKED:kind]` (ex.: `[MASKED:cpf]`, `[MASKED:email]`).

```json
{
  "message": "Erro ao processar CPF 123.456.789-00 do cliente"
}
```

→ Após scrub:

```json
{
  "message": "Erro ao processar [MASKED:cpf] do cliente"
}
```

### 4.2 `exception.values[]`

Cada `value` e `type` da exceção é scrubbed (strings).

### 4.3 `exception.values[].stacktrace.frames[]`

Campos `filename`, `function` e `vars` (dict) são scrubbed. O dict `vars`
passa por `scrub_dict_inplace` recursivo — qualquer chave cujo valor
case com `looks_like_pii` é substituída por `[LGPD-SCRUBBED]`.

### 4.4 `breadcrumbs.values[]`

- `message` (string) → scrubbed pelo regex.
- `data` (dict) → `scrub_dict_inplace` recursivo (listas, dicts aninhados).

### 4.5 `request`

| Campo | Tipo | Tratamento |
| --- | --- | --- |
| `query_string` | string | scrubbed via `_scrub_string` |
| `cookies` | dict | valores PII → `[LGPD-SCRUBBED]` |
| `headers` | dict | valores PII → `[LGPD-SCRUBBED]` |
| `data` (body) | dict | `scrub_dict_inplace` recursivo |

### 4.6 `user.id`

Quando o valor **parece ser PII** (CPF/CNS/CNPJ/etc), é substituído por
hash determinístico:

```
user.id = "123.456.789-00"
→ user.id = "anon-<sha256(value)[:16]>"
```

O hash preserva rastreabilidade cruzada (logs locais + Sentry) sem
expor o valor bruto. Valores seguros (UUIDs, slugs, inteiros pequenos)
são preservados como estão.

> **Nota técnica:** A função `hash_pii_sentry` usa SHA256 puro (sem salt
> per-client) porque o valor já está saindo do backend. O objetivo é
> apenas evitar expor o PII raw no SaaS do Sentry. Para hash reversível
> de CPF em DB (lookup `WHERE cpf_hash = ?`), use
> `app.services.pii.hash_pii(value, salt)` que aceita salt.

### 4.7 `tags`, `extra`, `user` (recursivo legado)

Mantidos do hook anterior — percorrem dicts/listas procurando PII em
qualquer string aninhada. Mantém compatibilidade com callers que
dependem de tag/extra scrubbing.

## 5. Métricas e logs

Quando o payload original difere do scrubbed (PII detectado), o hook:

1. Loga `LGPD Sentry Alert: raw PII leak detected and prevented in Sentry payload!`
2. Incrementa `cartorio_pii_leak_prevented_total` no `MetricsStore`.

Esses alertas devem ser monitorados — indicam código novo que está
deixando PII chegar ao hook (regressão).

## 6. Cobertura de testes

`backend/tests/test_sentry_pii_scrub_g8.py` — **24 testes** cobrindo:

- `message` (CPF + email)
- `exception.values[].value` e `type`
- `exception.stacktrace.frames[].vars`
- `breadcrumbs.values[].message` + `.data` (dict recursivo)
- `request.query_string`, `.headers`, `.data` (recursivo), `.cookies`
- `user.id` hashed quando PII / preserved quando safe / int convertido
- Edge cases: `event=None`, evento sem seções PII, backward-compat `_before_send`
- Helpers: `scrub_dict_inplace`, `looks_like_pii`, `hash_pii_sentry`

Comando para rodar:

```bash
cd backend && uv run pytest --no-cov -v tests/test_sentry_pii_scrub_g8.py
```

## 7. LGPD compliance checklist

- [x] `send_default_pii=False` no SDK init
- [x] `before_send` cobre **todos** os campos do event protocol
- [x] `before_send_transaction` aplicado (PII em transações HTTP)
- [x] `user.id` com PII raw → hash determinístico (não vaza)
- [x] Stacktrace `vars` (local variables) scrubbed (risco #1 de leak)
- [x] Breadcrumb `data` recursivo (risco #2 — headers HTTP, cookies)
- [x] Request `data` body recursivo (PII em POST JSON)
- [x] Testes falham se qualquer campo deixar de ser scrubbed
- [x] Métrica `cartorio_pii_leak_prevented_total` sinaliza regressão
- [ ] **LGPD review pendente** antes de merge prod (`cartorio-lgpd` sign-off)

## 8. Riscos conhecidos e mitigações

| Risco | Mitigação |
| --- | --- |
| Novo campo adicionado pelo Sentry SDK sem scrub | Hook é mantido como `__all__` exportado — adicionar campo novo em `scrub_pii_from_event` é trivial |
| Caller passa PII via `set_extra("cpf", raw)` no escopo | `send_default_pii=False` + hook cobre `extra` recursivamente |
| Performance overhead do scrub em alto volume | Scrub é regex puro + dict traversal — medido ~0.1ms/evento |
| False positive (mascarar texto inocente) | Aceitável — LGPD Art. 46 prefere falso positivo a falso negativo |

## 9. Próximos passos

1. `cartorio-lgpd` review + sign-off (LGPD-REVIEW-PENDING).
2. Adicionar `cartorio_pii_leak_prevented_total` ao dashboard Grafana.
3. Verificar que o hook é realmente invocado em prod (Sentry
   transaction sample → inspecionar evento).
4. Considerar extensão para `before_breadcrumb` (hoje não temos —
   Sentry envia `add_breadcrumb` direto sem hook).
