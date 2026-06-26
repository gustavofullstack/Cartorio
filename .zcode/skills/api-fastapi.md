# Skill: API FastAPI Management
## Purpose
Manage Cartório FastAPI backend.
## URL
- https://api.2notasudi.com.br
- Health: GET /health
- Radar: GET /api/v1/health/radar
- OpenAPI: GET /openapi.json
## Endpoints (89)
- Health: /health, /ready, /api/v1/health/*
- Business: /api/v1/emolumento/*, /api/v1/agendamento/*, /api/v1/protocolo/*
- LGPD: /api/v1/cliente/*/lgpd/*
- Brain: /api/v1/brain/*
- Admin: /api/v1/admin/*
- Webhooks: /api/v1/webhook/*, /api/v1/telegram/webhook
## MCP Server
- URL: http://localhost:8000/mcp
- Tools: 7 (emolumento, protocolo, audit, segunda-via, etc.)
## Gates
- mypy: 0 errors
- ruff: 0 errors
- pytest: 1543+ passed
- Coverage: 90%+
