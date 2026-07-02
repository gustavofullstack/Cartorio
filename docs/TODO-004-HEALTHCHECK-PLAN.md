# TODO-004 — Plano de Healthchecks Swarm

> **Status**: ⏳ Patch preparatório (Fase 0)
> **Data**: 2026-07-02
> **Owner**: orchestrator
> **Priority**: MEDIUM (SPRINT_REVIEW_2026-07-02.md:74)
> **Bloqueador para**: detectar CrashLoop **antes** do 502 público

## 1. Contexto

### 1.1 Problema operacional

Hoje a stack Cartório depende de **healthcheck HTTP externo** (`scripts/health_check_27services.sh`,
roda sob demanda via SSH) para detectar CrashLoop. Resultado:

- 502 é o **primeiro sintoma público** antes do alerta interno.
- Tempo médio de detecção: depende de quando alguém executa o script (manual).
- Swarm `HEALTHCHECK` nativo **não está declarado** em 22 dos 27 serviços.
- 5/27 já declaram: `anything-llm`, `api`, `crwal4ai`, `openclaw-gateway`, `redis-commander`
  (validado por `docker inspect --format='{{.State.Health.Status}}'`).

### 1.2 Por que HEALTHCHECK nativo

- Swarm marca o container `unhealthy` automaticamente após `start_period` sem sucesso.
- Traefik/Easypanel podem remover do pool de roteamento quando `unhealthy`.
- `docker service ls` mostra `0/1` ou `1/1 (restarting)` em vez de `1/1 (healthy)` — visibilidade imediata.
- Integra com `--health-cmd` direto no Dockerfile/compose (declarativo, versionado).

### 1.3 Por que NÃO foi feito ainda

- Wave 7 priorizou **diagnóstico** (`health_check_27services.sh`).
- Wave 8 priorizou **resolver TODO-003** (LiteLLM aliases).
- HEALTHCHECK depende de cada app expor endpoint HTTP/TCP — requer conhecimento de cada imagem.

## 2. Análise de impacto — 27 serviços categorizados

### 2.1 Serviços COM healthcheck já declarado (5/27) ✅

| Serviço | Imagem | Comando esperado |
|---|---|---|
| `cartorio_api` | `easypanel/cartorio/api:latest` | `curl -fsS http://localhost:8000/health` |
| `cartorio_anything-llm` | `mintplexlabs/anythingllm:pg` | `curl -fsS http://localhost:3001/api/ping` |
| `cartorio_crwal4ai` | `unclecode/crawl4ai:latest` | `curl -fsS http://localhost:11235/health` |
| `cartorio_openclaw-gateway` | `ghcr.io/openclaw/openclaw:latest` | `curl -fsS http://localhost:18789/health` |
| `cartorio_redis_rediscommander` | `...rediscommander...` | `curl -fsS http://localhost:8081/` |

**Ação**: Nenhuma. Já funcionam.

### 2.2 Serviços SEM healthcheck (22/27) — categorizados por **endpoint conhecido**

#### Grupo A — HTTP simples (root path) (10/22)

| Serviço | Imagem | Comando proposto |
|---|---|---|
| `cartorio_litellm-app` | `ghcr.io/berriai/litellm:v1.85.0` | `curl -fsS http://localhost:4000/health/readiness \|\| exit 1` |
| `cartorio_lobechat` | `lobehub/lobe-chat:1.143.3` | `curl -fsS http://localhost:3210/ \|\| exit 1` |
| `cartorio_open-notebook` | `lfnovo/open_notebook:1.8.5` | `curl -fsS http://localhost:8502/ \|\| exit 1` |
| `cartorio_evolution-api` | `evoapicloud/evolution-api:latest` | `curl -fsS http://localhost:8080/ \|\| exit 1` |
| `cartorio_chatwoot` | `chatwoot/chatwoot:latest` | `curl -fsS http://localhost:3000/api/v1/profiles/ping \|\| exit 1` |
| `cartorio_chatwoot-sidekiq` | `chatwoot/chatwoot:latest` | `pgrep -f sidekiq \|\| exit 1` (process probe) |
| `cartorio_argilla-web` | `argilla/argilla-server:v2.8.0` | `curl -fsS http://localhost:6900/api/v1/version \|\| exit 1` |
| `cartorio_argilla-worker` | `argilla/argilla-server:v2.8.0` | `pgrep -f "argilla.*worker" \|\| exit 1` (process probe) |
| `cartorio_langfuse-web` | `langfuse/langfuse:3.174.1` | `curl -fsS http://localhost:3000/api/public/health \|\| exit 1` |
| `cartorio_langfuse-worker` | `langfuse/langfuse-worker:3.155` | `pgrep -f "langfuse.*worker" \|\| exit 1` (process probe) |
| `cartorio_supabase_dbgate` | `dbgate:latest` | `curl -fsS http://localhost:3000/ \|\| exit 1` |
| `cartorio_supabase_pgweb` | `sosedoff/pgweb:latest` | `curl -fsS http://localhost:8081/ \|\| exit 1` |

#### Grupo B — TCP/CLI nativo (4/22)

| Serviço | Imagem | Comando proposto |
|---|---|---|
| `cartorio_redis` | `redis:8.8` | `redis-cli ping \| grep PONG` |
| `cartorio_supabase` | `pgvector/pgvector:pg17` | `pg_isready -U postgres \|\| exit 1` |
| `cartorio_argilla-elasticsearch` | `docker.elastic.co/elasticsearch/elasticsearch:8.12.2` | `curl -fsS http://localhost:9200/_cluster/health \| grep -E "green\|yellow"` |
| `cartorio_langfuse-clickhouse` | `clickhouse/clickhouse-server` | `wget -qO- http://localhost:8123/ping \| grep Ok` |

#### Grupo C — MinIO + Easypanel + Traefik + whoami (5/22)

| Serviço | Imagem | Comando proposto |
|---|---|---|
| `cartorio_langfuse-minio` | `minio/minio:latest` | `curl -fsS http://localhost:9000/minio/health/live \|\| exit 1` |
| `easypanel` | easypanel | `curl -fsS http://localhost:3000/ \|\| exit 1` |
| `easypanel-traefik` | traefik | `curl -fsS http://localhost:8082/api/overview \|\| exit 1` |
| `vps_whoami` | traefik/whoami | `curl -fsS http://localhost:80/ \|\| exit 1` |

#### Grupo D — Sem HTTP (process-only) (1/22)

| Serviço | Imagem | Comando proposto |
|---|---|---|
| `cartorio_zeroclaw` | `ghcr.io/zeroclaw-labs/zeroclaw:v0.7.5` | `pgrep -f zeroclaw \|\| exit 1` (process probe) |

### 2.3 Resumo numérico

- **22 serviços sem healthcheck**: 10 HTTP simples + 4 TCP/CLI + 5 minio/easypanel/traefik + 1 process
- **5 serviços já com healthcheck**: nenhum trabalho
- **Total**: 22 ações a executar (Fase 2)

## 3. Decisão proposta

### 3.1 Estratégia

Adicionar `HEALTHCHECK` via **`docker service update`** (não Dockerfile), porque:
- Não requer rebuild de imagem
- Reversível (rollback trivial)
- Aplica-se ao Swarm sem downtime
- Cada serviço é independente (1 update = 1 commit-friendly)

**Quando usar Dockerfile**:
- Apenas para imagens próprias (`cartorio_api`) — onde já temos `Dockerfile` em `/Dockerfile`.
- Manter comando coerente entre Dockerfile + override Swarm.

### 3.2 Parâmetros padrão sugeridos

```yaml
HEALTHCHECK:
  interval: 30s       # verificação a cada 30s
  timeout: 5s         # 5s timeout por probe
  retries: 3          # 3 falhas = unhealthy
  start_period: 60s   # 60s de carência no boot
```

**Justificativa**:
- `interval=30s` equilibra detecção rápida sem overhead excessivo.
- `start_period=60s` cobre apps lentos (Chatwoot Prisma, Langfuse migrations).
- `retries=3` evita falso positivo em pico de carga.

### 3.3 Cuidados especiais

- **`cartorio_chatwoot-sidekiq`** e **`cartorio_argilla-worker`** e **`cartorio_langfuse-worker`**:
  usar `pgrep` pois não expõem HTTP — process probe.
- **`cartorio_zeroclaw`**: idem (CLI agent, sem HTTP).
- **`cartorio_supabase`**: `pg_isready` precisa do binário na imagem (padrão em `pgvector/pgvector`).
- **`cartorio_argilla-elasticsearch`**: cluster status **green ou yellow** = OK (single-node nunca é green).

## 4. Script Swarm (Fase 2 — NÃO EXECUTAR)

> Script de exemplo. **Não executar até aprovação Gustavo** (regra SPRINT_REVIEW: zero mudança
> em Swarm sem janela).

```bash
#!/usr/bin/env bash
# add_healthchecks_22services.sh
# Adiciona HEALTHCHECK em 22 serviços via docker service update.
# Uso: ./scripts/add_healthchecks_22services.sh [--dry-run]
#
# Modified by Gustavo Almeida — 2026-07-02 (TODO-004 Fase 2)

set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

run_update() {
  local svc="$1" cmd="$2"
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "DRY-RUN: docker service update --health-cmd '$cmd' --health-interval 30s ..."
    echo "         service: $svc"
  else
    echo "UPDATING: $svc"
    docker service update \
      --health-cmd "$cmd" \
      --health-interval 30s \
      --health-timeout 5s \
      --health-retries 3 \
      --health-start-period 60s \
      "$svc"
  fi
}

# === GRUPO A: HTTP simples (10) ===
run_update cartorio_litellm-app        "curl -fsS http://localhost:4000/health/readiness || exit 1"
run_update cartorio_lobechat           "curl -fsS http://localhost:3210/ || exit 1"
run_update cartorio_open-notebook      "curl -fsS http://localhost:8502/ || exit 1"
run_update cartorio_evolution-api      "curl -fsS http://localhost:8080/ || exit 1"
run_update cartorio_chatwoot           "curl -fsS http://localhost:3000/api/v1/profiles/ping || exit 1"
run_update cartorio_chatwoot-sidekiq   "pgrep -f sidekiq || exit 1"
run_update cartorio_argilla-web        "curl -fsS http://localhost:6900/api/v1/version || exit 1"
run_update cartorio_argilla-worker     "pgrep -f argilla.*worker || exit 1"
run_update cartorio_langfuse-web       "curl -fsS http://localhost:3000/api/public/health || exit 1"
run_update cartorio_langfuse-worker    "pgrep -f langfuse.*worker || exit 1"
run_update cartorio_supabase_dbgate    "curl -fsS http://localhost:3000/ || exit 1"
run_update cartorio_supabase_pgweb     "curl -fsS http://localhost:8081/ || exit 1"

# === GRUPO B: TCP/CLI nativo (4) ===
run_update cartorio_redis                          "redis-cli ping | grep PONG"
run_update cartorio_supabase                       "pg_isready -U postgres || exit 1"
run_update cartorio_argilla-elasticsearch         "curl -fsS http://localhost:9200/_cluster/health | grep -E green\\|yellow"
run_update cartorio_langfuse-clickhouse            "wget -qO- http://localhost:8123/ping | grep Ok"

# === GRUPO C: MinIO + Easypanel + Traefik + whoami (5) ===
run_update cartorio_langfuse-minio     "curl -fsS http://localhost:9000/minio/health/live || exit 1"
run_update easypanel                   "curl -fsS http://localhost:3000/ || exit 1"
run_update easypanel-traefik           "curl -fsS http://localhost:8082/api/overview || exit 1"
run_update vps_whoami                  "curl -fsS http://localhost:80/ || exit 1"

# === GRUPO D: Process-only (1) ===
run_update cartorio_zeroclaw           "pgrep -f zeroclaw || exit 1"

echo "OK: 22 healthchecks aplicados (ou dry-run)."
```

## 5. Critérios de aprovação (Fase 2)

Bloqueios para Gustavo autorizar Fase 2:

- [ ] Gustavo leu este PLAN completo.
- [ ] Janela de manutenção definida (manhã de domingo 2026-07-05 preferencialmente).
- [ ] Confirmado que Traefik/Easypanel não serão afetados (HEALTHCHECK afeta só Swarm,
      não o router — exceto se Easypanel configurado para ler health).
- [ ] Confirmado que `docker service update` de cada serviço não conflita com deploy
      Easypanel (regra: parar Easypanel → rodar script → restart Easypanel).

## 6. Critérios de sucesso (Fase 2)

Após Fase 2, validar:

- [ ] `docker inspect <svc> | grep -A 5 Health` mostra `Status: healthy` em 27/27 serviços.
- [ ] `docker service ls --format '{{.Name}} {{.Replicas}}'` mostra `1/1` em todos.
- [ ] `./scripts/health_check_27services.sh` mostra `HEALTH=healthy` (não `none`) em 27/27.
- [ ] Simular CrashLoop (`docker kill <container>`) → Swarm marca `unhealthy` em até 90s.
- [ ] Traefik continua roteando normalmente (sem 502 espúrio).
- [ ] Nenhum falso positivo em 24h (HEALTHCHECK não oscila).

## 7. Rollback

Se HEALTHCHECK gerar falsos positivos ou comportamento estranho:

```bash
# Rollback por serviço (exemplo litellm-app)
docker service update --health-cmd "" --health-interval 0s cartorio_litellm-app

# Rollback em massa (todos os 22)
docker service ls --format '{{.Name}}' | grep -v "easypanel\|traefik\|whoami\|api$\|anything-llm\|crwal4ai\|openclaw-gateway\|rediscommander" \
  | xargs -I{} docker service update --health-cmd "" --health-interval 0s {}
```

**Importante**: `--health-cmd ""` + `--health-interval 0s` **remove** o healthcheck do Swarm.

## 8. Lições aplicadas

- **Lesson 290**: 1 fix cirúrgico — este PLAN é pure-doc, Fase 2 será 1 sessão isolada.
- **Lesson 116**: PROMPT.json não declarava healthcheck; este PLAN corrige o gap.
- **AGENTS.md § Security**: HEALTHCHECK não toca PII nem audit; revisão LGPD não requerida.
- **AGENTS.md § Team**: mudança em Swarm = revisão de Gustavo (owner); sem aprovação = gated.
- **SPRINT_REVIEW § Lessons Learned**: "deploy-port-conflict" → Fase 2 deve respeitar
  scale 0 → update → scale 1 quando env muda (não aplicável aqui, mas é regra da casa).
- **Lesson 287/288**: LOOP STATE pattern — manter execução silenciosa + resposta ultra-curta.

## 9. Próximos passos

1. **AGUARDAR** aprovação Gustavo para Fase 1 (criar `scripts/add_healthchecks_22services.sh` no repo).
2. **AGUARDAR** aprovação Gustavo para Fase 2 (executar script no Swarm).
3. Atualizar `docs/SERVICE_INVENTORY.md` com coluna "Healthcheck" pós-Fase 2.
4. Atualizar `docs/SPRINT_REVIEW_2026-07-02.md` (mover TODO-004 de "pendente" para "done").
5. Append em MEMORY.md com log da execução quando concluído.

---

**Modified by Gustavo Almeida**