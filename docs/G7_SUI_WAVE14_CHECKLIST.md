# G7 Wave 14 — SUI Checklist Executável (Gustavo)

**Tempo total estimado:** ~45 min  
**Pré-requisito:** ler `docs/CANAL_HEALTH_MATRIX.md` (probe 2026-07-16)  
**Agents já entregaram:** runbooks + validators; **você** fecha UI/DNS/tokens.

---

## Ordem obrigatória (não pular)

### 1. DNS Cloudflare (~5 min) — G7.12.T1
Painel Cloudflare → zona `2notasudi.com.br` → DNS:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `chatwoot` | `187.77.236.77` | Proxied |
| A | `n8n` | `187.77.236.77` | Proxied |
| A | `supabase` | `187.77.236.77` | Proxied |

Validar:
```bash
dig +short chatwoot.2notasudi.com.br A
dig +short n8n.2notasudi.com.br A
dig +short supabase.2notasudi.com.br A
bash scripts/check_dns_health.sh
```
Runbook: `infra/dns/CLOUDFLARE_RUNBOOK.md`

### 2. Easypanel DATABASE_URL (~15 min) — G7.04.T1 / Lesson 176
Para **evolution-api**, **chatwoot**, **n8n**:

- Usar DNS **interno Swarm** + credenciais do Postgres **atual** (`POSTGRES_USER=admin` / DB real).
- **Remover** IP externo antigo `10.11.211.12` e password legado `supabase_admin:e999…`.
- Após save: scale 0 → 1 (host-mode) se porta conflitar.

Validar:
```bash
curl -sS https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool
# n8n/evolution/chatwoot devem ir para online
```

### 3. Redeploy API (~5 min) — G7.18.T1
Publicar imagem com `/api/v1/health/radar/expanded` (já em master).

Validar:
```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://api.2notasudi.com.br/api/v1/health/radar/expanded
# esperado: 200
make radar-smoke
```

### 4. Telegram BotFather (~5 min) — G7.03.T1
1. `/token` no @BotFather para o bot do cartório  
2. Atualizar secret em Easypanel / `.secrets/telegram.env`  
3. Re-registrar webhook:
```bash
# exemplo (token NÃO commitar)
curl -sS "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://api.2notasudi.com.br/api/v1/telegram/webhook"
```
Ref: Lesson 178 + `docs/platforms/TELEGRAM_BOT.md`

### 5. LobeChat key (~3 min) — G7.06.T1
Easypanel LobeChat: trocar `OPENAI_API_KEY=sk-xxxx` pela key real do proxy OpenClaw/LiteLLM.

### 6. WhatsApp QR (~5 min) — G7.04.T2
Abrir `https://whatsapp.2notasudi.com.br/manager` → instância cartorio → escanear QR.

### 7. OpenClaw cartorio-bot (~7 min) — G7.06.T3
SSH/Tailscale + operator token com scopes + criar agent conforme  
`docs/openclaw/E6-cartorio-bot-spec.md` (Lesson 177).

### 8. DPA MiniMax (assinar) — G7.19.T2
**Wave27:** pacote READY_TO_SIGN em `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md`  
Template: `docs/lgpd/dpa_minimax_template.md`  
Tracker: `python3 scripts/dpa_sign_flow.py`  
Status matriz: **READY_TO_SIGN** (ainda **não** SIGNED — HOLD-GUSTAVO checklist §11 do pacote)

### 8b. Privacy Policy v3 (publicar) — G7.19.T3
**Wave27:** draft `docs/PRIVACY_POLICY_V3_G7.md` + checklist `docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md`  
HOLD-GUSTAVO: publicar em https://2notasudi.com.br/privacidade

---

## Depois de cada bloco

```bash
python3 scripts/g7_super_validator.py --report docs/G7_VALIDATOR_REPORT.md
# overall deve migrar HOLD → WORK
```

---

**Modified by Gustavo Almeida + cartorio-sre — G7 Wave 14**
