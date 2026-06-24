# Memory Configuration - OpenClaw Agent (CartórioBot)

Configuracao do sistema de memoria hibrido do OpenClaw Agent:

- **Short-term** (Redis): ultimas 24h de conversa por sessao
- **Long-term** (Supabase pgvector): padroes, preferencias, historico do cliente

## Short-term memory (Redis)

### Chave

```
cartorio:sess:<canal>:<sender>:<instance>
```

Exemplo: `cartorio:sess:whatsapp:5511999999999:cartorio-bot`

### Valor

Lista (Redis RPUSH/LRANGE) de mensagens em JSON:

```json
{
  "role": "user|assistant",
  "content": "<texto scrubbed - PII removida>",
  "timestamp": "2026-06-24T10:30:00.000Z",
  "scrubbed": true,
  "pii_findings": {"cpf": 1, "phone_br": 1},
  "request_id": "<uuid>"
}
```

### TTL

24 horas (`SESSION_TTL_SECONDS=86400` em `backend/app/config.py`)

Configuravel via env: `OPENCLAW_SESSION_TTL_SECONDS` (default: 86400)

### Operacoes

| Operacao | Quando | Comando Redis |
|----------|--------|---------------|
| Adicionar mensagem | Apos cada interacao | `RPUSH cartorio:sess:<key> <json>` |
| Recuperar historico | Inicio de sessao / context rebuild | `LRANGE cartorio:sess:<key> 0 -1` |
| Expirar | Apos TTL | `EXPIRE cartorio:sess:<key> <ttl>` |
| Limpar | Cliente pede REVOGAR | `DEL cartorio:sess:<key>` |

### LGPD

- Mensagens sao ANTES scrubbed (PII removida) antes de gravar
- Cliente pode pedir REVOGAR → `DEL` imediato + audit log `cliente.revogacao_consentimento`
- TTL de 24h garante que mensagens sensitive NAO persistem alem de 1 dia (LGPD art. 6o VIII - minimizacao)

## Long-term memory (Supabase pgvector)

### Tabela

```sql
CREATE TABLE openclaw_memory (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT REFERENCES clientes(id),
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX openclaw_memory_embedding_idx ON openclaw_memory USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX openclaw_memory_cliente_id_idx ON openclaw_memory(cliente_id);
```

### Quando gravar

- Apos cada conversa relevante (N8N workflow #15 session-sync)
- Topicos recorrentes do cliente (ex: "sempre pergunta sobre certidao de casamento")
- Preferencias declaradas (ex: "prefere horario da manha")
- Padroes temporais (ex: "sempre pergunta valor no sabado de manha")

### Quando recuperar (RAG)

- Antes de gerar resposta do bot, query por similarity:
  ```sql
  SELECT content, metadata
  FROM openclaw_memory
  WHERE cliente_id = $1
  ORDER BY embedding <=> $2  -- $2 = embedding da mensagem atual
  LIMIT 5;
  ```
- Adiciona resultados ao system prompt como contexto
- Se cliente revogou consentimento (`motivo_encerramento = REVOGACAO_CONSENTIMENTO`):
  - **NAO recupera** (LGPD art. 18 VI)
  - Marca `deleted_at = NOW()` em todas as rows de `openclaw_memory` daquele cliente

### LGPD

- Direita ao esquecimento (LGPD art. 18 VI): cascade delete em `cliente.revogacao_consentimento`
- Retencao minima: 5 anos para clientes COM protocolo (Provimento CNJ 74/2018)
- Retencao ate-revogacao: para clientes SEM protocolo
- Embedding NAO eh dado pessoal (vetor matematico), mas conteudo eh - scrubbing ANTES de embed

## Synchronization (N8N workflow #15)

Cron job sincroniza Redis → pgvector a cada 6h:

```
- Para cada sessao Redis com TTL ativo
  - Parse mensagens
  - Chunk em unidades semanticas (max 500 tokens)
  - Embed via OpenAI text-embedding-3-small (ou DeepSeek embedding)
  - INSERT INTO openclaw_memory
```

WF #15: `15-session-sync.json` em `infra/n8n-workflows/`

## Health check

Endpoint: `GET /api/v1/openclaw/memory/health`

Response:
```json
{
  "redis": {
    "connected": true,
    "sessions_active": 42,
    "avg_session_size_bytes": 1200
  },
  "pgvector": {
    "connected": true,
    "rows_total": 15320,
    "avg_embedding_latency_ms": 45
  },
  "sync": {
    "last_sync_at": "2026-06-24T06:00:00Z",
    "next_sync_at": "2026-06-24T12:00:00Z",
    "synced_last_24h": 340
  }
}
```

## LGPD compliance checklist

- [x] PII scrubbed ANTES de gravar em Redis
- [x] TTL 24h para short-term
- [x] Direita ao esquecimento cascade em pgvector
- [x] Retencao configuravel (5y para com-protocolo, ate-revogacao senao)
- [x] Audit log em toda gravacao/leitura (LGPD art. 37)
- [x] DPO pode exportar todos os dados de um cliente (LGPD art. 18 II)
- [x] Cliente pode pedir anonimizacao do embedding (LGPD art. 18 IV)

Modified by Gustavo Almeida