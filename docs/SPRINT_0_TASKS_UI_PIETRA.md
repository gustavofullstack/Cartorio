# 📋 Sprint 0 — Tasks UI/Externo pra Pietra (Gustavo)

> **4 tasks que SÓ TU podes fazer** (são UI/DNS/painel externo, não código).
> **Tempo total**: ~20min
> **Bloqueio**: T0.9 (DNS Chatwoot) bloqueia T1.1 (integração Chatwoot)

---

## T0.9 — DNS `chatwoot.2notasudi.com.br` ⏱️ 5min

**Por que**: container `cartorio_chatwoot` está UP (healthy) mas sem DNS público. Sem isso, ninguém acessa de fora.

**Como fazer** (escolhe 1):
- **Opção A — Hostinger** (se 2notasudi.com.br é gerenciado lá):
  1. `https://hpanel.hostinger.com` → Domínios → `2notasudi.com.br` → DNS / Zona DNS
  2. Adicionar registro: Tipo `A`, Nome `chatwoot`, Valor `187.77.236.77` (IPv4 público VPS), TTL 300
  3. (Opcional) Registro `AAAA` pra IPv6 `2a02:4780:6e:cd40::1`

- **Opção B — Cloudflare** (se 2notasudi.com.br está no Cloudflare):
  1. `https://dash.cloudflare.com` → Selecionar domínio → DNS → Records → Add
  2. Tipo `A`, Name `chatwoot`, Content `187.77.236.77`, Proxy OFF (cinza) ou ON (laranja — depende se quer CDN; recomendo ON)
  3. Salvar

**Validar** (depois de 5min pra propagar):
```bash
curl -s -m 5 -o /dev/null -w "chatwoot.2notasudi.com.br -> %{http_code}\n" https://chatwoot.2notasudi.com.br/
# esperado: 200 ou 302 (login Chatwoot)
```

---

## T0.10 — Chatwoot Agent Bot (webhook) ⏱️ 10min

**Por que**: Workflow N8N #03 (Handoff Humano) usa o Agent Bot pra abrir conversa. Sem bot, handoff vira fallback inbox URL.

**Como fazer**:
1. Acessar `https://chatwoot.2notasudi.com.br/super_admin` (login como super_admin)
2. Settings → Agents → Agent Bots → Add
3. Preencher:
   - **Name**: `cartorio-bot`
   - **Description**: `Bot do cartório - recebe PII handoff do N8N workflow #03`
   - **Webhook URL**: `https://api.2notasudi.com.br/api/v1/webhook/chatwoot` ⚠️ endpoint não existe ainda, criar no Sprint 1 T1.1
   - **Bot type**: `Webhook`
4. Salvar
5. Copiar o `Bot Token` gerado (chave longa)
6. Adicionar env no `cartorio_api`:
   ```bash
   ssh cartorio 'docker service update --env-add CHATWOOT_BOT_TOKEN=<token> cartorio_api'
   ```

---

## T0.11 — Easypanel API key regenerar ⏱️ 2min

**Por que**: a antiga morreu 401. Sem key nova, scripts de deploy automático quebram.

**Como fazer**:
1. `https://easypanel.2notasudi.com.br` → Settings → API
2. Clicar "Regenerate Token" ou "Generate New Token"
3. Copiar a chave
4. Salvar localmente (NUNCA commit):
   ```bash
   mkdir -p ~/.mavis/secrets
   echo "EASYPANEL_API_KEY=<nova-chave>" > ~/.mavis/secrets/easypanel-api-key.env
   chmod 600 ~/.mavis/secrets/easypanel-api-key.env
   ```
5. Atualizar `backend/.env` (NÃO o .env.example, o real):
   ```bash
   EASYPANEL_API_KEY=<nova-chave>
   ```
6. Atualizar `~/.zcode/.env` ou onde os scripts shell guardam:
   ```bash
   grep -r "EASYPANEL_API_KEY" ~/.zcode/ 2>/dev/null
   ```

---

## T0.12 — Decisão DNS typo `supbase` vs `supabase` ⏱️ 1min (só decisão, não execução)

**Por que**: afeta URL pública, MELHOR corrigr ou MANTER como oficial?

**Trade-offs**:

| Opção | Prós | Contras |
|---|---|---|
| **A) Manter `supbase`** | Nada a fazer agora; "marca" registrada; URLs já em uso | Feio, não-profissional |
| **B) Corrigir pra `supabase`** | URL correta, profissional | 15min mudança DNS + atualizar N8N workflows + .env em todos os serviços + 1 Sprint de migração |

**Decisão** (responde):
- (A) "mantém supbase" → eu documento como oficial e não mexo mais
- (B) "corrige pra supabase" → eu agendo task T-Sprint-X pra fazer com cuidado

---

## ✅ Quando terminar

Manda 1 mensagem no grupo Telegram (cartório-agent) com:
```
Sprint 0 UI done:
T0.9 [✓/✗] — chatwoot DNS
T0.10 [✓/✗] — Chatwoot Agent Bot
T0.11 [✓/✗] — Easypanel API key
T0.12 decisão: [A/B]
```

Aí eu sigo pra Sprint 1 (Chatwoot integration + OpenClaw LLM key + E2E test).

Modified by ZCode (Pietra session 2026-06-23)
