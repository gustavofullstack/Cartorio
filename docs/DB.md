# DB Schema — Cartório Chatbot

> **10 models + 3 migrations Alembic + PostgreSQL 16 (Supabase) + LGPD-by-design.**

## Stack DB

- **SGBD**: PostgreSQL 16 (self-hosted via Supabase)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Schema manager**: Supabase (Auth + Storage + Realtime)
- **URL**: `postgresql://cartorio_admin:***@supabase-db:5432/cartorio`

---

## Diagrama ER (Entity-Relationship)

```mermaid
erDiagram
    cliente ||--o{ protocolo : "solicita"
    cliente ||--o{ conversa : "inicia"
    cliente ||--o{ atendimento : "recebe"
    cliente ||--o{ documento : "apresenta"
    protocolo ||--o{ documento : "anexa"
    protocolo ||--|| protocolo_estado : "estado atual"
    conversa ||--o{ mensagem : "contem"
    atendimento ||--|| conversa : "contexto"
    atendimento ||--o{ audit_log : "gera"
    protocolo ||--o{ audit_log : "gera"
    cliente ||--o{ audit_log : "gera"
    outbox_message ||--o{ audit_log : "gera"
    webhook_event ||--|| audit_log : "gera"
    protocolo ||--o{ emolumento_snapshot : "calcula"

    cliente {
        uuid id PK
        string cpf_hash "SHA256+salt (LGPD)"
        string nome_scrubbed
        string email_scrubbed
        string phone_scrubbed
        bool consent_granted
        timestamp consent_at
        timestamp created_at
        timestamp deleted_at "soft delete"
    }

    protocolo {
        uuid id PK
        string numero UK "CART-YYYY-XXXXXX"
        uuid cliente_id FK
        string tipo_documento
        decimal valor_ato
        string status "draft|hitl|concluido|cancelado"
        string hitl_status "pendente|aprovado|rejeitado"
        uuid created_by
        timestamp created_at
        timestamp concluded_at
    }

    atendimento {
        uuid id PK
        uuid cliente_id FK
        uuid protocolo_id FK "nullable"
        string canal "whatsapp|telegram|web|balcao"
        string status "aberto|em_atendimento|concluido|stale"
        bool stale_flag
        timestamp created_at
        timestamp concluded_at
    }

    conversa {
        uuid id PK
        uuid cliente_id FK
        uuid atendimento_id FK
        jsonb messages
        string llm_model "MiniMax-M3|gemini-3.1-pro|deepseek-v4-flash"
        int llm_tokens_in
        int llm_tokens_out
        timestamp created_at
    }

    documento {
        uuid id PK
        uuid cliente_id FK
        uuid protocolo_id FK "nullable"
        string tipo_documento "rg|cpf|cnh|comprovante|escritura"
        string storage_path "Supabase Storage path"
        int file_size_bytes
        string mime_type
        string hash_sha256
        bool pii_scrubbed
        timestamp uploaded_at
    }

    audit_log {
        uuid id PK
        string prev_hash "SHA256 chain"
        string curr_hash UK
        string hmac_signature
        string actor_id
        string actor_type "cliente|escrevente|sistema|dpo"
        string resource "protocolo|cliente|atendimento|..."
        string action "create|read|update|delete|..."
        string request_id
        string ip_truncado "/24 LGPD D5"
        string ip_completo "2y retencao forensics"
        string user_agent
        jsonb payload
        timestamp timestamp
    }

    outbox_message {
        uuid id PK
        string queue "evolution|chatwoot|telegram|outbox"
        jsonb payload
        string status "pending|processing|done|failed"
        int attempts
        string last_error
        timestamp next_retry_at
        timestamp created_at
    }

    webhook_event {
        uuid id PK
        string source "evolution|chatwoot|telegram"
        string external_id "msg_id for idempotency"
        jsonb payload
        bool processed
        timestamp received_at
    }

    emolumento_snapshot {
        uuid id PK
        uuid protocolo_id FK
        string tabela_referencia "TABELA_2026_MG"
        decimal valor_base
        decimal valor_total
        date valido_ate
        timestamp created_at
    }
```

---

## Tabelas por criticidade LGPD

### TIER 1 — Críticas LGPD (PII direto)

| Tabela | PII armazenada | Hash usado | Retenção |
|---|---|---|---|
| **cliente** | cpf, email, phone, nome | `cpf_hash` SHA256+salt | até revogação |
| **conversa** | mensagens WhatsApp | scrubbed text | 2 anos |
| **documento** | RG/CPF/CNH upload | `hash_sha256` | até revogação |
| **audit_log** | IP (completo) | `ip_truncado` /24 | 5 anos |

### TIER 2 — Operacionais (sem PII)

| Tabela | Conteúdo | Retenção |
|---|---|---|
| **protocolo** | numero, valor, status, hitl | 5 anos |
| **atendimento** | canal, status, stale_flag | 2 anos |
| **emolumento_snapshot** | valor_base, valor_total | 5 anos (imutável) |

### TIER 3 — Infraestrutura (técnico)

| Tabela | Conteúdo | Retenção |
|---|---|---|
| **outbox_message** | payload, attempts | 30 dias após done/failed |
| **webhook_event** | payload, processed | 30 dias |
| **audit_log** | hash chain | 5 anos (compliance) |

---

## Models SQLAlchemy (10 total)

| Model | Path | Linhas | Tabela |
|---|---|---|---|
| `Cliente` | `app/models/cliente.py` | ~120 | `clientes` |
| `Protocolo` | `app/models/protocolo.py` | ~180 | `protocolos` |
| `Atendimento` | `app/models/atendimento.py` | ~100 | `atendimentos` |
| `Conversa` | `app/models/conversa.py` | ~150 | `conversas` |
| `Documento` | `app/models/documento.py` | ~130 | `documentos` |
| `AuditLog` | `app/models/audit_log.py` | ~200 | `audit_log` (append-only) |
| `OutboxMessage` | `app/models/outbox_message.py` | ~120 | `outbox_messages` |
| `WebhookEvent` | `app/models/webhook_event.py` | ~80 | `webhook_events` |
| `CpfCnpjValidator` | `app/models/cpf_cnpj_validator.py` | ~80 | (pure, no table) |
| `Base` | `app/models/base.py` | ~50 | (declarative_base) |

---

## Migrations Alembic (3)

| Revisão | Down Rev | Descrição | Linhas |
|---|---|---|---|
| `2026_06_23_0001` | (root) | Add audit_log + canal + cliente_encerramento | ~150 |
| `2026_06_24_0001` | `..._0001` | Add audit_log.ip_truncado (LGPD D5) | ~80 |
| `2026_06_24_0002` | `..._0001` | Add outbox_messages (DLQ A2) | ~120 |

### Como rodar migrations
```bash
cd backend
uv run alembic upgrade head
uv run alembic current
uv run alembic history
```

---

## Cardinalidade labels Prometheus (LGPD-by-design)

Cada label de métrica Prometheus tem cardinalidade **limitada** (LGPD + custo):

| Label | Tipo | Cardinalidade | Justificativa |
|---|---|---|---|
| `pii_blocked_total{channel,tipo_scrub}` | enum | ~20 | channel={whatsapp,telegram,web} × tipo_scrub={cpf,cnpj,email,phone,cns,cnh} |
| `scrub_latency_ms{channel}` | enum | ~3 | channel={whatsapp,telegram,web} |
| `dlq_depth{queue}` | enum | 4 | queue={evolution,chatwoot,telegram,outbox} |
| `audit_log_total{actor_type,resource}` | enum | ~30 | actor_type={cliente,escrevente,sistema,dpo} × resource={protocolo,cliente,...} |

**NUNCA** usar `user_id` ou `cpf_hash` como label (alta cardinalidade + LGPD).

---

## Índices críticos (perf)

```sql
-- Audit log (LGPD art. 37 + forensics)
CREATE INDEX ix_audit_request_id ON audit_log(request_id);
CREATE INDEX ix_audit_resource_action ON audit_log(resource, action);
CREATE INDEX ix_audit_timestamp ON audit_log(timestamp);
CREATE INDEX ix_audit_actor ON audit_log(actor_id);

-- Cliente (LGPD busca)
CREATE INDEX ix_cliente_cpf_hash ON clientes(cpf_hash);
CREATE INDEX ix_cliente_consent ON clientes(consent_granted) WHERE consent_granted = true;

-- Protocolo (workflow)
CREATE INDEX ix_protocolo_numero ON protocolos(numero);
CREATE INDEX ix_protocolo_cliente_status ON protocolos(cliente_id, status);
CREATE INDEX ix_protocolo_hitl_pendente ON protocolos(hitl_status) WHERE hitl_status = 'pendente';

-- Outbox (DLQ retry)
CREATE INDEX ix_outbox_queue_status ON outbox_messages(queue, status);
CREATE INDEX ix_outbox_next_retry_at ON outbox_messages(next_retry_at);

-- Webhook (idempotência)
CREATE UNIQUE INDEX ix_webhook_source_external ON webhook_events(source, external_id);
```

---

## Constraints CHECK (LGPD + integridade)

```sql
-- CPF/CNPJ válido
ALTER TABLE clientes ADD CONSTRAINT chk_cpf_hash_format
  CHECK (cpf_hash ~ '^[a-f0-9]{64}$');

-- Email scrubbed (SHA256 ou [MASKED:email])
ALTER TABLE clientes ADD CONSTRAINT chk_email_scrubbed
  CHECK (email_scrubbed ~ '^(SHA256:[a-f0-9]{64}|\[MASKED:email\])$');

-- Valor ato > 0
ALTER TABLE protocolos ADD CONSTRAINT chk_valor_ato_positive
  CHECK (valor_ato > 0);

-- Status enum
ALTER TABLE protocolos ADD CONSTRAINT chk_status_enum
  CHECK (status IN ('draft','hitl','concluido','cancelado'));

-- Audit log hash único
ALTER TABLE audit_log ADD CONSTRAINT uq_audit_curr_hash UNIQUE (curr_hash);
```

---

## Backup strategy

- **Local**: pg_basebackup diário 04:00 BRT (retenção 7d)
- **S3**: backup semanal segunda 04:00 (retenção 90d)
- **WAL archiving**: contínuo (point-in-time recovery)
- **Test restore**: mensal primeiro sábado
- **Encryption at-rest**: pgcrypto (LGPD L3) — coluna `encrypted_payload`

Ver [DEPLOYMENT.md](DEPLOYMENT.md) para detalhes.

---

## LGPD rights (diretos no DB)

| Direito | Como implementar | Storage |
|---|---|---|
| Acesso | `GET /cliente/{id}/historico` | SELECT direto |
| Correção | `PATCH /cliente/{id}` | UPDATE |
| Anonimização | `POST /cliente/{id}/anonimizar` | UPDATE cpf_hash='ANON' |
| Portabilidade | `GET /cliente/{id}/export` | SELECT + JSON+CSV+PDF |
| Esquecimento | `DELETE /cliente/{id}` | CASCADE + audit |
| Oposição | `POST /cliente/{id}/opar` | UPDATE consent_granted=false |
| Não-automação | `POST /cliente/{id}/opt-out-bot` | UPDATE bot_paused=true |

---

Modified by ZCode/Mavis + Gustavo Almeida — 2026-06-24
