# Validacao Telegram — Amanha (pos fix 2026-07-09)

**Bot:** [@test_cartorio_bot](https://t.me/test_cartorio_bot)  
**Grupo:** `TESTE/VALIDACAO/CORRECAO` — chat_id **`-1004331849032`** (supergroup)  
**Seu ID:** `6682284055`  
**Webhook:** `https://api.2notasudi.com.br/api/v1/telegram/webhook`

## O que foi corrigido (causa do 0/1000 + polish)

1. **Firewall DOCKER-USER dropava HTTPS publico (443)**  
   Telegram recebia `Connection timed out` → 0 requests no backend.  
   Fix: ACCEPT publico 80/443 + script `infra/firewall/f2-public-https-telegram.sh`.

2. **Grupo migrado para supergroup**  
   ID antigo `-5319980720` retornava 400 `migrate_to_chat_id`.  
   Fix: `_send_message` faz auto-retry no ID `-1004331849032`.

3. **Spam no grupo**  
   Orientacao a cada mensagem livre → agora no max **1x/5 min** + reacao eyes.

4. **Botoes (callback)**  
   Path `callback_query` + `cmd:*` validado com `response_sent: true`.

5. **set-commands / webhook-info 500**  
   Client HTTP sem `Host: api.telegram.org` no IP direto → agora usa pool TG.

6. **Metrics**  
   Callbacks OK contam em `responses_ok` + `callbacks_ok`. Debug last-updates grava resposta final.

7. **P0 HITL 2026-07-09 (Lesson 160)**  
   `fn_auto_audit` inseria `audit_log` sem `hash`/`hmac_signature` → 500 em
   `POST /api/v1/atendimento` → `/humano` nao criava ticket.  
   Fix live no Postgres + migration `0020`. Retest: `atendimento_id` OK.
   Repo: payload HITL + `atendimento_id` na msg (precisa deploy da API).

## Smoke 30 segundos (antes da validacao humana)

```bash
# 1) Webhook sem erro
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN_IN_SECRET_MANAGER>/getWebhookInfo" | python3 -m json.tool
# Esperado: url=api.2notasudi.com.br/...  pending=0  SEM last_error_message

# 2) Health bot
curl -s https://api.2notasudi.com.br/api/v1/telegram/health | python3 -m json.tool

# 3) Metrics subindo apos voce usar o bot
curl -s https://api.2notasudi.com.br/api/v1/telegram/metrics | python3 -m json.tool
```

## Roteiro no Telegram (privado primeiro, depois grupo)

### A) Chat privado com o bot

| # | Acao | Esperado |
|---|------|----------|
| 1 | `/start` | Menu + botoes inline |
| 2 | Clicar **Agendar Atendimento** | Lista de servicos |
| 3 | Clicar um servico | Pede data |
| 4 | `/menu` | Menu de novo |
| 5 | Clicar **Consultar Protocolo** | Pede numero |
| 6 | `/cancelar` | Cancela + menu |
| 7 | `/humano` | Pede descricao |
| 8 | `/lgpd` | Texto LGPD |

### B) Grupo de validacao (supergroup)

| # | Acao | Esperado |
|---|------|----------|
| 1 | `/menu` | Menu + botoes no grupo |
| 2 | Clicar botoes | Resposta no grupo (nao silenciar) |
| 3 | Texto livre sem / | So reacao eyes; orientacao no max 1x/5min |
| 4 | `/cancelar` | Volta menu |

**NAO:** spammar 10 mensagens. **NAO:** validar WhatsApp (Evolution/Chatwoot offline).

## Score alvo (1000 pts simplificado)

| Bloco | Pontos | Criterio |
|-------|--------|----------|
| Webhook vivo | 200 | getWebhookInfo sem last_error |
| /start /menu privados | 200 | 2 respostas com teclado |
| Botoes callback | 250 | 2+ cliques respondem |
| Grupo /menu + botao | 200 | funciona no supergroup |
| Anti-spam | 100 | grupo nao flooda |
| /humano HITL | 50 | pede descricao / ticket |
| **TOTAL** | **1000** | |

## Se algo falhar

```bash
# Reaplicar firewall 80/443
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 'bash -s' < infra/firewall/f2-public-https-telegram.sh

# Reset webhook
curl -s "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN_IN_SECRET_MANAGER>/setWebhook" \
  -d "url=https://api.2notasudi.com.br/api/v1/telegram/webhook" \
  -d 'allowed_updates=["message","callback_query","my_chat_member"]'

# Logs API
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 'docker service logs cartorio_api --tail 50'
```

## Status infra (nao bloqueia Telegram self-contained)

| Servico | Status |
|---------|--------|
| cartorio_api | UP |
| redis / supabase | UP |
| openclaw-gateway | UP (LLM fallback; bot nao depende) |
| evolution / chatwoot | DOWN (WhatsApp; fora do escopo Telegram) |
| n8n | OFF radar (bot self-contained) |

Modified by Gustavo Almeida
