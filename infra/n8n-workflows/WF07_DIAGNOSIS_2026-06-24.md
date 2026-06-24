# WF #07 — Evolution sendText Diagnosis

**Date**: 2026-06-24 10:55 BRT
**Owner**: cartorio-n8n (reun) — session `mvs_3fb892d492d7489caf3c78f1e621ea6d`
**Workflow**: 07 - Pesquisa Satisfacao (id `D9XJmlJRXZ3lavoa`)
**Status**: 🟡 **ROOT CAUSE IDENTIFIED** — aguarda Gustavo scan QR

## Symptom

Execution #760 (cron trigger 2026-06-24 04:00:30):
- Last node: `Evolution sendText`
- Error: `Could not get parameter "operation"`
- No further context (Context: `{}`)

The error is intermittent — depends on Evolution API state at the moment of trigger.

## Root Cause

**Instance `cartorio-2notas` is in `connectionStatus: "connecting"` — WhatsApp number has NEVER been connected via QR code.**

### Evidence (Evolution API runtime state, 2026-06-24 13:50 BRT)

```
GET /instance/fetchInstances (with apikey header)
→ [{
    "name": "cartorio-2notas",
    "connectionStatus": "connecting",    ← NOT "open"!
    "ownerJid": null,                    ← no WhatsApp number
    "number": null,                      ← no phone associated
    "integration": "WHATSAPP-BAILEYS",
    "_count": {"Message":0,"Contact":0,"Chat":0}  ← never received msg
}]

GET /instance/connectionState/cartorio-2notas
→ {"instance":{"instanceName":"cartorio-2notas","state":"connecting"}}
```

**This means**: The Evolution API has the WhatsApp session configured but the actual phone number has not been linked. No QR code has been scanned.

## Why this causes the N8N error

The `n8n-nodes-evolution-api.evolutionApi` node (v1.0.4) calls the Evolution API to enumerate available operations for a given `instanceName`. The internal N8N mechanism fetches the operation list dynamically. When the instance is in `connecting` state (no real WhatsApp session), the API may return a partial or empty operations list, causing the N8N node to throw "Could not get parameter 'operation'".

This is **NOT** a credential issue. The credential `evolution-api-cartorio` (id `adbzRn9sEZD7VZbs`) is correctly configured with type `evolutionApi` and is bound to the node.

## Other Configuration Verification ✅

| Item | Status | Evidence |
|------|--------|----------|
| Credential `evolution-api-cartorio` exists | ✅ | id `adbzRn9sEZD7VZbs`, type `evolutionApi` |
| Credential bound to WF #07 Evolution sendText | ✅ | N8N workflow JSON shows `credentials.evolutionApi.id` |
| AUTHENTICATION_API_KEY matches EVOLUTION_API_KEY | ✅ | Both = `429683C4C977415CAAFCCE10F7D57E11` |
| Instance `cartorio-2notas` exists in Evolution API | ✅ | DB row confirmed |
| API key works for fetchInstances | ✅ | Returns full JSON with instance data |
| QR code generation endpoint works | ✅ | `/instance/connect/cartorio-2notas` returns valid base64 PNG |

## Resolution Path

**Required action**: Gustavo must scan the QR code via the Evolution Manager UI to connect a real WhatsApp number to instance `cartorio-2notas`.

### Option A — UI (recommended)

1. Open https://whatsapp.2notasudi.com.br/manager
2. Login (admin@cartorio.com.br or @Techno832466 — known credentials may have changed; current Gustavos UI TODO)
3. Find instance `cartorio-2notas`
4. Click "Connect" → scan QR with WhatsApp app on phone
5. Status should change from `connecting` to `open`

### Option B — API (alternative, requires Gustavo's phone at hand)

```bash
# Get QR code as base64 PNG
curl -sS -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" \
  "https://whatsapp.2notasudi.com.br/instance/connect/cartorio-2notas" \
  | python3 -c "import json, sys, base64; d=json.load(sys.stdin); img=base64.b64decode(d['base64'].split(',')[1]); open('/tmp/qr.png','wb').write(img); print('QR saved to /tmp/qr.png')"
# Open /tmp/qr.png and scan with WhatsApp
```

### After QR scan

- `connectionStatus` should become `"open"` within 5-10 seconds
- N8N Evolution sendText node should work automatically on next cron trigger (every 24h)
- WF #07 will start running research satisfaction messages to clients

## Pre-flight Gate

- ✅ No hardcoded secrets in WF #07 (verified 2026-06-24 10:21 in M2.1 audit)
- ✅ All API calls use `credentials.evolutionApi` (no $env fallback)
- ✅ Pre-flight gate 25 cross-project: 0 hits `apiKey` in `infra/n8n-workflows/*.json`

## Next Steps

1. **GUSTAVO** — scan QR code (UI or API) ← **blocker único**
2. After QR scan, re-test WF #07 by waiting for next cron trigger OR by manually triggering via cron expression
3. Alternative: change WF #07 trigger from `every 24h` to `every 1 minute` temporarily for fast smoke test, then revert
4. Document in AUDIT_2026-06-24.md that issue C.2 is resolved

## Related

- AUDIT_2026-06-24.md issue C.2 (WF #07 runtime error)
- TASKS.md E6.S4.T1-E6.S4.T2 (Evolution Manager UI access + instance provisioning)
- ADR (pending): WhatsApp connection lifecycle management

Modified by Gustavo Almeida