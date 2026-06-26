# MCP Skill: Easypanel

## Visao Geral
- URL: https://easypanel.2notasudi.com.br
- Admin: admin@2notasudi.com.br
- Projeto: cartorio
- 13 servicos gerenciados

## Servicos Gerenciados
| Servico | Porta | Funcao |
|---------|-------|--------|
| cartorio_api | 8000 | API FastAPI |
| cartorio_chatwoot | 3000 | CRM |
| cartorio_evolution-api | 8080 | WhatsApp Gateway |
| cartorio_n8n | 5678 | Workflows |
| cartorio_openclaw-gateway | 18789 | Agent AI |
| cartorio_redis | 6379 | Cache |
| easypanel-traefik | 80/443 | Reverse Proxy |

## Comandos Uteis
- `easypanel-mcp-server` - MCP CLI (57 tools)
- Logs: `docker service logs <name> --tail 50`
- Deploy: `docker service update --image <image> <name>`
