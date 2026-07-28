# OpenClaw Gateway — LobeChat Integration Blocker Fix

> **Status (2026-07-14):** Diagnóstico concluído no repo, deploy depende de ação na VPS.
> Ver `infra/scripts/openclaw_fix_lobechat_cors_timeout.sh`.

## Sintomas reportados

1. LobeChat (browser em `https://cartorio-lobechat.dfgdxq.easypanel.host`)
   chama `POST https://agent.2notasudi.com.br/v1/chat/completions`
   → **preflight OPTIONS 405 Method Not Allowed**, sem header
   `Access-Control-Allow-Origin`. LobeChat aborta com
   `CORS preflight channel didn't succeed`.

2. Mesmo quando o preflight é forçado via curl, o `POST` autenticado retorna
   **408 Request Timeout** com `{"error":{"message":"upstream provider timeout","type":"api_error"}}`
   em ~2.37s, **para todos os 3 modelos** (`openclaw`, `openclaw/default`,
   `openclaw/main`).

## Diagnóstico (live, 2026-07-14, executado da máquina local)

```bash
# CORS preflight — 405, sem ACAO
curl -sS -o /dev/null -w "OPTIONS status=%{http_code} acao='%header{access-control-allow-origin}'\n" \
  --max-time 10 -X OPTIONS \
  -H "Origin: https://cartorio-lobechat.dfgdxq.easypanel.host" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  https://agent.2notasudi.com.br/v1/chat/completions
# → OPTIONS status=405 acao=''

# POST upstream timeout
curl -sS --max-time 35 -X POST https://agent.2notasudi.com.br/v1/chat/completions \
  -H "Authorization: Bearer @Techno832466" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw","messages":[{"role":"user","content":"oi"}],"max_tokens":20}'
# → {"error":{"message":"upstream provider timeout","type":"api_error"}} — 408

# Upstream direto (opencode-go) — SAUDAVEL
curl -sS -o /dev/null -w "opencode-go=%{http_code} time=%{time_total}s\n" \
  --max-time 10 https://opencode.ai/zen/go/v1/models \
  -H "Authorization: Bearer sk-***REDACTED-PURGED-2026-07-28***"
# → opencode-go=200 time=0.57s
```

**Conclusão:**
- **CORS**: o gateway OpenClaw não está emitindo headers CORS para o
  endpoint `/v1/chat/completions`. O campo `gateway.controlUi.allowedOrigins`
  no `openclaw.json` está como `"*"` (wildcard para debug), mas isso
  só abrange WebSocket / Control UI. O HTTP API não herda.
- **Timeout**: o upstream `opencode-go` está saudável (200 ms) e a
  chave `sk-***REDACTED-PURGED-2026-07-28***...` está válida. O 408 vem de um **default
  muito curto** (~2-3s) do OpenClaw para `models.providers.*`.

## Fix proposto (aplicado no snapshot, deploy manual na VPS)

### 1) CORS — adicionar origins explícitas

Em `infra/openclaw-agent/gateway-config-snapshot-t49.json` foi
substituído:

```jsonc
// ANTES
"controlUi": { "allowedOrigins": ["*"] }
// DEPOIS
"controlUi": {
  "allowedOrigins": [
    "https://cartorio-lobechat.dfgdxq.easypanel.host",
    "https://lobechat.dfgdxq.easypanel.host",
    "http://localhost:3210",
    "http://127.0.0.1:3210",
    "https://agent.2notasudi.com.br",
    "https://admin.2notasudi.com.br",
    "https://app.2notasudi.com.br",
    "tauri://localhost"
  ]
}
```

> ⚠ O snapshot no repo **não toma efeito** até ser aplicado dentro do
> container em `/home/node/.openclaw/openclaw.json`. Deploy é manual na VPS.

### 2) Upstream timeout — 30 segundos

Mesmo arquivo, em `models.providers.openai`:

```jsonc
// ANTES: campo ausente (default ~2s)
// DEPOIS
"openai": {
  "baseUrl": "https://opencode.ai/zen/go/v1",
  "apiKey": "...",
  "api": "openai-completions",
  "timeoutSeconds": 30   // NOVO
}
```

> ⚠ OpenClaw docs ([docs.openclaw.ai/gateway/configuration](https://docs.openclaw.ai/gateway/configuration))
> referenciam `models.providers.<id>.timeoutSeconds` em **segundos**, não ms.
> 30s é suficiente para modelos com reasoning tipo qwen3.7-max / deepseek-v4-pro.

### 3) Deploy script

Ver `infra/scripts/openclaw_fix_lobechat_cors_timeout.sh`. Idempotente,
faz backup, aplica via `openclaw config set`, faz fallback manual por
python se a CLI rejeitar as chaves, força restart e roda 3 validações
pós-deploy (health, CORS preflight, POST /v1/chat).

## Caminhos alternativos (caso `openclaw config` rejeite as chaves)

Estes estão documentados também no snapshot (`_t51_changes_2026-07-14.3_alternative_paths_*`):

| Problema | Alternativa | Como aplicar |
|---|---|---|
| `openclaw config set` rejeita `allowedOrigins` | `gateway.http.cors.allowedOrigins` no JSON, ou `OPENCLAW_HTTP_CORS_ALLOWED_ORIGINS` env | `docker service update cartorio_openclaw-gateway --env-add OPENCLAW_HTTP_CORS_ALLOWED_ORIGINS=https://cartorio-lobechat.dfgdxq.easypanel.host,http://localhost:3210` |
| `openclaw config set` rejeita `timeoutSeconds` | `agents.defaults.transportTimeoutSeconds` / `requestTimeoutSeconds` / `upstreamTimeoutMs` | Testar cada path; consultar `openclaw config schema \| grep timeout` no container |
| OpenClaw não tem knob CORS para HTTP API | Traefik middleware CORS no service | `docker service update cartorio_openclaw-gateway --label-add traefik.http.middlewares.cors-lobechat.headers.accesscontrolalloworigin=https://cartorio-lobechat.dfgdxq.easypanel.host --label-add 'traefik.http.routers.openclaw-cors.middlewares=cors-lobechat@docker'` |

## Pós-fix — validação a fazer na VPS

```bash
# 1. CORS preflight deve retornar 204 com ACAO preenchido
curl -sS -o /dev/null -D - --max-time 8 -X OPTIONS \
  -H "Origin: https://cartorio-lobechat.dfgdxq.easypanel.host" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  https://agent.2notasudi.com.br/v1/chat/completions | grep -i 'access-control'
# esperado: Access-Control-Allow-Origin: https://cartorio-lobechat.dfgdxq.easypanel.host
#           Access-Control-Allow-Methods: POST
#           Access-Control-Allow-Headers: authorization,content-type

# 2. POST nao deve dar 408
curl -sS --max-time 30 -X POST https://agent.2notasudi.com.br/v1/chat/completions \
  -H "Authorization: Bearer @Techno832466" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw","messages":[{"role":"user","content":"oi"}],"max_tokens":20}' | head -c 400
# esperado: {"id":"chatcmpl-...","object":"chat.completion",...}

# 3. Models ainda respondem
curl -sS https://agent.2notasudi.com.br/v1/models \
  -H "Authorization: Bearer @Techno832466" | head -c 400
```

## Rollback

```bash
# Dentro do container
docker exec cartorio_openclaw-gateway cp \
  /home/node/.openclaw/openclaw.json.bak-pre-t51-YYYYMMDD-HHMMSS \
  /home/node/.openclaw/openclaw.json
docker service update --force cartorio_openclaw-gateway
```

Modified by Gustavo Almeida
