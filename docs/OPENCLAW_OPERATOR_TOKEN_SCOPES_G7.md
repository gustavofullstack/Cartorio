# OpenClaw Operator Token Scopes — G7.14.T4

**Data:** 2026-07-17 BRT (Wave 28)  
**Task:** G7.14.T4 — Operator token scopes non-empty  
**Status:** **[x] Wave28 runbook (live SUI)** — procedimento documentado; **token real = HOLD-GUSTAVO**  
**Owner:** cartorio-sre + cartorio-dev · **Secrets:** nunca commitar token/password

---

## Por que importa

OpenClaw WS protocol v4 devolve no handshake:

```json
{
  "type": "hello-ok",
  "auth": {
    "role": "operator",
    "scopes": []
  }
}
```

Se `auth.scopes` e **`[]` (vazio)**:

- Health / presence podem funcionar
- **`agents.list` / `agents.create` / `models.list` / `skills.*` falham** com  
  `INVALID_REQUEST: missing scope: operator.read` (ou write/admin)
- Bloqueia provision do `cartorio-bot` (G7.14.T1 / G7.06.T3)

**Lesson 177** (2026-07-14): token em uso era **health-only** → `scopes=[]` mesmo pedindo `operator.read|write|admin` no connect.

Config canonic do bot:

```json
"auth": {
  "required_scopes": ["operator.read", "operator.write"],
  "notes": "Token health-only (scopes=[]) bloqueia agents.create — Lesson 177"
}
```

Fonte: `infra/openclaw/cartorio-bot.openclaw.json`.

---

## Scopes minimos (hello-ok)

| Scope | Uso |
|-------|-----|
| `operator.read` | `agents.list`, `models.list`, `skills.status`, `status`, `health` |
| `operator.write` | `agents.create/update`, `sessions.send`, mutacoes de skills |
| `operator.admin` (opcional) | pairing, config.apply, secrets, device.token.rotate |

**DoD G7.14.T4 (runtime):**

1. `hello-ok.auth.scopes` **nao-vazio**
2. Contem ao menos `operator.read` **e** `operator.write`
3. (Opcional prod) `operator.admin` so em token de operador humano, nao em token de LobeChat se principle of least privilege

---

## Como verificar scopes non-empty (drill)

### A) Preferido — WS hello-ok (sem logar o token)

Pre-req: token + password **locais** (env / vault / EasyPanel), **nunca** no git.

```bash
# Carregar de vault local (exemplo — NAO commitar valores):
# export OPENCLAW_GATEWAY_TOKEN='…'
# export OPENCLAW_GATEWAY_PASSWORD='…'

python3 <<'PY'
import json, os, ssl, sys, uuid

try:
    import websocket  # websocket-client
except ImportError:
    print("pip/uv: install websocket-client", file=sys.stderr)
    sys.exit(2)

token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
password = os.environ.get("OPENCLAW_GATEWAY_PASSWORD", "")
if not token:
    print("HOLD: set OPENCLAW_GATEWAY_TOKEN (and password if mode=backend)")
    sys.exit(3)

url = os.environ.get("OPENCLAW_WS_URL", "wss://agent.2notasudi.com.br/v1/chat")
result = {"scopes": None, "role": None, "ok": False}

def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "event" and data.get("event") == "connect.challenge":
        ws.send(json.dumps({
            "type": "req",
            "id": uuid.uuid4().hex[:16],
            "method": "connect",
            "params": {
                "minProtocol": 4,
                "maxProtocol": 4,
                "client": {
                    "id": "cli",
                    "version": "0.6.0",
                    "platform": "linux",
                    "mode": "backend",
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write", "operator.admin"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {"token": token, "password": password},
                "locale": "pt-BR",
                "userAgent": "cartorio-sre-scope-drill/g7.14.t4",
            },
        }))
        return
    if data.get("type") == "res" and data.get("ok"):
        payload = data.get("payload") or {}
        if payload.get("type") == "hello-ok":
            auth = payload.get("auth") or {}
            result["role"] = auth.get("role")
            result["scopes"] = auth.get("scopes")
            result["ok"] = True
            ws.close()
            return
    if data.get("type") == "res" and not data.get("ok"):
        print("connect failed:", json.dumps(data.get("error") or data)[:400])
        ws.close()

ws = websocket.WebSocketApp(url, on_message=on_message)
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_timeout=10)

scopes = result["scopes"]
print("role=", result["role"])
print("scopes=", scopes)
if not result["ok"]:
    sys.exit(1)
if not scopes:
    print("FAIL: scopes empty (health-only token) — Lesson 177")
    sys.exit(1)
need = {"operator.read", "operator.write"}
have = set(scopes)
missing = need - have
if missing:
    print("FAIL: missing scopes:", sorted(missing))
    sys.exit(1)
print("PASS: operator scopes non-empty and include read+write")
sys.exit(0)
PY
```

**Pass criteria:**

- exit 0
- print `scopes=` com lista nao-vazia contendo `operator.read` e `operator.write`

**Fail criteria (esperado ate SUI Gustavo):**

- exit 1 com `FAIL: scopes empty`
- ou exit 3 se env nao setado (HOLD local)

### B) Device pairing list (SSH VPS)

```bash
# HOLD-GUSTAVO — requer SSH/Tailscale (Lesson 176/11)
ssh cartorio 'docker exec $(docker ps -q --filter "name=cartorio_openclaw-gateway" | head -1) \
  openclaw devices list --json' | python3 -c '
import json,sys
d=json.load(sys.stdin)
for p in d.get("paired", []):
    print(p.get("deviceId","?")[:24], "scopes=", p.get("scopes", []))
'
```

Cada device pareado deve listar scopes nao-vazios se for operator UI.

### C) Health-only (nao prova scopes)

```bash
curl -sS --max-time 10 https://agent.2notasudi.com.br/health | head -c 200
# 200 JSON ok = gateway up; NAO prova operator scopes
```

---

## Como gerar token com scopes (HOLD-GUSTAVO)

Nao ha token de operator com write scopes no repo (de proposito). Gustavo:

### Opcao 1 — CLI no container (preferida se SSH OK)

```bash
ssh cartorio
CID=$(docker ps -q --filter "name=cartorio_openclaw-gateway" | head -1)

# Variante documentada em infra/lobechat/README.md (ajustar flags a versao live):
docker exec -it "$CID" openclaw operator create \
  --name cartorio-sre \
  --scopes operator.read,operator.write

# OU se a CLI usar outro formato (validar --help na versao do container):
# docker exec -it "$CID" openclaw operator create --name lobechat --scopes chat:write,models:read
```

Salvar o bearer **so** em:

- password manager (1Password / Bitwarden)
- EasyPanel env do LobeChat / OpenClaw (`OPENCLAW_GATEWAY_TOKEN`)
- `.secrets/openclaw.env` local **gitignored**

**Nunca** em git, PR, lesson, ou Postman commitado (placeholders apenas).

### Opcao 2 — Control UI

1. Abrir `https://agent.2notasudi.com.br` (ou Tailscale `https://vps-cartorio.tail2fe279.ts.net/?token=…`)
2. Pair device se pedido (`openclaw devices approve <requestId>`)
3. Config → Operators / tokens → create com **read+write**
4. Re-rodar drill WS (secao A)

### Opcao 3 — openclaw.json no volume

Editar `/home/node/.openclaw/openclaw.json` (path de deploy do `cartorio-bot.openclaw.json`) para declarar gateway auth scopes; restart service. Detalhe em:

- `docs/openclaw/E6-cartorio-bot-spec.md`
- `infra/openclaw/cartorio-bot.openclaw.json` → `deploy.sui`
- `infra/traefik/TAILSCALE_OPENCLAW.md` (pairing + token query)

---

## Pos-token: validar cartorio-bot

```bash
# 1) scopes non-empty (drill A) → PASS
# 2) agents.list deve incluir cartorio-bot apos mount do JSON
# 3) hello-ok snapshot defaultAgentId / agents (conforme versao)
```

Cross-check LobeChat: `docs/LOBCHAT_OPENCLAW_IMPORT_G7.md` —  
`OPENAI_API_KEY` = operator token com scopes, **nao** `sk-xxxx`.

---

## Seguranca / LGPD

- Token operator e **DATASENSITIVE** (acesso a tools que podem tocar PII via agent).
- Rotacao: `openssl rand -hex 32` + `docker service update --env-add OPENCLAW_GATEWAY_TOKEN=…` (invalida sessoes).
- Nao colar token em logs Sentry sem scrub; nao ecoar em issues GitHub.
- Preferir token LobeChat com **read+write** sem **admin** se o painel so precisa chat/agents.

---

## Checklist DoD G7.14.T4

| Item | Wave28 agent | Live SUI Gustavo |
|------|--------------|------------------|
| Runbook scopes non-empty | **[x]** este doc | — |
| Script/drill hello-ok | **[x]** secao A | rodar com env real |
| Token real com read+write | HOLD | **[ ]** Gustavo |
| cartorio-bot em agents.list | HOLD (depende token + mount) | **[ ]** |
| LobeChat usa token com scope | HOLD | **[ ]** |

Marcacao SUPER_PLANO: **[x] Wave28 runbook (live SUI)** — alinhado a tasks SUI-heavy (docs+drill; runtime token HOLD).

---

## Cross-refs

- `.harness/memory/lesson-177-openclaw-e8-finalize-2026-07-14.md`
- `infra/openclaw/cartorio-bot.openclaw.json`
- `infra/lobechat/README.md` (operator create)
- `infra/traefik/TAILSCALE_OPENCLAW.md` (pairing)
- `docs/LOBCHAT_OPENCLAW_IMPORT_G7.md`
- `docs/openclaw/E6-cartorio-bot-spec.md`
- `docs/G7_SUI_WAVE14_CHECKLIST.md` item 7

**Modified by Gustavo Almeida — G7 Wave 28 cartorio-sre G7.14.T4**
