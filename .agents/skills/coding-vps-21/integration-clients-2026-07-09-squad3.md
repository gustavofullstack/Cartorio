# coding-vps Integration Clients (SQUAD 3 - 2026-07-09)

Clients Python/JS + setup wizard para TRAE/Antigravity/SOLO consumirem o MCP orchestrator.

**Status**: PRONTO | **Versao**: 1.0.0 | **Data**: 2026-07-09

## Arquivos

- `scripts/coding_vps_client.py` — Python client (stdlib only, urllib)
- `scripts/coding_vps_client.js` — Node.js client (fetch nativo)
- `scripts/setup_coding_vps_integration.sh` — Wizard 1-click (TRAE/SOLO/Antigravity)

## Python Client

### Instalacao
Zero deps. Python 3.11+ com stdlib apenas (urllib + subprocess + json).

### CLI
```bash
# Listar tools
python3 scripts/coding_vps_client.py list

# Chamar tool
python3 scripts/coding_vps_client.py call chat_minimax prompt="hello" max_tokens=80
python3 scripts/coding_vps_client.py call list_services
```

### Library
```python
from coding_vps_client import CodingVPSClient, CodingVPSMCPClient

# HTTP mode
client = CodingVPSClient("http://100.99.172.84:8100")
tools = client.list_tools()
result = client.call("chat_minimax", prompt="hello", max_tokens=80)

# MCP stdio mode
mcp = CodingVPSMCPClient()
mcp.start()
result = mcp.call("chat_minimax", prompt="hello")
mcp.stop()
```

### 3 Exemplos Praticos

**Exemplo 1: Chat com MiniMax-M3**
```python
from coding_vps_client import CodingVPSClient
client = CodingVPSClient()
r = client.call("chat_minimax", prompt="O que e LGPD?", max_tokens=200)
print(r.get("text", r))
```

**Exemplo 2: Listar 89 servicos do VPS**
```python
client = CodingVPSClient()
services = client.call("list_services")
for s in services.get("services", []):
    print(f"{s['name']:30} {s['status']:10} {s.get('port', '-')}")
```

**Exemplo 3: Code review com squad**
```python
client = CodingVPSClient()
code = open("backend/app/services/audit.py").read()[:2000]
r = client.call("code_review", code=code, language="python", focus="security")
print(r.get("review", r))
```

## JavaScript Client

### Instalacao
Zero deps. Node.js 18+ (fetch nativo).

### CLI
```bash
# Listar tools
node scripts/coding_vps_client.js list

# Chamar tool
node scripts/coding_vps_client.js call chat_minimax prompt="hello" max_tokens=80
CODING_VPS_URL=http://custom:8100 node scripts/coding_vps_client.js call list_services
```

### Library
```javascript
// import { listTools, callTool } from "./coding_vps_client.js";

const BASE_URL = process.env.CODING_VPS_URL || "http://100.99.172.84:8100";

async function listTools() {
  const r = await fetch(`${BASE_URL}/tools`);
  return await r.json();
}

async function callTool(toolName, kwargs = {}) {
  const r = await fetch(`${BASE_URL}/call/${toolName}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(kwargs),
  });
  return await r.json();
}
```

### 3 Exemplos Praticos

**Exemplo 1: Chat com MiniMax-M3**
```javascript
async function main() {
  const r = await callTool("chat_minimax", { prompt: "O que e LGPD?", max_tokens: 200 });
  console.log(r.text || r);
}
main();
```

**Exemplo 2: Health check de 89 servicos**
```javascript
const services = await callTool("list_services");
const unhealthy = services.services.filter(s => s.status !== "running");
console.log(`Unhealthy: ${unhealthy.length}/${services.services.length}`);
unhealthy.forEach(s => console.log(`  ${s.name}: ${s.status}`));
```

**Exemplo 3: Webhook handler Express**
```javascript
import express from "express";
import { callTool } from "./coding_vps_client.js";

const app = express();
app.use(express.json());

app.post("/webhook/chatwoot", async (req, res) => {
  const msg = req.body.message;
  const reply = await callTool("chat_minimax", { prompt: msg, max_tokens: 200 });
  res.json({ reply: reply.text });
});
```

## Setup Wizard

### O que faz
1. Valida HTTP server (curl em /tools)
2. Cria `~/.trae/mcp-servers/coding-vps.json` (TRAE IDE)
3. Cria `~/.trae-solo/mcp-servers/coding-vps.json` (TRAE SOLO.APP)
4. Cria `~/.antigravity/mcp-servers/coding-vps.json` (Antigravity.APP)
5. Testa com chamada real (`chat_minimax`)

### Como rodar
```bash
chmod +x scripts/setup_coding_vps_integration.sh
./scripts/setup_coding_vps_integration.sh
```

### Output esperado
```
=== coding-vps MCP integration setup ===
1. Validating HTTP server...
OK HTTP server UP at http://100.99.172.84:8100/
   85 tools available
2. TRAE config...
OK ~/.trae/mcp-servers/coding-vps.json
3. TRAE SOLO config...
OK ~/.trae-solo/mcp-servers/coding-vps.json
4. Antigravity config...
OK ~/.antigravity/mcp-servers/coding-vps.json
5. Testing...
{
  "text": "SETUP-OK"
}
=== Setup complete ===
```

## Comparacao Python vs JavaScript

| Feature | Python | JavaScript |
|---------|--------|-----------|
| Deps | zero (stdlib) | zero (fetch nativo) |
| Min runtime | 3.11+ | Node 18+ |
| HTTP mode | sim | sim |
| MCP stdio mode | sim (subprocess) | nao (apenas HTTP) |
| Type hints | sim | parcial |
| Async | opcional (requests) | nativo |
| Use case | scripts / CI / backend | webhooks / front / Node |

## Troubleshooting

**HTTP 401/403**: API key do LiteLLM invalida. Ver `LITELLM_API_KEY` no env.

**Connection refused**: coding-vps-orchestrator offline. Rodar `docker ps | grep coding-vps`.

**MCP stdio trava**: garantir que `coding_vps_mcp_orchestrator.py` existe no path esperado.

## Related

- Skill: `coding-vps-orchestrator` — setup do MCP server
- Skill: `coding-vps-tools-100` — catalogo das 100+ tools
- Skill: `coding-vps-monitor` — health checks
- VPS: `100.99.172.84` (Tailscale)

Modified by Gustavo Almeida
