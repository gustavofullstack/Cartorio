# Skill: N8N Workflow Engine
## Purpose
Manage N8N workflows for automation.
## URL
- https://flow.2notasudi.com.br
- Health: GET /healthz
- MCP: https://flow.2notasudi.com.br/mcp-server/http
## Workflows (34 active)
- WF00: Error Handler Global
- WF01: Consulta Emolumento WhatsApp
- WF02: Criar Protocolo LGPD
- WF03: Handoff Humano Chatwoot
- WF04: Boas-Vindas + Consentimento LGPD
- WF05: Agendamento Atendimento
- WF06: Segunda Via Documento
- WF07: Pesquisa Satisfação 24h
- WF08: Audit Verify Diário (cron 03:30)
- WF09: Monitor Backup Diário (cron 04:00)
- WF10: FAQ Bot
- WF11: Monitor Cartório
- WF12: Chatbot LLM End-to-End
- MCP: Server Tools
## Plugins
- @devlikeapro/n8n-nodes-chatwoot
- @winth03/n8n-nodes-minio
- n8n-nodes-evolution-api
- n8n-nodes-mcp
- n8n-nodes-pdfkit
## Patterns
- Retry: 3x exponential backoff (63/63 nodes)
- Timeout: 5s/10s (130/130 nodes)
- X-Correlation-ID header
- Prometheus metrics
