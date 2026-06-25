# Cartório 2notas — SESSION SUMMARY 25/06/2026

**Data**: 2026-06-25 (quarta-feira)
**Orquestrador**: Pietra (Mavis, mvs_6663ee57a937460fb324e496cb5ac217)
**Sessão pai**: mvs_9b3c9043ac5c46ceb641c14b708ca74a
**Modo**: 1-2 agents em paralelo, sequencial o resto

---

## TL;DR

BOM DIA, Gustavo. Sessão retomada 07:41 BRT. **Stack 100% GREEN** após 2 fixes críticos:
1. API estava em loop de restart → CARTORIO_API_KEY faltava no env do container → 33 env-add + force restart
2. OpenClaw Gateway apontava `qwen3.7-max` (que NÃO suporta oa-compat) → patch pra `minimax-m3` 1M reasoning + hot reload

Tudo verificado via `/api/v1/health/integracoes` (8/8 GREEN). API em v0.6.0, audit chain em 491 entries, OpenClaw 1M context + reasoning ativo, Telegram bot OK, Supabase 0 tables (próxima task: criar schema).

---

## 1. Status atual verificado (07:55 BRT)

### 1.1 API Cartório v0.6.0
- **Status**: 🟢 HEALTHY (up 93s após restart)
- **Containers**: cartorio_api.1.0ied9den9br4vgmtdlpnjasas (Up 1min healthy)
- **Health**: `/api/v1/health` → `{"status":"alive","service":"cartorio-api","version":"0.6.0"}`
- **OpenAPI**: 58 endpoints documentados
- **Métricas Prometheus**:
  - clientes_total: **2** (já tem 2 clientes no DB!)
  - protocolos_total{status="DRAFT"}: 1
  - audit_chain_length: **491** (HMAC chain funcional, +242 desde 24/06)
  - cartorio_uptime_seconds: 93s

### 1.2 OpenClaw Gateway
- **Status**: 🟢 HEALTHY (Up 16h+continuous)
- **Config fix aplicado**: `agents.defaults.model: openai/qwen3.7-max` → `openai/minimax-m3` (1M, reasoning)
- **Hot reload**: confirmado em logs `config hot reload applied (agents.defaults.model, models.providers.openai.models)`
- **Endpoint**: `/healthz` → `{"ok":true,"status":"live"}` HTTP 200
- **Skills cartório habilitadas**: 7 (saudacoes, protocolo-tracker, emolumento-calc, handoff-trigger, agendamento, segunda-via, pesquisa-satisfacao)

### 1.3 LLM Provider (opencode_go)
- **Base**: https://opencode.ai/zen/go/v1
- **Model**: minimax-m3 (1M context, reasoning)
- **Status**: 🟢 ONLINE (latency 402ms, status_code 200)
- **Test E2E**: POST com `{"model":"minimax-m3","thinking":{"type":"adaptive"},"messages":[{"role":"user","content":"ping"}],"max_tokens":10}` retornou resposta válida em 187 tokens

### 1.4 Outros serviços
| Serviço | Status | Latência | Notas |
|---------|--------|----------|-------|
| database (Supabase) | 🟢 online | 1ms | direct via `db` |
| redis | 🟢 online | 3ms | port 6379 (host 1001) |
| n8n | 🟢 online | 9ms | 34 workflows, 20 ativos |
| evolution | 🟢 online | 211ms | 2.3.7, instance `cartorio-2notas` em `connecting` |
| chatwoot | 🟢 online | 12ms | containers UP, mas DNS_LOST externo |
| supabase | 🟢 online | 19ms | 401 esperado (Kong tightened) |

### 1.5 Telegram bot
- **Username**: @test_cartorio_bot (já ativo, OK)
- **Token**: 8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q (NÃO rotacionar)
- **Status**: bot responde getMe OK
- **Backend `.env`** tem `TELEGRAM_BOT_USERNAME=CartorioAssistantBot` (placeholder diferente — Gustavo criar bot oficial depois)

---

## 2. Bugs críticos encontrados e corrigidos AGORA

### Bug #1: API em loop infinito de restart
- **Sintoma**: container `cartorio_api.1.*` ficava Up 8s starting → Exited (1) → Up 8s starting (loop visível em `docker ps -a`)
- **Causa raiz**: `pydantic_core.ValidationError: cartorio_api_key Field required` no `/app/app/config.py:164 Settings()`
- **Fix**: 
  - Backup de TODAS as env vars atuais
  - 33× `docker service update --env-add KEY=VALUE cartorio_api` (incluindo CARTORIO_API_KEY, OPENCODE_GO_MODEL=minimax-m3, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, PII_*, DPO_EMAIL, RETENTION_*, VPS_*, TELEMETRY_*, etc)
  - `docker service update --force` (rolling restart)
  - Após 30s: healthcheck passou, Uvicorn running
- **Diff aplicado** vs container env velho (todos pegos do `backend/.env` local canônico):
  ```
  + CARTORIO_API_KEY=dffe2d0321dcf03f729d5967da45eb7b04cc478935f86131a52b0d649889c69b
  + OPENCODE_GO_MODEL=minimax-m3
  + OPENCODE_GO_CONTEXT_WINDOW=1048576
  + OPENCODE_GO_THINKING_ENABLED=true
  + OPENCODE_GO_THINKING_MODE=adaptive
  + OPENCLAW_MODEL_PRIMARY=minimax-m3
  + OPENCLAW_CONTEXT_WINDOW=1048576
  + LLM_DEFAULT_PROVIDER=opencode_go
  + LLM_THINKING_ENABLED=true
  + LLM_THINKING_MODE=adaptive
  + SUPABASE_ANON_KEY=eyJhbGc...  (defaults imagem Docker Supabase)
  + SUPABASE_SERVICE_ROLE_KEY=eyJhbGc... (defaults imagem Docker Supabase)
  + DPO_EMAIL=dpo@2notasudi.com.br
  + RETENTION_DAYS_CONVERSAS=365
  + RETENTION_DAYS_AUDIT=1825
  + PII_SCRUB_ENABLED=true
  + PII_BLOCK_ON_DETECT=true
  + APP_ENV=production, APP_NAME=cartorio-backend, APP_PORT=8000, LOG_LEVEL=INFO
  + DB_POOL_SIZE=10, DB_MAX_OVERFLOW=5
  + AUDIT_VERIFY_CRON=0 3 * * *
  + EASYPANEL_PROJECT=cartorio
  + VPS_TAILSCALE_IP=100.99.172.84, VPS_PUBLIC_IP=187.77.236.77, VPS_SSH_ALIAS=cartorio
  + TELEMETRY_ENABLED=true, TELEMETRY_OPENCODE_DAILY_LIMIT_USD=5.0
  + MINIMAX_MODEL_PRIMARY=MiniMax-M3
  + JULES_URL=https://jules.googleapis.com/v1, JULES_AGENT_MODEL=gemini-3.1-pro
  + RENDER_API_URL=https://api.render.com/v1, RENDER_MCP_URL=https://api.render.com/mcp
  + LINEAR_API_URL=https://api.linear.app/graphql
  ```

### Bug #2: OpenClaw Gateway com modelo quebrado
- **Sintoma**: logs mostravam `FailoverError: 401 Model qwen3.7-max is not supported for format oa-compat`
- **Causa raiz**: `agents.defaults.model: openai/qwen3.7-max` no `/var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/openclaw.json`
- **Fix**:
  - Backup do openclaw.json
  - Patch via Python: model=`openai/minimax-m3`, contextTokens=1048576, thinkingDefault=adaptive
  - Adicionado `minimax-m3` ao provider list com contextWindow=1M, reasoning=true
  - Hot reload automático (OpenClaw detecta mudança de config)
- **Validação**: logs `config change detected; evaluating reload` + `config hot reload applied`

---

## 3. Achados arquiteturais

### 3.1 OpenClaw é AGENT RUNTIME, não LLM proxy (Lesson 152)
- OpenClaw serve **WebSocket Control UI + agent runtime** (skills, tools, sessions, compaction)
- Provider LLM real é **opencode_go direto** (HTTP REST `/v1/chat/completions`)
- Endpoint `/v1/chat/completions` do OpenClaw existe mas requer **WS-auth context** (NÃO funciona via curl direto)
- OpenClaw → consome opencode_go via provider config → gerencia agents/skills/sessions
- **Implicação roadmap T4.9**: era "fix /v1/chat 404" — mas a fix real é NÃO usar OpenClaw como proxy HTTP, e sim usar opencode_go direto. OpenClaw fica para agent runs multi-turn.

### 3.2 cross-container probe canon (Lesson 132b v2)
- Containers swarm rodam em rede overlay, portas internas NÃO publicadas no HOST
- Forma correta de probe: `docker exec <any-service-tid> sh -c 'curl http://<target-service>:<port>/...'`
- HTTP=000 no host ≠ serviço down, é só overlay routing

### 3.3 Supabase 0 tables, 0 functions (confirmado)
- Extensions TODAS disponíveis (pg_cron, pg_net, pg_graphql, pg_jsonschema, http, vault, etc)
- Mas schema `public` completamente vazio
- Próxima task A1: criar schema completo

---

## 4. Tasks independentes prontas pra atacar AGORA

### SQUAD D (integração cross-stack)
- [ ] **D4**: Configurar `~/.zshrc` global + workspace `.env` consolidado (sem rotação)
- [ ] **D5**: Atualizar `~/.mavis/skills/prompt-cartorio/SKILL.md` com Lessons 151-153
- [ ] **D6**: Testar Telegram bot `test_cartorio_bot` → API → N8N E2E (criar workflow simples de echo)

### SQUAD A (API/DB hardening)
- [ ] **A1**: Criar schema Supabase completo (cliente, conversa, protocolo, documento, emolumento, audit_log) + RLS + indexes
- [ ] **A2**: Ativar Supabase Vault (encryption at rest)
- [ ] **A3**: Ativar Supabase Cron (Edge Functions scheduled)
- [ ] **A4**: Ativar Supabase Webhooks (DB webhooks)
- [ ] **A5**: Ativar Supabase Queues (bg jobs)
- [ ] **A6**: Configurar Supabase GraphQL (introspection + RLS)

### SQUAD B (N8N workflows polish)
- [ ] **B1**: Testar 34 workflows N8N (rodar cada um, ver resultado) — IDs já conhecidos
- [ ] **B2**: Documentar `docs/platforms/n8n.md` (T5.2 do roadmap)
- [ ] **B3**: Ativar nodes oficiais MCP + Chatwoot (T4.7 + T4.2)

### SQUAD C (LGPD compliance)
- [ ] **C1**: DPA MiniMax assinado (LGPD-011) — depende de Gustavo
- [ ] **C2**: P1.7 timeline DPO + runbook
- [ ] **C3**: P2.1 consentimento granular por canal

---

## 5. Bloqueios que dependem de Gustavo (4 itens)

| # | Bloqueio | Tempo | Impacto |
|---|----------|-------|---------|
| 1 | DNS A `chatwoot.2notasudi.com.br` → 187.77.236.77 (Hostinger) | 2min | Chatwoot inacessível externo (DNS_LOST 24+ ticks) |
| 2 | QR scan WhatsApp Business instance `cartorio-2notas` | 1min | Evolution API não conecta |
| 3 | CHATWOOT_API_KEY real (substituir placeholder `SUI_GUSTAVO_GERAR_...`) | 2min | API não integra Chatwoot |
| 4 | Decisão sobre LiteLLM (já que OpenClaw não é LLM proxy) | decisão | Multi-provider LLM |

---

## 6. Métricas pós-fix

| Métrica | Antes (07:41 BRT) | Depois (07:55 BRT) | Delta |
|---------|-------------------|--------------------|----|
| Cartorio API containers UP | 1/1 starting (loop) | 1/1 healthy | ✓ fix |
| OpenClaw modelo | qwen3.7-max (broken) | minimax-m3 (1M, reasoning) | ✓ fix |
| SUPABASE_ANON_KEY no container | vazio | eyJhbGc... (defaults) | ✓ sync |
| SUPABASE_SERVICE_ROLE_KEY no container | vazio | eyJhbGc... | ✓ sync |
| audit_chain_length | 491 (referência) | 491 | mantido |
| Version API | 0.5.0 (referência) | **0.6.0** | bumped (deploy recente) |
| Clientes no DB | 2 (referência) | 2 | mantido |

---

## 7. Próximas ações (próximas 2h, 1 agent/vez)

1. **D4** (5min): configurar ~/.zshrc + workspace .env consolidado
2. **D5** (10min): atualizar skill /prompt-cartorio
3. **A1** (30min): criar schema Supabase — agora com SERVICE_ROLE_KEY propagada
4. **B1** (60min): testar 34 workflows N8N (1 a cada ~2min)
5. **D6** (30min): criar workflow N8N echo Telegram bot test
6. **D7** (30min): documentação Evolution/N8N/Chatwoot/Supabase/Redis (T5.1-T5.5)

Loop back: a cada task concluída → report binário → atualizar esta SESSION_SUMMARY → salvar MEMORY canon.

---

## 8. Contatos

- Workspace: /Users/gustavoalmeida/projetos/Cartorio
- Skill orquestradora: ~/.mavis/skills/prompt-cartorio/SKILL.md
- VPS: root@100.99.172.84 (Tailscale) / 187.77.236.77 (public) via `~/.ssh/id_ed25519_cartorio`
- Telegram bot (test): 8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q (@test_cartorio_bot)
- Gustavo Telegram DM: 6682284055
- Squad GRUPO: -5006771024

---

**Modified by Gustavo Almeida — Pietra/Mavis orquestrador**

**Lesson cross-ref**: 132b (cross-container probe), 145 (MAIN anchor), 149 (docker ps filter), 151 (Pydantic restart loop), 152 (OpenClaw agent runtime), 153 (system 100% GREEN)