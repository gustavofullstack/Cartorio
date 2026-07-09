---
name: coding-vps-mcp-deploy-squad2
description: Squad 2 (2026-07-09) — Deploy do MCP orchestrator como serviço Docker Swarm na VPS coding-vps_apenas_para_auxilio. Expõe 60 tools via HTTP REST :8100 + MCP stdio. URL externa Tailscale http://100.99.172.84:8100/.
type: project
---

# MCP Orchestrator — Swarm Deploy (Squad 2)

**Data**: 2026-07-09
**Squad**: SUB-SQUAD 2 (MCP DEPLOY SWARM)
**Status**: ✅ **PRODUÇÃO** — Serviço `coding-vps_apenas_para_auxilio_mcp-orchestrator` UP

---

## Visão geral

O script `scripts/coding_vps_mcp_orchestrator.py` foi empacotado como imagem Docker e deployado como serviço **Docker Swarm** na VPS `coding-vps_apenas_para_auxilio` (Tailscale `100.99.172.84`). Expõe 60 tools agentic (LLM, DOCKER, EASYPANEL, DB, WORKFLOW, etc.) em **HTTP REST na porta 8100**.

| Atributo | Valor |
|---|---|
| **Imagem** | `coding-vps/mcp-orchestrator:latest` |
| **Serviço Swarm** | `coding-vps_apenas_para_auxilio_mcp-orchestrator` |
| **Network** | `easypanel-coding-vps_apenas_para_auxilio` |
| **Porta externa** | `*:8100 -> 8100/tcp` (mode=host) |
| **URL externa (Tailscale)** | http://100.99.172.84:8100/ |
| **Tools expostas** | 60 (13 categorias) |
| **Runtime base** | `python:3.11-slim` + `openssh-client` |
| **Replicas** | 1 |
| **Bind mounts** | `/opt/coding-vps-infra/ssh_key -> /root/.ssh/id_ed25519_cartorio` (ro) <br> `/opt/coding-vps-infra/known_hosts -> /root/.ssh/known_hosts` (ro) |
| **ENV vars** | `MCP_HTTP_PORT=8100`, `LITELLM_API_KEY`, `SSH_TAILSCALE_HOST=100.99.172.84` |

---

## Endpoints validados

| Verbo | Path | Exemplo | Resultado |
|---|---|---|---|
| GET | `/` | `curl http://100.99.172.84:8100/` | `{"name":"coding-vps-orchestrator","tools":60,"categories":[...]}` |
| GET | `/tools` | `curl http://100.99.172.84:8100/tools` | dict com 60 nomes |
| POST | `/call/<tool>` | `curl -X POST http://100.99.172.84:8100/call/chat_minimax -d '{"prompt":"OK","max_tokens":20}'` | `{"reply":"...","elapsed_s":2.26,"reasoning_tokens":18,"total_tokens":204}` |
| POST | `/call/<tool>` | `curl -X POST http://100.99.172.84:8100/call/list_services -d '{}'` | `{"total":90,"up":45,"down":45}` |

---

## Como TRAE / Antigravity se conectam

### Configuração MCP client (TRAE / Claude Desktop / etc.)

```json
{
  "mcpServers": {
    "coding-vps": {
      "type": "http",
      "url": "http://100.99.172.84:8100/sse",
      "transport": "streamable-http"
    }
  }
}
```

> ⚠️ **Importante**: ajustar `url` e `transport` para o que o orchestrator expõe. Para clientes MCP stdio (Antigravity), apontar comando para `python scripts/coding_vps_mcp_orchestrator.py stdio`.

### Acesso HTTP simples (qualquer cliente)

```bash
# Listar tools
curl http://100.99.172.84:8100/tools | jq 'keys'

# Chamar tool
curl -X POST http://100.99.172.84:8100/call/<tool_name> \
  -H "Content-Type: application/json" \
  -d '{"prompt":"...","max_tokens":50}'
```

---

## Arquitetura interna

```
TRAE/Antigravity (Mac)
       │
       │ HTTP Tailscale (100.99.172.84:8100)
       ▼
┌─────────────────────────────────────┐
│ Swarm Service coding-vps_..._mcp-   │
│ orchestrator (coding-vps/mcp-       │
│ orchestrator:latest)                │
│   ├── FastAPI :8100                 │
│   ├── 60 tools registradas          │
│   └── SSH client (subprocess) ──┐   │
└─────────────────────────────────┼─┘
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       │  SSH Tailscale (100.99.172.84:22)                   │
       │                                                     │
       ▼                                                     ▼
docker service ls                       docker exec ... python
(lista 90 serviços)                      (executa no container liteLLM)
                                  │
                                  ▼
                       coding-vps_apenas_para_auxilio_litellm-app:4000
                       (Network: easypanel-coding-vps_apenas_para_auxilio)
```

---

## Procedimento de deploy (replayable)

```bash
# 1. SCP código + chave
scp -i ~/.ssh/id_ed25519_cartorio scripts/coding_vps_mcp_orchestrator.py \
    root@100.99.172.84:/opt/coding-vps-infra/mcp-orchestrator/orchestrator.py
scp -i ~/.ssh/id_ed25519_cartorio ~/.ssh/id_ed25519_cartorio \
    root@100.99.172.84:/opt/coding-vps-infra/ssh_key

# 2. SSH keyscan para known_hosts
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 \
  "ssh-keyscan -H 100.99.172.84 > /opt/coding-vps-infra/known_hosts && chmod 644 /opt/coding-vps-infra/known_hosts"

# 3. Dockerfile + build
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 bash <<'EOF'
cat > /opt/coding-vps-infra/mcp-orchestrator/Dockerfile <<'DOCKER'
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn[standard]==0.32.0 httpx==0.27.2
COPY orchestrator.py /app/orchestrator.py
ENV MCP_HTTP_PORT=8100
EXPOSE 8100
CMD ["python", "orchestrator.py", "http"]
DOCKER
docker build -t coding-vps/mcp-orchestrator:latest /opt/coding-vps-infra/mcp-orchestrator
EOF

# 4. Criar/atualizar serviço
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 bash <<'EOF'
docker service rm coding-vps_apenas_para_auxilio_mcp-orchestrator 2>/dev/null
sleep 3
docker service create \
  --name coding-vps_apenas_para_auxilio_mcp-orchestrator \
  --network easypanel-coding-vps_apenas_para_auxilio \
  --publish mode=host,published=8100,target=8100 \
  --env MCP_HTTP_PORT=8100 \
  --env LITELLM_API_KEY=e39dss0k1baohuqkprjv \
  --env SSH_TAILSCALE_HOST=100.99.172.84 \
  --mount type=bind,src=/opt/coding-vps-infra/ssh_key,dst=/root/.ssh/id_ed25519_cartorio,readonly \
  --mount type=bind,src=/opt/coding-vps-infra/known_hosts,dst=/root/.ssh/known_hosts,readonly \
  --replicas 1 \
  coding-vps/mcp-orchestrator:latest
EOF
```

---

## Lições aprendidas

1. **Network name ≠ stack name**: a rede overlay não é `coding-vps_apenas_para_auxilio_default` — é `easypanel-coding-vps_apenas_para_auxilio` (nome composto Easypanel). Sempre confirmar com `docker network ls | grep <keyword>`.

2. **SSH key não existe por default no swarm manager**. Home root do container é `/root`, mas `~/.ssh/id_ed25519_cartorio` não está populado. Solução: SCP a chave para `/opt/coding-vps-infra/` na VPS, depois bind-mount em **dois paths críticos**:
   - `/root/.ssh/id_ed25519_cartorio` (SSH_PRIVATE_KEY default do código)
   - `/root/.ssh/known_hosts` (evita `Host key verification failed`)

3. **`python:3.11-slim` não inclui `openssh-client`**, e o orchestrator usa `subprocess.run(["scp", ...])`. Sem `ssh`/`scp`, o serviço sobe mas **todas as tools que dependem de SSH falham com `FileNotFoundError`**. Adicionar `openssh-client` no Dockerfile via `apt-get install`.

4. **`BatchMode=yes` no scp não resolve host-key verification sozinho**. O código do orchestrator não usa `-o StrictHostKeyChecking=no`, então precisamos popular `~/.ssh/known_hosts` antes (via `ssh-keyscan -H`). Perm 644 (ssh exige chave privada 600, mas known_hosts pode ser readable).

5. **Modo `host` para publish no Swarm exige escala prévia em alguns casos**. Aqui não houve conflito (porta 8100 estava livre), mas para recycling seguro usar: `docker service scale X=0 && scale X=1`.

6. **CPF/RG/CPF NUNCA trafega neste serviço**: o MCP orchestrator apenas roteia chamadas para tools. Tools que tocam dados do Cartório (api/swarm) passam pelas **3 camadas de PII scrubbing** do backend FastAPI — não é responsabilidade deste serviço.

7. **LGPD-by-design preservado**: o serviço é **stateless** (não grava nada), apenas orquestra. Audit log do Cartório fica no FastAPI principal (`backend/audit_log`). Este deploy não interfere no fluxo de auditoria.

---

## Comandos úteis

```bash
# Logs em tempo real
ssh root@100.99.172.84 "docker service logs -f coding-vps_apenas_para_auxilio_mcp-orchestrator"

# Status + port mapping
ssh root@100.99.172.84 "docker service ps coding-vps_apenas_para_auxilio_mcp-orchestrator --no-trunc"

# Restart (recreate)
ssh root@100.99.172.84 "docker service rm coding-vps_apenas_para_auxilio_mcp-orchestrator && sleep 3 && docker service create ..."

# Teste rápido LLM
curl -X POST http://100.99.172.84:8100/call/chat_minimax \
  -H "Content-Type: application/json" \
  -d '{"prompt":"OK","max_tokens":10}'
```

---

## Arquivos relacionados

| Path | Descrição |
|---|---|
| `scripts/coding_vps_mcp_orchestrator.py` | Código-fonte do MCP server (deployado) |
| `/opt/coding-vps-infra/mcp-orchestrator/` | Diretório na VPS com Dockerfile + orchestrator.py |
| `/opt/coding-vps-infra/ssh_key` | SSH private key bind-mountada (ro) |
| `/opt/coding-vps-infra/known_hosts` | VPS host key (ro) |

---

**Modified by Gustavo Almeida**
