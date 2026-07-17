---
name: sre-incident-2026-07-14-502-recovery
description: Incident P0 502 Bad Gateway em 7 domínios prod em 2026-07-14. Causa raiz: DATABASE_URL dos serviços dependentes (evolution-api/chatwoot/n8n) apontando para IP externo 10.11.211.12 (unreachable) e credenciais supabase_admin/e999... que não batem com o Postgres recriado (POSTGRES_USER=admin / POSTGRES_DB=supabase). cartorio_api OK porque usa DNS interno cartorio_supabase + credenciais admin. Restart --force NÃO resolve — env vars erradas. Fix manual via Easypanel UI.
type: project
date: 2026-07-14
agent: cartorio-sre
severity: P0
status: incident-open-needs-gustavo
tags: [sre, outage, easypanel, swarm, postgresql, supabase, chatwoot, evolution-api, n8n]
---

# Lesson 176 — SRE Incident 502 recovery 2026-07-14 (cartorio)

## TL;DR

- **7 domínios prod DOWN** (`whatsapp`, `chat` = 502; `flow`, `supbase` = 404); **3 WORK** (`api`, `agent`, `easypanel` = 200).
- **Traefik WORK** (`easypanel-traefik 1/1`, logs mostram requests HTTP/2 roteadas). **Causa NÃO é Traefik.**
- **cartorio_api WORK** (`/health 200`, `/api/v1/health/radar` retorna `database: online`).
- **Causa raiz**: `cartorio_supabase` rodando com `POSTGRES_USER=admin / POSTGRES_DB=supabase` (Easypanel sobrescreveu), mas os serviços dependentes ainda têm DATABASE_URL com:
  - **IP externo `10.11.211.12:5432`** (evolution-api, chatwoot) → `Host is unreachable` (`nc: connect to 10.11.211.12 port 5432: Operation now in progress`).
  - **Credenciais antigas `supabase_admin:e999b7439deb35dfe05c33f265dae1ea`** (n8n) → `password authentication failed`.
- **`docker service update --force` NÃO resolve** — env vars erradas persistem.
- **Ação corretiva requer Easypanel UI** (ou `docker service update --env-add/--env-rm`) para alinhar credenciais + apontar para DNS interno `cartorio_supabase:5432`.

## Estado dos serviços (pós-incidente, 2026-07-15 13:42 UTC)

```
NAME                           MODE         REPLICAS   IMAGE
cartorio_api                   replicated   1/1        easypanel/cartorio/api:latest          [WORK]
cartorio_chatwoot              replicated   0/1        chatwoot/chatwoot:latest               [DOWN — DB unreachable]
cartorio_chatwoot-sidekiq      replicated   1/1        chatwoot/chatwoot:latest               [WORK, mas inútil sem web]
cartorio_evolution-api         replicated   0/1        evoapicloud/evolution-api:latest       [DOWN — prisma P1001]
cartorio_lobechat              replicated   1/1        lobehub/lobe-chat:1.143.3              [WORK]
cartorio_n8n                   replicated   1/1        docker.n8n.io/n8nio/n8n:latest         [DOWN — DB_INIT crashloop]
cartorio_openclaw-gateway      replicated   1/1        ghcr.io/openclaw/openclaw:latest       [WORK]
cartorio_redis                 replicated   1/1        redis:8.8                              [WORK]
cartorio_supabase              replicated   1/1        pgvector/pgvector:pg17                 [WORK — mas sem dados de roles velhos]
easypanel                      replicated   1/1        easypanel/easypanel:latest             [WORK]
easypanel-traefik              replicated   1/1        traefik:3.6.7                          [WORK]
```

## Diagnóstico passo a passo (10 tasks executadas)

### T001 — `docker service ls`
- 17 serviços no swarm, 1 node leader (`srv1769726`), Docker 29.5.2.
- Stacks: `docker stack ls` retornou VAZIO (Easypanel faz deploy direto, sem compose stack).
- Networks: `cartorio_monitoring`, `easypanel`, `easypanel-cartorio`, `ingress`.

### T002 — Logs por serviço
- `cartorio_supabase` logs: `FATAL: password authentication failed for user "supabase_admin"` + `DETAIL: User has no password assigned`.
- `cartorio_chatwoot` logs: `PG::ConnectionBad: connection to server at "10.11.211.12", port 5432 failed: Host is unreachable`.
- `cartorio_n8n` logs: `Initial database connection attempt 1 failed: password authentication failed for user "supabase_admin"` × 5, depois `Error: There was an error initializing DB` → crashloop.
- `cartorio_evolution-api` logs: `Error: P1001: Can't reach database server at 10.11.211.12:5432` (Prisma).
- `easypanel-traefik` logs: 200 OK em `/health` e `/api/v1/health/radar` para `cartorio_api`; **502** explícito para `cartorio_chatwoot-0` e `cartorio_evolution-api-0` (confirmando que o erro é upstream, não Traefik).

### T003 — Traefik restart
- **Não necessário** — Traefik 1/1 estável, logs mostram HTTP/2 funcional. Restart seria overhead.

### T004 — `docker service update --force`
- `cartorio_evolution-api` converged → continua 0/1 (Prisma migrate continua falhando com mesmo erro).
- `cartorio_chatwoot` → `service update paused: update paused due to failure or early termination`.
- `cartorio_n8n` converged → 1/1 reportado mas serviço crashloop no DB init.
- **Conclusão**: `--force` não conserta env vars erradas. Não executar este passo cegamente em incidentes de DB.

### T005 — Health check interno (`cartorio_api`)
- **WORK**: `GET /health` → `{"status":"ok","service":"cartorio-backend","version":"0.6.0"}`
- **WORK**: `GET /ready` → `{"status":"ready","audit_chain_initialized":true}`
- **WORK (parcial)**: `GET /api/v1/health/radar` → `{"status":"red","services":{"database":"online","redis":"online","n8n":"offline","openclaw":"online","evolution":"offline","chatwoot":"offline","supabase":"online"}}`. Database online = API conecta via `admin@cartorio_supabase:5432`.

### T006 — Tail logs (já feito em T002)

### T007 — `curl 7 domínios externos`

```
api:       code=200 time=0.145s  [WORK]
flow:      code=404 time=0.067s  [404 — easypanel error-page, sem route]
whatsapp:  code=502 time=0.074s  [DOWN — evolution-api 0/1]
chat:      code=502 time=0.070s  [DOWN — chatwoot 0/1]
agent:     code=200 time=0.089s  [WORK]
supbase:   code=404 time=0.153s  [404 — easypanel error-page, sem route]
easypanel: code=200 time=0.071s  [WORK]
```

### T008 — Causa raiz

**Matriz de env vars (Docker service inspect)**:

| Serviço | DB_HOST | DB_USER | DB_PASS | DB_NAME | Status |
|---|---|---|---|---|---|
| `cartorio_api` | `cartorio_supabase` (DNS swarm) | `admin` | `@Techno832466` | `supabase` | ✅ BATE |
| `cartorio_n8n` | `cartorio_supabase` (DNS swarm) | `supabase_admin` | `e999b7439deb35dfe05c33f265dae1ea` | `n8n` | ❌ user/pass NÃO bate |
| `cartorio_chatwoot` | `10.11.211.12` (IP externo!) | `admin` | `@Techno832466` | `chatwoot` | ❌ IP unreachable |
| `cartorio_evolution-api` | `10.11.211.12` (IP externo!) | `supabase_admin` | `e999b7439deb35dfe05c33f265dae1ea` | `evolution` | ❌ IP unreachable + user/pass |
| `cartorio_supabase` (real) | `localhost:5432` | `admin` (POSTGRES_USER) | `@Techno832466` (POSTGRES_PASSWORD) | `supabase` (POSTGRES_DB) | — |

**Conclusão**:
1. O Postgres foi (re)criado com `POSTGRES_USER=admin` (não `supabase_admin`). Volume `bind:/etc/easypanel/projects/cartorio/supabase/data` foi reinicializado OU as env vars foram sobrescritas pelo Easypanel em algum restart.
2. **Dois serviços (evolution, chatwoot) têm IP externo errado `10.11.211.12`** — provavelmente configurados em momento anterior quando VPS tinha IP público diferente ou DNS customizado. **Esse IP não existe mais** (`nc -zv 10.11.211.12 5432 → Operation now in progress`).
3. **Dois serviços (n8n, evolution) têm credenciais antigas** `supabase_admin:e999b7439...` que não correspondem ao role atual `admin`.

### T009/T010 — Lesson + commit (este arquivo)

## [HOLD-GUSTAVO] Ações requeridas (NÃO fazer pelo sub-agent)

1. **Decidir caminho de recuperação**:
   - **Opção A (mínima)**: Editar env vars dos 4 serviços via Easypanel UI → Services → Cartório → cada serviço → Env → alinhar com o que `cartorio_api` já tem (admin / @Techno832466 / cartorio_supabase:5432 / database específica). Restart individual.
   - **Opção B (limpa)**: Dropar o container do `cartorio_supabase`, recriar com env vars que contenham **TODOS** os roles velhos (`supabase_admin` com senha `e999b7...`, `n8n`, `chatwoot`, `evolution`) E backup/restore dos bancos se houver dados. Risco: perda de dados se volume foi recriado.
   - **Opção C (debug primeiro)**: Inspecionar `docker service inspect cartorio_supabase` + comparar volumes + checar se `PGDATA=/var/lib/postgresql/data` ainda tem o cluster antigo ou foi inicializado fresh.

2. **Mudar `POSTGRES_HOST=10.11.211.12` para `cartorio_supabase`** em evolution-api e chatwoot (Easypanel UI ou `docker service update --env-add POSTGRES_HOST=cartorio_supabase`).

3. **Mudar `DB_POSTGRESDB_USER=supabase_admin` → `DB_POSTGRESDB_USER=admin` + `DB_POSTGRESDB_PASSWORD=e999b...` → `@Techno832466`** em n8n (e evolution).

4. **Criar databases `n8n`, `chatwoot`, `evolution`** se não existirem no Postgres atual:
   ```bash
   docker exec cartorio_supabase.1.XXX createdb -U admin n8n
   docker exec cartorio_supabase.1.XXX createdb -U admin chatwoot
   docker exec cartorio_supabase.1.XXX createdb -U admin evolution
   ```

5. **Re-rodar** `docker service update --force <svc>` para cada um após alinhar env.

6. **Criar A-record `chatwoot.2notasudi.com.br → 187.77.236.77`** no Cloudflare (se ainda não existir) — pode estar faltando.

7. **Atualizar `.harness/memory/MEMORY.md`** com referência a esta lesson (cross-link).

## Comandos úteis para o Gustavo

```bash
# SSH
ssh vps-public  # alias em ~/.ssh/config → 187.77.236.77

# Mudar env var sem perder outras (forma segura)
docker service update \
  --env-add POSTGRES_HOST=cartorio_supabase \
  --env-add POSTGRES_USER=admin \
  --env-add POSTGRES_PASSWORD='@Techno832466' \
  --env-add POSTGRES_DATABASE=evolution \
  cartorio_evolution-api

# Restart
docker service update --force cartorio_evolution-api

# Ver envs atuais
docker service inspect cartorio_evolution-api \
  --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}' | tr ',' '\n'

# Testar do container
docker exec $(docker ps -q -f name=cartorio_supabase.1 | head -1) \
  psql -U admin -d supabase -c "SELECT 1;"

# Smoke geral
for d in api flow whatsapp chat agent supbase easypanel; do
  curl -sk -o /dev/null -m 8 -w "$d: %{http_code}\n" https://$d.2notasudi.com.br/
done
```

## Gotchas aprendidos (codificar)

1. **`docker service update --force` NÃO conserta env vars erradas** — só reinicia o container com o env que ele já tem. Para mudar env, é `--env-add` / `--env-rm` (cuidado: dropa serviços `global` se errar ordem).

2. **IP externo em DATABASE_URL é red flag absoluto** — sempre usar DNS interno do swarm (`cartorio_supabase`, não IP numérico). IPs mudam em fail-over Hostinger.

3. **Traefik 502 ≠ Traefik down** — sempre ler o backend do log do Traefik (`http-cartorio_X-0@file` no access log) para distinguir 502 de Traefik vs 502 do upstream.

4. **Postgres `role does not exist` após restart = cluster foi reinicializado** (PGDATA vazio ou pg_resetwal). Investigar volume + bind mount antes de tentar `--force`.

5. **Tailscale offline 2+ dias** — usar `vps-public` (Hostinger direto) como fallback. Alias já em `~/.ssh/config`.

6. **`cartorio_api` sobreviveu porque conecta via DNS interno** — não depende de IPs externos. **Esse é o design correto.** Os outros serviços precisam ser alinhados a esse padrão.

## Cross-references

- `lesson-150-incident-vps-down-telegram-2026-07-08.md` — VPS down → Claude modo auto bloqueado → padrão de escalation doc.
- `lesson-151-cloudflare-tunnel-rescue-2026-07-08.md` — Cloudflare tunnel rescue pattern (não aplicável aqui, foi IP direto).
- `lesson-172-p0-outage-r8-actions.md` — Mesmo padrão de P0 outage (artefato + runbook).
- `.harness/STANDARDS.md` — adicionar regra: "DATABASE_URL sempre DNS interno swarm, nunca IP externo".
- `docs/OUTAGE_RECOVERY_RUNBOOK.md` — complementar seção "Database credential drift".

## Status

- [x] T001-T010 executados
- [x] Diagnóstico completo
- [x] Lesson + commit prontos
- [ ] **Fix manual Gustavo** (pendente — env vars + DB role)
- [ ] Smoke pós-fix (rodar `for d in ...`)
- [ ] PR com lesson (este arquivo) mergeado em master
