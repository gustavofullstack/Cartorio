# API Quick Reference - Cartorio Chatbot

> **Referencia RAPIDA dos 30+ endpoints com curl exemplo + response JSON.**
> Para doc completa, ver `docs/API.md`. OpenAPI spec: `/openapi.json`.
> Versao: 0.5.4 (2026-06-24)

## Como usar este guia

Cada bloco tem:
- **Metodo + path** (em negrito)
- **Auth**: tier necessario (`-` = sem auth, `padrao`, `dpo`, `n8n`, `admin`)
- **Request**: comando `curl` copy-paste
- **Response**: JSON esperado
- **Erros**: principais status codes

## Variaveis uteis

```bash
export API_BASE="https://api.2notasudi.com.br"
export N8N_KEY="n8n-29f8b4c7..."
export DPO_KEY="dpo-abc123..."
```

---

## HEALTH (sem auth)

### GET /health (liveness)
```bash
curl $API_BASE/health
```
```json
{"status": "ok", "service": "cartorio-backend", "version": "0.5.4"}
```

### GET /ready (readiness)
```bash
curl $API_BASE/ready
```
```json
{"status": "ready", "audit_chain_initialized": true}
```

### GET /api/v1/health/radar (7 servicos)
```bash
curl $API_BASE/api/v1/health/radar
```
```json
{
  "status": "green",
  "services": {
    "database": "online", "redis": "online", "n8n": "online",
    "openclaw": "online", "evolution": "online", "chatwoot": "online",
    "supabase": "online"
  }
}
```

### GET /api/v1/health/db (PostgreSQL)
```bash
curl $API_BASE/api/v1/health/db
```
```json
{"status": "online", "service": "postgresql", "latency_ms": 2.34}
```

### GET /api/v1/health/redis
```bash
curl $API_BASE/api/v1/health/redis
```
```json
{"status": "online", "service": "redis", "latency_ms": 1.12}
```

### GET /api/v1/health/llm
```bash
curl $API_BASE/api/v1/health/llm
```
```json
{"status": "online", "service": "llm", "provider": "opencode_go", "http_status": 200}
```

---

## EMOLUMENTO (sem auth, public)

### GET /api/v1/emolumento/calcular
```bash
curl "$API_BASE/api/v1/emolumento/calcular?tipo=certidao_negativa&folhas=2&urgencia=true"
```
```json
{
  "tipo": "certidao_negativa", "folhas": 2, "urgencia": true,
  "base": 25.50, "adicional_folhas": 1.27, "adicional_urgencia": 13.39,
  "total": 40.16, "tabela_referencia": "MG-2026", "valido_ate": "2026-12-31"
}
```

Tipos validos: `certidao_negativa`, `certidao_positiva`, `certidao_casamento`, `escritura_compra_venda`, `escritura_doacao`, `procuracao`, `autenticacao`, `reconhecimento_firma`, `registro_nascimento`, `registro_obito`.

---

## PROTOCOLO (tier padrao)

### GET /api/v1/protocolo/{numero}
```bash
curl -H "X-API-Key: $N8N_KEY" $API_BASE/api/v1/protocolo/PROT-2026-000123
```
```json
{
  "numero": "PROT-2026-000123", "status": "em_andamento",
  "tipo": "certidao_negativa", "cliente_id": 42,
  "criado_em": "2026-06-15T10:30:00Z", "atualizado_em": "2026-06-20T14:22:00Z",
  "documentos": [{"id": 1, "nome": "rg.pdf", "validado": true}],
  "valor_total": 40.16
}
```

### POST /api/v1/protocolo (HITL nivel 2)
```bash
curl -X POST -H "X-API-Key: $N8N_KEY" -H "Content-Type: application/json" \
  -d '{"cliente_id": 42, "tipo": "certidao_negativa", "folhas": 1}' \
  $API_BASE/api/v1/protocolo
```
```json
{"id": 123, "numero": "PROT-2026-000124", "status": "draft", "criado_em": "2026-06-24T12:00:00Z"}
```

---

## CLIENTE (tier padrao, exige LGPD)

### POST /api/v1/cliente (com consentimento LGPD)
```bash
curl -X POST -H "X-API-Key: $N8N_KEY" -H "Content-Type: application/json" \
  -d '{"nome": "Joao", "cpf": "12345678909", "telefone": "34988887777",
       "consentimento_lgpd": true, "consentimento_em": "2026-06-24T12:00:00Z"}' \
  $API_BASE/api/v1/cliente
```
```json
{"id": 42, "cpf_hash": "abc123...def", "consentimento_lgpd": true, "criado_em": "2026-06-24T12:00:00Z"}
```

### GET /api/v1/cliente/{id}/historico (LGPD art. 18 IV)
```bash
curl -H "X-API-Key: $DPO_KEY" $API_BASE/api/v1/cliente/42/historico
```
```json
{
  "cliente": {"id": 42, "nome": "Joao", "cpf_hash": "abc..."},
  "protocolos": [...], "conversas": [...],
  "auditoria_acessos": [{"data": "2026-06-24", "quem": "escrevente", "acao": "consultar_historico"}]
}
```

---

## DOCUMENTO (tier padrao)

### POST /api/v1/documento/upload
```bash
curl -X POST -H "X-API-Key: $N8N_KEY" \
  -F "protocolo_id=123" -F "file=@/path/to/rg.pdf" \
  $API_BASE/api/v1/documento/upload
```
```json
{"id": 456, "nome": "rg.pdf", "hash_sha256": "def456...", "tamanho_bytes": 102400, "validado": false}
```

---

## CONVERSA (tier padrao)

### POST /api/v1/conversa (HITL nivel 1)
```bash
curl -X POST -H "X-API-Key: $N8N_KEY" -H "Content-Type: application/json" \
  -d '{"canal": "whatsapp", "remetente": "5534988887777", "mensagem": "Quero certidao"}' \
  $API_BASE/api/v1/conversa
```
```json
{"conversa_id": 789, "resposta": "Para emitir certidao, preciso do CPF", "intencao": "solicitar_certidao_negativa", "confidence": 0.92, "handoff_humano": false, "pii_blocked": false}
```

---

## WEBHOOKS (sem auth, validacao por HMAC)

### POST /api/v1/webhook/evolution (WhatsApp)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"event": "messages.upsert", "instance": "cartorio-2notas",
       "data": {"key": {"remoteJid": "5534988887777@s.whatsapp.net", "id": "ABC123"},
                "message": {"conversation": "Quero certidao"}}}' \
  $API_BASE/api/v1/webhook/evolution
```
```json
{"status": "received", "event_type": "messages.upsert", "idempotency_key": "evo:ABC123", "processed": true}
```

### POST /api/v1/webhook/chatwoot (CRM)
```bash
curl -X POST -H "Content-Type: application/json" -H "X-Chatwoot-Signature: hmac_..." \
  -d '{"event": "message_created", "conversation": {"id": 1234},
       "sender": {"id": 42, "name": "Joao"}, "content": "Ola"}' \
  $API_BASE/api/v1/webhook/chatwoot
```
```json
{"status": "received", "event_type": "message_created"}
```

---

## LGPD / AUDITORIA (tier dpo)

### POST /api/v1/audit/verify
```bash
curl -X POST -H "X-API-Key: $DPO_KEY" $API_BASE/api/v1/audit/verify
```
```json
{"valid": true, "total_entries": 1234, "first_id": 1, "last_id": 1234, "checked_at": "2026-06-24T12:00:00Z"}
```

Se invalido: `{"valid": false, "broken_at_id": 567, "expected_hash": "abc...", "actual_hash": "def..."}`

### GET /api/v1/audit/query
```bash
curl -H "X-API-Key: $DPO_KEY" \
  "$API_BASE/api/v1/audit/query?cliente_id=42&tipo=pii_blocked&limit=50"
```
```json
{"total": 23, "items": [{"id": 5678, "tipo": "pii_blocked", "cliente_id": 42, "criado_em": "2026-06-24T11:00:00Z", "metadata": {"tipo_pii": "cpf"}}]}
```

### POST /api/v1/lgpd/direito-esquecimento (LGPD art. 18 VI)
```bash
curl -X POST -H "X-API-Key: $DPO_KEY" -H "Content-Type: application/json" \
  -d '{"cliente_id": 42, "confirmacao_dupla": true, "motivo": "cliente_solicitou"}' \
  $API_BASE/api/v1/lgpd/direito-esquecimento
```
```json
{"status": "processado", "cliente_id": 42, "soft_delete_at": "2026-06-24T12:00:00Z", "purged_at": "2026-07-24T12:00:00Z", "audit_log_id": 9999}
```

---

## INTEGRATIONS (tier padrao, header X-Session-Id)

### POST /integrations/agent/send
```bash
curl -X POST -H "X-Session-Id: session_abc" -H "Content-Type: application/json" \
  -d '{"canal": "whatsapp", "destinatario": "5534988887777",
       "mensagem": "Sua certidao foi emitida!", "protocolo_id": 123}' \
  $API_BASE/integrations/agent/send
```
```json
{"status": "sent", "message_id": "evo_XYZ789", "audit_log_id": 8888}
```

### GET /integrations/agent/health
```bash
curl $API_BASE/integrations/agent/health
```
```json
{"status": "online", "openclaw_url": "http://cartorio_openclaw-gateway:18790", "latency_ms": 15.2}
```

---

## ADMIN (tier admin)

### POST /admin/api-key/generate
```bash
curl -X POST -H "X-API-Key: $ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"tier": "n8n", "descricao": "N8N workflow #31"}' \
  $API_BASE/admin/api-key/generate
```
```json
{"api_key": "n8n-29f8b4c7...", "tier": "n8n", "criado_em": "2026-06-24T12:00:00Z"}
```

### POST /admin/agent/pause (HITL pause)
```bash
curl -X POST -H "X-API-Key: $DPO_KEY" -H "Content-Type: application/json" \
  -d '{"conversa_id": 789, "motivo": "escrevente_assumiu", "pausado_por": "escrevente@cartorio"}' \
  $API_BASE/admin/agent/pause
```
```json
{"status": "paused", "conversa_id": 789, "pausado_em": "2026-06-24T12:00:00Z", "audit_log_id": 7777}
```

---

## CRON (tier n8n)

### POST /cron/stale-detector
```bash
curl -X POST -H "X-API-Key: $N8N_KEY" $API_BASE/cron/stale-detector
```
```json
{"stale_count": 3, "marked_conversations": [123, 456, 789], "ran_at": "2026-06-24T12:00:00Z"}
```

---

## METRICS (sem auth, formato Prometheus)

### GET /api/v1/metrics/prometheus
```bash
curl $API_BASE/api/v1/metrics/prometheus
```
```
# TYPE cartorio_uptime_seconds gauge
cartorio_uptime_seconds 3600.12
# TYPE cartorio_http_requests_total counter
cartorio_http_requests_total{endpoint="/api/v1/emolumento/calcular",method="GET",status="200"} 42
...
```

---

## CODIGOS DE ERRO

| Status | Codigo | Significado |
|---|---|---|
| 400 | BAD_REQUEST | Payload malformado |
| 401 | UNAUTHORIZED | API key invalida/faltando |
| 403 | FORBIDDEN | API key sem permissao para tier |
| 404 | NOT_FOUND | Recurso nao existe |
| 422 | VALIDATION_ERROR | Campo invalido/faltando |
| 429 | RATE_LIMITED | Tier excedido (padrao 30/min, dpo 60/min, n8n 600/min) |
| 429 | RATE_LIMITED_DDOS | IP DDoS excedido (100 req/min) |
| 500 | INTERNAL_ERROR | Erro inesperado (ver logs) |
| 503 | SERVICE_UNAVAILABLE | Dependencia offline |

## TIER vs RATE LIMIT

| Tier | Header | Rate limit | Uso |
|---|---|---|---|
| (sem key) | - | 30 req/min | publico (emolumento) |
| padrao | X-API-Key: <key> | 30 req/min | clientes gerais |
| dpo | X-API-Key: dpo-* | 60 req/min | escrevente/dashboard |
| n8n | X-API-Key: n8n-* | 600 req/min | workflows (cron/polling) |
| admin | X-API-Key: admin-* | sem limite | admin/DPO |

**DDoS protection**: TODAS as rotas `/api/v1/*` tem limite adicional de **100 req/min por IP** (independente de tier).

Modified by ZCode/Mavis - 2026-06-24
