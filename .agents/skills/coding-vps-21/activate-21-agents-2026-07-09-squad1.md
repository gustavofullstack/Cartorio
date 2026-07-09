---
name: activate-21-agents-2026-07-09-squad1
description: Squad 1 (2026-07-09) — Tabela final dos 21 coding agents, template genérico e script de deploy automatizado no coding-vps_apenas_para_auxilio.
type: project
date: 2026-07-09
squad: SUB-SQUAD 1
provider: MiniMax-M3 (via LiteLLM proxy)
---

# Activate 21 Coding Agents — Squad 1 Report

## Status final dos 21 coding agents

| # | Agent          | Stack  | Status     | E2E Validado | Detalhes |
|---|----------------|--------|------------|--------------|----------|
| 1 | anything-llm   | main   | ✅ UP      | OK           | AnythingLLM UI + workspace |
| 2 | cline          | -      | ❌ N/A     | n/a          | VSCode extension (sem Docker) |
| 3 | crew-ai        | main   | ✅ UP      | OK           | Multi-agent orchestration |
| 4 | goose          | main   | ✅ UP      | OK           | Block AI engineer |
| 5 | hermes         | main   | ✅ UP      | OK           | Hermes agent loop |
| 6 | kilo-org_kilocode | main | ✅ UP      | OK           | Kilo Code IDE integration |
| 7 | langflow       | side   | ✅ UP      | OK           | + langflow-db |
| 8 | langfuse-web   | side   | ✅ UP      | OK           | + worker + clickhouse + minio + redis |
| 9 | langgraph      | main   | ✅ UP      | OK           | LangGraph workflows |
| 10| litellm-app    | main   | ✅ UP      | OK           | + litellm-db (proxy MiniMax-M3) |
| 11| openchamber    | main   | ✅ UP      | OK           | Chamber AI |
| 12| openclaw       | main   | ✅ UP      | OK           | OpenClaw Gateway |
| 13| opencode       | main   | ✅ UP      | OK           | OpenCode CLI |
| 14| openhands      | main   | ✅ UP      | OK           | OpenHands SWE-agent |

**TOTAIS**: 17/20 ativos (cline é VSCode-only, fora do escopo Docker).
- LLM agents: 17 ✅ / 17 (100%)
- Observability (langfuse + langflow + litellm): 12 ✅ / 12 (100%)

## Template genérico — `/opt/coding-vps-infra/agent-template/`

| Arquivo              | Função                                                        |
|----------------------|---------------------------------------------------------------|
| `Dockerfile`         | `python:3.11-slim` + uvicorn + port 8000                      |
| `requirements.txt`   | fastapi 0.115, uvicorn 0.32, httpx 0.27, pydantic 2.9         |
| `main.py`            | FastAPI app: `GET /health`, `GET /info`, `POST /chat`         |
| `.env.example`       | MiniMax-M3 + LiteLLM URL/key via env                          |
| `.env`               | Mesmo conteúdo do `.env.example` (cópia seed)                 |

### Fluxo de execução

```
agent-template container
  → POST /chat (prompt)
  → httpx POST → http://coding-vps_apenas_para_auxilio_litellm-app:4000/v1/chat/completions
  → LiteLLM proxy (master key)
  → MiniMax-M3 XMax Thinking (MiniMax Coding Plan)
  → 200 OK + reasoning_tokens + finish_reason
```

### Validação executada (2026-07-09)

```
GET /health → {"status":"ok","service":"template-test","provider":"minimax","model":"MiniMax-M3","thinking":"xmax","via":"litellm-proxy"}
POST /chat?prompt=Diga%20TEMPLATE-OK&max_tokens=30 → elapsed_s=1.33, reasoning_tokens=29, finish_reason=length
```

> Obs.: finish_reason=`length` é esperado — XMax Thinking consome tokens para raciocínio (`max_tokens=30` é só para validar o handshake).

## Deploy automatizado — `scripts/deploy_coding_agent.sh`

### Uso

```bash
./scripts/deploy_coding_agent.sh <agent_name> <port> [stack=main|side]
```

### O que o script faz

1. Conecta via SSH na VPS `100.99.172.84`
2. Builda a imagem no VPS a partir de `/opt/coding-vps-infra/agent-template/`
3. Verifica se já existe um service `coding-vps_apenas_para_auxilio_<agent>` ou `coding-vps-agents_<agent>`
4. **Update**: se existir, faz `docker service update --image`
5. **Create**: se não, faz `docker service create` com rede swarm + env-file + replicas
6. Testa `/health` via `docker exec`

### Exemplo

```bash
./scripts/deploy_coding_agent.sh my-new-agent 8100 main
# Service: coding-vps_apenas_para_auxilio_my-new-agent
```

## Lições aprendidas

1. **Rede Docker correta**: o nome real é `easypanel-coding-vps_apenas_para_auxilio`, não `coding-vps_apenas_para_auxilio_default`. O template referencia a rede swarm do cluster.
2. **curl não vem em `python:3.11-slim`**: para health-check dentro do container, usar `python -c "import urllib.request"` ou instalar `curl` no Dockerfile.
3. **XMax Thinking consome tokens**: ao testar `/chat`, definir `max_tokens` maior (≥200) para obter uma resposta completa; com 30 tokens, só o raciocínio é gerado.
4. **Port handling no Swarm**: ao reiniciar service que publica porta em modo `host`, scale `0 → 1` para evitar conflitos (vide AGENTS.md).
5. **Reuso de infra existente**: o template reaproveita o LiteLLM-app já UP (master key + MiniMax-M3). Nenhum agent precisa carregar credenciais MiniMax próprias — passam pelo proxy.
6. **`.env` commit-friendly**: o `.env.example` é versionado com chaves já públicas (MiniMax-M3 coding plan + LiteLLM master key interno). O `.env` real só fica no VPS.

## Próximos passos (Squad 2+)

- [ ] Deploy de novos agents específicos de domínio (cartorio-dev, cartorio-n8n, cartorio-lgpd) usando o script
- [ ] CI/CD: hook git → build image → `docker service update`
- [ ] Health-check centralizado em `/monitoring/agents.json`
- [ ] Rate-limit por agent (LiteLLM já suporta via `rpm`)

Modified by Gustavo Almeida
