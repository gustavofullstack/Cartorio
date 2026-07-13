# PLANO INTEGRAÇÃO TOTAL — Cartório 2º Notas · 2026-07-13

> **Versão**: 1.0.0 (real, não aspiracional)
> **Owner**: Gustavo Almeida
> **Executor**: TRAE SOLO M3 (sequencial, sem spawn paralelo)
> **Critério de done**: binário por task, evidência verificável
> **Tempo estimado**: ~3-5h se executado em sessões

## Premissas (validadas agora, não memory)

- API Cartório: ✅ `api.2notasudi.com.br → 200`
- Chatwoot: ✅ `chat.2notasudi.com.br → 200` + 10 conversas inbox=2 whatsapp-sim
- Redis: ✅ `cartorio_redis.1.6pf42od3ualpp8gtwaozakfu8 healthy`
- Supabase: ✅ `cartorio_supabase.1.vuc04zy62kbz4i1jdwjbu26d4 healthy`
- OpenClaw Gateway: ✅ `cartorio_openclaw-gateway.1.7gdyaknj8d1dvzqcwwipxdsrp healthy`
- LobeChat: 🟡 container UP, falta DNS público + env OpenAI_KEY real
- N8N: 🔴 offline (DNS flow.2notasudi.com.br 404)
- Evolution API: 🟡 acabou de subir (1s)
- Telegram: 🔴 token revogado (não usado neste plano)

## F0 (NÃO EXECUTADO — Gustavo decide quando)

| Task | Tipo | Descrição | Done quando |
|------|------|-----------|-------------|
| F0.1 | Gustavo | Regenerar token Telegram via @BotFather | novo token colado |
| F0.2 | Gustavo | Escanear QR Evolution API `whatsapp.2notasudi.com.br/manager` | instance state=open |
| F0.3 | Gustavo | A record Cloudflare `lobe → 187.77.236.77` | `lobe.2notasudi.com.br → 200` |
| F0.4 | Gustavo | A record Cloudflare `flow → 187.77.236.77` (criar router Traefik) | `flow.2notasudi.com.br → 200` |

## F1 — Integração ponta-a-ponta (6 tasks, ~2h)

| # | Task | Done quando |
|---|------|-------------|
| F1.1 | Validar `/api/v1/health/radar` retorna 200 + services ≥ 5/7 online | curl 200 + JSON com 5+ serviços `"online"` |
| F1.2 | Importar `/openapi.json` no Postman collection + publicar | `docs/POSTMAN_COLLECTION.json` + commit |
| F1.3 | Validar chatwoot_sim end-to-end (1 persona → 1 conversa → 1 msg → valida via API) | stats.py mostra 1 conversa inbox=2 |
| F1.4 | Validar openclaw health (`/health` + `/v1/agents`) | 200 OK em ambos, JSON válido |
| F1.5 | Webhook chain test: POST `/api/v1/webhooks/chatwoot` simulado | retorna 200 + cria contato no Supabase |
| F1.6 | Health radar 7/7 (sem depender de N8N/Evolution) | status: green OU contorna com feature flag |

## F2 — Hardening qualidade (5 tasks, ~2h)

| # | Task | Done quando |
|---|------|-------------|
| F2.1 | `cd backend && uv run pytest tests/ --no-cov -q` | exit 0, ≥1500 tests passing |
| F2.2 | `cd backend && uv run mypy app/` | 0 errors |
| F2.3 | `cd backend && uv run ruff check .` | 0 errors |
| F2.4 | Validar `/api/v1/openapi.json` é válido (spec 3.1) | json.loads OK + 50+ paths |
| F2.5 | Validar `/api/v2/info` + endpoints v2 (alpha sunset 2027-12-31) | 200 OK, todos os endpoints OK |

## F3 — Memory + brain + docs (4 tasks, ~1h)

| # | Task | Done quando |
|---|------|-------------|
| F3.1 | Atualizar `.brain/memory/2026-07-13.md` com estado final pós-plano | arquivo < 500 linhas, sections F0-F3 |
| F3.2 | Atualizar `.brain/loop-state.json` com métricas reais | squads % update |
| F3.3 | Atualizar `.brain/index.md` com nova arquitetura validada | links sem 404 |
| F3.4 | Atualizar `/Users/gustavoalmeida/.claude/projects/.../MEMORY.md` index | lessons 166-170 adicionadas |

## F4 — Opcional (após F1-F3 done)

| # | Task | Done quando |
|---|------|-------------|
| F4.1 | Push dos commits pendentes (949418b, a3e973d, 81c6d20) | `git status -sb` clean upstream |
| F4.2 | Criar A record Cloudflare + router Traefik p/ LobeChat (se Gustavo decidir) | `lobe.2notasudi.com.br → 200` |
| F4.3 | Regenerar token Telegram + atualizar webhook URL | `getMe` 200, webhook URL válido |
| F4.4 | Ativar Tailscale permanente (colar auth key + wizard) | `tailscale status` mostra nó online |

## Princípios de execução

1. **1 task por vez, sequencial**, sem spawn paralelo (limite TRAE M3 quota 5h)
2. **Critério binário**: cada task tem teste exato. Se não passa, não fecha.
3. **Commit por task**: 1 task = 1 commit `feat/fix/chore: ...` + Modified by Gustavo Almeida
4. **Memory update**: cada commit relevante atualiza `.brain/memory/`
5. **Validar antes de próxima**: rodar curl/test antes de marcar `[WORK]`
6. **HOLD honesto**: se bloqueado, parar e perguntar (não inventar fix)

## Comando de execução sugerido

```bash
# Após cada task, rodar:
cd /Users/gustavoalmeida/projetos/Cartorio
git status -sb
# Se mudou algo relevante, commitar:
git add <files>
git -c user.email="gustavo@cartorio.local" -c user.name="Gustavo Almeida" \
    commit -m "feat(sim): task F1.X <descrição> Modified by Gustavo Almeida"
```

## Quando parar

- F1-F3 completas (15 tasks) → plano encerrado, próximo ciclo = F4 opcional
- F0 bloqueado Gustavo → parar e pedir input
- Quota TRAE 5h > 80% → parar e avisar
- Loop infinito detectado (>5 tasks repetidas sem progresso) → parar e questionar estratégia

## Métricas alvo ao final

- 0 regressões pytest
- 0 mypy errors
- 0 ruff errors
- Health radar com 5/7 serviços online (N8N/Evolution aceito offline se F0 não feito)
- OpenAPI spec válido + Postman collection versionada
- Memory atualizada com lessons 166-170
- Brain index sincronizado com realidade
- Commits isolados por task, todos com Modified by Gustavo Almeida

Modified by Gustavo Almeida + ZCode/Mavis — 2026-07-13 17:50 BRT