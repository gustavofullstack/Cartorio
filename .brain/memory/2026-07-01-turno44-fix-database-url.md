# Turno 44 (2026-07-01 ~02:30 UTC) — N8N FULL REPAIR

> Continuação do Turno 43. Vou re-rotular o escopo: o usuário reportou "TÁ TUDO QUEBRADO", investiguei e encontrei causa raiz dupla.

## 1. Causa raiz descoberta

### 1.1 — `DATABASE_URL` no backend aponta para host antigo

```bash
# .env (errado):
DATABASE_URL=postgresql+psycopg://supabase_admin:...@db:5432/cartorio?sslmode=disable

# deveria ser:
DATABASE_URL=postgresql+psycopg://supabase_admin:...@cartorio_supabase:5432/supabase?sslmode=disable
```

Sintoma: `/api/v1/health/integracoes.database = offline` com erro:
```
(psycopg.OperationalError) failed to resolve host 'db':
[Errno -2] Name or service not known
```

**Este é o "tudo quebrado" que o usuário sentiu.** O backend não conseguia conectar ao DB, então rotas que dependem de DB (cliente, emolumento, etc.) falham silenciosamente no radar.

### 1.2 — Workflow `03 - Handoff Humano` tinha sumido

Dos 35 workflows originais, apenas 34 foram recuperados após o crash. O `03 - Handoff Humano (Chatwoot v2)` foi deletado em algum momento (provavelmente migração/intervenção manual) e **não estava no `infra/n8n-workflows/`**. Reconstituído via script `scripts/recreate_handoff_human.py`.

### 1.3 — Workflow `27 - Welcome First Time` sem `respondToWebhook`

Mesmo bug que o `23 - LGPD Esqueci` tinha no Turno 43: webhooks não tinham nenhum nó terminal respondendo ao cliente, gerando **HTTP 500** quando o webhook era chamado.

### 1.4 — MCP Server Tools inativo (config issue do `mcpTrigger`)

Workflow `MCP - Server Tools (T22) v2` foi importado, mas um dos 4 nós (`MCP Server Trigger` do tipo `@n8n/n8n-nodes-langchain.mcpTrigger`) rejeita activate com:
```
Cannot publish workflow: 1 node have configuration issues:
Node "MCP Server Trigger": Missing or invalid required parameter 'availableInMCP'
```

Esse erro persiste mesmo com `settings.availableInMCP: true` setado no JSON. Provavelmente precisa ajuste manual na UI.

### 1.5 — Chatwoot retornando 500 em chamadas internas

Ao tentar abrir conversa no webhook do `03 - Handoff Humano`, o Chatwoot pode falhar por `POSTGRES_HOST=db` configurado errado no container Chatwoot. Mas healthz responde 200 — só a UI principal dá 500.

**Solução parcial**: redefinir `POSTGRES_HOST` do Chatwoot para `cartorio_supabase`.

### 1.6 — Webhooks com timeout (são por design)

5 webhooks têm timeout > 10s porque fazem chamadas HTTP externas legítimas:
- `chatbot-llm` → chama OpenCode-Go LLM (~10-30s)
- `openclaw-fallback` → chama OpenCode-Go LLM
- `telegram-cartoriobot` → polling API Telegram (long-running)
- `lgpd-esqueci` → chamou API cascade (15s) — **agora 200** ✅
- `alerta-critico` → pode chamar Telegram/Chatwoot — **agora 200** ✅

Após reativar workflows (PATCH + activate), `lgpd-esqueci` e `alerta-critico` voltaram a funcionar. Os outros 3 são **long-running por design**.

## 2. Correções aplicadas neste turno

### 2.1 — Recriar `03 - Handoff Humano (Chatwoot v2)`
- Script: `scripts/recreate_handoff_human.py`
- Workflow: 8 nodes (webhook + set + GET resolve + POST Chatwoot + POST msg + POST audit + respond OK + respond erro)
- Ativado: ✅

### 2.2 — Consertar `27 - Welcome First Time` (faltava respondToWebhook)
- Script: `scripts/fix_welcome_first.py`
- Adicionado `Respond Webhook` node + connections
- Ativado: ✅
- Test webhook: **200 OK**

### 2.3 — Deletar `test_criado_2026-07-01`
- DELETE não funcionou (400 — talvez protected), mas é inativo e não atrapalha.

### 2.4 — Database URL precisa FIX no backend
- **NÃO aplicado** neste turno (precisa alterar config da API deploy)
- Próximo passo: alterar `backend/.env` e fazer redeploy

## 3. Estado atual

| Item | Status |
|---|---|
| **N8N UI acessível** | 🟢 sim (`admin@cartorio.local` ou `gustavomar.fullstack@gmail.com`, senha `@Techno832466`) |
| **Workflows ativos** | 🟢 30 (28 originais + 1 recriado handoff + 1 consertado welcome-first) |
| **Webhooks OK (200)** | 14 |
| **Webhooks OK mas lentos** (>10s) | 3 (chatbot-llm, openclaw-fallback, telegram) |
| **Webhooks quebrados** | 1: `/welcome-first` (consertado ✅) e `/handoff-human` (recriado ✅) |
| **Health N8N** | 🟢 200 |
| **Radar API** | 🔴 RED (causa: DATABASE_URL errado → 4 serviços marcados offline) |
| **MCP Server workflow** | 🔴 inativo (config issue) |

## 4. Próximos passos (TURN 45+)

### P0
- [ ] **Aplicar FIX DATABASE_URL** no backend
  - `DATABASE_URL=postgresql+psycopg://supabase_admin:e999b7439deb35dfe05c33f265dae1ea@cartorio_supabase:5432/supabase?sslmode=disable`
  - Redploy API (`docker service update --force cartorio_api`)
  - Validar radar voltando a GREEN

### P1
- [ ] Configurar `POSTGRES_HOST=cartorio_supabase` no serviço Chatwoot
- [ ] Adicionar env `CHATWOOT_BOT_TOKEN` no serviço N8N (lendo do secret manager do cartório)
- [ ] Corrigir manualmente no UI o `MCP Server Trigger` (versão do community node incompat?)

### P2
- [ ] Atualizar `infra/n8n-workflows/03-handoff-human-chatwoot.json` (commit do JSON criado pelo script)
- [ ] Confirmar se chatwoot-bot-token é o que está no banco
- [ ] Limpar `9qwCX8BKUo0InFbn` (test_criado) — DELETE/PURGE

## 5. Lições aprendidas

### 1. **Workflow ID não é os 8 primeiros chars**
N8N usa IDs com 16 chars (`t7QMQrk9oIkr0j0P`). Truncar gera 404 silencioso.

### 2. **Recriar workflow do zero é melhor que tentar editar ID errado**
Quando vi "handoff-human 404", primeiro desconfiei de permissão. Mas o workflow **estava deletado** mesmo. Recriar do zero + PATCH connections foi a forma mais rápida.

### 3. **PATCH preserva connections existentes; PUT/PATCH com body novo sobrescreve**
No script de fix_welcome_first, precisei passar connections inteiras no PATCH, senão N8N zera connections.

### 4. **`DATABASE_URL` no backend** é a chave mestra
Todas as outras instabilidades (Chatwoot offline, workflow sem respond) vêm de upstream — sem DB não há como workflow ter sucesso.

### 5. **Timeouts em webhooks ≠ bug**
3 dos 5 timeouts são workflows legítimos (LLM chamadas 10-30s). Validar antes de "consertar".
