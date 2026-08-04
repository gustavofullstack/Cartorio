# API Audit SQUAD1 T1

## /openapi.json
- **Methods**: HEAD, GET
- **Name**: openapi
- **Summary**: No summary
- **Description**: No description

## /version
- **Methods**: GET
- **Name**: version_info
- **Summary**: None
- **Description**: Retorna versao completa + links (RFC 8594).

## /health
- **Methods**: GET
- **Name**: health
- **Summary**: None
- **Description**: Liveness probe.

## /ready
- **Methods**: GET
- **Name**: ready
- **Summary**: None
- **Description**: Readiness probe - confirma DB e audit log inicializados.

## /healthz
- **Methods**: GET
- **Name**: healthz
- **Summary**: None
- **Description**: Liveness probe (alias canônico para k8s/Traefik).

## /readyz
- **Methods**: GET
- **Name**: readyz
- **Summary**: None
- **Description**: Readiness probe (alias canônico para k8s/Traefik).

## /metrics
- **Methods**: GET
- **Name**: metrics_root
- **Summary**: None
- **Description**: Redirect para `/api/v1/metrics/prometheus` (mesma exposicao Prometheus).

Orquestradores (k8s, Traefik, Prometheus scraper) costumam scrape
`/metrics` na raiz. Mantemos o endpoint canonico versionado em
`/api/v1/metrics/prometheus` e este alias devolve 410 com link no body
para evitar caching stale de respostas inconsistentes.

## /
- **Methods**: GET
- **Name**: root
- **Summary**: None
- **Description**: Root - redireciona para Swagger UI.

## /mcp-servers
- **Methods**: GET
- **Name**: mcp_servers
- **Summary**: None
- **Description**: Lista MCP servers registrados (descoberta via mcp_config global).

Retorna metadata dos 5 servers MCP disponiveis para clients
(Antigravity, OpenCode, Claude Code, Zed):

- n8n-mcp         : workflows N8N via MCP-HTTP
- supabase-mcp    : Postgres + docs (config em ~/.gemini/antigravity/mcp_config.json)
- cartorio-api    : esta propria API como MCP tools (backend/mcp_server.py)
- easypanel-mcp   : controle do Easypanel (helbertparanhos/easypanel-mcp-server)
- openclaw-mcp    : gateway OpenClaw para tools customizadas

Config global: ~/.mavis/mcp/clients/cartorio-mcp-config.json

## /tools_description.json
- **Methods**: GET
- **Name**: mcp_tools_description
- **Summary**: None
- **Description**: Serve o descritor versionado das tools MCP para descoberta por clientes.

O arquivo é mantido em paridade com ``backend/mcp_server.py`` por testes;
manter o endpoint na origem da API evita configurações de cliente apontando
para uma cópia local ou para o antigo caminho duplicado ``/mcp/mcp``.

## /docs
- **Methods**: GET
- **Name**: custom_swagger_ui_html
- **Summary**: None
- **Description**: Swagger UI customizado com header institucional e tema dark blue.

G8.17.T4 — `persistAuthorization: true` no JS faz o Swagger UI
armazenar o bearer token em `localStorage` do browser (e nao em cookie
nem em storage server). Isso garante que:

1. O token NAO vaza pro backend (LGPD art. 46 — seguranca).
2. O token PERSISTE entre reloads (F5/refresh) ate a aba fechar.
3. Cada aba/dominio tem storage isolado (same-origin policy).

Cache-Control: no-store evita que browsers/CDNs cacheiem a pagina e
sirvam uma versao antiga do schema OpenAPI ao desenvolvedor que
acabou de adicionar endpoints novos.

Ver docs/SWAGGER_PERSIST_AUTH_G8.md para detalhes do fluxo completo.

## /redoc
- **Methods**: GET
- **Name**: redoc_html
- **Summary**: None
- **Description**: ReDoc com branding institucional.

## /dashboard
- **Methods**: GET
- **Name**: dashboard_html
- **Summary**: None
- **Description**: Painel do Agente AI & Radar de Preços Reais do 2º Serviço Notarial de Uberlândia (Djalma).
