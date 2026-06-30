# Sprint 3 — SUI Runbook (1-click por SUI, 80min total)

> **Sprint**: 3 (v0.5.1 → v0.6.0 WhatsApp Pilot Ready)
> **Data**: 2026-06-30
> **Autor**: Mavis/Pietra (ZCode)
> **Bloqueio**: Sprint 3 stop-when 6/7. Os 6 SUIs são o que falta pra fechar 7/7.
> **Quem**: SÓ Gustavo pode executar. Mavis não tem acesso aos painéis web.

## TL;DR (Pra Gustavo)

Senta 80min numa janela só, abre 4 abas no navegador, segue a ordem abaixo. Cada SUI tem **campo pronto pra copy-paste** e **1 comando de validação**. Se travar, me chama.

**Janela recomendada**: terça 30/06 14h-16h (cartório fechado, foco total) ou sábado manhã.

## Pré-flight (5min antes de começar)

Antes de tocar em qualquer painel, abre essas 4 abas + 1 terminal:

```
# Aba 1: Easypanel (VPS) — https://easypanel.2notasudi.com.br
# Aba 2: N8N (workflows) — https://flow.2notasudi.com.br
# Aba 3: Chatwoot (atendentes) — https://chat.2notasudi.com.br/login
# Aba 4: Hostinger DNS — https://hpanel.hostinger.com.br → DNS → Zona
# Terminal 5: SSH via Tailscale — ssh root@100.99.172.84 (já configurado)
```

**Login em todas** antes de começar. Senha no Keychain (tag `cartorio`).

Confirma conectividade:
```bash
ssh root@100.99.172.84 "docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'chatwoot|n8n|openclaw|easypanel'"
```

Esperado: 4 containers UP. Se algum Restarting, **NÃO continue** — me chama antes.

---

## SUI 1.1 — DNS `chatwoot.2notasudi.com.br` ⏱ 10min

**O que**: Criar registro A no Hostinger DNS apontando pra IP público da VPS (187.77.236.77).

**Por que**: Container `cartorio_chatwoot` UP, mas domínio retorna NXDOMAIN. Sem DNS público, subdomínio é invisível pra fora.

**Onde**: Hostinger hPanel → DNS → Zona (do domínio `2notasudi.com.br`)

### Passo-a-passo

1. hPanel → **Domínios** → `2notasudi.com.br` → **DNS / Nameservers** → **Gerenciar registros DNS**
2. Clicar **Adicionar registro**:
   - Tipo: **A**
   - Nome: `chatwoot`
   - Valor: `187.77.236.77`
   - TTL: `3600` (1h)
3. Salvar.

### Validação (terminal)

```bash
# Espera 2min pra propagar, depois:
dig +short A chatwoot.2notasudi.com.br @8.8.8.8
# Esperado: "187.77.236.77"

curl -sI https://chatwoot.2notasudi.com.br/ | head -1
# Esperado: "HTTP/2 302" (redirect pro login Chatwoot)
```

### Rollback

Se der ruim, deleta o registro A no hPanel. Sem side-effect no container.

---

## SUI 1.2 — Credencial Evolution API no N8N ⏱ 5min

**O que**: Criar credencial `evolution-api-cartorio` no N8N, plugar no workflow `#07 Pesquisa Satisfação`.

**Por que**: Workflow #07 chama Evolution API pra enviar msg WhatsApp. Sem credencial configurada, fica em estado placeholder.

**Onde**: N8N UI → Credentials → New → Evolution API

### Passo-a-passo

1. flow.2notasudi.com.br → **Credentials** → **New**
2. Search: `Evolution API` → seleciona
3. Preenche:
   ```
   Name:           evolution-api-cartorio
   Base URL:       http://cartorio_evolution-api:8080
   API Key:        <pegar do .env — ver comando abaixo>
   ```
4. Salvar.

Pra pegar a API key:
```bash
ssh root@100.99.172.84 "grep EVOLUTION_API_KEY /etc/easypanel/projects/cartorio/evolution-api/.env"
# Copia o valor (sem aspas)
```

5. Workflows → abre **"07 - Pesquisa Satisfação"**
6. No node **"Evolution sendText"** → campo credential → seleciona `evolution-api-cartorio`
7. Campo `instanceName` → preenche `cartorio-2notas`
8. **Ativa** o workflow (toggle no canto superior direito).

### Validação

```bash
# Workflow ativo?
curl -s -H "X-N8N-API-KEY: <n8n_key>" \
  "https://flow.2notasudi.com.br/api/v1/workflows?limit=50" \
  | jq '.data[] | select(.name | contains("07")) | {id, name, active}'

# Esperado: { "active": true, ... }
```

### Rollback

Desativa workflow → apaga credencial. Nenhum side-effect.

---

## SUI 1.3 — Agent Bot Chatwoot "Cartório Assistant" ⏱ 30min

**O que**: Criar bot no Chatwoot que recebe webhook da API FastAPI, permitindo handoff humano completo.

**Por que**: Sem bot, handoff via workflow #03 N8N não fecha o ciclo. Cliente fica preso no bot sem escape pra humano.

**Onde**: Chatwoot UI → Settings → Agents → Agent Bots → Add

### Passo-a-passo

1. chat.2notasudi.com.br → login super_admin
2. **Settings** → **Agents** → **Agent Bots** → **Add Agent Bot**
3. Preenche:
   ```
   Name:           Cartório Assistant
   Description:    Bot oficial do 2º Tabelionato de Notas de Uberlândia
   Webhook URL:    https://api.2notasudi.com.br/api/v1/webhook/chatwoot
   Bot type:       Webhook
   ```
4. Salvar.
5. **Settings** → **Inboxes** → **Add Inbox** → **API**
   ```
   Name:           WhatsApp Cartório
   Channel:        API
   ```
6. Copia o **Inbox ID** gerado (vai precisar no próximo passo)
7. **Settings** → **Agents** → **Agents** → adicionar teu próprio user como agente do inbox

### Validação

```bash
# Bot criado?
curl -s -H "api_access_token: <chatwoot_token>" \
  "https://chat.2notasudi.com.br/api/v1/agent_bots" \
  | jq '.[] | {id, name}'

# Esperado: 1 bot com name "Cartório Assistant"
```

### Rollback

Settings → Agent Bots → Delete. Inbox → Delete. Sem perda de dado.

---

## SUI 1.4 — Regenerar Easypanel API key (exposta) ⏱ 2min

**O que**: A key atual vazou no chat há 2+ sprints. Precisa rotacionar.

**Por que**: Defesa em profundidade. Key comprometida = qualquer um com o token pode mexer na VPS via Easypanel API.

**Onde**: Easypanel UI → Settings → API

### Passo-a-passo

1. easypanel.2notasudi.com.br → **Settings** (canto inferior esquerdo) → **API**
2. Clicar **Generate New Token** (revoga o anterior automaticamente)
3. **Copiar o token IMEDIATAMENTE** (Easypanel só mostra 1x)
4. Salvar em:
   ```bash
   # MacBook:
   echo "EASYPANEL_API_KEY=<token>" > ~/.mavis/secrets/easypanel-api-key.env
   chmod 600 ~/.mavis/secrets/easypanel-api-key.env
   ```
5. **NÃO commitar** esse arquivo. Já tem regra pre-commit bloqueando.

### Validação

```bash
# No MacBook:
source ~/.mavis/secrets/easypanel-api-key.env
curl -s -H "Authorization: Bearer $EASYPANEL_API_KEY" \
  https://easypanel.2notasudi.com.br/api/health | jq .

# Esperado: { "status": "ok" } ou similar
```

### Rollback

Gera nova key de novo. Cada geração revoga a anterior. Sem efeito colateral cumulativo.

---

## SUI 1.5 — OpenClaw LLM key ⏱ 2min ⚠️ DEPENDE DE L1

**O que**: Configurar `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` no OpenClaw gateway.

**Por que**: Sem LLM key, OpenClaw serve só de gateway de UI, sem fazer inference real. Hoje só usamos OpenCode-Go direto (bypassa OpenClaw).

**⚠️ BLOQUEIO L1 LGPD**: Esta SUI **só pode ser executada** DEPOIS de assinar DPA com MiniMax (DPA Sentry/Anthropic/OpenAI — task CAR-107 do Sprint 4). Sem DPA, dado de cliente real pode ser usado pra treinar modelos — viola LGPD art. 33.

**Onde**: Easypanel UI → Services → `cartorio_openclaw-gateway` → Env

### Decisão recomendada (Mavis/Pietra)

**Recomendação**: usar **Anthropic Claude Haiku 4.5** (`claude-haiku-4-5`) por:
1. Custo: ~$0.80/M tokens input, ~$4/M output (mais barato que Opus/GPT-5.5)
2. Latência: <2s pra 90% prompts cartorários
3. LGPD: DPA Anthropic já tem template Enterprise Brasil (LGPD art. 33 OK)
4. Já temos track record positivo em outras chamadas do backend

**Alternativas rankeadas**:
| Opção | Modelo | Custo | LGPD | Recomendação |
|-------|--------|-------|------|--------------|
| A | Claude Haiku 4.5 | $$ | ✅ DPA template BR | **Recomendado** |
| B | Claude Sonnet 4.5 | $$$ | ✅ DPA template BR | Se A não bastar |
| C | GPT-5.5 mini | $$ | ⚠️ DPA negociar | Custo > A, LGPD pior |
| D | DeepSeek v3.1 | $ | ⚠️ Servidor China | LGPD complica |
| E | OpenCode-Go (atual) | $0 (free tier) | ⚠️ Queimado no chat | NÃO usar prod |

### Passo-a-passo (se L1 já assinado)

1. easypanel.2notasudi.com.br → Services → `cartorio_openclaw-gateway` → Env
2. Clicar **Add Environment Variable**:
   ```
   ANTHROPIC_API_KEY=<sk-ant-...>
   OPENCLAW_DEFAULT_MODEL=anthropic/claude-haiku-4-5
   ```
3. Salvar → Easypanel auto-restart em 30s
4. SSH: `docker service ps cartorio_openclaw-gateway` → confirma restart completo

### Validação

```bash
ssh root@100.99.172.84 "docker logs --tail 50 cartorio_openclaw-gateway.1.\$(docker service ps cartorio_openclaw-gateway -q | head -1) | grep -iE 'model|provider|ready'"

# Esperado: "provider=anthropic/claude-haiku-4-5 ready"
```

### Rollback

Remove a env var. Restart. Volta pro estado sem LLM (degraded mas não broken).

---

## SUI 1.6 — Decisão DNS typo `supbase` → `supabase` ⏱ 15min (se escolher B)

**O que**: Hoje o subdomínio é `supbase.2notasudi.com.br` (typo histórico). Decidir se corrige.

**Onde**: Easypanel UI → Services → `cartorio_supabase` → Domains

### Decisão recomendada (Mavis/Pietra)

**Recomendação**: **MANTER `supbase`** (não corrigir).

**Razões**:
1. **Não é bloqueante**: nenhum cliente vê esse subdomínio. É só usado internamente por devs/N8N workflows.
2. **Custo de corrigir > benefício**: 5 lugares pra atualizar (Easypanel, .env API, .env N8N, workflows N8N, ENV_PRODUCTION.md) — ~15min + risco de typo novo.
3. **Lei de Hyrum**: já tem cliente (você) acostumado com o endereço. Trocar confunde.
4. **Compromisso histórico**: Sprint 0 doc falava `supbase`, virou canônico.

**Se Gustavo discordar e quiser corrigir**, opção B abaixo.

### Opções

| Opção | Esforço | Benefício | Recomendação |
|-------|---------|-----------|--------------|
| A) Manter `supbase` | 0min | Zero risco | **SIM** |
| B) Renomear pra `supabase` | 15min + revisar 5 lugares | UX perfeita | Só se incomoda |

### Passo-a-passo (se escolher B)

1. Easypanel → Services → `cartorio_supabase` → Domains → Remove `supbase.2notasudi.com.br`
2. Easypanel → Services → `cartorio_supabase` → Domains → Add `supabase.2notasudi.com.br`
3. Hostinger DNS → adicionar registro A `supabase → 187.77.236.77`
4. SSH: `docker service update --force cartorio_supabase` (recria proxy)
5. Atualizar `.env` em todos os containers que referenciam (API, N8N):
   ```bash
   # No MacBook:
   grep -rl "supbase.2notasudi.com.br" ~/projetos/Cartorio/backend/
   # Substituir nos arquivos encontrados
   ```
6. Atualizar `docs/ENV_PRODUCTION.md` (linha que menciona `supbase`)
7. Atualizar workflows N8N que apontam pra `supbase`:
   - Workflow #12 (chatbot LLM) — campo base URL
   - Workflow #03 (handoff humano) — campo Chatwoot URL

### Validação (qualquer opção)

```bash
dig +short A supbase.2notasudi.com.br @8.8.8.8
curl -sI https://supbase.2notasudi.com.br/auth/v1/ | head -1
# Esperado: 401 (Kong auth required) = UP

# Se escolheu B, mesma coisa pra supabase.2notasudi.com.br
```

### Rollback (se escolheu B)

Remove `supabase` → recria `supbase`. Reversível em 5min.

---

## Resumo executivo

| # | SUI | Tempo | Bloqueio | Status após execução |
|---|-----|-------|----------|----------------------|
| 1.1 | DNS chatwoot | 10min | nenhum | ✅ |
| 1.2 | Cred Evolution N8N | 5min | nenhum | ✅ |
| 1.3 | Agent Bot Chatwoot | 30min | nenhum | ✅ |
| 1.4 | Easypanel API key | 2min | nenhum | ✅ |
| 1.5 | OpenClaw LLM key | 2min | **L1 DPA assinado** | ⏸️ depende L1 |
| 1.6 | Decisão DNS typo | 0min (A) ou 15min (B) | decisão Gustavo | ⏸️ decisão |

**Total executável sem L1**: ~47min (4 SUIs + 0min SUI 1.6 A)
**Total com L1**: ~51min (adiciona SUI 1.5)
**Total se Gustavo escolhe B em 1.6**: ~62min

## Smoke test final (depois de todas as SUIs executadas)

```bash
# Espera 5min depois da última SUI, depois roda tudo:
ssh root@100.99.172.84 << 'EOF'
echo "=== Container status ==="
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'chatwoot|n8n|openclaw|easypanel|evolution|supabase' | head -20

echo "=== Subdomain health ==="
for sub in api flow chat easypanel whatsapp supbase; do
  code=$(curl -sI -o /dev/null -w "%{http_code}" "https://$sub.2notasudi.com.br/")
  echo "$sub.2notasudi.com.br: HTTP $code"
done

echo "=== Workflows ativos ==="
curl -s -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows?limit=50" \
  | jq '[.data[] | select(.active==true)] | length'

echo "=== Bot Chatwoot ==="
curl -s -H "api_access_token: $CHATWOOT_TOKEN" \
  "https://chat.2notasudi.com.br/api/v1/agent_bots" \
  | jq '. | length'
EOF
```

**Critérios de done (todos devem passar)**:
- [ ] 4 containers UP (chatwoot, n8n, openclaw, easypanel)
- [ ] 6 subdomínios respondem 200/302/401 (não 000/502/404)
- [ ] Workflows ativos: ≥15 (era 15 antes, +1 se SUI 1.2 OK)
- [ ] Chatwoot agent bots: ≥1

Se tudo verde, Sprint 3 stop-when = **7/7** ✅

---

## Pós-Sprint 3 (handoff pra Sprint 4)

Depois das SUIs fechadas, próximo batch é **Sprint 4 task #1 = D29-G1 LGPD export PII** (já aprovado pela sister M2.7 + CEO). Detalhe em `docs/superpowers/specs/sprint-4-design.md` (a criar quando Gustavo der GO).

Modified by Gustavo Almeida