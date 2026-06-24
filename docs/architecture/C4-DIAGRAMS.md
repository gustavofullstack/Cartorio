# C4 Architecture - Cartorio Chatbot

> **Diagramas C4 (Context, Container, Component, Code) do sistema.**
> Versao 1.0 (2026-06-24)
> Formato: Mermaid (renderiza no GitHub, GitLab, VSCode).
> Ref: https://c4model.com

---

## N1 - System Context

Visao de **40.000 pes**. Mostra o sistema como 1 caixa e seus usuarios + sistemas externos.

```mermaid
graph TB
    Cliente["Cliente do Cartorio<br/>(cidadao)"]
    Escrevente["Escrevente / Tabeliao"]
    DPO["DPO (Encarregado de Dados)"]
    ANPD["ANPD<br/>(regulador)"]
    Cartorio["Sistema Cartorio Chatbot<br/>(este projeto)"]
    WhatsApp["WhatsApp Business"]
    Telegram["Telegram"]
    LGPD["LGPD / Lei 13.709/2018"]
    OpenAI["OpenAI / Anthropic<br/>(fallback LLM)"]
    DeepSeek["Opencode-Go / DeepSeek<br/>(LLM low-cost)"]

    Cliente -->|mensagens| Cartorio
    Escrevente -->|gerencia| Cartorio
    DPO -->|auditoria| Cartorio
    Cartorio -->|notificacoes| WhatsApp
    Cartorio -->|notificacoes| Telegram
    Cartorio -.->|transferencia internacional| DeepSeek
    Cartorio -.->|fallback| OpenAI
    Cartorio -->|reporta incidentes| ANPD
    Cartorio -.->|compliance| LGPD
```

---

## N2 - Container

Visao de **10.000 pes**. Mostra os **7 containers** do sistema.

```mermaid
graph TB
    Cliente["Cliente"]
    Evolution["Evolution API<br/>(WhatsApp gateway)"]
    TelegramBot["Telegram Bot API"]
    API["API Backend<br/>(FastAPI + Python)<br/>:8000"]
    N8N["N8N<br/>(workflow engine)<br/>:5678"]
    OpenClaw["OpenClaw Gateway<br/>(LLM routing)<br/>:18790"]
    Chatwoot["Chatwoot<br/>(CRM + Agent Bot)<br/>:3000"]
    Supabase["Supabase<br/>(Postgres + Storage + Auth)"]
    Redis["Redis<br/>(cache + rate limit + bus)<br/>:6379"]
    SupabaseKong["Supabase Kong<br/>(API gateway)<br/>:8000"]
    OpencodeGo["Opencode-Go<br/>(LLM DeepSeek-v4)<br/>[externo]"]

    Cliente -->|WhatsApp| Evolution
    Cliente -->|Telegram| TelegramBot
    Evolution -->|webhook| API
    TelegramBot -->|webhook| API
    API -->|query/insert| SupabaseKong
    API -->|cache/bus| Redis
    API -->|dispara workflow| N8N
    N8N -->|envia msg| Evolution
    N8N -->|envia msg| TelegramBot
    N8N -->|atualiza conversa| Chatwoot
    N8N -->|chama LLM| OpenClaw
    OpenClaw -->|LLM call| OpencodeGo
    API -->|chat (HITL)| OpenClaw
    Chatwoot -->|atendente humano| Cliente
    SupabaseKong --> Supabase
```

---

## N3 - Component (API Backend)

Visao de **1.000 pes**. Mostra os **componentes principais** do container API.

```mermaid
graph TB
    subgraph API["API Backend (FastAPI)"]
        Router["Router<br/>(api/v1/router.py)<br/>50+ endpoints"]
        WebhookEv["/webhook/evolution<br/>(evolution_ingest)"]
        WebhookCw["/webhook/chatwoot<br/>(chatwoot_handoff)"]
        Conversa["ConversaService<br/>(mensagens + intencao)"]
        Protocolo["ProtocoloService<br/>(criar + consultar)"]
        Emolumento["EmolumentoService<br/>(calcular valor)"]
        Audit["AuditService<br/>(hash chain + HMAC)"]
        PII["PIIService<br/>(scrubber 3 camadas)"]
        LGPD["LGPDService<br/>(direito esquecimento)"]
        Metrics["MetricsService<br/>(Prometheus)"]
        RateLimit["RateLimitMiddleware<br/>(DDoS + tier)"]
        Health["Health endpoints<br/>(/health/radar)"]
    end

    Router --> RateLimit
    Router --> WebhookEv
    Router --> WebhookCw
    Router --> Conversa
    Router --> Protocolo
    Router --> Emolumento
    Router --> Health
    Conversa --> PII
    Conversa --> Audit
    Conversa --> LGPD
    Protocolo --> Audit
    Emolumento --> Audit
    WebhookEv --> Conversa
    WebhookCw --> Conversa
    Metrics --> Audit
```

---

## Fluxo de dados end-to-end (N2 + sequencia)

Sequencia de 1 mensagem WhatsApp do cliente ate resposta:

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant Evo as Evolution API
    participant API as API Backend
    participant PII as PII Scrubber
    participant Audit as Audit Service
    participant LLM as Opencode-Go
    participant Chat as Chatwoot
    participant DB as Supabase

    C->>Evo: "Quero uma certidao, meu CPF 123.456.789-09"
    Evo->>API: POST /webhook/evolution (webhook)
    API->>PII: scrub("meu CPF 123...")
    PII-->>API: "meu CPF [CPF_REDACTED]"
    API->>Audit: log(message_received, request_id, ip)
    Audit->>DB: INSERT audit_log
    API->>LLM: chat(messages=[scrubbed])
    LLM-->>API: "Para emitir, preciso do RG"
    API->>PII: scrub(response)
    PII-->>API: response (sem PII)
    API->>Audit: log(message_sent)
    API->>Chat: pausar agente (HITL)
    API-->>Evo: 200 OK + reply
    Evo-->>C: "Para emitir, preciso do RG"
```

---

## Como ler este documento

- **N1 (Context)**: para stakeholders nao-tecnicos, gerentes, ANPD
- **N2 (Container)**: para devs novos, onboarding, decisao de stack
- **N3 (Component)**: para devs que vao mexer no codigo
- **Fluxo**: para entender LGPD, troubleshooting, code review

## Referencias

- [C4 model](https://c4model.com) - Simon Brown
- [LGPD art. 38](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) - RIPD
- `docs/ARCHITECTURE.md` - visao textual complementar
- `docs/DATA_FLOW.md` - fluxo de PII detalhado
- `docs/ONBOARDING.md` - primeiros passos

Modified by ZCode/Mavis - 2026-06-24
