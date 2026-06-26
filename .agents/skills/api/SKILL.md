---
name: api
description: |
  Skill para interagir com a API FastAPI do Cartório via REST, WebSocket e MCP.
  Use quando precisar: gerenciar atendimentos, protocolos, emolumentos, agendamentos,
  obter radar de status de integracoes, verificar integridade de logs de auditoria (SHA256 chain)
  e chamar o MCP Server da API (cartorio-mcp-cabuloso).
  URL: https://api.2notasudi.com.br | Versao: v0.6.0 | FastMCP 3.x
---

# API Backend Central — Skill de Integração

## Acesso

| Item | Valor |
|------|-------|
| **URL Base** | `https://api.2notasudi.com.br` |
| **Documentação OpenAPI** | `https://api.2notasudi.com.br/docs` |
| **Health Check Básico** | `GET /health` → 200 OK |
| **Radar de Integrações** | `GET /api/v1/health/radar` |
| **Porta interna** | 8000 |
| **MCP Server Mount** | `/mcp` (FastMCP) |

## Endpoints Principais

### Health & Radar
```bash
# Health check básico
GET /health

# Radar de integridade (Supabase, Redis, OpenClaw, Evolution, Chatwoot, etc.)
GET /api/v1/health/radar

# Detalhamento de conexões e latências de integrações
GET /api/v1/health/integracoes
```

### Agendamentos
```bash
# Consultar slots disponíveis para atendimento presencial
GET /api/v1/agendamento/disponibilidade?data=2026-06-27

# Reservar um slot
POST /api/v1/agendamento
{
  "nome_cliente": "João Silva",
  "data_hora": "2026-06-27T10:00:00",
  "tipo_ato": "escritura",
  "whatsapp": "+5534999999999"
}
```

### Protocolos & Emolumentos
```bash
# Consultar emolumento MG 2026
GET /api/v1/emolumentos?tipo=certidao_casamento&folhas=1

# Criar protocolo (requer consentimento LGPD)
POST /api/v1/protocolos
{
  "tipo": "segunda_via",
  "canal_origem": "telegram",
  "consent_granted": true,
  "client_ip": "127.0.0.1",
  "metadata": {"certidao": "casamento"}
}
```

## FastMCP Server Tools (164 tools em 6 servers no total)

O backend possui um servidor MCP integrado (`backend/mcp_server.py`) que expõe as seguintes ferramentas oficiais para inteligências artificiais:

| Nome da Tool | Descrição | Parâmetros |
|--------------|-----------|------------|
| `cartorio_calcular_emolumento` | Calcula o valor do emolumento MG 2026. | `tipo` (str), `folhas` (int), `urgencia` (bool) |
| `cartorio_consultar_protocolo` | Verifica status de um protocolo cadastrado. | `numero` (str: ANO-SEQUENCIAL) |
| `cartorio_criar_protocolo` | Abre um novo protocolo exigindo consentimento LGPD. | `tipo` (str), `canal` (str), `consent` (bool) |
| `cartorio_gerar_segunda_via` | Gera um link de download de PDF de segunda via. | `protocolo_numero` (str) |
| `cartorio_audit_verify` | Executa a verificação criptográfica da cadeia de logs de auditoria. | N/A |
| `cartorio_saudacao` | Retorna uma saudação e o status do sistema. | N/A |
| `super_server_info` | Retorna metadados do servidor MCP. | N/A |

### Como usar o MCP Server standalone localmente:
```bash
# Executar a partir do diretório backend
python mcp_server.py
```
O servidor inicializará um uvicorn escutando por padrão na porta `8100` exposto via HTTP/SSE.

## Arquitetura do Backend

```
backend/
├── app/
│   ├── main.py              # Ponto de entrada FastAPI e roteamento global
│   ├── config.py            # Variáveis e configurações do Pydantic Settings
│   ├── db.py                # Conexão SQLAlchemy e session_scope()
│   ├── api/v1/              # Roteadores da API v1 (Telegram, Evolution, LGPD)
│   ├── models/              # Modelos de dados (cliente.py, protocolo.py, etc.)
│   ├── integrations/        # Integrações externas (OpenClaw, Supabase, Redis, etc.)
│   └── services/            # Serviços de negócio (pii.py, audit.py, agendamento.py)
├── tests/                   # 1058 testes unitários e de integração
└── mcp_server.py            # Servidor FastMCP
```

## Variáveis de Ambiente Necessárias

```env
DATABASE_URL=postgresql+psycopg://supabase_admin:...@db:5432/cartorio
REDIS_URL=redis://default:@Techno832466@db:6379/0
OPENCLAW_BASE_URL=https://agent.2notasudi.com.br
OPENCLAW_API_KEY=@Techno832466
OPENCODE_GO_API_KEY=sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ
TELEGRAM_WEBHOOK_SECRET=mysecret
```

## Teste Rápido

```bash
# Validar se o radar de integridade da API está online e verde
curl https://api.2notasudi.com.br/api/v1/health/radar
```
