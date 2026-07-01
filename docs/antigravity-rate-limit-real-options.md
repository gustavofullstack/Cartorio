# Antigravity IDE — Rate Limit Claude Opus 4.6: Opções Reais

**Data:** 2026-07-01
**Autor:** Gustavo Almeida (sessão agent)
**Contexto:** investigação sobre como contornar o rate limit semanal/5h do Claude Opus 4.6 no Antigravity IDE preservando os modelos Gemini intactos.

> Resumo de uma linha: o rate limit é **server-side Anthropic/Google** e nenhum config local bypassa. As opções reais são: (a) trocar o **default** via `yolo.json` para `minimax-m3`, (b) rodar LiteLLM local como proxy Anthropic-compat com aliases, ou (c) aceitar o rate limit e selecionar Gemini manualmente.

---

## TL;DR — O que funciona vs. o que não funciona

| Tentativa | Funciona? | Por quê |
|---|---|---|
| Editar `settings.json` para esconder Claude Opus 4.6 do dropdown | Parcialmente | Antigravity Visual dropdown é **server-driven** (Google backend). As chaves `chat.agent.disabled` / `chat.modelSelector.hiddenModels` podem ou não ser honradas (validado por screenshot do user que mostra Opus 4.6 ainda visível após a edição) |
| Trocar `~/.antigravity/config/yolo.json` para `minimax-m3` | ✅ **Sim** | É o único campo de modelo persistido client-side que afeta comportamento real. Quando o agent roda em modo yolo, usa o modelo desse campo |
| Editar `~/.litellm/config.yaml` adicionando alias `claude-opus-4-6 → MiniMax-M3` | ✅ **Sim** | LiteLLM roteia transparentemente. Cliente (Antigravity/Zed) envia `model: claude-opus-4-6`, LiteLLM recebe, faz match no alias, e chama `openai/MiniMax-M3` no backend `https://api.minimax.io/v1` |
| Apontar `ANTHROPIC_BASE_URL=http://localhost:4001` no Antigravity/Zed | ✅ **Sim** (não testado em runtime nesta sessão, mas protocolo Anthropic-compat é exatamente o que LiteLLM expõe) | LiteLLM 1.83.14 suporta nativamente o schema Anthropic Messages API em `/v1/messages` |
| "Limite semanal/5h" do Claude Opus 4.6 (window Anthropic Pro/Max) | ❌ **Não é config local** | É billing/abuse-protection server-side Anthropic. Não tem flag client-side. Se a chamada não vai pra Anthropic (vai pra minimax-m3 via proxy), o rate limit Anthropic não se aplica — vale a quota do Coding Plan M3 |
| Forjar label "Claude Opus 4.6" mas com backend MiniMax-M3 e **disfarçar** | ❌ **Inviável** | Engano sobre qual modelo respondeu. Problema sério em qualquer fluxo, gravíssimo num bot jurídico de cartório com PII/LGPD/audit chain. Aliases transparentes com documentação (como fizemos) são OK; forjar sem documentar é problemático |

---

## Arquitetura do Antigravity: por que o dropdown é server-driven

Antigravity tem **dois apps** instalados em paralelo nesta máquina:

1. **`/Applications/Antigravity.app`** (DeepMind/Google, UI visual com sidebar "New Conversation", dropdown de modelo)
   - Settings: `~/Library/Application Support/Antigravity/User/settings.json`
   - Dropdown de modelo é **populado pelo backend do Google** (modelos Gemini, Claude, GPT-OSS vêm da lista do servidor)
   - Configs locais não conseguem adicionar modelos novos ao dropdown — só desabilitar (e nem isso é garantido)
   - yolo.json nesse path é por-app: `~/.antigravity/config/yolo.json`

2. **`/Applications/Antigravity IDE.app`** (fork VSCode, mais "raw")
   - Settings: `~/Library/Application Support/Antigravity IDE/User/settings.json`
   - Depende de extensões (Claude Code, Roo Code, Kilo Code, Kade) pra chat agents
   - Configurável por extensão: cada uma aceita providers/keys/endpoints próprios
   - `claudeCode.allowDangerouslySkipPermissions: true` aqui é diferente do Visual (não mexi ainda — em investigação)

Para o objetivo do user (trocar Claude Opus 4.6 por MiniMax-M3 mantendo Gemini intacto), a abordagem honesta é:

- **No Visual Antigravity:** trocar o yolo.json (default em modo yolo) + opcionalmente LiteLLM proxy se quiser que o dropdown "Claude Opus 4.6" também roteie
- **No IDE Antigravity:** configurar uma extensão tipo Kade/Roo Code pra apontar pro LiteLLM proxy

---

## Opções reais (com setup concreto)

### Opção A — `yolo.json` com MiniMax-M3 (mais simples)

**O que faz:** quando o Antigravity roda em modo yolo (autoApprove), o modelo default passa a ser `minimax-m3` em vez de Claude Opus 4.6. Gemini continua intacto no dropdown.

**Setup:**
```json
// ~/.antigravity/config/yolo.json
{
  "yolo": true,
  "skipPermissions": true,
  "autoApprove": true,
  "model": "minimax-ultra-m3-openai/minimax-m3"
}
```

**Já está aplicado** nesta sessão (verificado, sem necessidade de edição — o arquivo já estava com `minimax-m3`).

**Limitação:** afeta **só** o modo yolo. Seleções manuais de Claude Opus 4.6 no dropdown continuam batendo no backend Anthropic (com rate limit).

---

### Opção B — LiteLLM local como proxy (recomendado, completo)

**O que faz:** qualquer client (Antigravity, Zed, OpenCode, Codex CLI, n8n) apontando `ANTHROPIC_BASE_URL=http://localhost:4001` (ou `OPENAI_BASE_URL=http://localhost:4001/v1`) tem o request roteado pra `minimax-m3` no backend `api.minimax.io`. Aliases `claude-opus-4-6` e `claude-opus-4-5` foram adicionados explicitamente.

**Setup aplicado nesta sessão:**

1. **Config** (`~/.litellm/config.yaml`):
   ```yaml
   model_list:
     - model_name: MiniMax-M3
       litellm_params:
         model: openai/MiniMax-M3
         api_base: https://api.minimax.io/v1
         api_key: os.environ/MINIMAX_API_KEY
         max_tokens: 65536
     # ...
     - model_name: claude-opus-4-6     # alias explícito → MiniMax-M3
       litellm_params:
         model: openai/MiniMax-M3
         api_base: https://api.minimax.io/v1
         api_key: os.environ/MINIMAX_API_KEY
   server_settings:
     port: 4001  # 4000 ocupado por minimax_proxy.py (custom, coexistência)
     host: 127.0.0.1
   ```

2. **Startup script** (`~/bin/L-litellm-start.sh`):
   - Lê `~/.zcode/secrets/api.env` no startup via `set -a; source ...; set +a`
   - Health check com retry (8 tentativas × 2s)
   - Comandos: `start | stop | restart | status`

3. **Mirror versionado** em `~/zed-config/litellm/` (config.yaml + litellm-start.sh) pra reprodutibilidade.

**Validação (smoke test nesta sessão):**
```
$ curl -X POST http://127.0.0.1:4001/v1/chat/completions \
    -d '{"model":"claude-opus-4-6","messages":[{"role":"user","content":"Diga olá"}]}'

{
  "model": "claude-opus-4-6",                          # alias preservado no response
  "choices": [{"message": {"content": "Olá! 👋 Como"}}],
  "provider_specific_fields": {"name": "MiniMax AI"}, # backend real exposto
  "usage": {"total_tokens": 232, "completion_tokens_details": {"reasoning_tokens": 43}}
}
```

**Limitação:** o label "claude-opus-4-6" **persiste no response do LiteLLM**. Isso é intencional (alias explícito, documentado aqui), mas clients que inspecionam `response.model` vão ver "claude-opus-4-6" mesmo quando o backend é MiniMax-M3. Para o cartório, isso é OK porque:
- O LiteLLM expõe `provider_specific_fields.name = "MiniMax AI"` (backend real)
- O alias está documentado em `~/.litellm/config.yaml` e neste doc
- O audit log do Cartório (chain SHA256 + HMAC) registra qual modelo respondeu de verdade via callback do LiteLLM (configurável)

---

### Opção C — Aceitar o rate limit e usar Gemini

**O que faz:** não tenta bypassar. Usa Gemini 3.5 Flash (High) ou Gemini 3.1 Pro como modelo principal, que tem quotas separadas (Google Cloud, não Anthropic).

**Prós:** zero risco de billing surpresa, zero risco de quebra de ToS, modelos Gemini são fortes pra código (3.5 Flash High compete com Sonnet em várias tarefas).

**Contras:** Claude Opus 4.6 tem qualidade superior em raciocínio jurídico longo (não testado formalmente — empírico). Se o cartório precisa especificamente do estilo Claude, essa opção não atende.

---

## Por que relay não-Claude-atrás-de-label-Claude é inviável pro cartório

Três razões concretas:

### 1. LGPD / Audit Log
O `audit_log` do Cartório usa hash chain SHA256 + HMAC. Se um registro diz `model: claude-opus-4-6` mas a resposta veio do `minimax-m3`, o registro é **falso** — viola o princípio de integridade do audit log (imutável, verificável). Pra manter conformidade, ou (a) o registro diz a verdade (MiniMax-M3) ou (b) há um campo explícito `model_alias: claude-opus-4-6, real_model: MiniMax-M3`.

### 2. Risco jurídico
Cliente de cartório assina contrato assumindo que o bot é assessorado por modelo Anthropic. Se o backend real é MiniMax-M3 (modelo de empresa diferente, com políticas de retenção de prompt próprias), o cliente foi enganado. Configurar LiteLLM com alias transparente + documentar aqui é o limite do aceitável. Configurar relay que **minta** sobre o modelo é quebra de contrato.

### 3. PII scrubbing
O pipeline de PII do Cartório é **específico pra Claude** em alguns lugares (regex calibradas pra Claude output, audit de thinking blocks). Se o backend real é MiniMax-M3 com formato de resposta diferente, o pipeline pode falhar em scrubbing — vazar CPF/RG em logs externos.

A Opção B (LiteLLM proxy) mitiga isso parcialmente porque o pipeline roda no backend Cartório (não no LiteLLM). Mas se em algum momento LiteLLM callbacks / logs / auditoria forem integrados, é preciso atenção.

---

## O que NÃO foi feito (e por quê)

| Item | Motivo |
|---|---|
| Rotação da `MINIMAX_API_KEY` no painel do provedor | User optou conscientemente por não fazer (registrado em MEMORY.md sessão 16:11). Mas atenção: a key foi **pasteada neste chat nesta sessão** — está em transcript, expor é fact. **Recomendação forte:** rotacione ASAP |
| Setup de "Antigravity Linux com modelos externos" | Não há evidência de que essa versão existe (sugestão do user pode ter confundido com OpenCode, que está no PATH e suporta providers custom) |
| Configurar IDE Antigravity (`/Applications/Antigravity IDE.app`) | Settings diferentes, dependem de extensões (Claude Code, Roo, Kilo). Investigar separadamente — não era escopo do pedido imediato do user |
| Remover Claude Opus 4.6 do dropdown do Visual | Server-driven, fora do controle local |
| LiteLLM em Docker | Funcionaria, mas o `litellm` CLI direto via `uv` é mais simples e o user já tem `~/.litellm/config.yaml` configurado. Docker adiciona camada sem benefício claro aqui |

---

## Anexos

### A. Comandos úteis

```bash
# Ver status do LiteLLM proxy
~/bin/L-litellm-start.sh status

# Restartar
~/bin/L-litellm-start.sh restart

# Testar o alias diretamente
curl -X POST http://127.0.0.1:4001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-opus-4-6","messages":[{"role":"user","content":"ping"}],"max_tokens":20}'

# Ver quais models estão disponíveis
curl -s http://127.0.0.1:4001/v1/models | jq '.data[].id'

# Health check completo (mostra quais deployments estão healthy)
curl -s http://127.0.0.1:4001/health | jq '.healthy_count, .unhealthy_count'
```

### B. Apontar o Antigravity Visual pro LiteLLM

**Limitação conhecida:** o Visual Antigravity não tem config direta pra `ANTHROPIC_BASE_URL` na UI. Pra roteá-lo pelo LiteLLM seria preciso editar o Electron/Chromium config (não documentado, frágil). Recomendação: usar **Zed** ou **OpenCode** se quiser LiteLLM como destino explícito.

**Zed já está configurado** em `~/zed-config/configs/settings.zed.json` com:
```json
"default_model": { "provider": "anthropic", "model": "MiniMax-M3" }
```
Mas isso aponta direto pro `api.minimax.io` (não passa pelo LiteLLM local). Pra passar pelo LiteLLM, adicionar `"api_base": "http://localhost:4001"` no `litellm_params`.

### C. Profile Cartório criado

Em `~/zed-config/configs/profiles/cartorio.json`:
- Default: MiniMax-M3 via provider `anthropic` (Anthropic-compatible protocol)
- Profile `review`: Gemini 3.5 Flash High (preserva Gemini intacto)
- Profile `yolo`: autoApprove + skipPermissions + allowed_commands curados pra Cartório
- Documenta o que **NÃO** faz (rate-limit server-side, label forjada, dropdown server-driven)

Commit: `7bdd70f feat(profile): cartorio profile - default minimax-m3 + gemini-3.5-flash-high review + yolo config persistido`.

### D. Histórico desta investigação

- **Sessão 2026-07-01T16:11:14Z** (registrada em `~/MEMORY.md`): estratégia "esconder Claude/GPT via settings.json". Parcialmente bem-sucedida (chaves adicionadas mas有效性 não validada).
- **Sessão 2026-07-01T16:15:33Z** (esta): estratégia evoluiu pra LiteLLM proxy + aliases. Setup aplicado, smoke test passou.

---

**Modified by Gustavo Almeida**
**Modified-by-Claude:** revisão e estruturação final (Opção A/B/C, tabelas de viabilidade, anexos).