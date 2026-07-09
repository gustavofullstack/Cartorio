# TRAE / SOLO / Antigravity Deep Integration — 2026-07-09

## Como adicionar MCP server ao TRAE.APP

1. Abra TRAE IDE → Settings → MCP Servers
2. Clique em "Add Server"
3. Preencha:
   - **Name**: `coding-vps-orchestrator`
   - **Command**: `python3`
   - **Args**: `/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py mcp`
   - **Env**: `SSH_PRIVATE_KEY=/Users/gustavoalmeida/.ssh/id_ed25519_cartorio;LITELLM_API_KEY=e39dss0k1baohuqkprjv`
4. Salvar e Restart
5. Verificar conexão: deve aparecer "85 tools registered" no log

Alternativa — usar config JSON em `~/.trae/mcp-servers/coding-vps.json`:
```json
{
  "mcpServers": {
    "coding-vps": {
      "command": "python3",
      "args": ["/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py", "mcp"],
      "env": {"SSH_PRIVATE_KEY": "/Users/gustavoalmeida/.ssh/id_ed25519_cartorio", "LITELLM_API_KEY": "e39dss0k1baohuqkprjv"},
      "description": "coding-vps-orchestrator: 85 tools via MCP stdio"
    }
  }
}
```

## Como adicionar ao TRAE SOLO.APP

1. Abrir TRAE SOLO.APP → Preferences → MCP
2. Adicionar server idêntico (acima)
3. Validar conexão

## Como adicionar ao Antigravity.APP

1. Antigravity.APP → Settings → Integrations → MCP
2. Colar config em `~/.antigravity/mcp-servers/coding-vps.json`
3. Restart

## HTTP Mode (alternativa para clients sem suporte stdio)

```bash
cd /Users/gustavoalmeida/projetos/Cartorio
MCP_HTTP_PORT=8100 python3 scripts/coding_vps_mcp_orchestrator.py http &
```

Endpoints:
- `GET http://localhost:8100/` → status + 85 tools
- `GET http://localhost:8100/tools` → listagem completa
- `POST http://localhost:8100/call/{tool_name}` body=`{"arg1":"v1"}`
- `GET http://localhost:8100/openapi.json` → OpenAPI 3.1 spec

## 10 Exemplos Práticos de Uso

### 1. Chat com MiniMax-M3 XMax Thinking
```python
# Via MCP client
result = await mcp.call_tool("chat_minimax", prompt="Como deployar um agent no coding-vps?")
print(result)
```

### 2. Listar 89 serviços
```python
services = await mcp.call_tool("list_services", stack="all")
# 44 UP + 45 scale=0 + 0 down
```

### 3. Reiniciar um agent
```python
await mcp.call_tool("restart_service", service="coding-vps_apenas_para_auxilio_crew-ai")
```

### 4. Ver logs de um serviço
```python
logs = await mcp.call_tool("service_logs", service="coding-vps_apenas_para_auxilio_litellm-app", tail=100)
```

### 5. Scrapar uma URL
```python
md = await mcp.call_tool("firecrawl_scrape", url="https://example.com")
```

### 6. RAG via AnythingLLM
```python
ans = await mcp.call_tool("anythingllm_query", workspace="cartorio", query="LGPD retenção")
```

### 7. Ping Redis
```python
pong = await mcp.call_tool("redis_ping", redis_service="langfuse-redis")
# {result: "PONG"} ou {error: "NOAUTH"} se tem auth
```

### 8. SQL query
```python
result = await mcp.call_tool("postgres_query", db="litellm-db", sql="SELECT count(*) FROM \"LiteLLM_ModelTable\"")
```

### 9. Atualizar imagem (rolling update)
```python
await mcp.call_tool("deploy_image", service="coding-vps_apenas_para_auxilio_crew-ai", image="coding-vps/crew-ai:v3")
```

### 10. Publicar via WebSocket
```python
await mcp.call_tool("centrifugo_publish", channel="cartorio:notifications", data={"event": "novo_atendimento", "id": 12345})
```

## Validação

```bash
# HTTP server
curl -s http://localhost:8100/ | python3 -m json.tool | head

# MCP stdio (testar manualmente)
cd /Users/gustavoalmeida/projetos/Cartorio
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 scripts/coding_vps_mcp_orchestrator.py mcp | head
```

## Referências

- [MCP-ORCHESTRATOR-100-TOOLS.md](file:///Users/gustavoalmeida/projetos/Cartorio/.agents/skills/coding-vps-21/MCP-ORCHESTRATOR-100-TOOLS.md) — doc completa
- [validate-final-2026-07-09-squad5.md](file:///Users/gustavoalmeida/projetos/Cartorio/.agents/skills/coding-vps-21/validate-final-2026-07-09-squad5.md) — validação 18/18 LLM
- [perf-2026-07-09-squad4.md](file:///Users/gustavoalmeida/projetos/Cartorio/.agents/skills/coding-vps-21/perf-2026-07-09-squad4.md) — perf optimize

Modified by Gustavo Almeida (via orquestrador TRAE + MiniMax-M3 XMax Thinking)
[00:00] feat(integration): squad3 deep - MCP configs TRAE/SOLO/Antigravity + 10 examples. Modified by Gustavo Almeida
