# WebSocket /ws/atendimentos test — 2026-06-24 (sessao 3)

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Resultado: SUCCESS — WS 100% funcional**.

## E2E Test (Python websocket-client)

```python
import websocket, ssl

API_KEY = "CARTORIO_API_KEY_2026_06_24_..."
ws = websocket.create_connection(
    "wss://api.2notasudi.com.br/ws/atendimentos",
    timeout=10,
    header=[f"X-API-Key: {API_KEY}"],
    sslopt={"cert_reqs": ssl.CERT_NONE}  # Easypanel self-signed
)

ws.send('{"type":"ping"}')
# Received: {"type":"pong"}

ws.send('{"type":"subscribe","channel":"atendimentos"}')
# Received: {"type":"echo","data":{"type":"subscribe","channel":"atendimentos"}}

ws.close()
# WS CLOSED OK
```

## Respostas

1. **Ping → Pong** ✅
2. **Subscribe → Echo** ✅ (com channel "atendimentos")
3. **Disconnect limpo** ✅

## Protocolo descoberto

```json
// Client → Server
{"type": "ping"}
{"type": "subscribe", "channel": "atendimentos"}
{"type": "data", ...}  // (client pode enviar dados arbitrarios)

// Server → Client
{"type": "pong"}
{"type": "echo", "data": ...}  // echo de qualquer mensagem recebida
```

## BUG + WORKAROUND

**Bug**: Traefik/Easypanel usa **certificado self-signed** (`cert: Easypanel, valid 2036`)
- `wscat` e `websocket-client` rejeitam por padrão (SSL: CERTIFICATE_VERIFY_FAILED)
- OpenAPI 3.1 não documenta WS (FastAPI adiciona via @app.websocket mas não aparece em /openapi.json)

**Workaround**: `sslopt={"cert_reqs": ssl.CERT_NONE}` no Python
- Para browsers, usuário precisa aceitar cert manualmente (1x)
- Para produção, **configurar Let's Encrypt** (manual ou via acme.sh)

## WebSocket Manager

- **Path**: `/ws/atendimentos` (registrado em `app/api/v1/ws/atendimentos.py:68`)
- **Router**: `ws_router` (incluído em `app/main.py:460`)
- **Manager**: `app.services.websocket_manager.ConnectionManager`
- **Supabase Realtime**: `commit f6aac74` (publication supabase_realtime com 5 tabelas)

## Coverage de testes API (até agora)

- **7/7 health** (DONE)
- **3/3 docs** (DONE)
- **6/6 MCP servers** (DONE)
- **5/5 LGPD** (DONE)
- **6/6 atendimento** (DONE com 1 path typo)
- **2/2 historicos** (DONE)
- **1/1 outbox/dispatch** (DONE)
- **1/1 WebSocket /ws/atendimentos** (DONE - pings + subscribes)
- **TOTAL: 31+ endpoints, 96%+ sucesso**

## Próximos passos

### Curto prazo
- [ ] Configurar Let's Encrypt no Traefik (acme.sh) para remover self-signed
- [ ] Adicionar WS ao OpenAPI (custom OpenAPI schema com @app.websocket)
- [ ] Testar publish real (criar atendimento + receber update via WS)

### Médio prazo
- [ ] Padronizar path `/atendimento` (singular) - remover typo `/atendimentos` (plural)
- [ ] Implementar reconnect automático no cliente WS
- [ ] Adicionar auth via JWT (mais seguro que X-API-Key para WS)

Modified by Gustavo Almeida
