# SESSION_SUMMARY_2026-06-30-1535.md

## Realidade (15:35 BRT) vs PROMPT "8/8 GREEN"

Achado crítico durante diagnóstico em silêncio (Gustavo em LOOP STATE 8+).

### Status verificado via SSH VPS (187.77.236.77) + curl externo

| Serviço | PROMPT v4.2.0 diz | Real agora | Diagnóstico |
|---|---|---|---|
| API | UP v0.6.0 | UP v0.6.0 | OK |
| Evolution | UP v2.3.7 | UP v2.3.7 | OK |
| OpenClaw | UP live | UP live | OK |
| Redis | UP | UP | OK |
| N8N | UP | DOWN | migration-loop hell, exit(1) 6h atrás |
| Chatwoot | UP | UP+só | Traefik rota OK, mas endpoint sem auth/Tenant |
| Supabase | UP | DOWN | Traefik label errada → easypanel:3000 |

**Atual: 4/8 serviços realmente UP. PROMPT.json está desatualizado.**

### 3 quebras detalhadas

#### 1. N8N — `cartorio_n8n` Swarm "Running" mas refusing connections

- `curl 127.0.0.1:5678/healthz` → connection refused (porta NÃO responde mesmo container UP)
- Traefik log: `GET /healthz → 499 + 7-9s timeout` (request fica pendurado)
- Logs contêm: `Unknown filter parameter operator "string:notEqual"` + SIGTERM + `Deregistered all crons` + migration error pendente
- 5 falhas históricas (`task: non-zero exit (1)`) há 6h, subiu de novo há 3h, ainda travado
- **Fix proposto**: `docker service update --force cartorio_n8n` — 1 comando, reversível. NÃO executado, aguarda GO Gustavo.

#### 2. Chatwoot — container UP, app 200, mas 404 via domínio

- Container `cartorio_chatwoot.1` UP healthy 6h (porta 3000/tcp)
- `127.0.0.1:3000/` → 200 HTML Chatwoot (3ms)
- `127.0.0.1:3000/api/v1/accounts` → 200 OK (1.2ms) **internamente**
- MAS `https://chat.2notasudi.com.br/api/v1/accounts` → 404 + 3378 bytes (página HTML "Page not found" do próprio Chatwoot via Traefik)
- Memory: `CHATWOOT_API_KEY= VAZIO` em `backend/.env`
- Causa mais provável: Tenant ID não setado OU roteamento Chatwoot rejeitando requests por falta de token Bearer
- **Bloqueio**: SUI3 do PROMPT — Gustavo precisa gerar/copiar API key real pelo Chatwoot SuperAdmin UI

#### 3. Supabase — Traefik label errada (bug estrutural)

- `cartorio_supabase-kong-1` UP healthy 6h, escutando 8000/tcp (OK)
- Traefik log: `GET supbase.2notasudi.com.br/auth/v1/health → 502 em 2ms`, router `https-cartorio_supabase-1@file` apontando pra `http://easypanel:3000` (label errada!)
- Memory §Traefik manual: "Easypanel gera dynamic config via yml do projeto, NÃO Swarm labels"
- **Fix proposto**: criar/editar `/etc/easypanel/projects/cartorio/traefik/dynamic/custom.yaml` com router correto pra Kong
- NÃO executado — mudança persistente em prod requer GO Gustavo

### Outros achados durante diag

- `cartorio_hermes` Swarm 1/1 — service NOVO não documentado em PROMPT.json v4.2.0
  - PROMPT BLOCO 19.11 menciona "Hermes gateway PLANO APRESENTADO aguardando GO"
  - Container deployed mas prompt não atualizado
- `cartorio_n8n-runner` 5680/tcp — bate com Lesson 47v5 (dual-port)
- `cartorio_supabase-functions-1`, `cartorio_supabase-realtime-1`, `cartorio_supabase-supavisor-1` em loop **Restarting** agora (a cada 25-40s). Sintoma ou causa do Kong label issue?
- `cartorio_supabase-analytics-1` em estado "unhealthy" — silencioso até agora

### Pendências (ação Gustavo)

| # | Pendência | Tipo | Comando/ação |
|---|---|---|---|
| 1 | Restart N8N | operacional reversível | `docker service update --force cartorio_n8n` |
| 2 | Fix Supabase Traefik label | config persistente prod | editar custom.yaml |
| 3 | Chatwoot API key real | UI-only Gustavo | SuperAdmin Chatwoot |
| 4 | Atualizar PROMPT.json com status real | docs | adicionar nota v4.2.1 |
| 5 | Investigar Supabase functions/realtime/supavisor loop | causa-raiz | ssh logs container specific |

### Pendências (próxima sessão, pós-loop)

- Validar M3 quota pós-reset (Lesson 212 confirmou reset 14:00 BRT)
- Validar 9+ sessões Paperclip paralelas não corromperam config (Lesson 187)
- Se Gustavo responder de fato, executar restart N8N + corrigir custom.yaml Supabase (estes 2 destravam 50% do backlog)

---

Sessão: mvs_8ccc2e9f0ccf4472853fe143ecb71726
Acumulado: 3ª resposta em loop state, decidi parar textão + salvar achados. Próxima sessão REAL retoma.
Modified by Gustavo Almeida
