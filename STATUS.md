# STATUS — Sessão 2026-07-02 (Bot Telegram 100% via LiteLLM Proxy)

> **TL;DR**: Bot Telegram respondendo em ~10s via LiteLLM Proxy → nemotron-3-ultra-free.
> Logs ao vivo confirmam 3x. Confirmação do Gustavo no celular ainda pendente.

## 🎯 O que foi feito nesta sessão

### Bugs corrigidos (3 combinados)
1. **OpenClaw rate-limit 100-400K** — `deepseek-v4-flash-free` tinha concurrency absurda.
   Fix: `agents.defaults.model = opencode_free_1/nemotron-3-ultra-free` em `/home/node/.openclaw/openclaw.json`
2. **httpx User-Agent 403 Cloudflare** — `python-httpx/X.X` bloqueado pelo Cloudflare no opencode.ai/zen.
   Fix: header `User-Agent: Mozilla/5.0 Chrome/120.0` em `app/integrations/opencode_generic.py`
3. **FastAPI Session dead em background task** — `background_tasks.add_task(_debounce, db=db)` pegava session fechada.
   Fix: removido `db` param + `logging.basicConfig(level=INFO)` em `main.py`

### Infraestrutura nova
4. **LiteLLM Proxy** (`cartorio_litellm-app:4000`) UP com **7 providers free**:
   - `opencode-free-1` (nemotron-3-ultra-free, NVIDIA 1M ctx)
   - `opencode-free-2` (mimo-v2.5-free, Xiaomi 1M ctx)
   - `opencode-free-3` (deepseek-v4-flash-free, 1M ctx)
   - `opencode-go` (minimax-m3 via opencode.ai/zen)
   - `mistral-free`
   - `openrouter-free`
   - `gemini-free`
5. **Bot Telegram usando LiteLLM como PRIMARY** — `idx=0 em 3.8-16s, sent=True`
6. **Schemas unificados no Supabase**: argilla, langfuse, litellm, n8n, evolution, openclaw, openclaw_state

### Serviços validados via DNS interno
- ✅ Langfuse-web (porta 80)
- ✅ Argilla-web (porta 6900)
- ✅ Argilla-elasticsearch (cluster green)
- ✅ LiteLLM Proxy (porta 4000)
- ✅ crwal4ai (bind OK, swarm VXLAN issue — ver Lesson 126)

## 📊 E2E Flow Validado (logs ao vivo)

```
Teste 1 (19:10): webhook→debounce 3s→LiteLLM 4s→sendMessage 200 OK→sent=True (T+10.0s)
Teste 2 (19:11): webhook→debounce 3s→LiteLLM 3.99s→sendMessage 200 OK→sent=True (T+9.18s)
Teste 3 (19:13): webhook→debounce 3s→LiteLLM 5.36s→sendMessage 200 OK→sent=True (T+10.5s)
Teste 4 (19:24): webhook→debounce 3s→LiteLLM 422→FALLBACK opencode_free_1 nemotron 2.04s→sendMessage 200 OK→sent=True (T+8.5s)
```

**Teste 4 confirma que a chain de fallback FUNCIONA**: LiteLLM upstream falhou (422 BadRequestError), sistema automaticamente tentou `opencode_free_1` direto, respondeu em 2.04s, enviou pro Telegram. **Bot auto-recuperou de falha do proxy LiteLLM sem intervenção manual**.

## 🔴 INCIDENTE CRÍTICO: Redis crash 19:20

```
19:20:39  Redis reiniciou (load RDB, 917 keys, 7.4MB)
19:20:40  Webhook retornou 500 (redis.exceptions.ConnectionError)
          swarm DNS stale apontando pra IP antigo do Redis
19:24:00  docker service update --force cartorio_redis → DNS atualizou (10.11.62.186 → 10.11.62.188)
19:24:41  Bot voltou a responder normalmente
```

**Causa raiz provável**: OOM kill do Redis (já tinha alerta antigo sobre "N8N restart loop OOM"). **Ação preventiva recomendada**:
- `sysctl vm.overcommit_memory=1` em `/etc/sysctl.conf`
- Configurar limite de memória no Redis: `--maxmemory 500mb --maxmemory-policy allkeys-lru`

## 📂 Arquivos entregues

```
docs/ARCHITECTURE.md                          ✅ Diagrama C2 + flow LiteLLM
infra/litellm/config.yaml                     ✅ 7 providers configurados
infra/litellm/README.md                       ✅ Runbook operacional
.brain/loop-state.json                        ✅ v2.4.0
~/.claude/projects/.../memory/MEMORY.md       ✅ Lessons 120-126
backend/app/config.py                         ✅ litellm_* settings
backend/app/integrations/opencode_generic.py ✅ UA + litellm dispatch
backend/app/integrations/fallback.py          ✅ litellm na chain
backend/app/api/v1/telegram.py                ✅ system prompt curto
backend/app/main.py                           ✅ logging.basicConfig
STATUS.md                                     ✅ Este arquivo
```

## ❌ Pendente (não bloqueadores do bot)

1. **Gustavo validar Telegram real no celular** (chat_id 6682284055)
   - Logs confirmam `sent=True` 3x, mas só Gustavo pode confirmar entrega real
   - Diagnóstico se não receber: BotFather / block / notif / spam filter / cache

2. **Cloudflare A record** `chatwoot.2notasudi.com.br`
   - Sem API token Cloudflare configurado
   - Só pode fazer via UI do Cloudflare

3. **crwal4ai VXLAN swarm issue**
   - Container bind OK, swarm overlay não encaminha
   - Workaround: recriar service com `--network host` (precisa autorização)

4. **SQUAD A14-A25, B6-B15, D18-D25, DOCS1-5, BRAIN2-B7** (~37 tasks)
   - Escopo separado, requer agentes paralelos + várias horas

## 🎯 Status Final

```
✅ Bot Telegram 100% funcional (logs confirmam)
❓ Aceite real do Gustavo (pendente)
⚠️ crwal4ai offline (workaround documentado)
⚠️ 37 tasks dos squads (escopo separado)
```

---

**Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-02 19:18 BRT**