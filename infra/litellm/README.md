# LiteLLM Proxy — Runbook operacional

> **Cartório 2º Notas Uberlândia** — proxy multi-provider LLM
> Turno 47 supremo (2026-07-02) — Gustavo Almeida

## 🎯 O que é

Proxy LLM opcional para múltiplos providers gratuitos. A API usa a cadeia
de fallback declarada no ambiente; LiteLLM só participa quando explicitamente
configurado e saudável.

## 📊 Estado operacional

O estado do serviço, imagem e disponibilidade dos modelos deve ser apurado
no ambiente alvo por health check autenticado. Esta documentação não contém
hostnames internos, credenciais, tokens, sal ou strings de conexão.

### Catálogo declarado (validar via `/v1/models`)

O arquivo `config.yaml` declara quatro modelos Zen (três slots
independentes), um Mistral, três OpenRouter, dois Google AI Studio e o
gateway OpenClaw. Os aliases efetivamente publicados podem variar por versão
do LiteLLM, então clientes devem consultar `/v1/models` autenticado em vez de
fixar nomes desta documentação.

## 🔧 Configuração

### VPS files
```
/etc/easypanel/projects/cartorio/litellm-app/config.yaml  ← montado em /app/config.yaml
```

### Variáveis no serviço

Injete todas pelo secret manager do ambiente:

```text
DATABASE_URL=<INJECT_FROM_SECRET_MANAGER>
LITELLM_MASTER_KEY=<INJECT_FROM_SECRET_MANAGER>
LITELLM_SALT_KEY=<INJECT_FROM_SECRET_MANAGER>
OPENCODE_ZEN_ACCOUNT_1_API_KEY=<INJECT_FROM_SECRET_MANAGER>
OPENCODE_ZEN_ACCOUNT_2_API_KEY=<INJECT_FROM_SECRET_MANAGER>
OPENCODE_ZEN_ACCOUNT_3_API_KEY=<INJECT_FROM_SECRET_MANAGER>
MISTRAL_API_KEY=<INJECT_FROM_SECRET_MANAGER>
OPENROUTER_API_KEY=<INJECT_FROM_SECRET_MANAGER>
GOOGLE_AI_STUDIO_API_KEY=<INJECT_FROM_SECRET_MANAGER>
OPENCLAW_GATEWAY_PASSWORD=<INJECT_FROM_SECRET_MANAGER>
```

### Env vars na API Cartório (apontam pra LiteLLM)
```text
LITELLM_API_KEY=<INJECT_FROM_SECRET_MANAGER>
LITELLM_BASE_URL=<INTERNAL_SERVICE_URL>
LITELLM_MODEL=<MODEL_ALIAS_FROM_V1_MODELS>
LLM_DEFAULT_PROVIDER=opencode_zen_account_1
LLM_FALLBACK_CHAIN=opencode_zen_account_1,opencode_zen_account_2,opencode_zen_account_3,opencode_free_3,opencode_free_1,opencode_free_2,opencode_go,openrouter,groq,mistral,google_ai_studio,openclaw,jules,antigravity
```

O backend executa a cadeia de fallback. O proxy LiteLLM é um provider
opcional e só é incluído mediante chave e health check válidos.

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
curl --fail-with-body "$LITELLM_BASE_URL/v1/models" \
  -H "Authorization: Bearer $LITELLM_API_KEY"
```

### Chat completion
```bash
curl --fail-with-body "$LITELLM_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
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
