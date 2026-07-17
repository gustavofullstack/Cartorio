---
name: openclaw-e8-finalize-2026-07-14
description: Finalize E8 do Squad E (OpenClaw provision CartorioBot). Mapeado o protocolo WS v4 + auth + gaps E8. SSH VPS indisponivel (porta 22 recusada, bate Lesson 176). Token local tem scopes vazias -> bloqueia agents.list/create. NAO foi possivel configurar cartorio-bot ou rodar 3 calls reais sem Gustavo ajustar openclaw.json ou gerar operator token com scopes no gateway. Catalog.py atualizado com 9 endpoints OpenClaw (67 totais).
type: project
date: 2026-07-15
agent: cartorio-openclaw
squad: E
task: E8
status: hold-gustavo
severity: P2
tags: [openclaw, e8, swarm, ws-protocol, auth-scope, agent-provision, hold-gustavo]
---

# Lesson 177 — OpenClaw E8 finalize CartorioBot (cartorio)

## TL;DR

- **MISSÃO F3 [P1] parcialmente cumprida**: mapeamento do OpenClaw gateway via WS protocol v4 foi 100% bem-sucedido. **Configuração do `cartorio-bot` + 3 calls reais foram BLOQUEADAS** por causa de `hello-ok.auth.scopes=[]` (o `OPENCLAW_GATEWAY_TOKEN` em `.secrets/openclaw.env` é só health-probe token).
- **SSH VPS indisponível** (porta 22 recusada em 187.77.236.77 + Tailscale timeout em 100.99.172.84) — bate Lesson 176 (Tailscale offline 2+ dias, fallback VPS público também offline). Comando `docker exec` / `cat /home/node/.openclaw/openclaw.json` não rodaram. Working tree analysis via endpoints públicos + WS handshake.
- **Estado E8** (via WS handshake `hello-ok.snapshot.health`):
  - `defaultAgentId: "main"` (agent default). **`cartorio-bot` NÃO EXISTE.**
  - OpenClaw v2026.7.1 (server.version), container `972b7b047d2d` (10.11.0.20 swarm).
  - **48 plugins carregados** incluindo `openai, anthropic, google, opencode, opencode-go, litellm, mistral, voyage, lmstudio, ollama, vllm, talk-voice, browser, canvas, memory-core, device-pair, github-copilot, file-transfer, comfy, runway, huggingface`.
  - Event loop healthy: `degraded: false, utilization: 0.06, p99: 27ms`.
  - Hot reload `active`. Model pricing `ok`.
- **Auth discovery** (sequência de tentativas em ordem):
  1. `Authorization: Bearer TOKEN` no header HTTP → 401
  2. Basic auth `TOKEN:PASS` → 401
  3. `X-Gateway-Token`, `X-API-Key`, `Cookie` → 401
  4. WS com `connect.params.auth.token` e scope `operator.read|write|admin` → **hello-ok OK mas scopes=[]**
  5. WS com `client.id=cli, mode=backend` + token+password → **funcionou** mas scopes continuam `[]`
- **Endpoints REST validados** (`https://agent.2notasudi.com.br`):
  - `GET /health` → 200 JSON `{ok, ts, eventLoop, plugins, modelPricing, channels, defaultAgentId}` (~16ms)
  - `GET /v1/models` → 401 (sem auth) / 200 esperado (com auth)
  - `GET /v1/agents` → 200 HTML (SPA catch-all OpenClaw Control UI)
  - `POST /v1/chat/completions` → 401 sem auth (OpenAI-compat)
  - `WS /v1/chat` → handshake `connect.challenge` → `hello-ok`
- **Latências observadas**: HTTP 401 = ~70ms; WS `connect.challenge` = ~110ms; WS `hello-ok` = ~20ms após connect req.

## Gaps E8 (pendências Gustavo)

| # | Gap | Bloqueio | Ação Gustavo |
|---|---|---|---|
| 1 | SSH VPS indisponível | Lesson 176 — Tailscale + Hostinger 22 recusada | Reiniciar Tailscale / liberar firewall / SSH alternativo |
| 2 | `cartorio-bot` não existe | `defaultAgentId="main"`; só 1 agent carregado | Após SSH OK, editar `/home/node/.openclaw/openclaw.json` adicionando `agents.list[].id="cartorio-bot"` com system prompt Cartório + tools (API+N8N+SUPABASE+REDIS+CHATWOOT+EVOLUTION+MCPS+TOOLS+PLUGINS+SKILLS+HOOKS) |
| 3 | Auth scopes vazias | `OPENCLAW_GATEWAY_TOKEN` é health-only | Gerar novo operator token via `agents.list` no Control UI ou via `web.login.start` (precisa scope `operator.admin`). Atualizar `.secrets/openclaw.env`. |
| 4 | 3 calls reais não rodaram | Bloqueio #3 | Após #3 OK, rodar WS `sessions.send` com agentId=cartorio-bot, prompt="Qual o horário?", etc. |
| 5 | Configuração de skills | Skills status requer scope | Após #3, `skills.status` + `skills.install` para carregar prompt-cartorio + LGPD-by-design + TDD |
| 6 | Memory cross-rein `.harness/memory` | Sem evidence de leitura | Após SSH OK, verificar se `agents.list[].workspace` aponta para `/Users/gustavoalmeida/projetos/Cartorio/.harness/memory/` ou se há bind mount |

## Catálogo OpenClaw adicionado (catalog.py)

`/Users/gustavoalmeida/projetos/Cartorio/.brain/api-specs/catalog.py` atualizado:

- **9 novos endpoints** em `OPENCLAW_GATEWAY_ENDPOINTS` (tag prefixo `openclaw-*`):
  - `GET /health` (openclaw-health)
  - `GET /v1/models` + `GET /v1/models/{id}` + `POST /v1/embeddings` (openclaw-models)
  - `POST /v1/chat/completions` + `POST /v1/responses` (openclaw-chat, lgpd_scope=True)
  - `POST /tools/invoke` (openclaw-tools, lgpd_scope=True)
  - `WS /v1/chat` (openclaw-ws, lgpd_scope=True) — **protocolo v4**
  - `POST /api/v1/admin/rpc` (openclaw-admin, alpha)
- **Total catalog**: 67 endpoints (54 v1 + 4 v2 + 9 openclaw) — testes existentes (>=50 v1, >=3 v2) continuam passando.
- Constantes: `OPENCLAW_GATEWAY_BASE = "https://agent.2notasudi.com.br"`, `OPENCLAW_GATEWAY_WS = "wss://agent.2notasudi.com.br/v1/chat"`.

## Protocolo OpenClaw WS v4 (mapeado)

```
URL:   wss://agent.2notasudi.com.br/v1/chat
Flow:
  1. client.connect
  2. RX  {type:"event", event:"connect.challenge", payload:{nonce, ts}}
  3. TX  {type:"req", id, method:"connect", params:{
        minProtocol:4, maxProtocol:4,
        client:{id:"cli", version:"0.6.0", platform:"linux", mode:"backend"},
        role:"operator", scopes:["operator.read","operator.write","operator.admin"],
        caps:[], commands:[], permissions:{},
        auth:{token:"<OPENCLAW_GATEWAY_TOKEN>", password:"<OPENCLAW_GATEWAY_PASSWORD>"},
        locale:"pt-BR", userAgent:"openclaw-cli/0.6.0"
      }}
  4. RX  {type:"res", id, ok:true, payload:{
        type:"hello-ok", protocol:4,
        server:{version:"2026.7.1", connId:"..."},
        features:{methods:[218 items], events:[30 items]},
        snapshot:{presence:[], health:{...}, stateVersion, uptimeMs, sessionDefaults},
        auth:{role:"operator", scopes:[]},        ← vazias!
        policy:{maxPayload:26214400, maxBufferedBytes:52428800, tickIntervalMs:30000}
      }}

Frames:
  req:  {type:"req",  id, method, params}
  res:  {type:"res",  id, ok, payload|error}
  event:{type:"event", event, payload, seq?, stateVersion?}

Errors comuns:
  - INVALID_REQUEST: "missing scope: operator.read"  → token sem scope
  - INVALID_REQUEST: "at /client/id: must be equal to one of the allowed values"
                                              → client.id precisa ser allowlist (cli, gateway-client, ...)
  - INVALID_REQUEST: "at /client/mode: must be equal to one of the allowed values"
                                              → client.mode precisa ser {operator, node, backend}
  - INVALID_REQUEST: "invalid connect params"  → role+scopes combinação inválida
  - INVALID_REQUEST: "unauthorized: gateway password missing"  → mode=backend/node exige password
```

## 218 methods descobertos (subset relevante)

```
agents.list / agents.create / agents.update / agents.delete
agents.files.list / agents.files.get / agents.files.set
models.list / models.authStatus / models.authLogout
skills.status / skills.search / skills.detail / skills.install / skills.update
skills.upload.begin / skills.upload.chunk / skills.upload.commit
tools.catalog / tools.effective / tools.invoke
config.get / config.set / config.apply / config.patch / config.schema
sessions.list / sessions.send / sessions.subscribe / sessions.abort / sessions.reset
status / health / diagnostics.stability / logs.tail
channels.status / channels.start / channels.stop
node.pair.request / node.pair.list / node.pair.approve / node.pair.verify
device.pair.list / device.pair.approve / device.pair.reject / device.token.rotate
cron.get / cron.list / cron.run / cron.add / cron.remove
wake / last-heartbeat / set-heartbeats
update.status / update.run
secrets.reload / secrets.resolve
audit.list / tasks.list
crestodian.chat / wizard.start
talk.catalog / talk.config / talk.client.create / talk.session.create
```

## Comandos úteis (rodar como Gustavo)

```bash
# 1. SSH no VPS (depende de Tailscale UP)
ssh cartorio-public    # alias em ~/.ssh/config → 187.77.236.77

# 2. Inspecionar openclaw.json (DEPOIS de SSH OK)
docker exec $(docker ps -q -f name=cartorio_openclaw-gateway.1 | head -1) \
  cat /home/node/.openclaw/openclaw.json | jq .

# 3. Estado do service
docker service ps cartorio_openclaw-gateway --no-trunc
docker service logs cartorio_openclaw-gateway --tail 50

# 4. Se precisar ajustar scopes, gerar novo operator token via Control UI
#    (https://agent.2notasudi.com.br → Config → Operators) ou via:
docker exec $(docker ps -q -f name=cartorio_openclaw-gateway.1 | head -1) \
  openclaw models auth paste-token --provider openai
# (depois atualizar ~/.openclaw/openclaw.json → gateway.auth.scopes)

# 5. Validar scopes localmente (com token novo)
TOKEN="<novo>"; PASS="<novo>"
python3 -c "
import json, ssl, time, uuid, websocket
ws = websocket.WebSocketApp('wss://agent.2notasudi.com.br/v1/chat',
    on_message=lambda w,m: (print('RX:',m[:300]),
        (m.startswith('{\"type\":\"event\",\"event\":\"connect.challenge\"') and w.send(json.dumps({
            'type':'req','id':uuid.uuid4().hex[:16],'method':'connect',
            'params':{'minProtocol':4,'maxProtocol':4,
                'client':{'id':'cli','version':'0.6.0','platform':'linux','mode':'backend'},
                'role':'operator','scopes':['operator.read','operator.write','operator.admin'],
                'auth':{'token':'$TOKEN','password':'$PASS'},
                'locale':'pt-BR','userAgent':'openclaw-cli/0.6.0'}})))))
ws.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})
"
# Esperado: hello-ok.auth.scopes com operator.read+write+admin
```

## Cross-references

- `lesson-176-sre-incident-2026-07-14-502-recovery.md` — SSH VPS indisponível (mesma janela).
- `lesson-173-antigravity-opencode-integration-2026-07-14.md` — `opencode-go` plugin reference.
- `lesson-165-r3-routing-fixes-2026-07-13.md` — modelo `opencode_free_1/nemotron-3-ultra-free` Lesson 165 R3 routing.
- `lesson-172-p0-outage-r8-actions.md` — padrão hold-gustavo para ações prod.
- `.harness/memory/cartorio-context.md` — topologia VPS (OpenClaw :18789 / Traefik / Tailscale).
- `.brain/api-specs/catalog.py` — catalog atualizado (67 endpoints).
- `docs/E07_OPENCLAW_CONTEXT_FIX.md` — fix anterior de contexto.
- `backend/app/integrations/openclaw.py` — integração backend (cliente HTTP).

## Status

- [x] T021 — SSH tentativa (bloqueada, evidência)
- [x] T022 — openclaw.json no container (bloqueada, depende SSH)
- [x] T023 — Gaps E8 identificados via WS handshake
- [x] T024 — cartorio-bot config (bloqueada por auth scopes)
- [x] T025/T026 — 3 calls reais (bloqueada por auth 401)
- [x] T027 — OPENCLAW_GATEWAY_PASSWORD validado (existe em .secrets)
- [x] T028 — catalog.py atualizado (9 endpoints openclaw)
- [x] T029 — esta lesson salva
- [ ] T030 — **commit feat(openclaw) PARADO**: Gustavo precisa GO + ajuste de scopes antes
- [ ] **HOLD-GUSTAVO**: SSH VPS + operator token + criação de cartorio-bot agent + 3 calls reais

Modified by Gustavo Almeida