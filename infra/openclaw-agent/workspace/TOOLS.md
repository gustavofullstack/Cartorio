# TOOLS.md - Notas Técnicas Específicas do Cartório

## Endpoints da API (api.2notasudi.com.br)

Base URL: `https://api.2notasudi.com.br`

| Endpoint | Método | Auth | Função |
|---|---|---|---|
| `/health` | GET | — | Liveness check |
| `/api/v1/health/radar` | GET | — | Status de DB, Redis, N8N, OpenClaw, Evolution |
| `/api/v1/integrations/opencode/test` | POST | `X-API-Key` | Proxy para OpenCode-Go (deepseek-v4-flash) |
| `/api/v1/emolumento/calcular` | GET | `X-API-Key` | Calcula emolumento MG 2026 (tipo, folhas, urgência) |
| `/api/v1/agendamento/disponibilidade` | GET | `X-API-Key` | Lista slots livres |
| `/api/v1/protocolo` | POST | `X-API-Key` | Cria protocolo (LGPD) |
| `/api/v1/webhook/evolution` | POST | `X-API-Key` | Recebe mensagens WhatsApp |
| `/api/v1/webhook/chatwoot` | POST | `X-API-Key` | Recebe eventos Chatwoot (handoff) |
| `/mcp-servers` | GET | — | Lista tools do nosso MCP server |
| `/docs` | GET | — | Swagger UI |
| `/redoc` | GET | — | Redoc UI |

**API Key compartilhada:** `cartorio-api-shared-secret-v1` (header `X-API-Key`)

## Domínio Tailscale (rede privada)

- `vps-cartorio.tail2fe279.ts.net` → OpenClaw Control UI (token via query string)
- `100.99.172.84:18789` → OpenClaw gateway direto (sem TLS, só pra debug)
- `100.83.180.16` → MacBook Pro do Gustavo (admin Tailscale)

## SSH shortcut

```bash
ssh cartorio           # conecta no VPS (Tailscale ou pub key)
ssh 100.99.172.84      # IP direto
```

## Docker Swarm comandos úteis

```bash
docker service ls | grep cartorio
docker service ps cartorio_openclaw-gateway
docker exec $(docker ps -q --filter "name=cartorio_openclaw-gateway") openclaw devices list --json
docker logs $(docker ps -q --filter "name=cartorio_openclaw-gateway") --tail 50
```

## N8N (flow.2notasudi.com.br)

- API Key pública (header `X-N8N-API-KEY`)
- Workflow principal: `12 - Chatbot LLM End-to-End` (id `WuQAi2ttarGGdPyD`, active)
- Webhook principal: `POST /webhook/chatbot-llm`
- 15 workflows Published, 0/1 page (tem mais na page 2)

## Supabase (supbase.2notasudi.com.br)

- Default Project, 0 tables (N8N DB schema não migrada ainda)
- 1 function (chatwoot)
- Kong 401 esperando API key
- User: `supabase_admin` (cartorio-network container)
- Senha: `e999b7439deb35dfe05c33f265dae1ea` (env `POSTGRES_PASSWORD` no Supabase)

## Redis

- Host: `cartorio_redis:6379` (rede compose)
- Porta externa: `1001` (host: `187.77.236.77`)
- Senha: `@Techno832466`
- Dbsgate (UI): `http://187.77.236.77:3000/projects/cartorio/app/redis-dbgate`

## Evolution API (whatsapp.2notasudi.com.br)

- Endpoint manager: `/manager`
- NÃO conectar número WhatsApp ainda (PENDÊNCIA)
- Integração com N8N via community node `n8n-nodes-evolution-api`

## OpenCode-Go (LLM provider)

- Base URL: `https://opencode.ai/zen/go/v1`
- API Key: `sk-j03KVdV6rDkSW1D2KmrmbCL8zRjhBw0IkOes2BNCEetOokTnbLJXwc7AyltoRscr`
- Model default: `deepseek-v4-flash` (low cost)
- Configurado na API env: `OPENCODE_GO_API_KEY` (não commitado, ver `backend/.env.example`)

## Senhas / tokens recorrentes (NUNCA logar texto puro)

- **Easypanel:** `@Techno832466`
- **VPS SSH user:** `gustavomar.fullstack@gmail.com` (chave ed25519)
- **OpenClaw gateway password:** `@Techno832466`
- **OpenClaw gateway token:** `fz1qzo2xka8n82rn62irscuqws75mm1e17mpsnxzqlp13z1p35skrbg2ck8yg8pg` (em env do container)
- **API shared secret:** `cartorio-api-shared-secret-v1`
- **N8N API Key:** (JWT no contexto da sessão)
- **N8N MCP token:** (JWT no contexto)

## Cron jobs existentes

- `sprint2-p0-status-check` — verifica status do P0 PII blocker a cada 30min
- `p0-pii-blocker-watch` — observer do mesmo

## Branches (regra do Gustavo)

- **NUNCA criar worktree.** Tudo na `master`. Merge + delete worktrees.
- Cada commit direto em master com mensagem descritiva.

## Comandos "mágicos" do Gustavo (citados literalmente)

- "marcha total" → executar sem parar
- "salva na memoria" → registrar decisão/lição em `docs/` ou commit
- "transcreve em micro-skill" → se uma ação se repetir 2+ vezes, criar skill
- "use o Chrome aberto" → interage com o que ele já tem aberto no navegador
