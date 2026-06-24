# OpenClaw HTTP API — Cartório Chatbot

> **Contrato público do OpenClaw Gateway** (TID `5d2e77f114e2`, image `ghcr.io/openclaw/openclaw:latest`)
> Endpoint público: `https://agent.2notasudi.com.br` (Traefik + Cloudflare)
> Endpoint interno (Tailscale): `http://100.99.172.84:18789`

## Estado atual (pós-T4.9, 2026-06-24 15:13 BRT)

| Endpoint | Método | Status HTTP antes | Status HTTP agora | Notas |
|---|---|---|---|---|
| `/v1/models` | GET | 200 (HTML SPA — enganoso) | **200 JSON** | Retorna 3 modelos: `openclaw`, `openclaw/default`, `openclaw/main` |
| `/v1/models/{id}` | GET | n/a | **200 JSON** | Ex: `/v1/models/openclaw/default` |
| `/v1/chat/completions` | POST | **404 Not Found** | **401 Unauthorized** | Endpoint HABILITADO, requer Bearer auth |
| `/v1/embeddings` | POST | 404 | 404 | NÃO habilitado (default) — `gateway.http.endpoints.embeddings.enabled` precisa ser `true` |
| `/v1/responses` | POST | 404 | 404 | NÃO habilitado (default) |
| `/` | GET | 200 HTML | 200 HTML | OpenClaw Control UI (SPA) |

## Autenticação

**Dois modos ativos** (configurados via env vars no container):

- **Token mode**: `Authorization: Bearer fz1qzo2xka8n82rn62irscuqws75mm1e17mpsnxzqlp13z1p35skrbg2ck8yg8pg` (env `OPENCLAW_GATEWAY_TOKEN`)
- **Password mode**: `Authorization: Bearer @Techno832466` (env `OPENCLAW_GATEWAY_PASSWORD`) ← **password funciona testado em 2026-06-24**

**Verificação**:

```bash
curl -sS https://agent.2notasudi.com.br/v1/models \
  -H "Authorization: Bearer @Techno832466"
# → {"object":"list","data":[{"id":"openclaw",...}]}
```

⚠️ Sem `Authorization` → 401. Com token/password errado → 401.

## POST /v1/chat/completions

### Contrato OpenAI-compatible

```http
POST /v1/chat/completions HTTP/1.1
Host: agent.2notasudi.com.br
Content-Type: application/json
Authorization: Bearer @Techno832466

{
  "model": "openclaw",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Olá"}
  ],
  "stream": false,
  "max_tokens": 1024
}
```

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `model` | string | sim | SEMPRE `"openclaw"` (rota para o default agent) ou `"openclaw/<agentId>"`. NÃO usar `"deepseek-v4-flash"` direto — é nome do modelo interno do agent |
| `messages` | array | sim | OpenAI format com `role` ∈ {system, user, assistant, tool} |
| `stream` | bool | não (default false) | SSE streaming quando true |
| `max_tokens` | int | não | Limite de saída |
| `temperature` | float | não | Default 1.0 |

### Response (não-streaming, 200 OK)

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1782314123,
  "model": "openclaw",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Olá! Sou o CartórioBot 📜..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 8,
    "total_tokens": 20
  }
}
```

### Erros comuns

| Status | Causa | Fix |
|---|---|---|
| 401 Unauthorized | Sem header `Authorization: Bearer ...` ou bearer errado | Adicionar Bearer com token ou `@Techno832466` |
| 401 com mensagem `"Missing bearer... url: https://api.openai.com/v1/responses..."` | OpenClaw tentou chamar OpenAI como upstream → 401 (chave OpenAI ausente ou provider errado) | Verificar agent.json: provider deve ser `opencode-go` (não `openai`) para modelo `deepseek-v4-flash`. **Pendente T4.9 — ver gateway-config-snapshot-t49.json** |
| 404 Not Found | Endpoint não habilitado | Habilitar `gateway.http.endpoints.chatCompletions.enabled: true` em openclaw.json (JÁ FEITO em T4.9) |
| 429 Too Many Requests | Rate limit acionado | Aguardar `Retry-After` header |

### Streaming (SSE)

```bash
curl -N https://agent.2notasudi.com.br/v1/chat/completions \
  -H "Authorization: Bearer @Techno832466" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw","messages":[{"role":"user","content":"olá"}],"stream":true}'
```

Retorna chunks `data: {...}\n\n` terminando em `data: [DONE]`.

## Pendências pós-T4.9 (bloqueio real)

**O endpoint HTTP existe e autentica, MAS a chamada LLM downstream ainda falha** porque:

1. **Provider errado em agent.json**: `provider: "openai"` deveria ser `"opencode-go"` (deepseek-v4-flash só existe no catálogo opencode-go)
2. **OPENCODE_GO_API_KEY ausente** no env do container (chave existe em `/home/node/.openclaw/workspace/.env.production` e `backend/.env.example`)
3. **max_context_tokens não definido** — AGENTS.md diz 1M mas openclaw.json não configura (default provavelmente 131k)

**Ação recomendada**:

| Quem | O quê |
|---|---|
| Gustavo | Injetar `OPENCODE_GO_API_KEY=sk-j03KVd...` no Easypanel env do serviço `cartorio_openclaw-gateway` |
| cartorio-dev / cartorio-n8n | Alterar `/home/node/.openclaw/agents/main/agent/agent.json` provider para `opencode-go` (testar antes — pode quebrar testes integração backend) |
| Gustavo | Decidir se configura `max_context_tokens=1000000` agora ou depois do Sprint 3 |

**NÃO executado por regra absoluta**: "NUNCA rotacionar chaves" e "NÃO inventar chave ausente" — chave já existe no projeto mas deploy/configuração é SUI Gustavo.

## Segurança (do OpenClaw docs)

- **Esta surface é full operator-access**: bearer aqui NÃO é narrow per-user scope
- Trate o token/password como owner/operator credential
- NÃO exponha publicamente — manter em Tailscale ou Traefik com IP allowlist
- Mantenha `gateway.controlUi.allowedOrigins` restrito em prod real (atualmente `"*"` para debug)

## Hot reload

Gateway watches `/home/node/.openclaw/openclaw.json` e aplica mudanças automaticamente em ~3s. Não precisa restart.

## Backup

Backup do config aplicado em T4.9: `infra/openclaw-agent/gateway-config-snapshot-t49.json` (no repo)
Backup dentro do container: `/home/node/.openclaw/openclaw.json.pre-t4.9-1782314031`

Para rollback:

```bash
ssh cartorio "docker exec cartorio_openclaw-gateway.1.* sh -c 'cp /home/node/.openclaw/openclaw.json.pre-t4.9-1782314031 /home/node/.openclaw/openclaw.json'"
```

## Modificado por

- T4.9 (2026-06-24 15:13 BRT): habilita `/v1/chat/completions` + documenta contrato HTTP
- Modified by Gustavo Almeida