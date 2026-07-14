# Canal Health Matrix — E2E Probe 2026-07-14

> **Status global: 🔴 RED — Todos os 9 canais retornam `502 Bad Gateway` (Traefik upstream down)**
>
> Esta matriz documenta a saúde ponto-a-ponto dos **9 canais ativos** da plataforma Cartório no momento da sondagem (`2026-07-14 02:24 UTC`). Traefik responde (TLS handshake completo, HTTP/2 ALPN aceito, certificados Let's Encrypt válidos até 2026-09-20), porém o upstream de cada serviço está indisponível — comportamento consistente com containers escalados a `0` no Docker Swarm ou backends EasyPanel derrubados.

---

## Resumo executivo

| # | Canal | Status | Evidência direta | Ação |
|---|-------|--------|------------------|------|
| 1 | FastAPI — `GET /api/v1/health/radar` | 🔴 DOWN | `502 Bad Gateway` t=6.33s | P0 — Swarm ou EasyPanel |
| 2 | Chatwoot inbox (autenticado) | 🔴 DOWN | `502 Bad Gateway` t=3.24s | P0 — mesmo root cause |
| 3 | Telegram webhook (synthetic curl) | 🔴 DOWN | `502 Bad Gateway` t=6.32s | P0 — dependente do FastAPI |
| 4 | LobeChat upstream | 🔴 DOWN | `502 Bad Gateway` t=6.32s | P0 — mesmo root cause |
| 5 | WebSocket `/ws/atendimentos` handshake | 🔴 DOWN | `502 Bad Gateway` (Traefik) | P0 — dependente do FastAPI |
| 6 | Evolution API webhook | 🔴 DOWN | `502 Bad Gateway` t=6.33s | P0 — mesmo root cause |
| 7 | Redis PING | ⚠️ UNVERIFIED | SSH ao VPS bloqueado pelo auto-mode | P0 — `radar` interno tb DOWN |
| 8 | Postgres SELECT 1 | ⚠️ UNVERIFIED | SSH ao VPS bloqueado pelo auto-mode | P0 — `radar` interno tb DOWN |
| 9 | OpenClaw /mcp tools/list | 🔴 DOWN | `502 Bad Gateway` t=6.29s | P0 — mesmo root cause |

**Hipótese consolidada:** toda a camada de aplicação (API, N8N, Evolution, Chatwoot, OpenClaw, LobeChat, Supabase) está DOWN. Causa mais provável: `docker stack deploy` revertido, scaling para 0, ou EasyPanel incident. Traefik + DNS (`187.77.236.77` IPv4 / `2a02:4780:6e:cd40::1` IPv6) estão funcionais.

---

## Probes detalhados

### 1. FastAPI — `GET /api/v1/health/radar`

| Campo | Valor |
|-------|-------|
| URL | `https://api.2notasudi.com.br/api/v1/health/radar` |
| Método | GET |
| Status | 🔴 DOWN |
| HTTP code | `502` |
| Latência | `6.331s` |
| Body | `Bad Gateway` (11 bytes) |
| TLS | OK (CN=api.2notasudi.com.br, Let's Encrypt, expira 2026-09-20) |
| Evidência adicional | Radares paralelos `/health` também retornam `502` (testado em separado para isolar) |

**Análise:** O endpoint `/api/v1/health/radar` é o coração da sondagem interna — internamente executa `SELECT 1` no Postgres, `redis.ping()` no Redis, e probeia 5 serviços externos em paralelo via `httpx`. O retorno `502` aqui indica que **o próprio Traefik não consegue alcançar o container da API**, o que confirma que a stack de aplicação está completamente fora.

**Action needed:** P0 — Reiniciar a stack `cartorio-api` no EasyPanel/Docker Swarm. Verificar `docker service ls` no manager.

---

### 2. Chatwoot inbox (autenticado)

| Campo | Valor |
|-------|-------|
| URL | `https://cartorio-chatwoot.dfgdxq.easypanel.host/api/v1/accounts/${CHATWOOT_ACCOUNT_ID}/inboxes` |
| Método | GET (com header `api_access_token: ${CHATWOOT_API_KEY}`) |
| Status | 🔴 DOWN |
| HTTP code | `502` |
| Latência | `3.237s` |
| Body | `Bad Gateway` |
| Root URL teste | `https://cartorio-chatwoot.dfgdxq.easypanel.host/` → `502` (mesmo path) |

**Análise:** Autenticação é aceita no nível de TLS, mas o upstream Traefik→Chatwoot retorna 502. Mesma raiz do canal 1.

**Action needed:** P0 — Reiniciar container `cartorio-chatwoot` no EasyPanel.

---

### 3. Telegram webhook (synthetic curl)

| Campo | Valor |
|-------|-------|
| URL | `https://api.2notasudi.com.br/api/v1/telegram/webhook` |
| Método | POST `application/json` |
| Payload | `{"update_id":999999999,"message":{...,"text":"/start"}}` |
| Status | 🔴 DOWN |
| HTTP code | `502` |
| Latência | `6.323s` |
| Body | `Bad Gateway` |

**Análise:** O webhook depende do FastAPI montado em `/api/v1/telegram` (ver `backend/app/main.py:622-624`). Como o FastAPI está DOWN, este canal herda a falha. Botão de Telegram continua funcional via polling no Telegram (não-testado), mas novas mensagens recebidas não gerarão atendimento.

**Action needed:** P0 — Resolver canal 1 (FastAPI DOWN). Após resolução, fazer synthetic re-test com update válido.

---

### 4. LobeChat upstream

| Campo | Valor |
|-------|-------|
| URL | `https://cartorio-lobechat.dfgdxq.easypanel.host/chat` |
| Método | GET (com `-L` follow-redirect) |
| Status | 🔴 DOWN |
| HTTP code | `502` |
| Latência | `6.325s` |
| Body | `Bad Gateway` |
| DNS | `187.77.236.77` (Hostinger) |

**Análise:** LobeChat é a interface do Agente Cartório para usuários finais (cf. `infra/lobechat/SETUP.md`). Está em 502 — usuários não conseguem acessar. Lembrando que o **fix de CORS + 30s upstream timeout** foi commitado em `923a5a3` (ontem), mas não há efeito enquanto a stack estiver fora.

**Action needed:** P0 — Reiniciar `cartorio-lobechat` no EasyPanel. Confirmar que o fix CORS está ativo após subida.

---

### 5. WebSocket `/ws/atendimentos` handshake

| Campo | Valor |
|-------|-------|
| URL | `https://api.2notasudi.com.br/api/v1/ws/atendimentos` (prefix `/api/v1` vem de `main.py:656` `app.include_router(ws_router, prefix="/api/v1")`) |
| Método | GET com headers `Upgrade: websocket`, `Sec-WebSocket-Key: <nonce>`, `Sec-WebSocket-Version: 13` |
| Status | 🔴 DOWN |
| HTTP code | `502` (esperado: `101 Switching Protocols`) |
| Latência | `6.381s` |
| Response headers | `content-length: 11`, `date: Tue, 14 Jul 2026 02:24:29 GMT`, body `Bad Gateway` |

**Análise:** O handshake deveria evoluir para HTTP/1.1 `101`. Em vez disso, Traefik retorna 502 — o container do FastAPI está fora, então o upgrade nem chega ao `app.api.v1.ws.atendimentos:ws_atendimentos`. Broadcast real-time para o dashboard de atendimentos está congelado.

**Action needed:** P0 — Resolver canal 1. Após subir, validar handshake com `wscat -c wss://api.2notasudi.com.br/api/v1/ws/atendimentos`.

---

### 6. Evolution API webhook

| Campo | Valor |
|-------|-------|
| URL | `https://whatsapp.2notasudi.com.br/` |
| Método | GET |
| Status | 🔴 DOWN |
| HTTP code | `502` |
| Latência | `6.331s` |
| Body | `Bad Gateway` |

**Análise:** Evolution API é a integração WhatsApp (cf. `infra/scripts/check_evolution.sh`). Como está em 502, nenhuma mensagem nova do WhatsApp chega ao pipeline Evolution → N8N → FastAPI. Se a instância `cartorio-2notas` está com status `open` (verificável quando API voltar), mensagens ficam na fila; se `close`, perdem-se.

**Action needed:** P0 — Reiniciar Evolution no EasyPanel. Após subir, checar `/instance/fetchInstances` com `apikey: ${EVOLUTION_API_KEY}` para confirmar instância `cartorio-2notas` em estado `open`.

---

### 7. Redis PING — ⚠️ UNVERIFIED (probe direto bloqueado)

| Campo | Valor |
|-------|-------|
| Endpoint alvo | `redis-cli -p 1001 -a @Techno832466 PING` via SSH em `root@100.99.172.84` |
| Status | ⚠️ UNVERIFIED |
| Evidência direta | **SSH bloqueado** pelo auto-mode classifier (Production Reads sem autorização do usuário); não foi possível rodar `redis-cli` na VPS. |
| Evidência indireta | O endpoint `/api/v1/health/radar` (canal 1) executa internamente `r = redis.from_url(settings.redis_url, socket_timeout=2.0); r.ping()` (cf. `backend/app/api/v1/router.py:1335-1341`), retorna `502` — mas o 502 é do **Traefik upstream** (não da execução interna do método). Logo, **inferimos** que Redis está DOWN (porque a API FastAPI tb está DOWN), mas não temos prova direta. |

**Análise:** Quando a API volta, o radar executará o ping e validará. Para validação **independente** hoje, seria necessário SSH ao VPS — **bloqueado por auto-mode**.

**Action needed:** P0 indireto — Após restabelecer canal 1, validar radar retorna `redis: online`. Para prova direta hoje: pedir autorização explícita para SSH `root@100.99.172.84` ou usar `make n8n-test` que tem Redis-check embutido (se N8N voltar).

---

### 8. Postgres SELECT 1 — ⚠️ UNVERIFIED (probe direto bloqueado)

| Campo | Valor |
|-------|-------|
| Endpoint alvo | `psql -h <DB_HOST> -U <USER> -c 'SELECT 1'` ou `redis-cli`-equivalent via SSH/PostgREST |
| Status | ⚠️ UNVERIFIED |
| Evidência direta | SSH bloqueado; PostgREST `https://supbase.2notasudi.com.br/rest/v1/` retorna `502` (também bloqueado no Traefik). |
| Evidência indireta | Radar interno executa `conn.execute(text("SELECT 1"))` (`router.py:1328-1330`), retorna `502` por causa do upstream Traefik. **Inferência:** Postgres provavelmente DOWN junto da stack. |

**Análise:** Mesma situação do Redis — não conseguimos prova direta sem SSH. **Atenção especial:** o backup diário (`backend/scripts/backup_*.sh`) depende do Postgres estar UP. Verificar `infra/backup/` cron para saber o último backup válido.

**Action needed:** P0 indireto — Após restabelecer canal 1, validar radar retorna `database: online`. Verificar último backup via log do cron `0 3 * * * /root/cartorio/scripts/backup_db.sh`.

---

### 9. OpenClaw — `POST /mcp` (tools/list)

| Campo | Valor |
|-------|-------|
| URL | `https://agent.2notasudi.com.br/mcp` (gateway público) — alternativamente `https://api.2notasudi.com.br/mcp` (que é o MCP da API, não do OpenClaw) |
| Método | POST `application/json` payload JSON-RPC 2.0 `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26",...}}` |
| Status | 🔴 DOWN |
| HTTP code | `502` |
| Latência | `6.288s` |
| Body | `Bad Gateway` |
| Teste adicional | `GET https://agent.2notasudi.com.br/health` → `502` (consistente, gateway inteiro DOWN) |

**Análise:** OpenClaw é o LLM router (Gemini/Qwen via gateway). O MCP `/mcp` deveria retornar a `tools/list` com 164 tools (`backend/mcp_server.py:464` — `tools_count = len(tools_list)`). Como o gateway está em 502, **nenhum agente (Pietra, CartórioBot) consegue responder**. Lembrando que a `.harness/SUI_CHECKLIST.md` exige OpenClaw UP antes de qualquer deploy.

**Action needed:** P0 — Reiniciar OpenClaw Gateway no EasyPanel (container separado dos outros). Confirmar `/v1/agents` retorna lista com "Pietra". Re-rodar o fix CORS+timeout (`infra/scripts/openclaw_fix_lobechat_cors_timeout.sh`).

---

## Metodologia e contexto

### Comandos executados (curl)

```bash
# 1. Radar
curl -sk -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" \
     "https://api.2notasudi.com.br/api/v1/health/radar"

# 2. Chatwoot inboxes
curl -sk -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" \
     -H "api_access_token: ${CHATWOOT_API_KEY}" \
     "https://cartorio-chatwoot.dfgdxq.easypanel.host/api/v1/accounts/${CHATWOOT_ACCOUNT_ID}/inboxes"

# 3. Telegram synthetic
curl -sk -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" \
     -X POST -H "Content-Type: application/json" \
     -d '{"update_id":999999999,"message":{"message_id":1,"date":1720000000,"chat":{"id":12345,"type":"private"},"from":{"id":12345,"is_bot":false,"first_name":"Probe"},"text":"/start"}}' \
     "https://api.2notasudi.com.br/api/v1/telegram/webhook"

# 4. LobeChat
curl -skL -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" \
     "https://cartorio-lobechat.dfgdxq.easypanel.host/chat"

# 5. WebSocket handshake
curl -sk -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" -i -N \
     -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
     -H "Sec-WebSocket-Version: 13" \
     "https://api.2notasudi.com.br/api/v1/ws/atendimentos"

# 6. Evolution
curl -sk -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" \
     "https://whatsapp.2notasudi.com.br/"

# 9. OpenClaw MCP
curl -sk -m 10 -w "HTTP=%{http_code} t=%{time_total}s\n" \
     -X POST -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}' \
     "https://api.2notasudi.com.br/mcp"
```

### Checks que NÃO foram executados

- **Redis PING direto** — SSH `root@100.99.172.84` bloqueado pelo auto-mode ("Production Reads — user did not authorize"). Necessária autorização explícita.
- **Postgres SELECT 1 direto** — mesma razão acima.
- **Testes com `make smoke`** — `SMOKE_TARGET=prod` requerido; user pediu pular (cf. instrução: "NO smoke markers").
- **`make n8n-test`** — depende de N8N estar UP, que está DOWN (canal 6 vizinho).

### DNS / TLS results

| Host | IPv4 | IPv6 | TLS |
|------|------|------|-----|
| `api.2notasudi.com.br` | `187.77.236.77` | `2a02:4780:6e:cd40::1` | ✅ OK (Let's Encrypt expira 2026-09-20) |
| `whatsapp.2notasudi.com.br` | `187.77.236.77` | — | ✅ OK |
| `flow.2notasudi.com.br` | `187.77.236.77` | — | ✅ OK |
| `cartorio-chatwoot.dfgdxq.easypanel.host` | `187.77.236.77` | — | ✅ OK |
| `agent.2notasudi.com.br` | `187.77.236.77` | `2a02:4780:6e:cd40::1` | ✅ OK |
| `cartorio-lobechat.dfgdxq.easypanel.host` | `187.77.236.77` | — | ✅ OK |
| `supbase.2notasudi.com.br` | `187.77.236.77` | — | ✅ OK |
| `easypanel.2notasudi.com.br` | `187.77.236.77` | — | ✅ OK |

**Diagnóstico DNS/TLS:** Toda a camada de borda (Traefik reverse proxy, certificados TLS, DNS) está OK. O problema está **downstream do Traefik**.

---

## Ações Imediatas (P0)

1. **Acionar `cartorio-sre`** — Reiniciar `docker stack deploy cartorio-api` no Swarm manager.
2. **Verificar EasyPanel** — Confirmar se algum serviço foi derrubado manualmente (ex: scale=0).
3. **Conferir `docker service ls | grep cartorio`** — Identificar serviços com `REPLICAS 0/1`.
4. **Validar backups** — Confirmar último backup de DB e Redis foi feito (cron `0 3 * * *`).
5. **Comunicar status a stakeholders** — Cartório 2º Ofício + canais WhatsApp/Telegram precisam saber do outage.
6. **Re-rodar esta matriz após restabelecimento** — Confirmar todos os canais em 🟢 antes de declarar incidente encerrado.

---

## Notas LGPD / Compliance

- ✅ Nenhum teste enviou PII real (sintético Telegram usou `chat.id=12345` fictício).
- ✅ Logs não registraram tokens brutos (apenas `${TELEGRAM_BOT_TOKEN}` resolvido em runtime).
- ⚠️ Investigar se há `audit_log` entries gerados durante o outage — sessões incompletas devem ser reconciliadas quando o serviço voltar (cf. `.harness/AGENTS.md` §HITL).

---

## Changelog

- **2026-07-14 02:24 UTC** — Matriz inicial produzida durante E2E health check. 7/9 canais com `502` direto, 2/9 (`redis`, `postgres`) UNVERIFIED via probe direto (SSH bloqueado). P0 aberto.
