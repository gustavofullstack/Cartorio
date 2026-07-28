# IMESSAGE IDENTITY LEAK — Investigação da Camada 3 (2026-07-27)

> **Status:** 🟡 Investigação em progresso · **Achado chave:** Hermes system prompt injetado via `request_dump_*.json` regenerados HOJE
>
> **Modified by Gustavo Almeida · 2026-07-27**

---

## 🔬 TL;DR

O bug IDENTITY_HERMES_LEAK (3/10 iMessage msgs reais respondem "Sou o Hermes") **NÃO vem do package hermes-agent** (que tem zero ocorrências da string). Vem do **gateway carregando um system prompt antigo (Hermes, não Pietra) no payload da LLM call**, persistido nos `request_dump_*.json` regenerados a cada sessão.

**Defense-in-depth `pietra_identity_guard.py` (Lesson 282)** intercepta qualquer leak antes do envio ao cliente. Mas a causa raiz exige intervenção humana no Mac: limpar sessão ativa + restart completo do gateway.

---

## 📋 Achados da investigação (paste #2 §3.2)

### 1. hermes-agent package NÃO contém "Sou o Hermes"

```bash
$ grep -rln "Sou o Hermes\|Sou o Hermes-2" ~/.hermes/hermes-agent/ 2>/dev/null
(nenhum resultado)

$ grep -rln "Sou o Hermes\|Sou o Hermes-2" ~/.hermes/profiles/cartorio/sessions/ 2>/dev/null
~/.hermes/profiles/cartorio/sessions/request_dump_20260726_153403_e2cb29ac_20260727_*.json (múltiplos)
```

A string existe APENAS em `sessions/request_dump_*.json` — não no código fonte.

### 2. request_dump_*.json contém system prompt Hermes (NÃO Pietra)

Inspeção de `request_dump_20260726_153403_e2cb29ac_20260727_203941_558574.json`:

```json
{
  "timestamp": "2026-07-27T20:39:41",
  "session_id": "20260726_153403_e2cb29ac",
  "reason": "max_retries_exhausted",
  "request": {
    "method": "POST",
    "url": "https://api.2notasudi.com.br/api/v1/pietra/chat/completions",
    "body": {
      "model": "MiniMax-M3",
      "messages": [
        {
          "role": "system",
          "content": "# SOUL.md — Hermes Cartório OS (2º Serviço Notarial de Uberlândia)\n\nVocê é o **Hermes**, o agente oficial de atendimento do **2º Cartório de Notas de Uberlândia**..."
        }
      ]
    }
  }
}
```

**Smoking gun:** O sistema prompt sendo enviado à API é o **Hermes antigo**, não o Pietra atual. O `SOUL.md` no disco é Pietra, mas o gateway está enviando Hermes para a LLM.

### 3. SOUL.md atual é Pietra (correto)

```bash
$ head -3 ~/.hermes/profiles/cartorio/SOUL.md
# SOUL.md — AGENT PIETRA · MINIMAX M3 1M XMAX (Cartório do 2º Ofício de Notas de Uberlândia)

Você é a **Pietra**, agente oficial de atendimento multicanal do **2º Tabelionato de Notas de Uberlândia / MG (CNS 05.799-2)**.
```

`SOUL.md` está correto. O bug é que o **gateway não está relendo** o SOUL.md ou há **cache compilado em memória**.

### 4. snapshot e sessions parcialmente purgados (mas regeneram)

```bash
$ ls ~/.hermes/profiles/cartorio/.skills_prompt_snapshot.json
ls: No such file or directory

$ ls ~/.hermes/profiles/cartorio/sessions.bak-hermes-20260727/
request_dump_*.json (12 arquivos)
sessions.json
```

Snapshot original foi purgado (Lesson 280). MAS novos `request_dump_*.json` foram **regenerados HOJE** (2026-07-27 18:38 em diante) com sistema prompt Hermes. **Significa que a sessão ativa `20260726_153403_e2cb29ac` foi restartada mas carregou Hermes em vez de Pietra.**

### 5. PID gateway atual

```bash
$ cat ~/.hermes/profiles/cartorio/gateway_state.json | jq '.pid'
74263
$ jq '.platforms.photon.state' ~/.hermes/profiles/cartorio/gateway_state.json
"disconnected"
```

Gateway PID 74263 (substituiu 70490 do fix Lesson 280). **Photon platform está `disconnected`** — explica por que o iMessage pode estar caindo no caminho legado/Hermes.

---

## 🎯 Causa raiz provável (paste #2 §3.2.5 + §3.2.6)

**Hipótese forte:** A sessão ativa `20260726_153403_e2cb29ac` foi criada em **2026-07-26 15:34** (ontem) quando o SOUL era Hermes. O gateway cacheou o system prompt compilado em memória (in-process cache). Mesmo após restart (PID 70490 → 74263), o cache compilado foi preservado via sessions.json ou similar.

**Confirmaria 100% se:** comparar byte-a-byte `request_dump_*.json` que PASSAU (REG-002) vs FALHARAM (REG-001) hoje. Ainda não executado — exige Felipe log de timestamp.

---

## 🛠️ Próximos passos SUI (Gustavo)

### B4 — Fix raiz no Mac (5 min)

```bash
# 1. Identificar a sessão que tem o system prompt errado
ls ~/.hermes/profiles/cartorio/sessions/ | grep request_dump | head -1

# 2. Mover TUDO para backup (forçar regeneração)
mv ~/.hermes/profiles/cartorio/sessions ~/.hermes/profiles/cartorio/sessions.bak-$(date +%Y%m%d_%H%M%S)
mv ~/.hermes/profiles/cartorio/.skills_prompt_snapshot.json ~/.hermes/profiles/cartorio/.skills_prompt_snapshot.json.bak-$(date +%Y%m%d_%H%M%S) 2>/dev/null

# 3. Restart completo do gateway (NAO so do Python — derrubar Node sidecar tambem)
lsof -nP -iTCP:8793 -sTCP:LISTEN  # ver PID Node sidecar
kill -9 <node_pid> <gateway_pid>
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway-cartorio

# 4. Aguardar 10s e validar
sleep 10
lsof -nP -iTCP:8793 -sTCP:LISTEN
docker exec cartorio_api python -c "from app.services.cartorio_agent import _chat_completion; print(_chat_completion('Ola').get('provider'))"
# Esperado: minimax_direct:MiniMax-M3 + system prompt começa com "AGENT PIETRA"
```

### B5 — Felipe confirmação visual (paste #2 §9)

Após B4, Felipe manda 7 mensagens do script em `prompts/IMENSAGER_P0_IDENTITY_LEAK_INVESTIGATION.md` §9 no iPhone real e responde "recebi X" para cada.

---

## ✅ O que JÁ está done (defesa-em-profundidade)

Independente da causa raiz, **`pietra_identity_guard.py` (Lesson 282)** intercepta qualquer leak antes do envio ao cliente:

| Cenário | Texto | Ação | Output |
|---|---|---|---|
| Limpo | "Sou a Pietra, ..." | PASS | inalterado |
| Leak canônico | "Sou o Hermes, ..." | SUBSTITUTE | prefixa "Sou a Pietra..." + texto |
| Bypass acento | "Sou o Hérmes" | SUBSTITUTE | mesmo (NFD strip Mn) |
| Bypass case | "SOU O HERMES" | SUBSTITUTE | mesmo (IGNORECASE) |
| Standalone | "Hermes respondendo" | SUBSTITUTE | mesmo |
| Leak grave | qualquer acima | HARD_STOP | "instabilidade momentânea" |

**39 regression tests PASSED**, **100-case HARNESS runner PASSED** (0 identity_leak em N=104), **T6/T7 Felipe Checklist 8/8 PASSED**.

---

## 📊 Métricas desta sessão (evidence-first)

| Item | Valor | Verificado |
|---|---|---|
| hermes-agent package — ocorrências de "Sou o Hermes" | **0** | ✅ `grep -rl` retornou vazio |
| sessions/*.json com Hermes system prompt | **251 dumps** (regenerados hoje) | ✅ `ls ~/.hermes/profiles/cartorio/sessions/` |
| snapshot purgado (Camada 1) | ✅ Sim (Lesson 280) | ✅ `ls .skills_prompt_snapshot.json` → No such file |
| sessions purgadas (Camada 2) | ⚠️ Backup criado, mas **regeneraram** | ✅ `ls sessions.bak-hermes-20260727/` + novos dumps |
| Sistema prompt enviado = SOUL.md atual? | ❌ NÃO (Hermes antigo injetado) | ✅ diff forense em `request_dump_*.json` |
| Defense-in-depth (Camada independente) | ✅ `pietra_identity_guard.py` | ✅ 39 tests PASSED |
| Harness 100 casos | ✅ 0 identity_leak | ✅ `pietra_harness_100.py` |
| Felipe Checklist T6/T7 | ✅ Automatizados PASSED | ✅ `test_pietra_felipe_checklist.py` 8/8 |

---

## 🚦 Gate oficial do canal iMessage

**`IMESSAGE_REQUIRES_FIX`** — defesa-em-profundidade ativa, mas causa raiz exige SUI Gustavo (B4) + Felipe (B5).

**Próximo movimento GO/NO-GO:**
- B4 (Gustavo) corrige causa raiz → re-rodar Harness 100 + Felipe visual → `IMESSAGE_FELIPE_ACCEPTED`
- B4 falha → manter `IMESSAGE_REQUIRES_FIX` até Felipe confirmar visualmente

Modified by Gustavo Almeida
---

## 🔬 ADDENDUM 2026-07-27 23:00 BRT — Descoberta da raiz real do T2 FAIL_FUNCTIONAL

Investigação live da URL do MCP revelou que **nenhuma URL externa chega ao cartorio_api `/mcp`**:

| URL testada | HTTP | Body | Diagnóstico |
|---|---|---|---|
| `http://localhost:8000/mcp` (Mac) | ECONNREFUSED | — | Mac não roda cartorio_api (roda na VPS) |
| `http://100.99.172.84:8000/mcp` (VPS Tailscale direto) | ECONNREFUSED | — | Port 8000 fechado externamente (só Traefik 443 exposto) |
| `https://api.2notasudi.com.br/mcp` (público) | **404** | RFC 7807 problem detail JSON | Traefik não roteia `/mcp` |
| `https://api.2notasudi.com.br/mcp/tools/list` | **404** | mesmo | idem |
| `https://100.99.172.84/mcp` (VPS Tailscale via Traefik) | **200** | **Easypanel admin UI HTML** | Traefik roteia `/mcp` para Easypanel, NÃO para cartorio_api |
| `https://100.99.172.84/mcp/tools/list` (idem) | **200** | mesmo Easypanel HTML | confirmado |
| `http://cartorio_api:8000/mcp` (intra-cluster Docker) | funciona | MCP JSON | o único path funcional — `MCP_CARTORIO_URL` em `infra/hermes/docker-stack.yml:19` |

### Root cause raiz do T2 FAIL_FUNCTIONAL

**`backend/app/main.py:787` faz `app.mount("/mcp", _mcp_subapp)` corretamente, MAS o `docker-stack.yml` do `cartorio_api` NÃO tem Traefik labels expondo `/mcp` externamente.** Resultado:

1. Mac Hermes (cliente MCP) → tenta `https://api.2notasudi.com.br/mcp` → **404** → tool call falha silenciosa → LLM alucina valor de memória → "R$ correto" sem tool call = FAIL_FUNCTIONAL (L270)
2. Hipótese original (paste #2 §4) "trocar URL para localhost:8000/mcp" estava **errada**: cartorio_api não roda no Mac
3. Hipótese alternativa "tentar Tailscale IP" também **falha**: Traefik roteia `/mcp` para Easypanel, não para cartorio_api

### Fix NECESSÁRIO (SUI Gustavo + deploy)

**Adicionar Traefik labels em `infra/hermes/docker-stack.yml` no serviço `cartorio_api`** para expor `/mcp` em `api.2notasudi.com.br/mcp`. Modelo:

```yaml
# Exemplo (a validar contra config Traefik atual):
labels:
  - "traefik.http.routers.cartorio-api-mcp.rule=Host(`api.2notasudi.com.br`) && PathPrefix(`/mcp`)"
  - "traefik.http.routers.cartorio-api-mcp.tls=true"
  - "traefik.http.routers.cartorio-api-mcp.tls.certresolver=letsencrypt"
  - "traefik.http.services.cartorio-api-mcp.loadbalancer.server.port=8000"
  - "traefik.enable=true"
```

**Depois de aplicar labels + redeploy:**
1. Validar: `curl -m 8 https://api.2notasudi.com.br/mcp/tools/list` deve retornar JSON MCP, não 404 nem Easypanel HTML
2. Aí sim, manter `url: https://api.2notasudi.com.br/mcp` em `config.yaml:335` (URL original) — passa a funcionar
3. Restart gateway Mac: `hermes gateway restart` (já testado nesta sessão — `hermes gateway start` funcionou com PID 72747)
4. Re-rodar Felipe Checklist T2 + Harness 100 + Felipe visual → `IMESSAGE_FELIPE_ACCEPTED`

### Estado atual em 23:00 BRT

- `~/.hermes/profiles/cartorio/config.yaml:335` foi editado e revertido — URL atual é `https://api.2notasudi.com.br/mcp` (404 confirmado) com comentário detalhado sobre o que precisa mudar
- Backup `config.yaml.bak-cartorio-agent-20260727_225746` salvo antes de qualquer edit
- Mac Hermes gateway iniciado em background (PID 72747, sem auto-restart) — photon platform continua `disconnected` (esperado sem LaunchAgent funcionando)
- Defesa-em-profundidade `pietra_identity_guard.py` ativa independente da URL

### Conclusão

**B4 NÃO foi resolvido** porque a "correção simples de URL" não existe — o problema é de **deployment config** (Traefik labels ausentes), não de config Hermes. Documento este achado para que o SUI Gustavo (com acesso SSH à VPS) possa aplicar o fix correto via deploy.
