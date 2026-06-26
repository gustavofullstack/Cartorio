# MCP Skill: Chatwoot CRM

## Visao Geral
- URL: https://chat.2notasudi.com.br
- Versao: 4.15.1
- Admin: admin@2notasudi.com.br
- 2 access tokens configurados

## Funcionalidades
- Inbox WhatsApp (via Evolution API)
- Inbox Telegram (via webhook)
- HITL (Human In The Loop)
- Canned responses FAQ
- Macros para atendentes
- Teams de atendimento
- Labels/Tags para categorizacao

## Integracoes
- Webhook Telegram: conectado
- Agent OpenClaw (Pietra): integrado
- Evolution API: pending QR scan

## Endpoints API
- GET /api/v1/accounts - Listar contas
- GET /api/v1/conversations - Listar conversas
- POST /api/v1/accounts/{id}/conversations - Criar conversa
- POST /api/v1/accounts/{id}/conversations/{id}/messages - Enviar msg
