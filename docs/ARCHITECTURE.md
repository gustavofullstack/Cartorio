# Arquitetura - Cartorio Chatbot

## Visao geral

```
┌────────────────────────────────────────────────────────────────────┐
│                       Cliente Final                                  │
│   (WhatsApp / Telegram / Web Widget / Email / Balcao)                │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│   OpenClaw Gateway (port 8080)                                       │
│   - Roteamento multi-canal                                           │
│   - Rate limiting por origem                                         │
│   - Normalizacao de payload                                          │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│   Evolution API (WhatsApp Business)                                  │
│   - Webhook in/out                                                   │
│   - QR code / sessao WhatsApp                                        │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│   n8n + n8n-runner (orquestrador visual)                            │
│   - Workflow: msg recebida → classifica → roteia                    │
│   - Integracao: Supabase, Evolution, LLM gateway                     │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│   FastAPI Backend (este repo, port 8000)                             │
│   ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│   │  PII Scrubber    │  │  Audit Service  │  │  Emolumento Svc  │  │
│   │  (regex + LLM)   │  │  (hash chain)   │  │  (regras estado) │  │
│   └──────────────────┘  └─────────────────┘  └──────────────────┘  │
│   ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│   │  Protocolo Svc   │  │  Documento Svc  │  │  Cliente Svc     │  │
│   │  (create/update) │  │  (upload/hash)  │  │  (LGPD consent)  │  │
│   └──────────────────┘  └─────────────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌─────────────┐  ┌─────────┐  ┌─────────────────┐
        │ Supabase    │  │ LiteLLM │  │  Audit Log      │
        │ (Postgres + │  │ Gateway │  │  (Postgres +    │
        │  Storage +  │  │ (Claude │  │   HMAC key +    │
        │  Auth)      │  │  Opus / │  │   hash chain)   │
        │             │  │  GPT)   │  │                 │
        └─────────────┘  └─────────┘  └─────────────────┘
```

## Decisoes arquiteturais criticas

### 1. Hash chain no audit log (NÃO WAL shipping, NÃO storage externo)

**Decisão**: append-only com SHA256(prev_hash + payload + timestamp) + HMAC.

**Por que**:
- Cartorio pode ser auditado por corregedoria, CNJ, ou tribunal
- Storage externo (S3 com Object Lock) eh caro + operacional
- Hash chain em Postgres normal eh verificado em milissegundos
- HMAC requer chave do servidor — quem edita DB sem chave nao consegue forjar

**Como verificar integridade**: `POST /api/v1/audit/verify` percorre cadeia, retorna `(ok, last_valid_position)`. Job diario cron roda e alerta se `ok=false`.

### 2. PII scrubbing em 3 camadas

| Camada | Quando | O que |
|--------|--------|-------|
| Input | Antes de logar conversa | mascara CPF/RG/email/etc, guarda hash + scrubbed |
| Pre-LLM | Antes de chamar Claude/GPT | garante zero PII puro pra API publica |
| Output | Antes de responder ao cliente | confirma que resposta nao vaza |

**Por que 3 camadas**: defesa em profundidade. LLM eh caixa-preta, nao podemos confiar que "vai lembrar de nao mencionar CPF". Hash de CPF eh deterministic com salt por cliente — permite `WHERE cpf_hash = ?` sem armazenar o valor.

### 3. Human-in-the-loop obrigatorio

Bot **NUNCA** toma decisao final em:
- Concessao de isencao
- Aplicacao de urgencia
- Validacao de documento juridico
- Emissao de certidao / escritura

Bot **PODE** tomar sozinho:
- Responder "horario de funcionamento"
- Calcular emolumento (mostrar valor)
- Consultar status de protocolo existente
- Esclarecer duvidas sobre documentacao necessaria

**Implementacao**: campo `handoff_to_human` em `conversa`. Quando intent detectado tem `confidence < 0.7`, automatic handoff pro escrevente via Telegram interno.

### 4. Tabela de emolumento snapshot (NÃO live)

Toda tabela usada eh **snapshotada no momento do calculo**, com `tabela_referencia` e `valido_ate`. Protocolo guarda:
- `valor_base` (na hora do calculo)
- `valor_total` (snapshot)
- `tabela_referencia` ("TABELA_2026_MG")

Carga automatica diaria puxa DO do estado e cria nova versao. Protocolos antigos NAO recalculam — eles estao sob a tabela da epoca.

### 5. Multi-tenancy futuro (multi-cartorio)

`schema_name` em cada tabela de negocio. `cartorio_id` em cada query. Supabase gerencia schemas separados por cartorio. Single backend, multi-tenant.

Implementacao: Sprint 5+ (multi-cartorio white label).

## Fluxo end-to-end: "cliente pergunta status do protocolo"

```
1. Cliente WhatsApp: "qual o status do protocolo 12345?"
2. Evolution API recebe webhook
3. OpenClaw gateway normaliza payload
4. n8n workflow #2 aciona (intent: consultar_protocolo)
5. POST /api/v1/webhook/evolution → PII scrubber (none nesse caso)
6. Audit log: conversa.received, payload scrubbed
7. Backend: SELECT * FROM protocolos WHERE numero = '12345'
8. Audit log: protocolo.read
9. Backend retorna: "Protocolo 12345 - em_andamento - previsao 2026-06-25"
10. n8n workflow monta resposta WhatsApp
11. Evolution API envia msg
12. Audit log: conversa.sent
13. Conversa atualizada com bot_response + llm_tokens
```

Tempo total esperado: < 2s. Com cache Redis para consultas repetidas: < 200ms.

Modified by Gustavo Almeida
