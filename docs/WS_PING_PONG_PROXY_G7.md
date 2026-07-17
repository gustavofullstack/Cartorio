# WebSocket `/ws/atendimentos` — ping/pong sob reverse proxy (G7.10.T4)

| Campo | Valor |
|-------|--------|
| **Task** | G7.10.T4 — WS ping/pong under reverse proxy |
| **Wave** | G7 Wave 26 (agent-side; sem mutar prod) |
| **Rein** | cartorio-sre (+ cartorio-dev no app) |
| **Endpoint** | `wss://api.2notasudi.com.br/api/v1/ws/atendimentos` |
| **Código** | `backend/app/api/v1/ws/atendimentos.py` |
| **Manager** | `backend/app/services/websocket_manager.py` |
| **Edge** | Traefik (`easypanel-traefik`) → Swarm service `cartorio_api` |
| **Regra** | Doc + testes locais. Sem SSH, sem force redeploy. |

---

## 0. TL;DR

O WebSocket de atendimentos usa **ping/pong de aplicação** (JSON), não o frame de controle RFC 6455 do browser.

| Camada | Quem manda | Quem responde | Payload |
|--------|------------|---------------|---------|
| App (canônico) | Cliente | API FastAPI | `{"type":"ping"}` → `{"type":"pong"}` |
| Outro JSON | Cliente | API | qualquer → `{"type":"echo","data":…}` |
| WS control frame | Cliente/proxy/stack | stack ASGI | opcional; **não** é o keep-alive do cartório |

**Por que importa atrás do Traefik:** idle timeouts no edge (e às vezes no Cloudflare se o host estiver *proxied*) fecham sockets “silenciosos”. O dashboard **deve** emitir `{"type":"ping"}` a cada 20–30s e esperar `{"type":"pong"}`. Se o pong não chega, reconectar.

Multi-réplica: o fan-out de eventos é via **Redis pub/sub** (`cartorio:atendimentos`). Sticky session **não** é necessária para correctness de broadcast; sticky só reduz churn se o cliente mantiver estado local na réplica (hoje: só o socket naquela instância).

---

## 1. Topologia

```
Browser / dashboard
        │  WSS (TLS 443)
        ▼
  Traefik (easypanel-traefik)
  Host(`api.2notasudi.com.br`)
        │  HTTP upgrade → WS
        ▼
  Swarm: cartorio_api (N tasks / workers)
        │  local ConnectionManager room
        │  RedisBus.subscribe("cartorio:atendimentos")
        ▼
  Redis 8  ◄── publish de qualquer réplica / serviço
```

Fonte no app:

- Router montado em `app.main` com `prefix="/api/v1"` → path canônico **`/api/v1/ws/atendimentos`**.
- Protocolo documentado no docstring de `ws_atendimentos` (accept → register → Redis listener → ping/pong loop → cleanup).

---

## 2. Contrato de protocolo (app)

### 2.1 Handshake

1. Cliente abre `wss://api.2notasudi.com.br/api/v1/ws/atendimentos`.
2. Server `accept()` + `ConnectionManager.register(ws, "cartorio:atendimentos")`.
3. Server spawna `_redis_listener_loop` (broadcast local de mensagens Redis).
4. Server fica em `receive_text()` loop.

Não há auth no handshake WS neste MVP (dashboard interno). **Não** enviar PII no canal — scrub **antes** do `publish`/`broadcast` (`app/services/pii.py`). Audit de eventos jurídicos fica no serviço publicador, não no endpoint WS.

### 2.2 Keep-alive (obrigatório sob proxy)

```json
// client → server
{"type": "ping"}

// server → client
{"type": "pong"}
```

Recomendação operacional:

| Parâmetro | Valor sugerido | Motivo |
|-----------|----------------|--------|
| Intervalo de ping cliente | **25s** | < idle tipico 60s de LB/proxy |
| Timeout aguardando pong | **10s** | reconectar se silêncio |
| Backoff reconexão | 1s → 2s → 5s → 15s (cap) | evita storm pós-redeploy |
| Max reconnects / sessão UI | ilimitado com jitter | dashboard long-lived |

### 2.3 Echo (debug)

Qualquer payload com `type != "ping"` (ou JSON inválido / texto puro) recebe:

```json
{"type": "echo", "data": { ... }}
// texto não-JSON:
{"type": "echo", "data": {"raw": "..."}}
```

Não use echo como health de produção — use **ping/pong**.

### 2.4 Broadcast (eventos)

Mensagens publicadas no Redis channel `cartorio:atendimentos` chegam a **todas** as réplicas subscritas e são `broadcast` locais para sockets da room. Formato livre (dict JSON); o endpoint **não** persiste.

---

## 3. Traefik / reverse proxy — checklist

Config live fica no EasyPanel/Traefik do VPS (não versionada 1:1 neste repo). Use este checklist ao auditar ou mergear dynamic config.

### 3.1 Upgrade WebSocket

Traefik 2.x+ faz upgrade WS por default no `loadBalancer` HTTP se o cliente manda:

```
Connection: Upgrade
Upgrade: websocket
```

Não adicione middleware que force `Content-Length` fixo ou buffer de body completo no path WS.

### 3.2 Timeouts (entryPoint / transport)

Alvo mínimo para `api` (valores de referência; ajustar no host se o live divergir):

| Setting | Valor mínimo recomendado | Efeito se baixo |
|---------|--------------------------|-----------------|
| EntryPoint `transport.respondingTimeouts.idleTimeout` | **≥ 90s** (prefer 180s–300s) | corta WS idle |
| `readTimeout` / `writeTimeout` | 0 (disable) **ou** ≥ 0 com idle generoso | corta streams longos |
| Service `serversTransport.forwardingTimeouts.idleConnTimeout` | ≥ 90s | corta conn upstream idle |
| Backend uvicorn / proxy interno | sem kill agressivo de idle WS | mesma classe de falha |

Se o host `api` passar por **Cloudflare orange-cloud**, idle WS público costuma ser ~100s — o ping app a 25s mitiga. Preferir **DNS only** (cinza) para WSS long-lived se houver quedas misteriosas.

### 3.3 Sticky session (opcional)

```yaml
# Exemplo de service Traefik (snippet — merge manual no dynamic config)
http:
  services:
    cartorio-api:
      loadBalancer:
        sticky:
          cookie:
            name: cartorio_api_ws
            httpOnly: true
            secure: true
            sameSite: lax
        servers:
          - url: "http://cartorio_api:8000"
```

| Cenário | Sticky? |
|---------|---------|
| Broadcast via Redis (estado atual) | **Não obrigatório** — qualquer réplica serve |
| Sessão com estado só na memória local sem Redis | Obrigatório |
| Rolling update Swarm | Sticky + ping cliente reduz 1006/1001 no browser |

**Recomendação cartório:** manter Redis fan-out (já implementado) + ping cliente; sticky é **nice-to-have** em multi-task.

### 3.4 Headers / middlewares a evitar no path WS

- Rate-limit por IP muito agressivo no **handshake** (60/min costuma ser OK; storms de reconnect não).
- Auth middleware HTTP que não entende Upgrade (se um dia exigir API key no WS, preferir query/header no handshake testado).
- Compressão gzip em upgrade (Traefik em geral não comprime WS; não force).

### 3.5 Path canônico

| Correto | Errado |
|---------|--------|
| `/api/v1/ws/atendimentos` | `/ws/atendimentos` (sem prefix se o router API usa `/api/v1`) |
| `wss://` em prod | `ws://` em prod (TLS obrigatório atrás Traefik LE) |

Health HTTP (não WS): `GET https://api.2notasudi.com.br/health` e `/api/v1/health/radar`.

---

## 4. Expectativas de falha (diagnóstico)

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| Handshake 404 | Router Traefik / path errado | Conferir Host + path `/api/v1/ws/…` |
| Handshake 502/504 | task API down / rede Swarm | `docker service ps cartorio_api` (HOLD SSH) |
| Conecta, cai ~30–60s sem msg | idle timeout proxy | subir idleTimeout **e** ping 25s no cliente |
| Conecta, ping sem pong | hit réplica morta / bug app | reconectar; ver logs `ws.error` |
| Eventos sumindo em 1 aba | client em réplica sem Redis | checar Redis + `RedisBus.subscribe` |
| 1006 abnormal closure | proxy/LB ou rede | correlacionar com deploy / CF |

Logs úteis no app (nível debug/warning):

- `ws.register` / `ws.unregister`
- `ws.redis.broadcast`
- `ws.disconnect` / `ws.error`
- `ws.broadcast.send_failed` (unregister de cliente morto)

---

## 5. Teste local (TestClient) — regressão

Já coberto em `backend/tests/test_ws_atendimentos.py` (Grupo 6 ping/pong) e reforçado em `backend/tests/test_ws_ping_g7.py` (G7.10.T4).

```bash
cd backend
uv run pytest -v --no-cov tests/test_ws_ping_g7.py tests/test_ws_atendimentos.py::TestWSAtendimentosPingPong
# ou da raiz:
make test-one TEST=tests/test_ws_ping_g7.py
```

O TestClient **não** simula Traefik idle; ele valida o contrato app. Timeouts de proxy só se validam em smoke contra `wss://api…` (secção 6).

---

## 6. Smoke prod / staging com cliente `websockets`

Dependência: `websockets` (ou `pip install websockets` / `uv add --dev websockets` em ambiente de ops — **não** commitar secret).

### 6.1 Sketch mínimo (stdlib-friendly com lib websockets)

```python
#!/usr/bin/env python3
"""Smoke WSS ping/pong — G7.10.T4. Não logar PII. Uso ops only."""
from __future__ import annotations

import asyncio
import json
import os
import sys

import websockets

URL = os.environ.get(
    "WS_ATENDIMENTOS_URL",
    "wss://api.2notasudi.com.br/api/v1/ws/atendimentos",
)
PING_EVERY_S = float(os.environ.get("WS_PING_EVERY", "25"))
PONG_TIMEOUT_S = float(os.environ.get("WS_PONG_TIMEOUT", "10"))
ROUNDS = int(os.environ.get("WS_PING_ROUNDS", "3"))


async def main() -> int:
    print(f"connect {URL}")
    async with websockets.connect(URL, open_timeout=15, close_timeout=5) as ws:
        for i in range(1, ROUNDS + 1):
            await ws.send(json.dumps({"type": "ping"}))
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=PONG_TIMEOUT_S)
            except TimeoutError:
                print(f"FAIL round={i}: pong timeout {PONG_TIMEOUT_S}s")
                return 2
            msg = json.loads(raw)
            if msg.get("type") != "pong":
                print(f"FAIL round={i}: expected pong got {msg!r}")
                return 3
            print(f"OK round={i} pong")
            if i < ROUNDS:
                await asyncio.sleep(PING_EVERY_S)
    print("PASS ping/pong under live edge")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

Uso:

```bash
# smoke curto (3 pongs, sem sleep longo)
WS_PING_EVERY=1 WS_PING_ROUNDS=3 python scripts/ws_ping_smoke.py

# simular keep-alive sob proxy (~50s)
WS_PING_EVERY=25 WS_PING_ROUNDS=2 python scripts/ws_ping_smoke.py
```

> O sketch acima pode viver como script ad-hoc no laptop do ops. **Não** é obrigatório versionar se o pytest G7 + doc bastarem; se versionar, colocar em `scripts/ws_ping_smoke.py` sem secrets.

### 6.2 One-liner `websockets` CLI (se disponível)

```bash
python - <<'PY'
import asyncio, json, websockets
async def t():
    uri = "wss://api.2notasudi.com.br/api/v1/ws/atendimentos"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        print(await asyncio.wait_for(ws.recv(), timeout=10))
asyncio.run(t())
PY
```

Esperado: `{"type": "pong"}`.

### 6.3 Critérios DoD smoke

- [ ] Handshake WSS 101 / open sem exception  
- [ ] ≥1 `ping` → `pong` em &lt; 2s RTT típico  
- [ ] ≥2 pongs com intervalo 25s **sem** disconnect (prova idle proxy)  
- [ ] Fechar limpo (sem loop de reconnect storm)

---

## 7. Cliente dashboard (pseudocódigo)

```javascript
// Intervalo 25s; reconectar com backoff se pong faltar
const WS_URL = "wss://api.2notasudi.com.br/api/v1/ws/atendimentos";

function connect() {
  const ws = new WebSocket(WS_URL);
  let pingTimer, pongWatchdog;

  ws.onopen = () => {
    pingTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
        clearTimeout(pongWatchdog);
        pongWatchdog = setTimeout(() => ws.close(4000, "pong-timeout"), 10000);
      }
    }, 25000);
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "pong") {
      clearTimeout(pongWatchdog);
      return;
    }
    // handle broadcast / echo …
  };

  ws.onclose = () => {
    clearInterval(pingTimer);
    clearTimeout(pongWatchdog);
    setTimeout(connect, 2000 + Math.random() * 1000);
  };
}
```

---

## 8. LGPD / segurança

- Canal é **forwarding only** — sem persistência no endpoint WS.
- **Nunca** mandar CPF/RG/protocolo raw no payload de broadcast; scrub no publicador.
- Logs do manager usam `type(e).__name__` / contagens — sem corpo de mensagem PII.
- Expor WSS só em `api.` com TLS; não publicar WS em porta host crua.

---

## 9. Definition of Done (G7.10.T4)

| Item | Status agent-side |
|------|-------------------|
| Doc path Traefik + sticky + timeouts | **este arquivo** |
| Contrato ping/pong app documentado | **este arquivo** |
| Teste pytest ping/pong (TestClient) | `tests/test_ws_ping_g7.py` + suite WS existente |
| Sketch cliente `websockets` | secção 6 |
| Smoke 2× ping/25s em prod | **HOLD** (ops com rede; não bloqueia merge doc) |
| Ajuste live idleTimeout Traefik | **HOLD-GUSTAVO** se smoke falhar por idle |

---

## 10. Referências

- `backend/app/api/v1/ws/atendimentos.py` — protocol loop  
- `backend/app/services/websocket_manager.py` — rooms + broadcast  
- `backend/tests/test_ws_atendimentos.py` — suite T2.API.T19  
- `backend/tests/test_ws_ping_g7.py` — G7.10.T4  
- `docs/CANAL_HEALTH_MATRIX.md` — matriz canais  
- `docs/DNS_TRAEFIK_SUI_PACK_G7.md` — pack Traefik/DNS  
- `infra/traefik/ROUTERS_PENDENTES.yaml` — templates routers  

**Modified by Gustavo Almeida + cartorio-sre — G7 Wave 26**
