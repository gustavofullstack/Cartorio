---
name: easypanel
description: |
  Skill para interagir com Easypanel via API REST — deploy, gerenciamento de serviços,
  variáveis de ambiente, logs, snapshots e monitoramento.
  URL: https://easypanel.2notasudi.com.br | Projeto: cartorio | 12 serviços Docker Swarm
---

# Easypanel — Skill de Deploy e Gerenciamento

## Acesso

| Item | Valor |
|------|-------|
| **URL** | `https://easypanel.2notasudi.com.br` |
| **API Key** | `1a8ce30b87e79ea57626ade3b4b6215320ff9938472de00ed8eb033213bfac04` |
| **Projeto** | `cartorio` |
| **Admin** | `admin@2notasudi.com.br` |
| **Auth Header** | `Authorization: Bearer <api_key>` |

## API Endpoints

```bash
BASE=https://easypanel.2notasudi.com.br
KEY=1a8ce30b87e79ea57626ade3b4b6215320ff9938472de00ed8eb033213bfac04

# Listar projetos
curl -H "Authorization: Bearer $KEY" $BASE/api/trpc/projects.list

# Listar serviços do projeto cartorio
curl -H "Authorization: Bearer $KEY" "$BASE/api/trpc/services.list?input={\"projectName\":\"cartorio\"}"

# Obter logs de um serviço
curl -H "Authorization: Bearer $KEY" "$BASE/api/trpc/services.logs?input={\"projectName\":\"cartorio\",\"serviceName\":\"api\"}"

# Deploy (atualizar imagem)
curl -X POST \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"projectName":"cartorio","serviceName":"api"}' \
  $BASE/api/trpc/services.deploy
```

## 12 Serviços Docker Swarm

| Serviço | Porta Interna | Estado |
|---------|--------------|--------|
| `cartorio_api` | 8000 | ✅ UP 1/1 |
| `cartorio_chatwoot` | 3000 | ✅ UP 1/1 |
| `cartorio_chatwoot-sidekiq` | worker | ✅ UP 1/1 |
| `cartorio_evolution-api` | 8080 | ✅ UP 1/1 |
| `cartorio_n8n` | 5678 | ✅ UP 1/1 |
| `cartorio_n8n-runner` | worker | ✅ UP 1/1 |
| `cartorio_openclaw-gateway` | 18789 | ✅ UP 1/1 |
| `cartorio_redis` | 6379 | ✅ UP 1/1 |
| `cartorio_redis_dbgate` | 3001 | ✅ UP 1/1 |
| `cartorio_redis_rediscommander` | 8081 | ✅ UP 1/1 |
| `easypanel` | — | ✅ UP 1/1 |
| `easypanel-traefik` | 80/443 | ✅ UP 1/1 |

## Deploy da API FastAPI

```bash
# Método recomendado: SSH + docker build + service update
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 "
  cd /etc/easypanel/projects/cartorio/api/code/ &&
  docker build -t easypanel/cartorio/api:latest . &&
  docker service update --image easypanel/cartorio/api:latest cartorio_api
"

# Verificar após deploy
curl https://api.2notasudi.com.br/health
```

## Atualizar Variável de Ambiente via Docker Service

```bash
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 "
  docker service update \
    --env-add 'NOVA_VAR=valor' \
    cartorio_api
"
```

## Monitoramento

```bash
# Stats de todos os containers
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'

# Logs em tempo real
docker service logs cartorio_api --follow --tail=50

# Swarm status
docker service ls
docker stack ps cartorio
```

## Infraestrutura VPS

| Item | Valor |
|------|-------|
| **Provider** | Hostinger |
| **IP Público** | 187.77.236.77 |
| **IP Tailscale** | 100.99.172.84 |
| **SO** | Ubuntu LTS |
| **RAM** | 15.62 GiB |
| **Disco** | 193G (16% usado) |
| **SSH Key** | `~/.ssh/id_ed25519_cartorio` |

## Variáveis de Ambiente

```env
EASYPANEL_URL=https://easypanel.2notasudi.com.br
EASYPANEL_API_KEY=1a8ce30b87e79ea57626ade3b4b6215320ff9938472de00ed8eb033213bfac04
EASYPANEL_PROJECT=cartorio
```

## Paths VPS Importantes

```
/etc/easypanel/projects/cartorio/     → Config de todos os serviços
/etc/easypanel/projects/cartorio/api/code/  → Código da API FastAPI
/var/backups/cartorio/                → Backups automáticos
/home/node/.openclaw/                 → Config OpenClaw
```

## MCP Server & Client Integration

- **Easypanel/Traefik MCP Client**: O orquestrador de agents utiliza chamadas MCP para automatizar o deploy e coletar status.
- **Tools MCP**:
  - `easypanel_deploy_service(projectName: str, serviceName: str)`: Dispara deploy via API trpc.
  - `easypanel_get_service_logs(projectName: str, serviceName: str)`: Recupera logs.

