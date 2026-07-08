# Integração TRAE / Antigravity / Claude Desktop — coding-vps MCP Orchestrator

> **Squad 3 — 2026-07-08**. Documenta como integrar o MCP orchestrator (`scripts/coding_vps_mcp_orchestrator.py`) com **TRAE IDE**, **TRAE SOLO.APP**, **Antigravity.APP** e **Claude Desktop**.
>
> **Pré-requisito**: 100+ tools MCP em 15 categorias, expostas via 3 modos: CLI, HTTP (porta 8100) e stdio (MCP nativo).

---

## 1. TRAE IDE (modo MCP stdio)

### Instalação one-time

O arquivo `.trae/mcp-servers/coding-vps.json` já está no repo. TRAE IDE detecta automaticamente.

**Se não detectar manualmente:**

1. Abrir TRAE IDE → Settings → MCP Servers → Add Server
2. Name: `coding-vps`
3. Command:
   ```json
   {
     "command": "python3",
     "args": ["/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py", "mcp"],
     "env": {
       "SSH_PRIVATE_KEY": "/Users/gustavoalmeida/.ssh/id_ed25519_cartorio",
       "SSH_TAILSCALE_HOST": "100.99.172.84",
       "LITELLM_API_KEY": "e39dss0k1baohuqkprjv"
     }
   }
   ```
4. Restart TRAE IDE.

**Validação:**
- TRAE IDE → Tools panel → deve listar 100+ tools em 15 categorias.

---

## 2. TRAE SOLO.APP (modo HTTP)

### Subir o HTTP server

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
uvicorn scripts.coding_vps_mcp_orchestrator:http_app --port 8100 --host 0.0.0.0
```

### Configurar SOLO.APP

1. SOLO.APP → Settings → Tools → Custom MCP Server
2. URL: `http://localhost:8100`
3. (Sem auth, sem token)

### Endpoints

- `GET  http://localhost:8100/` → metadata
- `GET  http://localhost:8100/tools` → lista pública
- `POST http://localhost:8100/call/{tool_name}` → executa tool

---

## 3. Antigravity.APP (modo HTTP + streamable)

Antigravity consome MCP via HTTP streaming. Setup:

```bash
# 1. Subir HTTP server (mesmo de cima)
uvicorn scripts.coding_vps_mcp_orchestrator:http_app --port 8100

# 2. Configurar Antigravity
#    Settings → MCP → URL: http://localhost:8100/mcp
```

---

## 4. Claude Desktop (modo MCP stdio)

Edite `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "coding-vps": {
      "command": "python3",
      "args": ["/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py", "mcp"],
      "env": {
        "SSH_PRIVATE_KEY": "/Users/gustavoalmeida/.ssh/id_ed25519_cartorio",
        "SSH_TAILSCALE_HOST": "100.99.172.84",
        "LITELLM_API_KEY": "e39dss0k1baohuqkprjv"
      }
    }
  }
}
```

Restart Claude Desktop.

---

## 5. Cinco exemplos de uso (qualquer cliente)

### Exemplo 1 — Chat com MiniMax-M3 XMax Thinking

```bash
# CLI
python3 scripts/coding_vps_mcp_orchestrator.py call chat_minimax "Liste os serviços Docker ativos"

# HTTP
curl -X POST http://localhost:8100/call/chat_minimax \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Liste os serviços Docker ativos"}'

# TRAE IDE (linguagem natural)
"Use chat_minimax para listar os 89 serviços Docker ativos no VPS"
```

### Exemplo 2 — Listar serviços (STATUS)

```bash
# CLI
python3 scripts/coding_vps_mcp_orchestrator.py call list_services

# HTTP
curl -X POST http://localhost:8100/call/list_services \
  -H "Content-Type: application/json" -d '{}'

# TRAE IDE
"Chame list_services e mostre os 5 serviços com maior uso de CPU"
```

### Exemplo 3 — Restart de serviço (DOCKER)

```bash
# CLI
python3 scripts/coding_vps_mcp_orchestrator.py call restart_service openclaw

# HTTP
curl -X POST http://localhost:8100/call/restart_service \
  -H "Content-Type: application/json" -d '{"service": "openclaw"}'

# TRAE IDE
"Reinicie o serviço openclaw no VPS e me avise quando terminar"
```

### Exemplo 4 — Web scrape com Firecrawl (SEARCH)

```bash
# CLI
python3 scripts/coding_vps_mcp_orchestrator.py call firecrawl_scrape https://example.com

# HTTP
curl -X POST http://localhost:8100/call/firecrawl_scrape \
  -H "Content-Type: application/json" -d '{"url": "https://example.com"}'

# TRAE IDE
"Faça scrape de https://example.com via firecrawl_scrape e me devolva o conteúdo em markdown"
```

### Exemplo 5 — RAG query via AnythingLLM (RAG)

```bash
# CLI
python3 scripts/coding_vps_mcp_orchestrator.py call anythingllm_query \
  "Qual a política de retenção LGPD do cartório?"

# HTTP
curl -X POST http://localhost:8100/call/anythingllm_query \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual a política de retenção LGPD do cartório?"}'

# TRAE IDE
"Pergunte ao AnythingLLM qual a política de retenção LGPD do cartório e resuma em 3 bullets"
```

---

## 6. Como adicionar nova tool (para dev)

Ver [coding-vps-orchestrator/SKILL.md](../../.agents/skills/coding-vps-orchestrator/SKILL.md).

**TL;DR:**

```python
# 1. Em scripts/coding_vps_mcp_orchestrator.py
def my_new_tool(arg1: str) -> dict:
    """Descrição da tool."""
    return {"result": "ok", "arg1": arg1}

# 2. Em _register_xxx() correspondente
"my_new_tool": {
    "func": my_new_tool,
    "args": ["arg1"],
    "category": "xxx",
    "desc": "Descrição curta",
},

# 3. Validar
python3 scripts/coding_vps_mcp_orchestrator.py list
python3 -c "import ast; ast.parse(open('scripts/coding_vps_mcp_orchestrator.py').read())"
```

---

## 7. Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| `fastmcp not installed` | Dep não instalada | `pip install fastmcp` ou `uv add fastmcp` |
| `SSH timeout` em qualquer tool | Chave SSH não autorizada | `ssh-add ~/.ssh/id_ed25519_cartorio` |
| `tool not found` no TRAE | TRAE não recarregou MCP | Restart TRAE IDE |
| `Connection refused` no HTTP | Server não está rodando | `uvicorn ... --port 8100` em outro terminal |
| `LITELLM_API_KEY invalid` em `chat_minimax` | Key rotacionada | Checar `https://coding-vps_apenas_para_auxilio_litellm-app:4000` |
| HTTP 502 em call | Serviço remoto caiu | `restart_service <name>` |

---

## 8. Referências

- `.agents/skills/coding-vps-orchestrator/SKILL.md` — skill completa do orchestrator
- `.agents/skills/coding-vps-deploy/SKILL.md` — como deployar novos agents
- `.agents/skills/coding-vps-monitor/SKILL.md` — como monitorar saúde
- `.agents/skills/INDEX.md` — catálogo central de skills
- `scripts/coding_vps_mcp_orchestrator.py` — fonte (100+ tools)
- `docs/integrations/` — outros runbooks de integração

---

**Modified by Gustavo Almeida**
