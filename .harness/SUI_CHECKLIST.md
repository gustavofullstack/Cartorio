# 🟥 SUI BLOCKERS CHECKLIST — Gustavo UI Actions (Turn 50)

> **Status:** Aguardando ação do Gustavo. Single-agent não pode executar SUI (UI humana).
> **Criado:** 2026-07-02 (mission 9 turn 50)
> **Tempo estimado para Gustavo:** 10-15 min total

---

## 📋 Resumo: 3 SUIs + 0 técnicos novos

| ID | Blocker | Tipo | Tempo | Ação |
|---|---|---|---|---|
| SUI1 | DNS 3 subdomínios | UI Cloudflare | 5min | Criar A records |
| SUI2 | Evolution WhatsApp QR | UI Evolution Manager | 2min | Escanear QR |
| SUI3 | Chatwoot ENABLE_ACCOUNT_SIGNUP=true | **NÃO-UI** (auto-fix!) | <2min | Rodar fix script |

---

## 🟥 SUI1 — DNS Cloudflare (3 subdomínios)

### Status atual:
```
❌ chatwoot.2notasudi.com.br → NXDOMAIN
❌ n8n.2notasudi.com.br → NXDOMAIN
❌ supabase.2notasudi.com.br → NXDOMAIN
✅ chat.2notasudi.com.br → 187.77.236.77 (canônico funciona)
✅ flow.2notasudi.com.br → 187.77.236.77
✅ supbase.2notasudi.com.br → 187.77.236.77
```

### Por que canônicos funcionam mas aliases não:
- `chat.`, `flow.`, `supbase.` foram criados manualmente no Cloudflare
- Aliases exatos não existem (DNS não suporta alias puro, precisa A record próprio)

### 🛠️ Ação Gustavo (manual — 5min UI):

**OPÇÃO A — Manual (sem API token):**
1. Abra https://dash.cloudflare.com/
2. Selecione domínio `2notasudi.com.br`
3. Vá em **DNS** → **Records** → **Add record**
4. Criar 3 A records:
   - `chatwoot` → `187.77.236.77` (proxy ON 🔵)
   - `n8n` → `187.77.236.77` (proxy OFF ⚪ — para evitar Traefik conflito)
   - `supabase` → `187.77.236.77` (proxy OFF ⚪)
5. Save + aguardar propagar (~30s)
6. **OPCIONAL (automação):** gerar API token Zone:DNS:Edit e rodar:
   ```bash
   ./scripts/cloudflare_dns.sh add
   ```

**OPÇÃO B — Script automatizado (precisa API token):**
```bash
# 1. Gerar token em https://dash.cloudflare.com/profile/api-tokens
#    Perm: Zone > DNS > Edit (zone 2notasudi.com.br)
# 2. Criar .secrets/cloudflare.env:
cat > /Users/gustavoalmeida/projetos/Cartorio/.secrets/cloudflare.env <<SEC
CLOUDFLARE_API_TOKEN=<TOKEN>
CLOUDFLARE_ZONE_ID=<ZONE_ID>
SEC
chmod 600 /Users/gustavoalmeida/projetos/Cartorio/.secrets/cloudflare.env
# 3. Rodar script:
./scripts/cloudflare_dns.sh add   # 3 A records + remove flow zombie
./scripts/cloudflare_dns.sh list # ver resultado
./scripts/cloudflare_dns.sh verify # curl test em cada subdomínio
```

---

## 🟥 SUI2 — WhatsApp QR Scan (Evolution)

### Status atual:
```
Evolution API v2.3.7 ✅ UP
Container: cartorio_evolution-api.1.ajxytouy87i5fo9iind2eobnb
AUTHENTICATION_API_KEY=429683C4C977415CAAFCCE10F7D57E11
Instance: cartorio-2notas (state=close)
Webhook: https://flow.2notasudi.com.br/webhook/evo-in
```

### 🛠️ Ação Gustavo (UI — 2min):

1. Abra https://whatsapp.2notasudi.com.br/manager
2. Login com `AUTHENTICATION_API_KEY = 429683C4C977415CAAFCCE10F7D57E11`
3. Selecione instância `cartorio-2notas`
4. **Aparecerá QR code** se instance estiver `close` (estado atual)
5. Abra WhatsApp Business no celular **+55 34 99999-9999** (Gustavo pessoal)
6. Vá em **Aparelhos conectados** → **Conectar aparelho** → **escanear QR**
7. Confirmar conexão — instance state deve virar `open`
8. **OPCIONAL:** testar webhook com mensagem real

**Verificação após scan:**
```bash
ssh root@100.99.172.84 'docker exec cartorio_evolution-api.1.ajxytouy87i5fo9iind2eobnb \
  wget -q -O - "http://localhost:8080/instance/connectionState/cartorio-2notas" \
  --header="apikey: 429683C4C977415CAAFCCE10F7D57E11"'
# Esperado: {"instance":{"state":"open"}}
```

---

## 🟥 SUI3 — Chatwoot ENABLE_ACCOUNT_SIGNUP (AUTOMÁTICO!)

### Status atual:
```
❌ Cartorio Chatwoot: ENABLE_ACCOUNT_SIGNUP=true (no container env)
✅ Admin já existe (admin@2notasudi.com.br)
⚠️ Loop signup → erro "já existe" no login
```

### 🛠️ Ação (AUTOMÁTICO — single-agent pode executar):
```bash
# Script documentado em scripts/FIX_CHATWOOT_SIGNUP.md
# Troca ENABLE_ACCOUNT_SIGNUP=true → false
ssh root@100.99.172.84 'docker service update \
  --env-add ENABLE_ACCOUNT_SIGNUP=false \
  --env-rm ENABLE_ACCOUNT_SIGNUP=true \
  cartorio_chatwoot'
```

**Approval needed:** Gustavo — pode single-agent executar este? (não tem PII rotation, é só toggle)

---

## ✅ Verification Final (após Gustavo completar SUI1+SUI2)

```bash
# 1. DNS
for sub in chatwoot n8n supabase; do
  dig +short "$sub.2notasudi.com.br"
done
# Esperado: 187.77.236.77 cada

# 2. EVO QR
ssh root@100.99.172.84 'docker exec cartorio_evolution-api.1.*.*.* \
  wget -q -O - "http://localhost:8080/instance/connectionState/cartorio-2notas" \
  --header="apikey: 429683C4C977415CAAFCCE10F7D57E11"'
# Esperado: state=open

# 3. Bot Telegram (já funcional, opcional):
curl -s "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/getWebhookInfo"
# Esperado: pending_update_count=0 (após flush manual)
```

---

## 📊 Após completar tudo

- Compliance ANPD: 95% → 100% (com DNS correto)
- WhatsApp produção: conectado
- Bot Telegram: standby + bot WhatsApp ativo
- Production readiness: 95% → 100%

---

**Owner:** Gustavo Almeida  
**Reviewer:** cartorio-lgpd (Pietra)  
**Deadline:** ASAP (bloqueadores P0/P1)
