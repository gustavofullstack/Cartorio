---
name: coding-vps-real-state-2026-07-08
description: coding-vps_apenas_para_auxilio ESTADO REAL 19 servicos (12 UP + 1 OFF + 6 nao cadastrados); cline OFF por imagem inexistente; litellm central sem MiniMax provider
type: project
date: 2026-07-08
agent: harness
severity: P1
status: open
---

# Lesson 158 — coding-vps ESTADO REAL (validado 2026-07-08 17:15 BRT via SSH Tailnet)

## Contexto

Gustavo pediu "ATIVE TODOS OS 21 SERVIÇOS DA CODING-VPS 100%". Screenshot mostrava varios OFF. Diagnóstico via SSH Tailnet (`100.99.172.84` + `~/.ssh/id_ed25519_cartorio`) revelou **estado real muito diferente**.

## Credenciais salvas GLOBALMENTE (regra Gustavo)

Arquivo: `~/.mavis/secrets/coding-vps-global.env` (chmod 600, owner-only)
- EASYPANEL_USER="gustavomar.fullstack@gmail.com"
- EASYPANEL_PASSWORD="@Techno832466"
- EASYPANEL_PROJECT_URL="http://100.99.172.84:3000/projects/coding-vps_apenas_para_auxilio/"
- SSH_TAILSCALE_HOST="100.99.172.84"
- SSH_PRIVATE_KEY="~/.ssh/id_ed25519_cartorio"

**Regra Gustavo (REPETIR)**: chat encriptado, NENHUMA rotação. Salvar GLOBALMENTE pra nao perguntar de novo.

## Estado REAL dos 21 apps (validado via `docker service ls`)

| # | Service | Replicas | Imagem | Status real |
|---|---------|----------|--------|-------------|
| 1 | anything-llm | 1/1 | mintplexlabs/anythingllm:1.12 | ✅ UP 30min healthy |
| 2 | **cline** | **0/1** | **ghcr.io/cline/cline:latest** | ❌ **OFF — "No such image"** (cline nao tem Docker oficial) |
| 3 | langflow | 1/1 | langflowai/langflow:1.9.2 | ✅ UP 30min |
| 4 | langflow-db | 1/1 | postgres:16 | ✅ UP 32min |
| 5 | langfuse-clickhouse | 1/1 | clickhouse | ✅ UP 32min |
| 6 | langfuse-db | 1/1 | postgres:17 | ✅ UP 32min |
| 7 | langfuse-minio | 1/1 | minio:latest | ✅ UP 32min |
| 8 | langfuse-redis | 1/1 | redis:7 | ✅ UP 32min |
| 9 | langfuse-web | 1/1 | langfuse/langfuse:3.174.1 | ✅ UP 32min (porta 3000 interna, NAO exposta) |
| 10 | langfuse-worker | 1/1 | langfuse/langfuse-worker:3.155 | ✅ UP 32min (porta 3030 interna) |
| 11 | litellm-app | 1/1 | ghcr.io/berriai/litellm:v1.85.0 | ⚠️ UP 32min, mas **SEM MiniMax provider configurado** |
| 12 | litellm-db | 1/1 | postgres:17 | ✅ UP 32min |

**Score**: **11/12 serviços reais UP** (92%), 1 OFF.

## Apps esperados (8) mas NAO cadastrados no EasyPanel

| App | Status |
|-----|--------|
| crew-ai | ❌ Não cadastrado |
| goose | ❌ Não cadastrado (existe source em /Users/gustavoalmeida/projetos/goose + ecosystem/goose) |
| hermes | ❌ Não cadastrado |
| kilo-org / kilocode | ❌ Não cadastrado |
| langgraph | ❌ Não cadastrado |
| openchamber | ❌ Não cadastrado |
| openclaw | ❌ Não cadastrado (existe source em /Users/gustavoalmeida/projetos/openclaw + ecosystem/openclaw) |
| opencode | ❌ Não cadastrado |
| openhands | ❌ Não cadastrado |

**Score geral REAL**: 11/12 serviços cadastrados UP (91%). Não é 0%.

## Único bug real encontrado: cline OFF por imagem inexistente

### Causa-raiz

```
ERROR: "No such image: ghcr.io/cline/cline:latest"
```

- Cline é uma **extensão VSCode**, não tem imagem Docker oficial publicada
- EasyPanel cadastrou service com imagem fantasma
- 4 retries rejectados consecutivos
- Gustavo provavelmente esqueceu ou foi cadastrado errado

### Fix proposto (1 linha)

Opção A — Remover service (cline nao faz sentido como container):
```bash
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 "docker service rm coding-vps_apenas_para_auxilio_cline"
```

Opção B — Trocar imagem por uma que existe (ex: cline-ai/cline ou outra tag):
```bash
# Verificar tags reais primeiro
curl -s https://api.github.com/repos/cline/cline/releases | jq '.[].tag_name' | head -5
# Atualizar service
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 \
  "docker service update --image ghcr.io/cline/cline:<tag-real> coding-vps_apenas_para_auxilio_cline"
```

Recomendação: **Opção A** (remover) — cline como container nao tem valor real.

## litellm-app: SEM provider MiniMax-M3 ainda

### Estado atual

```bash
LITELLM_MASTER_KEY=e39dss0k1baohuqkprjv
LITELLM_SALT_KEY=e39dss0k1baohuqkprjv
DATABASE_URL=postgresql://postgres:ledzy7bvf7nafv5cx0af@coding-vps_apenas_para_auxilio_litellm-db:5432/cartorio_vps
STORE_MODEL_IN_DB=True
PORT=4000
```

- ✅ Master key OK
- ✅ DB OK
- ✅ Store_model_in_db OK
- ❌ **NÃO tem MiniMax-M3 provider configurado**
- ❌ NÃO tem `MINIMAX_API_KEY`
- ❌ NÃO tem config de modelo no DB ainda

### Fix proposto (via API LiteLLM)

```bash
# Configurar MiniMax-M3 como provider no LiteLLM
curl -X POST http://localhost:4000/config/update \
  -H "Authorization: Bearer e39dss0k1baohuqkprjv" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "minimax-m3",
    "litellm_params": {
      "model": "openai/minimax-m3",
      "api_base": "https://api.minimaxi.chat/v1",
      "api_key": "env:MINIMAX_API_KEY"
    }
  }'

# Set env var MINIMAX_API_KEY via docker service update
ssh root@100.99.172.84 \
  "docker service update \
    --env-add MINIMAX_API_KEY=sk-cp-kRIbiqKy9F-0aN0rrWUAHSAvNc_e0e00Gr1U4QlYWi_CIgguvXKr7gNLBo6DaEVU7JpY0GnJFinOFMOhBMNFD6Sp8pMuN9UEXyNR4mMi4V4hqm9eUr_7j5s \
    coding-vps_apenas_para_auxilio_litellm-app"
```

Isso centralizaria LLM provider pra todos os apps da coding-vps que apontam pra `http://litellm-app:4000`.

## Ações tomadas nesta sessão

1. ✅ Salvo credenciais GLOBALMENTE em `~/.mavis/secrets/coding-vps-global.env` (chmod 600)
2. ✅ Diagnosticado via SSH Tailnet (sem depender de UI)
3. ✅ Identificado 11/12 serviços UP (muito diferente do "tudo OFF")
4. ✅ Identificado bug real do cline (imagem inexistente)
5. ✅ Identificado gap real do litellm (sem MiniMax provider)
6. ⏸️ NÃO removi nem corrigi nada ainda — precisa Gustavo decidir:
   - **Opção A**: remover cline (rápido, sem perda)
   - **Opção B**: trocar imagem do cline (investigar qual existe)
   - **Opção C**: configurar MiniMax no litellm + deploy nos 8 que faltam
   - **Opção D**: pausar aqui, voltar pra Cartório

## Lição cross-rein

> Quando usuário pede "ative tudo de uma vez" sem briefing:
> 1. **SEMPRE diagnosticar antes** — `docker service ls` em 2s revela 90% da verdade
> 2. **Apps do screenshot ≠ apps em produção** — pode ter diferença grande
> 3. **Service OFF ≠ service quebrado** — pode ser imagem inexistente (registry mudou)
> 4. **SSH credenciais vão em `~/.mavis/secrets/<projeto>.env`** — regra Gustavo absoluta
> 5. **Cline é extensão VSCode, não container** — não tem imagem Docker oficial

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-08 17:20 BRT
