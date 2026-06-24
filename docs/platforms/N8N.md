# N8N 1.x - Quick Reference (Cartorio)

> **10 nodes + expressions + credentials para integracao Chatwoot + Supabase + HTTP.**
> Versao: 1.x (2026-06-24)
> Base URL prod: `https://flow.2notasudi.com.br`
> Doc oficial: https://docs.n8n.io/

## Visao geral

N8N e' um **workflow engine** open-source visual. Roda em Docker (`n8nio/n8n:latest`). Suporta 400+ integracoes nativas + custom nodes. Workflows sao exportados em JSON.

**Por que usamos**: visual (debug facil), self-hosted, custom nodes, suporta AGI/LangChain nodes, codigo aberto (sem lock-in).

## 10 Nodes principais (Cartorio usa esses)

### 1. Webhook (Trigger)

Recebe eventos HTTP.

```json
{
  "httpMethod": "POST",
  "path": "chatwoot-events",
  "authentication": "headerAuth",
  "responseMode": "lastNode"
}
```

**Cartorio**: recebe webhook do Chatwoot quando chega nova mensagem.

### 2. HTTP Request (Action)

Chama API externa qualquer.

```json
{
  "method": "POST",
  "url": "https://api.example.com/endpoint",
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "{\"key\":\"value\"}",
  "authentication": "genericCredentialType",
  "genericAuthType": "headerAuth"
}
```

**Cartorio**: chamar API da Receita/Redesim/Serpro.

### 3. Chatwoot - Send Message (Action)

Envia mensagem via Chatwoot.

```json
{
  "operation": "sendMessage",
  "accountId": "1",
  "conversationId": "={{$json.conversation_id}}",
  "message": "={{$json.reply}}",
  "messageType": "outgoing"
}
```

**Cartorio**: responder cliente no Chatwoot apos consulta.

### 4. Chatwoot - List Conversations (Action)

Lista conversas.

```json
{
  "operation": "getAll",
  "accountId": "1",
  "filters": {"status": "open"}
}
```

**Cartorio**: listar conversas abertas para triagem automatica.

### 5. Supabase - Insert Row (Action)

Insere linha.

```json
{
  "operation": "create",
  "tableId": "atendimentos",
  "dataUi": {"mapValues": true},
  "fieldsUi": {"values": [
    {"name": "telefone", "value": "={{$json.phone}}"},
    {"name": "mensagem", "value": "={{$json.body}}"}
  ]}
}
```

**Cartorio**: salvar atendimento recebido do Chatwoot.

### 6. Supabase - Select Rows (Action)

Busca linhas.

```json
{
  "operation": "getAll",
  "tableId": "clientes",
  "filters": {"cpf": "={{$json.cpf}}"},
  "limit": 1
}
```

**Cartorio**: buscar cliente por CPF antes de responder.

### 7. Code (JavaScript inline) (Action)

Logica custom.

```json
{
  "language": "javaScript",
  "mode": "runOnceForEachItem",
  "jsCode": "return [{json:{telefone: $json.phone, msg: $json.body, normalizado: $json.body.toLowerCase()}}];"
}
```

**Cartorio**: normalizar payload, calcular, transformar dados.

### 8. IF (condicional) (Action)

Roteamento condicional.

```json
{
  "conditions": {
    "conditions": [{
      "leftValue": "={{$json.status}}",
      "rightValue": "open",
      "operator": {"type": "string", "operation": "equals"}
    }]
  },
  "combineOperation": "and"
}
```

**Cartorio**: rotear se mensagem e inbound.

### 9. Schedule Trigger (Trigger)

Cron / intervalo.

```json
{
  "rule": {
    "interval": [{
      "field": "cronExpression",
      "expression": "0 8 * * *"
    }]
  }
}
```

**Cartorio**: disparar relatorio diario as 8h, backup as 3h.

### 10. Set (transformar dados) (Action)

Mapeia campos.

```json
{
  "assignments": {
    "assignments": [
      {"name": "fullName", "value": "={{$json.firstName}} {{$json.lastName}}"},
      {"name": "correlationId", "value": "={{$now.format('yyyyMMddHHmmss')}}-{{$json.id}}"}
    ]
  }
}
```

**Cartorio**: montar campos antes de inserir no Supabase.

## Expressions N8N

Sintaxe mustache: `{{ $json.field }}` em campos de valor.

**Variaveis uteis**:
- `{{ $json.campo }}` - campo do node anterior
- `{{ $node["NomeNode"].json.campo }}` - campo de node especifico
- `{{ $now }}` - data/hora atual
- `{{ $env.VARIAVEL }}` - variavel de ambiente
- `{{ $execution.id }}` - ID da execution
- `{{ $input.all() }}` - todos os items

**Exemplo completo**:
```javascript
{
  "value": "={{$json.firstName.toUpperCase()}} - {{$now.format('yyyy-MM-dd')}}"
}
```

## Credential Management

Criar em **Settings > Credentials**:
- **Supabase API**: host + service_role key
- **Chatwoot API**: api_access_token + base_url
- **Header Auth**: name + value (para webhooks)
- **Basic Auth**: username + password

Cada node referencia por campo `credentials` no JSON. **NUNCA commitar chave** - usar `.env` no self-hosted.

## Webhook URL

Formato: `https://{N8N_HOST}/webhook/{path}`

- **Test URL**: aparece ao clicar "Execute Workflow" (temporario)
- **Production URL**: aparece ao publicar (Activate toggle)
- Path suporta rota: `/chatwoot/:account_id`

**Exemplo**: webhook do Chatwoot no Cartorio:
- Production: `https://flow.2notasudi.com.br/webhook/chatwoot-events`
- Chatwoot config: `https://flow.2notasudi.com.br/webhook/chatwoot-events` (POST)

## Instalacao de community nodes

O node Chatwoot correto e' `n8n-nodes-chatwoot` (community), NAO `n8n-nodes-langchain.chatwoot`.

Instalar via **Settings > Community Nodes > Install**:
```
n8n-nodes-chatwoot
```

## Cenarios de uso no Cartorio

| Workflow | Nodes usados |
|---|---|
| #07 Evolution Webhook | Webhook -> IF (msg.inbound) -> Code (normalize) -> API |
| #08 Audit Verify Diario | Schedule (cron 03:30) -> HTTP (audit/verify) -> Supabase (insert log) |
| #09 Backup Diario | Schedule (cron 03:00) -> HTTP (POST /backup) -> Alert (fail) |
| #25 Pesquisa Mercado | Schedule (cron 08:00) -> HTTP (Google) -> Supabase (insert leads) |
| #31 CartorioBot Telegram | Webhook (Telegram) -> IF (msg) -> LLM -> Telegram send |

## Troubleshooting

| Problema | Solucao |
|---|---|
| Webhook 404 | Workflow nao foi "Activated" (toggle) |
| Expression `{{ $json.x }}` retorna undefined | Campo nao existe no payload - usar `$node["NodeName"].json.x` |
| Credential invalid | Verificar em Settings > Credentials > Test |
| Workflow lento | Adicionar IF para pular nodes desnecessarios |

## Referencias

- Doc oficial: https://docs.n8n.io/
- Indice completo: `docs/platforms/N8N_OFFICIAL_INDEX.md` (linktree oficial)
- Community nodes: https://www.npmjs.com/search?q=n8n-nodes
- Workflows do projeto: `infra/n8n-workflows/*.json`
- Estado: `infra/` (config Easypanel)
- Integrações com API: `backend/app/api/v1/integrations.py`

Modified by ZCode/Mavis - 2026-06-24
