# Sequence Diagram - PII Flow end-to-end

> **Diagrama de sequencia mostrando cada hop de dados PII pelo sistema.**
> Renderiza em GitHub/GitLab/VSCode (Mermaid).
> Ref: `docs/DATA_FLOW.md` (visao geral) + `docs/architecture/C4-DIAGRAMS.md` (visao de container)

## Fluxo: Cliente manda WhatsApp com CPF ate receber resposta

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente WhatsApp
    participant Evo as Evolution API
    participant API as API Backend
    participant PII1 as PII Scrubber Camada 1
    participant Bus as Redis Bus
    participant LLM as OpenClaw Agent
    participant PII2 as PII Scrubber Camada 2
    participant OC as Opencode-Go (DeepSeek)
    participant PII3 as PII Scrubber Camada 3
    participant Audit as Audit Service
    participant DB as Supabase

    Note over C,DB: T0: Cliente manda WhatsApp com CPF

    C->>+Evo: "Quero certidao, meu CPF 123.456.789-09"
    Evo->>Evo: Sanitiza payload (formato Baileys)

    Note over Evo,API: T+0.1s: Evolution faz POST no webhook

    Evo->>+API: POST /api/v1/webhook/evolution
    API->>API: RequestContextMiddleware (correlation_id)

    Note over API,PII1: Camada 1: Scrub ANTES de tudo

    API->>+PII1: scrub(message)
    PII1-->>-API: "[CPF_REDACTED] Quero certidao, meu CPF"

    Note over API,Audit: LGPD art. 37: registrar operacao

    API->>+Audit: log(message_received, correlation_id, ip, user_agent)
    Audit->>+DB: INSERT audit_log (hash chain)
    DB-->>-Audit: OK (id, hash_chain_position)
    Audit-->>-API: audit_id

    Note over API,LLM: HITL nivel 1: se confidence >= 0.85, bot responde

    API->>+LLM: chat(messages=[scrubbed], consent_granted)
    LLM->>+PII2: scrub novamente (defense in depth)
    PII2-->>-LLM: texto (ja scrubbed)
    LLM->>+OC: POST chat/completions (deepseek-v4-flash)
    OC-->>-LLM: response "Para emitir, preciso do RG"
    LLM->>+PII3: scrub(response) (camada 3)
    PII3-->>-LLM: response (sem PII)

    Note over LLM,Audit: Registrar RESPOSTA do LLM

    LLM->>Audit: log(message_sent, correlation_id, response_size)
    Audit->>DB: INSERT audit_log (append)
    DB-->>Audit: OK

    LLM-->>-API: response

    Note over API,Evo: T+1.2s: API envia resposta via Evolution

    API->>+Evo: POST /message/sendText/{instance}
    Evo-->>-API: 200 OK (message_id)
    Evo->>-C: "Para emitir, preciso do RG"

    Note over C,DB: T+1.5s: Cliente recebe resposta
```

## Detalhes por etapa

| # | Etapa | Latencia | LGPD | Onde no codigo |
|---|---|---|---|---|
| 1 | Cliente -> Evolution | ~0.5s (network) | - | WhatsApp Meta |
| 2 | Evolution sanitiza | ~10ms | - | Evolution internals |
| 3 | Evolution -> API webhook | ~50ms | - | webhook |
| 4 | Middleware context | ~1ms | - | `app/middleware/request_context.py` |
| 5 | PII scrub camada 1 | **0.021ms p99** | art. 6 VIII | `app/services/pii.py::scrub` |
| 6 | Audit log INSERT | ~5ms | art. 37 | `app/services/audit.py::log` |
| 7 | LLM chamada (OpenClaw) | ~5ms (roteamento) | - | `app/integrations/opencode_go.py` |
| 8 | PII scrub camada 2 | **0.021ms p99** | defense in depth | mesma funcao |
| 9 | Opencode-Go LLM | **~800ms p50** | - | https://api.2notasudi.com.br |
| 10 | PII scrub camada 3 | **0.021ms p99** | art. 6 VIII | mesma funcao |
| 11 | Audit log INSERT (2) | ~5ms | art. 37 | `app/services/audit.py` |
| 12 | Evolution send | ~100ms | - | Evolution API |
| 13 | Evolution -> Cliente | ~0.5s | - | WhatsApp Meta |
| **TOTAL** | | **~2.0s** | | |

## Fluxo alternativo: HITL escalado (confidence < 0.85)

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant API as API Backend
    participant LLM as OpenClaw
    participant Chat as Chatwoot
    participant H as Humano (escrevente)

    C->>API: mensagem
    API->>LLM: chat(confidence_score)
    LLM-->>API: response (confidence=0.6)
    API->>Chat: POST /conversations/{id}/messages (handoff)
    Chat->>H: notifica escrevente
    H->>Chat: responde
    Chat->>API: webhook conversation_updated
    API->>C: resposta do humano (via Evolution)
```

## Fluxo de auditoria LGPD (consulta)

```mermaid
sequenceDiagram
    autonumber
    actor DPO as DPO Gustavo
    participant API as API Backend
    participant Audit as Audit Service
    participant DB as Supabase

    DPO->>API: GET /api/v1/audit/verify
    API->>Audit: verify_hash_chain()
    Audit->>DB: SELECT * FROM audit_log ORDER BY id
    DB-->>Audit: 1234 entries
    Audit->>Audit: check hash[i] == sha256(prev_hash + data[i])
    Audit-->>API: {valid: true, total: 1234}
    API-->>DPO: 200 OK {valid, total_entries, ...}

    Note over DPO,DB: Se valid: false, broken_at_id indica onde<br/>a cadeia foi corrompida
```

## Fluxo de direito ao esquecimento (LGPD art. 18 VI)

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant API as API Backend
    participant Chat as Chatwoot
    participant DB as Supabase
    participant Cron as N8N workflow (30d)

    C->>Chat: "Quero esquecer meu dado"
    Chat->>API: webhook (solicitacao)
    API->>API: validar identidade (canal autenticado)
    API->>DB: UPDATE cliente SET motivo_encerramento='REVOGACAO_CONSENTIMENTO', data_encerramento=NOW()
    API->>API: audit_log LGPD_BLOCKED + DELETE_PENDING
    API-->>Chat: 200 OK (confirma ao cliente)
    Chat-->>C: "OK, seus dados serao apagados em 30 dias (LGPD)"

    Note over Cron,DB: T+30d: job de retencao apaga fisicamente

    Cron->>DB: DELETE FROM clientes WHERE motivo_encerramento='REVOGACAO' AND data_encerramento < NOW() - INTERVAL '30 days'
    DB-->>Cron: N rows deleted
    Cron->>API: log(retention_purge, count)
```

## Onde cada arquivo entra

| Componente | Arquivo | Cobre |
|---|---|---|
| WhatsApp webhook | `backend/app/api/v1/router.py::post_webhook_evolution` | Etapas 1-4 |
| PII scrub | `backend/app/services/pii.py::scrub` | Etapas 5, 8, 10 |
| Audit log | `backend/app/services/audit.py::log` | Etapas 6, 11 |
| LLM call | `backend/app/integrations/opencode_go.py::chat` | Etapas 7-11 |
| Evolution send | `backend/app/integrations/evolution_*` | Etapa 12 |
| HITL handoff | `backend/app/services/chatwoot_handoff.py` | Fluxo alternativo |
| Direito esquecimento | `backend/app/services/lgpd/direito_esquecimento.py` | Fluxo LGPD |
| Audit verify | `backend/app/services/audit.py::verify_hash_chain` | Fluxo auditoria |

## Referencias

- LGPD art. 6 VIII (prevencao): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- LGPD art. 37 (registro): mesma lei
- LGPD art. 18 VI (esquecimento): mesma lei
- Bench PII: `tests/test_pii_bench.py` (p99 = 0.021ms)
- Visao geral: `docs/DATA_FLOW.md`
- C4 diagrams: `docs/architecture/C4-DIAGRAMS.md`

Modified by ZCode/Mavis - 2026-06-24
