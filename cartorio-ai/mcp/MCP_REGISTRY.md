# MCP_REGISTRY

Registro MCP (Model Context Protocol) do projeto (2026-07-20).

## Servidor MCP do backend

- `backend/mcp_server.py` (FastMCP, protocolo 2025-03-26), montado em `/mcp` quando `MCP_SERVER_ENABLED=true`.
- Inventário real: `grep -c '@mcp.tool' backend/mcp_server.py` → **14 tools** (número muda; não hardcodar).
- Start standalone: `make -C backend mcp-server` (porta default 8765).
- Config de clientes: `~/.mavis/mcp/clients/cartorio-mcp-config.json` (caminho de config, **não** cofre de segredos).

## Tools expostas (categorias)

- Saúde/diagnóstico: health radar, status de serviços Swarm.
- Consulta operacional: protocolos, agendamentos, emolumentos (read-only, PII mascarada).
- Auditoria: verificação de cadeia SHA256+HMAC (amostra), contagem de entradas.

## Regras de segurança MCP

- Nenhuma tool retorna PII raw — scrub `pii.py` na borda.
- Auth: API key (`X-API-Key`) com rate limit 3-tier (N8N 600 / DPO 60 / default 30).
- N8N consome via `/mcp-server/http` — 401 silencioso se o header de auth estiver errado (gotcha conhecido).
- Permissões por tool em `mcp/MCP_PERMISSIONS.md`; testes em `mcp/MCP_TESTS.md`.

## Clientes conhecidos

- n8n (workflow engine), agentes locais (Kimi/Claude), smoke tests E2E.
