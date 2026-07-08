# MCP Server: coding-vps-orchestrator

MCP server para gerenciar todos os coding agents da `coding-vps_apenas_para_auxilio` via
Easypanel API v2 + Docker Swarm + SSH Tailscale.

## Tools Disponíveis

| Tool | Descrição |
|------|-----------|
| `coding_vps_status()` | Status de todos os 21+ coding agents (UP/DOWN + imagem) |
| `health_check_all()` | Health check HTTP de cada agent rodando |
| `chat_minimax(prompt, max_tokens)` | Chat com MiniMax-M3 XMax Thinking via LiteLLM proxy |
| `configure_agent(service_name)` | Adiciona env vars MiniMax-M3 ao service |

## Configuração

```json
{
  "mcpServers": {
    "coding-vps-orchestrator": {
      "command": "python3",
      "args": ["/path/to/server.py"],
      "env": {
        "EASYPANEL_URL": "http://100.99.172.84:3000",
        "EASYPANEL_USER": "gustavomar.fullstack@gmail.com",
        "EASYPANEL_PASSWORD": "@Techno832466",
        "MINIMAX_API_KEY": "sk-cp-..."
      }
    }
  }
}
```

## Uso standalone

```bash
# Status
python3 server.py status

# Health check
python3 server.py health

# Chat MiniMax-M3
python3 server.py chat "Diga OK"

# Configure agent
python3 server.py configure "crew-ai"
```

## Validação 2026-07-08

- 13/13 services detectados
- 10/13 UP (76.9%)
- 3 DOWN: cline (imagem inexistente), langfuse-web (restart loop), 
  + 1 service que precisa restart manual

## Lições Aprendidas

1. **Easypanel API mudou de `/api/trpc/` para `/api/rpc/`** (v2)
2. **Auth: API key fixa → JWT dinâmico** via `/api/rpc/auth/login`
3. **Coding agents sem docker-compose** — diretórios vazios
4. **LiteLLM proxy centraliza MiniMax-M3** para todos agents
5. **SSH Tailscale bypassa VPS Hostinger DOWN**

Modified by Gustavo Almeida — 2026-07-08