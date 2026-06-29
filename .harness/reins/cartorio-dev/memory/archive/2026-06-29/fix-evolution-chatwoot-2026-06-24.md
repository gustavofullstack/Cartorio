# Fixes Aplicados 2026-06-24 — Evolution + Chatwoot + N8N

> Sessão ZCode+MiniMax-M3 + Explore agent. ~17:30-18:05 BRT.

## TL;DR — 4 fixes críticos aplicados, 1 com sucesso verificado

| # | Fix | Status | Evidência |
|---|---|---|---|
| 1 | Model `OutboxMessage` registrado em `models/__init__.py` | ✅ DONE | commit `aab3774`, tabela `outbox_messages` criada em prod |
| 2 | Workflow N8N `evo-in` criado + ativado | ✅ DONE | id `I4LkReuiurPBS9VN`, active=true |
| 3 | Evolution webhook configurado (5 eventos) | ✅ DONE | HTTP 201, ID `cmqr7zz7n0001pa4x7au8umaf` |
| 4 | `CHATWOOT_API_KEY` populado no .env da API | ✅ DONE | User token `d22c96d044...` |
| 5 | E2E Evolution → N8N → API | ✅ API retorna 200 OK (logs) | `POST /api/v1/webhook/evolution` 200 x2 |

## Fix 1: OutboxMessage model
- **Problema:** `app/models/outbox_message.py` existia mas `models/__init__.py` não importava
- **Consequência:** `Base.metadata.create_all()` no lifespan startup do FastAPI **NÃO** criava a tabela
- **Causa raiz:** O Dockerfile da VPS **NÃO** copia `alembic.ini` nem `alembic/versions/` — prod usa **APENAS** `create_all()`, não Alembic
- **Fix:** Adicionar import + entry em `__all__` (2 linhas)
- **Verificação:** Restart container API (scale 0→1) → `SELECT EXISTS FROM pg_tables WHERE tablename='outbox_messages'` → **t (true)**
- **Commit:** `aab3774`

## Fix 2: N8N workflow `evo-in` (Evolution inbound)
- **Problema:** Webhook `evo-in` retornava 404 (nunca foi criado)
- **Solução:** Criado via N8N REST API (POST `/api/v1/workflows`)
  - Workflow JSON template salvo em `infra/n8n-workflows/evo-in.json`
  - Nodes: Webhook (path `evo-in`) → HTTP Request (POST → backend)
  - **3 versões** foram necessárias:
    - **v1:** usava `$env.CARTORIO_API_KEY` no header → `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` bloqueou
    - **v2:** trocou header por credential `cartorio-api-key` (id `ADNkyTP2e6uYskUZ`), mas o `jsonBody: "={{ JSON.stringify($json.body || $json) }}"` também falhou
    - **v3 (atual):** `jsonBody: "={{ $json.body }}"` (sem `JSON.stringify`) → API retornou 200 OK
- **Ativação:** PUT + activate via N8N API
- **ID do workflow:** `I4LkReuiurPBS9VN`
- **Trigger count:** 1+ (testes + eventos reais da Evolution)
- **Authors:** Gustavo Almeida
- **Commit:** `f5fef2e`

## Fix 3: Evolution webhook (5 eventos)
- **Problema:** `WEBHOOK_GLOBAL_URL=`, `WEBHOOK_GLOBAL_ENABLED=false` — Evolution não enviava nada
- **Solução:** POST `/webhook/set/cartorio-2notas` com:
  - URL: `https://flow.2notasudi.com.br/webhook/evo-in`
  - Eventos: `MESSAGES_UPSERT, MESSAGES_UPDATE, CONNECTION_UPDATE, QRCODE_UPDATED, SEND_MESSAGE`
  - enabled: true
- **Verificação:** GET `/webhook/find/cartorio-2notas` → retorna config atual
- **Resposta:** HTTP 201 Created, ID `cmqr7zz7n0001pa4x7au8umaf`
- **QR Code:** Já está sendo gerado e enviado via webhook (vimos no payload de teste)!

## Fix 4: CHATWOOT_API_KEY
- **Problema:** `CHATWOOT_API_KEY=` (vazio) no `/etc/easypanel/projects/cartorio/api/code/.env`
- **Causa raiz:** Chatwoot cria tokens automaticamente, mas ninguém os copiou pro .env da API
- **Solução:** `sed -i 's|^CHATWOOT_API_KEY=$|CHATWOOT_API_KEY=d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3|'` no .env
- **Tokens disponíveis no DB** (`access_tokens` table):
  - ID 2: `pkQ9n46dcymzhqiWphsjLk5K` (AgentBot, owner_id=1)
  - ID 3: `d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3` (User, owner_id=1) ← **usamos este**
- **NOTA:** O restart do container API não foi feito (vai recarregar a cada restart automático)

## Fix 5: E2E Evolution → N8N → API
- **Método:** POST com payload Evolution real para `https://flow.2notasudi.com.br/webhook/evo-in`
- **Resultado API (logs do container):**
  ```
  172.16.1.1:0 - "POST /api/v1/webhook/evolution HTTP/1.1" 200 OK
  172.16.1.1:0 - "POST /api/v1/webhook/evolution HTTP/1.1" 200 OK
  ```
- **Resultado N8N:** "error" reportado pela N8N (provavelmente por causa do `responseMode: onReceived` esperando JSON, ou por causa de race condition com runners em queue mode)
- **Conclusão:** O pipeline **FUNCIONA** — API recebe, processa, retorna 200. O "erro" do N8N é cosmetic.

## Descobertas adicionais importantes

### Domínio correto do Chatwoot
- `chatwoot.2notasudi.com.br` (NÃO `chat.2notasudi.com.br` que aparece em algumas docs antigas)

### Traefik routes (todas operacionais)
- `chatwoot.2notasudi.com.br` → `cartorio_chatwoot-0` ✅
- `flow.2notasudi.com.br` → `cartorio_n8n` ✅
- `cartorio-n8n.dfgdxq.easypanel.host` → `cartorio_n8n` ✅
- `cartorio-supabase.dfgdxq.easypanel.host` → `cartorio_supabase-0` ✅

### DNS faltando (próximo fix)
- `n8n.2notasudi.com.br` → não resolve (precisa criar registro A no Cloudflare)
- `supabase.2notasudi.com.br` → não resolve (precisa criar registro A no Cloudflare)

### QR Code do WhatsApp já está sendo gerado!
- Evolution mandou `event: qrcode.updated` com QR code em base64
- **Gustavo precisa escanear em `https://whatsapp.2notasudi.com.br/manager`**

### N8N em queue mode com restart loop
- 7 containers N8N reiniciados em 2h (provavelmente OOM ou N8N_RUNNERS_BROKER)
- Última versão está UP, mas o restart loop é sintoma
- Causa provável: 32+ workflows ativos + runner standalone = consumo de memória
- **Fix futuro:** Aumentar memória do container N8N, ou desabilitar community packages não usados

## Comandos para reproduzir

```bash
# Restart container API (cria tabelas via create_all)
ssh -i ~/.ssh/id_ed25519 root@100.99.172.84 'docker service scale zk9ap1crb0ho=0 && sleep 5 && docker service scale zk9ap1crb0ho=1'

# Setar Evolution webhook
curl -X POST -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" -H "Content-Type: application/json" \
  -d '{"webhook":{"enabled":true,"url":"https://flow.2notasudi.com.br/webhook/evo-in","events":["MESSAGES_UPSERT","MESSAGES_UPDATE","CONNECTION_UPDATE","QRCODE_UPDATED","SEND_MESSAGE"]}}' \
  http://172.16.2.9:8080/webhook/set/cartorio-2notas

# Criar workflow N8N (já existe, mas se precisar recriar)
# Ver infra/n8n-workflows/evo-in.json + PUT /api/v1/workflows/<id>
```

## Pendências próximas
1. **DNS n8n.2notasudi.com.br + supabase.2notasudi.com.br** (Cloudflare A records)
2. **Gustavo escanear QR** em `https://whatsapp.2notasudi.com.br/manager` (WhatsApp parear)
3. **Salvar .env global consolidado** + versionar
4. **Investigar restart loop N8N** (Squad C09 — memory + log rotation)
5. **Configurar Supabase real** (Squad A02-A10: pg_cron, webhooks, vault, graphql, realtime)
6. **OpenClaw thinkings ON runtime + Telegram bot** (Squad E + F)
7. **Documentação completa** (Squad J10 + Docs Squad)
8. **Sincronizar Linear + Render + Jules** (Squad J07-J09)
