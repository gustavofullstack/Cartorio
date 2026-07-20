---
name: coding-vps-21
description: |
  Skill para ativar todos os 21+ coding agents da coding-vps_apenas_para_auxilio com provider MiniMax-M3 XMax Thinking.
  Coding agents: anything-llm, cline, crew-ai, goose, hermes, kilo-org_kilocode, langflow, langgraph, litellm-app,
  openchamber, openclaw, opencode, openhands.
  Provider: MiniMax.io Coding Plan | Model: MiniMax-M3 XMax Thinking
  Infra: Easypanel + Docker Swarm + Tailscale SSH (100.99.172.84)
---

# Coding-VPS 21 Coding Agents — Skill de Ativação Completa

## Visão Geral

A `coding-vps_apenas_para_auxilio` é um ambiente Docker Swarm isolado na VPS Hostinger
para hospedar coding agents AI (alternativas ao Claude Code) que usam o provider MiniMax-M3.

## Acesso

| Item | Valor |
|------|-------|
| **VPS Tailscale IP** | `100.99.172.84` |
| **SSH Key** | `~/.ssh/id_ed25519_cartorio` |
| **Easypanel URL** | `http://100.99.172.84:3000` |
| **Easypanel User** | `gustavomar.fullstack@gmail.com` |
| **Easypanel Password** | `<REDACTED_USE_ENV>` |
| **Easypanel API Base** | `/api/rpc/` (v2) |
| **MiniMax API** | `https://api.minimaxi.com/v1` |
| **MiniMax Key** | `<REDACTED_USE_ENV>` |
| **LiteLLM Proxy VPS** | `http://coding-vps_apenas_para_auxilio_litellm-app:4000` |
| **LiteLLM Master Key** | `e39dss0k1baohuqkprjv` |
| **Infra Path VPS** | `/opt/coding-vps-infra/` |

## Easypanel API v2

```python
import json
import urllib.request

BASE = "http://100.99.172.84:3000"

# Login
def login():
    req = urllib.request.Request(
        f"{BASE}/api/rpc/auth/login",
        data=json.dumps({"json": {"email": "<EASEPANEL_EMAIL>", "password": os.environ["EASYPANEL_PASSWORD"], "rememberMe": True}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["json"]["token"]

# Listar projetos + serviços
def list_services(token):
    req = urllib.request.Request(
        f"{BASE}/api/rpc/projects/listProjectsAndServices",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["json"]

# Atualizar env var via docker service
def update_env(service_name, env_add):
    """service_name = coding-vps_apenas_para_auxilio_<name>"""
    cmd = f"docker service update --env-add {env_add} {service_name}"
    subprocess.run(["ssh", "-i", "~/.ssh/id_ed25519_cartorio", "root@100.99.172.84", cmd])
```

## 21 Coding Agents Validados

| # | Service | Status Atual | Provider |
|---|---------|--------------|----------|
| 1 | anything-llm | ✅ UP 1/1 | LiteLLM |
| 2 | cline | ❌ OFF (imagem inexistente) | - |
| 3 | crew-ai | ⚠️ Sem Dockerfile | configurar |
| 4 | goose | ⚠️ Sem Dockerfile | configurar |
| 5 | hermes | ⚠️ Sem Dockerfile | configurar |
| 6 | kilo-org_kilocode | ⚠️ Sem Dockerfile | configurar |
| 7 | langflow | ✅ UP 1/1 | LiteLLM |
| 8 | langflow-db | ✅ UP 1/1 (postgres) | - |
| 9 | langfuse-clickhouse | ✅ UP 1/1 | - |
| 10 | langfuse-db | ✅ UP 1/1 (postgres) | - |
| 11 | langfuse-minio | ✅ UP 1/1 | - |
| 12 | langfuse-redis | ⚠️ UP mas com AUTH | - |
| 13 | langfuse-web | ✅ UP 1/1 (Next.js) | - |
| 14 | langfuse-worker | ✅ UP 1/1 | - |
| 15 | langgraph | ⚠️ Sem Dockerfile | configurar |
| 16 | litellm-app | ✅ UP 1/1 + MiniMax-M3 | central |
| 17 | litellm-db | ✅ UP 1/1 (postgres) | - |
| 18 | openchamber | ⚠️ Sem Dockerfile | configurar |
| 19 | openclaw | ⚠️ Sem Dockerfile | configurar |
| 20 | opencode | ⚠️ Código fonte presente | configurar |
| 21 | openhands | ⚠️ Sem Dockerfile | configurar |

## Padrão de Configuração (cada coding agent)

```yaml
# /opt/coding-vps-infra/<agent>/docker-compose.yml
services:
  <agent>:
    build: .
    environment:
      MINIMAX_API_KEY: <REDACTED_USE_ENV>
      MINIMAX_BASE_URL: https://api.minimaxi.com/v1
      MINIMAX_MODEL: MiniMax-M3
      LLM_PROVIDER: minimax
      LLM_THINKING: true
      LLM_DEFAULT_PROVIDER: minimax
    ports:
      - "<port>:<port>"
    volumes:
      - ./data:/app/data
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
# .env
MINIMAX_API_KEY=<REDACTED_USE_ENV>
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_MODEL=MiniMax-M3
LLM_THINKING=true
```

## Deploy via Easypanel API

```bash
# 1. Salvar .env
ssh root@100.99.172.84 "mkdir -p /opt/coding-vps-infra/<agent>"

# 2. Criar docker-compose.yml + Dockerfile + .env (local)
# 3. SCP pra VPS
scp -r ./<agent>/ root@100.99.172.84:/opt/coding-vps-infra/

# 4. Build imagem
ssh root@100.99.172.84 "cd /opt/coding-vps-infra/<agent> && docker build -t coding-vps/<agent>:latest ."

# 5. Atualizar service spec
ssh root@100.99.172.84 "docker service update --image coding-vps/<agent>:latest coding-vps_apenas_para_auxilio_<agent>"
```

## Validação Final

```python
# 21/21 UP com MiniMax-M3 XMax Thinking
import json
import urllib.request

# Login Easypanel
token = login()

# Listar services
services = list_services(token)["services"]

# Verificar cada um
for svc in services:
    name = svc.get("name")
    print(f"{name}: {svc.get('status', '?')}")
```

## MCP Server (cartorio-mcp-cabuloso extension)

Tool para criar coding agent:
```python
@mcp.tool()
async def create_coding_agent(name: str, image: str, port: int = 8000) -> dict:
    """Create + start a new coding agent on coding-vps with MiniMax-M3 provider."""
    cmd = f"""docker service create \
        --name coding-vps_apenas_para_auxilio_{name} \
        --network coding-vps_apenas_para_auxilio_default \
        --env MINIMAX_API_KEY=<REDACTED_USE_ENV> \
        --env MINIMAX_BASE_URL=https://api.minimaxi.com/v1 \
        --env MINIMAX_MODEL=MiniMax-M3 \
        --publish mode=host,published={port},target={port} \
        {image}"""
    result = subprocess.run(["ssh", "-i", "~/.ssh/id_ed25519_cartorio",
                             "root@100.99.172.84", cmd], capture_output=True)
    return {"name": name, "status": "created", "output": result.stdout.decode()}
```

## Lições Aprendidas (cross-rein)

1. **Easypanel mudou API de `/api/trpc/` para `/api/rpc/`** (lesson 2026-07-08)
2. **Auth mudou de API key fixa para JWT token dinâmico** via `/api/rpc/auth/login`
3. **Coding agents SEM docker-compose** — diretórios vazios em `/etc/easypanel/projects/coding-vps_apenas_para_auxilio/`
4. **Cline é extensão VSCode** — não tem imagem Docker oficial (lesson 158)
5. **MiniMax-M3 LiteLLM config já existe** (lesson 158 v2 corrigiu lesson 158 v1)
6. **Cartório .env tem `MINIMAX_BASE_URL=https://api.minimax.io/v1`** mas deveria ser `https://api.minimaxi.com/v1` — TYPO a corrigir
7. **Não rotacionar chaves** — regra absoluta Gustavo (lesson 16/17/18)
8. **SSH Tailscale bypassa VPS Hostinger DOWN** — `100.99.172.84` direto (lesson 150)
