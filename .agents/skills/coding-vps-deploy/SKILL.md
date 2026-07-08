---
name: coding-vps-deploy
description: Como deployar novos agents (Docker) no coding-vps_apenas_para_auxilio. Template Dockerfile + docker-compose + .env + registro no MCP orchestrator.
type: agent
created: 2026-07-08
squad: 3
---

# coding-vps-deploy

Skill que guia o **deploy ponta-a-ponta** de um novo agent (FastAPI, Node.js, etc.) no VPS `100.99.172.84` (Docker Swarm) e o registro no MCP orchestrator.

## Quando usar

- Você criou um **novo agent** (ex: novo LLM router, novo scraper) e precisa colocar em produção.
- Você precisa **migrar um serviço** entre stacks Docker ou entre VPS.
- Você quer **adicionar o serviço ao MCP orchestrator** para que outros agentes possam chamá-lo.

## Pré-requisitos

1. VPS acessível via Tailscale: `100.99.172.84`
2. SSH key: `~/.ssh/id_ed25519_cartorio`
3. `docker` e `docker swarm` inicializados (já estão)
4. Porta disponível (verificar com `python3 scripts/coding_vps_mcp_orchestrator.py call port_scan 100.99.172.84 8001-8010`)

## Template de deploy (3 passos)

### Passo 1 — Dockerfile (pasta do agent)

```dockerfile
# agents/my-new-agent/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8010
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
```

### Passo 2 — Deploy via MCP orchestrator

```bash
# 1. Build local e push para registry (Docker Hub, GHCR, ou local registry)
docker build -t gustavomar/my-new-agent:latest ./agents/my-new-agent
docker push gustavomar/my-new-agent:latest

# 2. Criar serviço no Swarm via MCP tool
python3 scripts/coding_vps_mcp_orchestrator.py call swarm_service_create \
  my-new-agent gustavomar/my-new-agent:latest "PORT=8010,LOG_LEVEL=info" 8010

# 3. Verificar saúde
python3 scripts/coding_vps_mcp_orchestrator.py call health_check_all
```

### Passo 3 — Adicionar ao MCP orchestrator

Editar `scripts/coding_vps_mcp_orchestrator.py`:

```python
def my_new_agent_query(prompt: str) -> dict:
    """Rota o prompt para o novo agent via HTTP."""
    return http_post(
        "http://coding-vps_apenas_para_auxilio_my-new-agent:8010/query",
        {"prompt": prompt},
    )

# Em _register_xxx():
"my_new_agent_query": {
    "func": my_new_agent_query,
    "args": ["prompt"],
    "category": "agent",
    "desc": "Chama my-new-agent",
},
```

## Template de .env

```bash
# agents/my-new-agent/.env (NÃO commitar — usar gitignore)
AGENT_NAME=my-new-agent
LOG_LEVEL=info
LITELLM_API_KEY=e39dss0k1baohuqkprjv
REDIS_URL=redis://coding-vps_apenas_para_auxilio_redis:6379
```

## Checklist pré-deploy

- [ ] Porta livre (scan: `port_scan 100.99.172.84 8010`)
- [ ] Imagem com tag `:latest` e/ou `:<git-sha>`
- [ ] `.env` montado como Docker secret ou env inline (não comitar)
- [ ] Health check endpoint `/health` retornando 200
- [ ] Service registrado no MCP orchestrator
- [ ] Skill criada em `.agents/skills/<name>/SKILL.md`
- [ ] Index atualizado em `.agents/skills/INDEX.md`

## Patterns comuns

### FastAPI agent (recomendado)
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query")
def query(prompt: str):
    return {"echo": prompt}
```

### Node.js agent
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 8010
CMD ["node", "server.js"]
```

### Service com dependência de Redis
```yaml
# Embed no swarm_service_create env=... ou criar docker-compose separado
environment:
  - REDIS_HOST=coding-vps_apenas_para_auxilio_redis
  - REDIS_PORT=6379
```

## Rollback

```bash
# 1. Listar versões anteriores
python3 scripts/coding_vps_mcp_orchestrator.py call service_logs my-new-agent 100

# 2. Escalar para 0 e reimagem com tag antiga
python3 scripts/coding_vps_mcp_orchestrator.py call scale_service my-new-agent 0
docker service update --image gustavomar/my-new-agent:v1.0.0 coding-vps_my-new-agent
python3 scripts/coding_vps_mcp_orchestrator.py call scale_service my-new-agent 1
```

## Validação pós-deploy

```bash
# 1. Health check
curl -fsS http://100.99.172.84:8010/health

# 2. Chamada de smoke test
python3 scripts/coding_vps_mcp_orchestrator.py call my_new_agent_query "smoke-test"

# 3. Métricas
python3 scripts/coding_vps_mcp_orchestrator.py call prometheus_query \
  "up{job='my-new-agent'}"
```
