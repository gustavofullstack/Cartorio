# 🚨 OUTAGE_RECOVERY_RUNBOOK — P0 Traefik Upstream 502 (2026-07-14)

> **Severidade**: P0 — 7/9 canais DOWN, 2/9 UNVERIFIED
> **Sintoma global**: `502 Bad Gateway` em todas as URLs públicas (Traefik responde TLS mas não alcança upstream)
> **Detectado por**: T2 (canal-sondagem) + T5 (recon pós-R8) — ver `docs/CANAL_HEALTH_MATRIX.md`
> **SSH VPS**: BLOQUEADO de auto-mode (Production Reads sem autorização explícita) → **ação humana obrigatória**
> **Versão**: 1.0.0 — 2026-07-14 02:30 BRT
> **Mantenedor**: Gustavo Almeida (intervenção manual) + cartorio-sre (revisor)

---

## 0. Resumo executivo (TL;DR para Gustavo)

**Problema**: Traefik (edge OK, TLS válido até 2026-09-20) não consegue alcançar **qualquer** container de aplicação. DNS OK (`187.77.236.77` IPv4 + `2a02:4780:6e:cd40::1` IPv6). Causa mais provável: containers Swarm escalados a `0`, EasyPanel derrubou backends, ou `docker stack deploy` foi revertido.

**O que precisa ser feito** (em ordem):

1. **SSH VPS** com alias correto: `ssh cartorio` (Tailscale) ou `ssh cartorio-public` (IP público).
2. **Verificar estado** dos 27 serviços Swarm: `bash scripts/health_check_27services.sh --only-down`.
3. **Reiniciar Traefik** (`docker service update --force easypanel-traefik`) para forçar re-leitura de routers.
4. **Redeployar serviços na ordem**: `cartorio_api → cartorio_n8n* → cartorio_evolution-api → cartorio_chatwoot (+ sidekiq) → cartorio_openclaw-gateway → cartorio_lobechat → cartorio_supabase → cartorio_redis`.
5. **Validar** com sequência de health checks abaixo.
6. **Se rollback**: parar tudo + restaurar último backup válido.

**Estimativa de tempo**: 15–25 min se for simples (Traefik + API reiniciados); 1–2 h se precisar restaurar de backup.

---

## 1. Endpoints afetados (lista canônica)

> Fonte: `docs/CANAL_HEALTH_MATRIX.md` (probe `2026-07-14 02:24 UTC`).

### 1.1 — DOWN confirmado (7/9) — `502 Bad Gateway`

| # | Canal | URL pública | Latência observada | Serviço Swarm raiz |
|---|-------|-------------|---------------------|---------------------|
| 1 | **FastAPI — `/health/radar`** | `https://api.2notasudi.com.br/api/v1/health/radar` | 6.33s | `cartorio_api` |
| 2 | **Chatwoot inbox** (autenticado) | `https://cartorio-chatwoot.dfgdxq.easypanel.host/api/v1/accounts/${CHATWOOT_ACCOUNT_ID}/inboxes` | 3.24s | `cartorio_chatwoot` |
| 3 | **Telegram webhook** (synthetic) | `https://api.2notasudi.com.br/api/v1/telegram/webhook` | 6.32s | `cartorio_api` (downstream) |
| 4 | **LobeChat upstream** | `https://cartorio-lobechat.dfgdxq.easypanel.host/chat` | 6.32s | `cartorio_lobechat` |
| 5 | **WebSocket `/ws/atendimentos`** | `wss://api.2notasudi.com.br/api/v1/ws/atendimentos` | 6.38s | `cartorio_api` |
| 6 | **Evolution API** | `https://whatsapp.2notasudi.com.br/` | 6.33s | `cartorio_evolution-api` |
| 9 | **OpenClaw MCP `/mcp`** | `https://agent.2notasudi.com.br/mcp` | 6.29s | `cartorio_openclaw-gateway` |

### 1.2 — UNVERIFIED (2/9) — depende de validação indireta

| # | Canal | Por que não verificado | Como verificar após recovery |
|---|-------|-------------------------|------------------------------|
| 7 | **Redis PING** | SSH bloqueado pelo auto-mode | Após API UP: `curl /api/v1/health/redis` retorna `"status": "online"`. Direto: `ssh cartorio 'docker exec cartorio_redis.1.<task> redis-cli -p 1001 -a @Techno832466 PING'` |
| 8 | **Postgres SELECT 1** | SSH bloqueado | Após API UP: `curl /api/v1/health/db` retorna `"status": "online"`. Direto: `ssh cartorio 'docker exec cartorio_supabase.1.<task> pg_isready -U postgres'` |

### 1.3 — Edge / DNS / TLS (todos OK — não afetados)

| Camada | Estado | Evidência |
|--------|--------|-----------|
| Traefik TLS handshake | ✅ OK | `curl -kv https://api.2notasudi.com.br/healthz` completa TCP+TLS |
| Certificados Let's Encrypt | ✅ OK | expira 2026-09-20 |
| DNS IPv4 (`187.77.236.77`) | ✅ OK | `dig +short api.2notasudi.com.br A` |
| DNS IPv6 (`2a02:4780:6e:cd40::1`) | ✅ OK | `dig +short api.2notasudi.com.br AAAA` |
| Easypanel UI | 🔴 DOWN (mesma causa raiz) | `https://easypanel.2notasudi.com.br` → 502 |

---

## 2. Comandos exatos — Restart do Traefik upstream

> **Regra de ouro** (de `docs/RUNBOOK_VPS.md:3`): use SEMPRE `ssh cartorio` (Tailscale) — NUNCA `ssh vps` (IP stale).

### 2.1 — Conectar ao VPS

```bash
# Preferência 1: Tailscale (RECOMENDADO, IP estável 100.99.172.84)
ssh cartorio

# Preferência 2: IP público Hostinger (fallback se Tailscale off)
ssh cartorio-public      # alias para 187.77.236.77

# Key: ~/.ssh/id_ed25519_cartorio
```

### 2.2 — Diagnóstico inicial (sem mutar nada)

```bash
# Estado dos 27 serviços Swarm
docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | grep cartorio

# Filtra só DOWN / restarting / missing
docker service ls --format "{{.Name}} {{.Replicas}}" | awk -F'[/ ]' '$2 != $3 {print}'

# Estado dos containers
docker ps --filter "name=cartorio" --format "{{.Names}}: {{.Status}}" | grep -v "Up "

# Logs recentes do Traefik
docker service logs easypanel-traefik --tail 100 --no-trunc

# Logs recentes da API
docker service logs cartorio_api --tail 100 --no-trunc
```

### 2.3 — Restart do Traefik (forçar re-leitura de routers)

```bash
# 1. Restart Traefik SEM mudar imagem (preserva routers persistidos)
docker service update --force easypanel-traefik

# 2. Aguardar 5–10s e validar
sleep 10
docker service logs easypanel-traefik --tail 20
# Esperado: "Router ... added", sem erros "no such service"

# 3. Se Traefik não subir (porta 80/443 ocupada), reinício "pesado"
docker service scale easypanel-traefik=0
sleep 5
docker service scale easypanel-traefik=1
sleep 10
docker service logs easypanel-traefik --tail 30

# 4. Sanity: Traefik dashboard (se habilitado)
curl -fsS http://localhost:8080/api/http/routers 2>/dev/null | jq '.[].name' | head
```

### 2.4 — Se Traefik crashloop após restart

```bash
# Inspeção profunda
docker service ps easypanel-traefik --no-trunc
docker inspect $(docker ps -aqf 'name=easypanel-traefik') --format '{{json .State}}' | jq

# Causa comum: config inválida no volume montado
docker exec $(docker ps -qf 'name=easypanel-traefik') cat /etc/traefik/traefik.yml 2>&1 | head -30

# Fix de último caso: recriar service (cuidado — pode perder labels DNS)
docker service rm easypanel-traefik
# (re-criar via Easypanel UI > Services > easypanel-traefik > Deploy)
```

---

## 3. Ordem de redeploy dos serviços

> **Premissa**: dependências em cascata. Redeploy do errado pode causar rollback em cascata (ver §5).

```
[DB + Cache]                [App]                  [UI / Integração]
supabase    ───┐
               ├──► cartorio_api ───► cartorio_chatwoot ───► Evolution (WhatsApp)
redis        ───┘                ───► cartorio_openclaw-gateway ───► LobeChat
                                ───► (cartorio_n8n) [zombie — turn 45]
                                                  ───► Telegram webhook
                                                  ───► WebSocket atendimentos
```

### 3.1 — Tabela de ordem e justificativa

| # | Serviço | Comando | Justificativa da ordem | Dependências |
|---|---------|---------|------------------------|--------------|
| 1 | **`cartorio_api`** | `docker service update --force cartorio_api` | Raiz de todos os outros (radar, webhook, ws) | supabase + redis |
| 2 | **`cartorio_n8n`** (zombie) | `docker service scale cartorio_n8n=1` (se existir) | Workflows orquestram canais; turn 45 removeu, mas check se há service órfão | supabase |
| 3 | **`cartorio_evolution-api`** | `docker service update --force cartorio_evolution-api` | WhatsApp = entrada de ~40% das mensagens; standalone (não depende da API para responder webhook) | nenhuma interna |
| 4 | **`cartorio_chatwoot` + `cartorio_chatwoot-sidekiq`** | `docker service update --force cartorio_chatwoot && docker service update --force cartorio_chatwoot-sidekiq` | CRM/handoff humano; sidekiq processa jobs async | supabase + redis |
| 5 | **`cartorio_openclaw-gateway`** | `docker service update --force cartorio_openclaw-gateway` | LLM router (Gemini/Qwen); MCP server | nenhuma interna |
| 6 | **`cartorio_lobechat`** | `docker service update --force cartorio_lobechat` | UI do Agente Cartório para usuários finais | openclaw (5) |
| 7 | **`cartorio_supabase`** | `docker service update --force cartorio_supabase` | Postgres+pgvector; se cair, restart afeta todos que dependem | nenhuma interna (mas tem volume persistente) |
| 8 | **`cartorio_redis`** | `docker service update --force cartorio_redis` | Cache/sessão/fila; restart LIMPA cache (não perder sessões é impossível sem persistência AOF) | nenhuma interna |

### 3.2 — Comandos prontos (copiar/colar no SSH)

```bash
# === FASE 1 — RAIZ (validar antes de subir UI) ===
docker service update --force cartorio_api
sleep 15
curl -fsS https://api.2notasudi.com.br/healthz && echo "  ← API UP" || echo "  ← API DOWN, ver logs"

# === FASE 2 — CANAIS DE ENTRADA ===
# (cartorio_n8n é zombie desde turn 45; rodar scale=1 só se service ainda existir)
docker service inspect cartorio_n8n >/dev/null 2>&1 && \
  docker service update --force cartorio_n8n || echo "cartorio_n8n: zombie (removido turn 45), pulando"

docker service update --force cartorio_evolution-api
sleep 10
curl -fsS -H "apikey: ${EVOLUTION_API_KEY}" \
  https://whatsapp.2notasudi.com.br/instance/fetchInstances | jq '.[].name'

# === FASE 3 — CRM ===
docker service update --force cartorio_chatwoot
docker service update --force cartorio_chatwoot-sidekiq
sleep 10
curl -fsS https://chat.2notasudi.com.br/ -o /dev/null -w "Chatwoot: %{http_code} (302 esperado)\n"

# === FASE 4 — LLM + UI ===
docker service update --force cartorio_openclaw-gateway
sleep 10
curl -fsS https://agent.2notasudi.com.br/health -o /dev/null -w "OpenClaw: %{http_code}\n"

docker service update --force cartorio_lobechat
sleep 10
curl -fsSL https://cartorio-lobechat.dfgdxq.easypanel.host/chat -o /dev/null -w "LobeChat: %{http_code}\n"

# === FASE 5 — DATA LAYER (por ÚLTIMO para evitar race) ===
docker service update --force cartorio_supabase
sleep 20
docker exec $(docker ps -qf 'name=cartorio_supabase') pg_isready -U postgres

docker service update --force cartorio_redis
sleep 10
docker exec $(docker ps -qf 'name=cartorio_redis') redis-cli -p 1001 PING
```

### 3.3 — Modo automático (script idempotente)

```bash
# Se preferir 1-command: usar scripts/health_check_27services.sh + loop de restart
bash scripts/health_check_27services.sh --only-down

# Restart em ordem canônica:
for svc in cartorio_api cartorio_evolution-api cartorio_chatwoot cartorio_chatwoot-sidekiq \
           cartorio_openclaw-gateway cartorio_lobechat cartorio_supabase cartorio_redis; do
  state=$(docker service inspect "$svc" --format '{{.Spec.Mode.Replicated.Replicas}}' 2>/dev/null || echo 0)
  if [[ "$state" == "0" ]]; then
    echo "[UP]   $svc (era scale=0 → scale=1)"
    docker service scale "$svc"=1
  else
    echo "[FRC]  $svc (update --force)"
    docker service update --force "$svc"
  fi
  sleep 5
done

# Validar todos UP
sleep 30
bash scripts/health_check_27services.sh --only-down
```

---

## 4. Sequência de health checks (pós-recovery)

### 4.1 — Sequência canônica (executar nesta ordem)

```bash
# 1. Edge (validar que Traefik respondeu — não 502)
curl -sk -m 5 -w "\nHTTP=%{http_code} t=%{time_total}s\n" \
  https://api.2notasudi.com.br/healthz
# Esperado: 200 + {"status":"alive","version":"..."} t<1s

# 2. Ready (DB + Redis + audit prontos)
curl -sk -m 10 -w "\nHTTP=%{http_code} t=%{time_total}s\n" \
  https://api.2notasudi.com.br/readyz
# Esperado: 200 + {"status":"ready","checks":{"database":"online","redis":"online","audit":"online"}}

# 3. Radar (7 serviços externos em paralelo)
curl -sk -m 15 -w "\nHTTP=%{http_code} t=%{time_total}s\n" \
  https://api.2notasudi.com.br/api/v1/health/radar | jq .
# Esperado: 200 + services todos "online"

# 4. Metrics (Prometheus exposition — útil pra alertas)
curl -sk -m 5 -w "\nHTTP=%{http_code} t=%{time_total}s\n" \
  -L https://api.2notasudi.com.br/metrics | head -5
# Esperado: 200 + "# HELP ..." headers OU 301 redirect → /api/v1/metrics/prometheus

# 5. Granular (se radar reportar OFFLINE em algum)
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/health/db
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/health/redis
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/health/audit
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/health/llm
```

### 4.2 — Tabela de respostas esperadas

| Endpoint | HTTP esperado | Body crítico | Tempo-alvo |
|----------|---------------|--------------|------------|
| `/healthz` | 200 | `status: "alive"` | < 1s |
| `/readyz` | 200 | `database: "online"` | < 2s |
| `/api/v1/health/radar` | 200 | todos 7 serviços `online` | < 3s |
| `/metrics` (redirect) | 200 ou 301→200 | `# HELP` lines | < 1s |
| `/api/v1/health/db` | 200 | `status: "online"` | < 1s |
| `/api/v1/health/redis` | 200 | `status: "online"` | < 1s |
| `/api/v1/health/audit` | 200 | `status: "online"` | < 2s |
| `/api/v1/health/llm` | 200 | `status: "online"` | < 3s |

### 4.3 — Validação dos canais (não-API)

```bash
# 6. Telegram webhook (sintético)
curl -sk -m 5 -X POST -H "Content-Type: application/json" \
  -d '{"update_id":999999998,"message":{"message_id":1,"date":1720000000,"chat":{"id":12346,"type":"private"},"from":{"id":12346,"is_bot":false,"first_name":"Recovery"},"text":"/start"}}' \
  https://api.2notasudi.com.br/api/v1/telegram/webhook
# Esperado: 200 + {"status":"ok"|"duplicate",...}

# 7. WebSocket handshake
wscat -c wss://api.2notasudi.com.br/api/v1/ws/atendimentos --no-color -x 'ping'
# Esperado: HTTP 101 Switching Protocols, "ping" echoed

# 8. Evolution instance state
curl -fsS -H "apikey: ${EVOLUTION_API_KEY}" \
  https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas | jq '.instance.state'
# Esperado: "open"

# 9. Chatwoot reachability
curl -sk -m 5 -w "HTTP=%{http_code}\n" \
  https://cartorio-chatwoot.dfgdxq.easypanel.host/ -o /dev/null
# Esperado: 302 (login redirect) — não 502

# 10. OpenClaw health
curl -fsS -m 5 https://agent.2notasudi.com.br/health | jq .
# Esperado: {"status":"ok"} ou 200 com payload

# 11. LobeChat
curl -skL -m 5 -w "HTTP=%{http_code}\n" \
  https://cartorio-lobechat.dfgdxq.easypanel.host/chat -o /dev/null
# Esperado: 200 (não 502)

# 12. MCP tool inventory (Cartório)
curl -sk -m 5 -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"recovery","version":"1.0"}}}' \
  https://api.2notasudi.com.br/mcp | jq '.result.serverInfo'
# Esperado: {"name":"cartorio-mcp","version":"..."}
```

### 4.4 — Critério de "OK para declarar incidente resolvido"

Todos os 12 checks acima devem retornar o HTTP esperado em < 5s. Se **qualquer** falhar:
- Repetir comando `docker service update --force <servico>` específico.
- Se persistir 2x, abrir sub-investigação (logs + Sentry dashboard).
- Se múltiplos serviços falharem, **escalar para §5 (rollback)**.

---

## 5. Plano de rollback

> **Premissa**: rollback só é necessário se a recovery NÃO restaurar os serviços (ex: bug em nova imagem, volume corrompido).

### 5.1 — Rollback por serviço (Easypanel UI)

Para **cada serviço** que falhou no restart:

1. Acessar `https://easypanel.2notasudi.com.br` → projeto `cartorio` → serviço afetado.
2. Aba **Deployments** → ver lista de deploys anteriores.
3. Clicar no último deploy **GREEN** (com ✅) → **Rollback to this deployment**.
4. Aguardar Easypanel rebuildar + Swarm redistribuir (1–3 min).
5. Re-executar §4 para aquele serviço.

> ⚠️ **Limitação**: se Easypanel UI também está DOWN (mesma causa raiz), o rollback precisa ser via Easypanel CLI/API (`easypanel services rollback <service> --deployment-id <id>`) — requer token de API válido.

### 5.2 — Rollback por imagem (Docker Swarm direto)

```bash
# 1. Listar deploys anteriores do serviço
docker service ps cartorio_api --no-trunc --format "table {{.Name}}\t{{.Image}}\t{{.DesiredState}}\t{{.CurrentState}}"

# 2. Identificar o IMAGE_DIGEST do último deploy bom
# Ex: easypanel/cartorio/api@sha256:abc123...

# 3. Forçar update para imagem anterior (rollback Swarm)
docker service update --image easypanel/cartorio/api@sha256:<digest_anterior> cartorio_api

# 4. Validar
sleep 30
curl -fsS https://api.2notasudi.com.br/healthz
```

### 5.3 — Rollback de banco (último recurso)

> ⚠️ **NUNCA** rollback de banco sem alinhar com Gustavo — perda de dados irreversível.

```bash
# 1. Localizar último backup válido
ssh cartorio 'ls -lh /var/backups/cartorio/ | tail -5'
# Esperado: cartorio_db_YYYYMMDD_HHMMSS.sql.gz

# 2. Confirmar que o backup é válido (testar restore em DB temporário)
ssh cartorio 'gunzip -c /var/backups/cartorio/cartorio_db_LATEST.sql.gz | head -100'

# 3. PARAR todos os serviços que dependem do DB (evitar race)
for svc in cartorio_api cartorio_chatwoot cartorio_chatwoot-sidekiq \
           cartorio_openclaw-gateway cartorio_lobechat cartorio_evolution-api; do
  docker service scale ${svc}=0
done

# 4. Restaurar (via docker exec no Supabase container)
ssh cartorio 'gunzip -c /var/backups/cartorio/cartorio_db_LATEST.sql.gz | \
  docker exec -i $(docker ps -qf "name=cartorio_supabase") psql -U postgres -d cartorio'

# 5. Subir serviços de volta na ordem §3
```

### 5.4 — Rollback de Redis (cache-only — sem perda de dados)

Redis só tem cache/sessão. Restart **NÃO requer restore**:

```bash
# 1. Restart forçado
docker service update --force cartorio_redis

# 2. Aceitar perda de cache (sessões reiniciam; idempotency keys expiram em 24h)
echo "Cache Redis perdido. Próximas 24h: idempotency keys vão re-popular."
```

### 5.5 — Critério de "rollback suficiente"

Após rollback, §4.4 deve passar em **todos** os 12 checks. Se **qualquer canal** persistir DOWN:
1. Verificar logs do serviço: `docker service logs <svc> --tail 200 --no-trunc | grep -iE "error|fatal|panic|crash"`
2. Sentry dashboard: `https://sentry.io/organizations/cartorio/issues/?query=is:unresolved`
3. Abrir postmortem em `docs/postmortems/2026-07-14-traefik-502.md` (template em §5 de `docs/INCIDENT_RESPONSE_PLAYBOOK.md`).

---

## 6. Comunicação durante o incidente

### 6.1 — Status updates (a cada 15 min enquanto P0)

Template (de `docs/INCIDENT_RESPONSE_PLAYBOOK.md:4.2`):

```
[HH:MM BRT] STATUS: [MITIGANDO / RESOLVIDO / MONITORANDO]
- Ação: <o que está sendo feito agora>
- Próximo: <próximo passo + ETA>
- ETA resolução: <horário>
- Impacto atual: <N canais UP / N DOWN>
- Link runbook: docs/OUTAGE_RECOVERY_RUNBOOK.md
```

### 6.2 — Canais de comunicação

| Canal | Quando | Quem |
|-------|--------|------|
| Telegram DM Gustavo (`6682284055`) | P0 imediato | On-call |
| Telegram grupo Squad Pietra (`-5006771024`) | Updates a cada 15min | On-call |
| Email DPO (`dpo@2notasudi.com.br`) | Só se breach LGPD envolvido | Gustavo |
| ANPD (`gov.br/anpd`) | Só se LGPD art. 48 (72h) | Gustavo + DPO |

### 6.3 — Pós-mortem obrigatório

Após P0 resolvido, abrir `docs/postmortems/2026-07-14-traefik-502.md` em **48h** (template completo em `docs/INCIDENT_RESPONSE_PLAYBOOK.md:5.3`).

---

## 7. Prevenção (ações pós-incidente)

| # | Ação | Owner | ETA | Status |
|---|------|-------|-----|--------|
| 1 | Adicionar alerta Prometheus `probe_success{target="traefik_upstream"} < 1` | cartorio-sre | +1 sprint | TODO |
| 2 | Adicionar healthcheck Docker `wget --spider` em TODOS os 27 serviços (22/27 sem) | cartorio-sre | +1 sprint | TODO |
| 3 | Configurar `restart_policy: on-failure:5` no compose (evitar crashloop silencioso) | cartorio-sre | +1 sprint | TODO |
| 4 | Adicionar dead-man's switch no Traefik (heartbeat a cada 60s; alerta se 2 misses) | cartorio-sre | +2 sprints | TODO |
| 5 | Implementar auto-restart de serviços Swarm quando `Replicas < Desired` por > 2min | cartorio-sre | +2 sprints | TODO |
| 6 | Re-rodar `health_check_27services.sh` em cron 5min + alerta Telegram se DOWN>0 | cartorio-sre | +1 sprint | TODO |
| 7 | Documentar causa-raiz real do outage (postmortem) e adicionar teste de regressão | cartorio-dev | +2 sprints | TODO |

---

## 8. Anexos

### 8.1 — Referências cruzadas

- `docs/CANAL_HEALTH_MATRIX.md` — probe inicial (9 canais, 02:24 UTC)
- `docs/RUNBOOK_VPS.md` — comandos SSH + aliases (regra "ssh cartório, NUNCA ssh vps")
- `docs/INCIDENT_RESPONSE_PLAYBOOK.md` — classificação P0/P1 + template postmortem
- `docs/SERVICE_INVENTORY.md` — 27 serviços Swarm (estado real)
- `scripts/health_check_27services.sh` — health check de 27 serviços
- `.harness/memory/lesson-150-incident-vps-down-telegram-2026-07-08.md` — P0 anterior (mesmo padrão: VPS inacessível → escalation doc + ação humana)
- `.harness/memory/lesson-172-p0-outage-r8-actions.md` — pattern "P0 + SSH bloqueado = escalation doc only"

### 8.2 — Comandos proibidos (do `docs/RUNBOOK_VPS.md:6`)

```bash
# NÃO execute sem Gustavo autorizar
docker service rm cartorio_*              # remove serviço
docker network rm easypanel-cartorio       # remove rede
rm -rf /var/lib/docker/volumes/*           # deleta volumes (DADOS)
docker swarm leave --force                 # sai do swarm
```

### 8.3 — Contatos de emergência (de `docs/RUNBOOK_VPS.md:5`)

- **Gustavo Almeida (CEO)**: Telegram `6682284055` / email `gustavomar.fullstack@gmail.com`
- **DPO LGPD**: `dpo@2notasudi.com.br`
- **Easypanel UI**: `https://easypanel.2notasudi.com.br`
- **Hostinger painel**: `https://hpanel.hostinger.com`
- **Cloudflare**: `https://dash.cloudflare.com`

---

**Próxima revisão**: após resolução do P0 (adicionar causa-raiz real ao §0 + métricas de tempo de recovery ao §1.4).

Modified by Gustavo Almeida — 2026-07-14 02:30 BRT