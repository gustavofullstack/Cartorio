# MCP Skill: N8N Workflow Engine

## Visao Geral
- URL: https://flow.2notasudi.com.br
- MCP URL: https://flow.2notasudi.com.br/mcp-server/http
- Versao: 2.27.4
- 34 workflows ativos
- 50 MCP tools

## Plugins
- @devlikeapro/n8n-nodes-chatwoot
- n8n-nodes-evolution-api
- n8n-nodes-mcp
- n8n-nodes-pdfkit
- @winth03/n8n-nodes-minio

## Workflows Core
| WF | Nome | Status |
|----|------|--------|
| #00 | Error Handler Global | ✅ |
| #01 | Consulta Emolumento | ✅ |
| #02 | Criar Protocolo LGPD | ✅ |
| #03 | Handoff Humano Chatwoot | ✅ |
| #04 | Boas-Vindas + Consentimento | ✅ |
| #05 | Agendamento | ✅ |
| #06 | Segunda Via | ✅ |
| #12 | Chatbot LLM End-to-End | ✅ |

## Padroes
- Retry: 3x exponential backoff em 63/63 HTTP nodes
- Timeout: 5s/10s em 130/130 HTTP nodes
- X-Correlation-ID em todas requisicoes
- Error Handler conectado ao WF #00 global
