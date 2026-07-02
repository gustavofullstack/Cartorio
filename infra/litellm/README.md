# LiteLLM Proxy — Runbook operacional

> **Cartório 2º Notas Uberlândia** — proxy multi-provider LLM
> Turno 47 supremo (2026-07-02) — Gustavo Almeida

## 🎯 O que é

Proxy LLM único que roteia entre 7 modelos free de múltiplos providers,
usado como `LLM_DEFAULT_PROVIDER=litellm` na API Cartório.

## 📊 Status (validado 2026-07-02)

```
Container: cartorio_litellm-app (1/1 UP)
Image:     ghcr.io/berriai/litellm:v1.85.0
Porta:     4000 (interno swarm)
DB:        postgresql://cartorio_supabase:5432/litellm
Master key: 0vrszdxd19zweryz7cfl
Salt:      0vrszdxd19zweryz7cfl
```

### 7 modelos disponíveis (chamando `/v1/models`)

| LiteLLM model | Provider real | Provider API | Context |
|---|---|---|---|
| `opencode-free-1` | nemotron-3-ultra-free | opencode.ai/zen (key 1) | 1M |
| `opencode-free-2` | mimo-v2.5-free | opencode.ai/zen (key 2) | 1M |
| `opencode-free-3` | deepseek-v4-flash-free | opencode.ai/zen (key 3) | 1M |
| `opencode-go` | minimax-m3 (minimax.io) | opencode.ai/zen (key 4) | 1M |
| `mistral-free` | mistral-free | api.mistral.ai | 1M |
| `openrouter-free` | multi-provider | openrouter.ai | 256K |
| `gemini-free` | gemini-3.5-flash | generativelanguage.googleapis.com | 1M |

## 🔧 Configuração

### VPS files
```
/etc/easypanel/projects/cartorio/litellm-app/config.yaml  ← montado em /app/config.yaml
```

### Env vars no service
```
DATABASE_URL=postgresql://admin:@Techno832466@cartorio_supabase:5432/litellm
LITELLM_MASTER_KEY=0vrszdxd19zweryz7cfl
LITELLM_SALT_KEY=0vrszdxd19zweryz7cfl
MISTRAL_FREE_API_KEY=qT8egbtiX6uokD9W5HTxg42mZPql8dxc
STORE_MODEL_IN_DB=True
PORT=4000
```

### Env vars na API Cartório (apontam pra LiteLLM)
```
LITELLM_API_KEY=0vrszdxd19zweryz7cfl
LITELLM_BASE_URL=http://cartorio_litellm-app:4000
LITELLM_MODEL=opencode-free-1
LLM_DEFAULT_PROVIDER=litellm
LLM_FALLBACK_CHAIN=litellm,opencode_free_1,opencode_free_2,opencode_free_3,opencode_go,openrouter,groq,mistral,google_ai_studio,openclaw,jules
```

## 🔍 Endpoints

| Endpoint | Auth | Descrição |
|---|---|---|
| `GET /health/liveliness` | não | Liveness probe |
| `GET /health/readiness` | não | Readiness probe |
| `GET /v1/models` | sim | Lista modelos |
| `POST /v1/chat/completions` | sim | OpenAI-compat |
| `POST /v1/embeddings` | sim | OpenAI-compat embeddings |

Auth: header `Authorization: Bearer <LITELLM_MASTER_KEY>`.

## 🧪 Como testar

### Da VPS via Docker exec
```bash
ACID=$(docker ps --filter 'name=^cartorio_api' --format '{{.ID}}' | head -1)
docker exec $ACID python3 -c "
import urllib.request, json
req = urllib.request.Request('http://cartorio_litellm-app:4000/v1/models',
    headers={'Authorization':'Bearer 0vrszdxd19zweryz7cfl'})
r = urllib.request.urlopen(req, timeout=5)
print(json.dumps(json.loads(r.read()), indent=2))
"
```

### Chat completion
```bash
curl -sS http://cartorio_litellm-app:4000/v1/chat/completions \
  -H "Authorization: Bearer 0vrszdxd19zweryz7cfl" \
  -H "Content-Type: application/json" \
  -d '{"model":"opencode-free-1","messages":[{"role":"user","content":"Diga oi"}]}'
```

## 🔄 Operações comuns

### Restart LiteLLM
```bash
docker service update --force cartorio_litellm-app
```

### Trocar provider default na API
```bash
docker service update --env-rm LLM_DEFAULT_PROVIDER cartorio_api
docker service update --env-add 'LLM_DEFAULT_PROVIDER=litellm' cartorio_api
docker service update --force cartorio_api
```

### Adicionar novo provider
1. Editar `infra/litellm/config.yaml`
2. SCP pra VPS: `scp infra/litellm/config.yaml root@100.99.172.84:/etc/easypanel/projects/cartorio/litellm-app/`
3. Restart: `docker service update --force cartorio_litellm-app`

### Ver logs
```bash
LLID=$(docker ps --filter 'name=litellm-app' --format '{{.ID}}' | head -1)
docker logs $LLID --tail 50
```

## 🐛 Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| HTTP 400 "Invalid model name" | Modelo passado errado (nemotron vs opencode-free-1) | Usar nome LiteLLM (`opencode-free-1`) |
| HTTP 401 | Master key errado | Verificar `LITELLM_API_KEY` no env da API |
| Timeout 30s | Provider upstream offline | LiteLLM tenta fallback automaticamente; ver logs |
| Container reiniciando | Prisma migrate falhou | Verificar `DATABASE_URL` |
| Conexão recusada do container API | DNS interno swarm stale | `docker service update --force cartorio_litellm-app` |

## ⚠️ Limitações conhecidas

- **Cache desabilitado** (LGPD) — toda request vai ao provider real
- **Logs verbose desabilitado** (silencioso em prod)
- **OpenClaw models** listados mas não roteados pelo LiteLLM (passa direto)

## 📚 Lessons relacionadas

- `lesson-121-litellm-proxy-2026-07-02.md` — Setup completo
- `lesson-120-telegram-bot-3-bugs-2026-07-02.md` — Por que chegamos aqui

---

**Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-02 19:08 BRT**