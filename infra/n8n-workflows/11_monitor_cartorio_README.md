# 11 - Monitor Cartório

**Workflow ID**: `5ABAZCQVRLd7AmM5`
**Active Version**: `45dfb8a6-d611-42a0-963b-f6df3f0ec90d`
**Webhook URL**: `POST https://cartorio-n8n.dfgdxq.easypanel.host/webhook/monitor-cartorio`
**Cron**: Every 5 minutes

## Purpose
Validates health of 6 cartório services and optionally sends an alert to Chatwoot inbox if any is down.

## Nodes (13 total)
- **POST /monitor-cartorio** (webhook trigger, manual) + **Cron 5min** (schedule trigger, every 5min)
- **Check API** → `GET https://api.2notasudi.com.br/health` (continueErrorOutput)
- **Check Evolution** → `GET https://whatsapp.2notasudi.com.br/` (continueErrorOutput)
- **Check OpenClaw** → `GET https://agent.2notasudi.com.br/health` (continueErrorOutput)
- **Check Supabase** → `GET https://supbase.2notasudi.com.br/auth/v1/health` (continueErrorOutput)
- **Check Chatwoot** → `GET https://api.2notasudi.com.br/health` (proxy via API, real Chatwoot URL TBD)
- **Check Redis** → `GET https://api.2notasudi.com.br/health` (proxy via API, real Redis URL TBD)
- **Combine Results** (merge, append, 6 inputs)
- **Has outage?** (ifElse: degraded?)
- **Format Alert** (Set node)
- **Send Chatwoot Alert** (httpRequest, continueErrorOutput)
- **Respond Health Report** (RespondToWebhook)

## Response
- Healthy: `200` `{"checked_at":"...","trigger":"webhook","items_count":6}`
- Degraded: `503` (same body, items_count may be < 6 if some checks errored)

## Known issues
1. **N8N_BLOCK_ENV_ACCESS_IN_NODE** is set on this instance. The `Code` node sandbox cannot use `$env` or `fetch`. Workaround: use `httpRequest` nodes in parallel.
2. **chat.2notasudi.com.br** does not resolve. Chatwoot alert step uses placeholder URL. cartorio-n8n must update with real Chatwoot URL via N8N panel UI.
3. **Real Chatwoot and Redis health URLs** are not yet defined. Both proxy to `https://api.2notasudi.com.br/health` as placeholder.
4. **X-N8N-API-KEY** (TWMpHt_jmsfoITKI7hA_gZwy54RA5P3nNwe_yAPCjD4) returns 401 on all REST endpoints. Cannot set N8N variables via API. Use panel UI.

## Deployment
```bash
# Workflow is already created and active. To recreate from code:
curl -X POST https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $N8N_MCP_BEARER" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg code "$(cat 11_monitor_cartorio.js)" '{jsonrpc:"2.0",id:1,method:"tools/call",params:{name:"create_workflow_from_code",arguments:{code:$code}}}')"

# Publish
# then: POST /webhook/monitor-cartorio with {}
```

## Test payload
```bash
curl -X POST https://cartorio-n8n.dfgdxq.easypanel.host/webhook/monitor-cartorio \
  -H "Content-Type: application/json" -d '{}' -w "\n--- HTTP %{http_code} ---\n"
```

Modified by Gustavo Almeida
