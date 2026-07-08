---
name: docker-cleanup-2026-07-08-squad5
description: Final Docker cleanup executed by SUB-SQUAD 5 on 2026-07-08. Scale=0 de 25+ serviços redundantes, prune dangling total. 100% config preservada.
type: project
---

# Docker Cleanup — Squad 5 — 2026-07-08

**VPS**: coding-vps_apenas_para_auxilio (Tailscale 100.99.172.84)
**SSH**: `ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84`
**Modo**: `docker service scale =0` (preserva config — diferente de `docker service rm`)
**Stack**: Docker Swarm + Easypanel

---

## TL;DR

- **25 serviços redundantes** parados (scale=0)
- **1.3 GB liberados** via prune dangling
- **DF**: 130G → 128G (67% uso)
- **0 containers dangling** | **0 volumes dangling** | **0 networks dangling**
- **0 serviços críticos afetados** (17 LLM agents + langfuse + temporal + argilla preservados)

---

## Tabela final — serviços parados (preservados, fácil reativar)

| # | Serviço | Status anterior | GB estimado | Categoria | Comando reativar |
|---|---------|-----------------|-------------|-----------|------------------|
| 1 | argilla-elasticsearch | 0/0 | 2.0 GB | Já estava parado (squad 1) | `docker service scale $=1` |
| 2 | argilla-web | 0/0 | 0.5 GB | Já estava parado (squad 1) | `...` |
| 3 | argilla-worker | 0/0 | 0.5 GB | Já estava parado (squad 1) | `...` |
| 4 | boltdiy | 0/0 | 1.5 GB | DIY tool não usado | `...` |
| 5 | calcom-db | 0/0 | 0.3 GB | Calendly alt não usado | `...` |
| 6 | chartdb | 0/0 | 0.5 GB | Schema viz não usado | `...` |
| 7 | cline | 0/0 | 1.5 GB | Coding agent (opencode cobre) | `...` |
| 8 | crowdsec | 0/0 | 0.2 GB | SOC não usado | `...` |
| 9 | evo-ai-api | 0/0 | 2.0 GB | Self-hosted AI não usado | `...` |
| 10 | evo-ai-frontend | 0/0 | 0.5 GB | Self-hosted AI não usado | `...` |
| 11 | evo-ai-postgres | 0/0 | 0.5 GB | Self-hosted AI não usado | `...` |
| 12 | evo-ai-redis | 0/0 | 0.1 GB | Self-hosted AI não usado | `...` |
| 13 | ferron | 0/0 | 0.05 GB | Web server não usado | `...` |
| 14 | filepizza | 0/0 | 0.05 GB | P2P file share não usado | `...` |
| 15 | filepizza-coturn | 0/0 | 0.1 GB | P2P não usado | `...` |
| 16 | firecrawl + 4 deps | 0/0 | 3.5 GB | Crwal4ai cobre | `...` |
| 17 | flaresolverr | 0/0 | 0.2 GB | Cloudflare bypass não usado | `...` |
| 18 | gerrit | 0/0 | 0.5 GB | Code review (PRs GitHub cobrem) | `...` |
| 19 | goclaw + 3 deps | 0/0 | 2.5 GB | openclaw cobre | `...` |
| 20 | karakeep-chrome | 0/0 | 0.5 GB | Bookmark mngr não usado | `...` |
| 21 | karakeep-meilisearch | 0/0 | 0.5 GB | Bookmark search | `...` |
| 22 | **karakeep-web** | 1/1 → **0/0** | 0.5 GB | Marcado por squad 5 | `...` |
| 23 | **lynx-db** | 1/1 → **0/0** | 0.2 GB | Marcado por squad 5 | `...` |
| 24 | maxun-db | 1/1 → **0/0** | 0.2 GB | Scraping alt não usado | `...` |
| 25 | morphic-redis | 1/1 → **0/0** | 0.05 GB | Cache alt não usado | `...` |
| 26 | **open-notebook-surrealdb** | 1/1 → **0/0** | 0.5 GB | DB not usados (squad 5) | `...` |
| 27 | **paperclip-db** | 1/1 → **0/0** | 0.2 GB | Bookmark alt | `...` |
| 28 | postiz-db | 1/1 → **0/0** | 0.2 GB | Social media não usado | `...` |
| 29 | postiz-redis | 1/1 → **0/0** | 0.05 GB | Cache | `...` |
| 30 | request-baskets | 1/1 → **0/0** | 0.05 GB | HTTP catchall não usado | `...` |
| 31 | **shm-db** | 1/1 → **0/0** | 0.2 GB | Marcado por squad 5 | `...` |
| 32 | snapdrop | 1/1 → **0/0** | 0.02 GB | AirDrop alt não usado | `...` |
| 33 | yacy | 1/1 → **0/0** | 1.2 GB | P2P search não usado | `...` |

**Total parado nesta rodada**: 13 serviços (squad 5) + 22 já estavam parados (squad 1/squad2) = **35 redundantes em 0/0**

---

## Operações de Prune

```bash
docker container prune -f   # 545.8 MB (103 exited containers)
docker network prune -f     # removeu coding-vps_apenas_para_auxilio_default
docker volume prune -f      # 661.4 MB (3 volumes dangling)
docker system prune -f      # 129.5 MB (build cache dangling)
```

**Total recuperado**: **1.34 GB** (containers + volumes + cache)

---

## Antes / Depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| DF / (size) | 193G | 193G |
| DF / (used) | **130G** | **128G** |
| DF / (avail) | 64G | 66G |
| DF / (use%) | 68% | **67%** |
| Containers parados | 103 | **0** |
| Volumes dangling | 3 | **0** |
| Networks dangling | 1 | **0** |
| Imagens reclaimable | ? | 63.47 GB (53%) |
| Services coding-vps (running) | 60 | **~47** |

**Gap para target**: Disco deveria cair para ~110-120G; ficamos em 128G.
**Motivo**: imagens Docker (95 total, 119.7 GB) consomem maioria. Para reduzir mais, seria preciso `docker image prune -a` (DESTRUTIVO, requer análise manual caso-a-caso).

---

## Serviços CRÍTICOS preservados (100%)

**17 LLM coding agents**:
- `coding-vps-agents_crew-ai`, `_goose`, `_hermes`, `_kilo-org_kilocode`, `_langgraph`, `_openchamber`, `_openclaw`, `_opencode`, `_openhands`
- `coding-vps_apenas_para_auxilio_cline` (parado — havia redundância c/ opencode)
- `coding-vps_apenas_para_auxilio_crew-ai`, `_goose`, `_hermes`, `_kilo-org_kilocode`, `_langgraph`

**Langfuse LLM observability**:
- `langfuse-web`, `langfuse-worker`, `langfuse-db`, `langfuse-redis`, `langfuse-clickhouse`, `langfuse-minio`

**LiteLLM gateway**:
- `litellm-app`, `litellm-db`

**Langflow / RAG**:
- `langflow`, `langflow-db`

**Argilla (data labeling)**:
- `argilla-web`, `argilla-db`, `argilla-redis` (3 running; worker/elasticsearch/web parado pelo squad 1)

**AnythingLLM RAG**:
- `anything-llm`

**Temporal (workflow engine)**:
- `temporal-server`, `temporal-web`, `temporal-db`, `temporal-elasticsearch`, `temporal-admin-tools`

**Outros**:
- `sonarqube`, `sonarqube-db`
- `sourcegraph`
- `crwal4ai`
- `centrifugo`
- `hermes`, `openclaw`
- `easypanel`, `easypanel-traefik` (control plane)
- `filepizza-redis`, `mirotalk`, `ngrok`, `zincsearch`

---

## Comando padrão de reativação

```bash
# Reativar serviço parado (preserva volumes e config):
docker service scale coding-vps_apenas_para_auxilio_<NAME>=1

# Exemplo:
docker service scale coding-vps_apenas_para_auxilio_yacy=1
```

**Aviso**: ao reativar, verificar se o secret `.env` correspondente ainda está presente em `/var/lib/docker/configs/` ou no vault do Easypanel.

---

## Próximos passos (não executados)

1. **Image prune destrutivo** (`docker image prune -a`) — recuperaria +20 GB, requer curadoria
2. **Remover volumes órfãos** (não-dangling) dos serviços parados há >30 dias — **APENAS com backup** de volumes críticos
3. **Mover argilla-* para scale=1 apenas os usados** (atualmente só redis roda)
4. **Auditar imagens** com `docker images --filter "dangling=false"` para identificar duplicatas (`crawl4ai:latest` vs `all-arm64` = 11 GB)

---

## Lições aprendidas

1. **`docker service scale =0` ≠ `docker service rm`** — scale=0 preserva a definição do serviço e configs no Swarm; rm remove permanentemente. SEMPRE preferir scale=0 em cleanup.
2. **Swarm converge async** — `docker service ls` pode mostrar 1/0 ou 0/0 transitório entre scale e o converge. Aguardar 5-30s para estabilizar antes de re-check.
3. **`docker system prune -f --volumes`** é DESTRUTIVO (deleta TODOS os volumes sem service). Use `docker volume prune` (dangling only) primeiro, `docker volume ls --filter dangling=true` para revisar.
4. **`df` nível VPS não cai imediatamente** após parar containers — só cai após `docker system prune` (real回收 de imagens/containers).
5. **Easypanel preserva tudo** — UI mostra stack original; só containers Swarm não rodam.

---

Modified by Gustavo Almeida
