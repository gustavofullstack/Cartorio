# Telegram Bot — Documentação Operacional

> Bot oficial do **2º Serviço Notarial de Uberlândia** no Telegram.
> Status 2026-07-15 14:45 BRT: **MORTO** (token revogado). Ver `STATUS` abaixo.
> Cross-ref: `backend/app/api/v1/telegram.py` (handler) · Lessons 160/161/162/170/178.

## Índice

- [STATUS (2026-07-15)](#status-2026-07-15)
- [Setup via @BotFather (passo-a-passo)](#setup-via-botfather-passo-a-passo)
- [Webhook handler — mapa do backend](#webhook-handler--mapa-do-backend)
- [20 cenários smoke test](#20-cenarios-smoke-test)
- [LGPD — PII scrubbing em 3 camadas](#lgpd--pii-scrubbing-em-3-camadas)
- [Fallback chain: OpenClaw → LiteLLM → opencode_free_1](#fallback-chain-openclaw--litellm--opencode_free_1)
- [Monitoramento](#monitoramento)
- [Cross-ref Lessons](#cross-ref-lessons)

---

## STATUS (2026-07-15)

| Item | Estado | Notas |
|------|--------|-------|
| Bot handle | `@TestCartorioBot` | criado via @BotFather |
| Bot token | **REVOGADO** | Gustavo revogou em 2026-07-XX; precisa regenerar |
| Webhook Telegram | configurado: `https://api.2notasudi.com.br/api/v1/telegram/webhook` | endpoint backend UP |
| Backend handler | `/api/v1/telegram/webhook` | FastAPI v0.6.1-p0fix |
| PII scrubbing | 3 camadas ativas (input/pre-LLM/output) | OK |
| Debounce 3s | ativo | OK |
| Rate limit | sliding 60/min + 3-tier API key | OK |
| Webhook secret | configurado em prod | OK |
| Alertas Telegram | TELEGRAM_CHAT_ID_DPO=6682284055 | OK |

**Próximo passo (Gustavo)**:
1. Regenerar token via @BotFather (`/revoke` → `/token`)
2. Atualizar `.secrets/telegram.env` real (não commitar)
3. Restart backend (EasyPanel)
4. Re-registrar webhook: `curl https://api.telegram.org/bot<NEW_TOKEN>/setWebhook?url=...&secret_token=...`

---

## Setup via @BotFather (passo-a-passo)

### 1. Abrir conversa com @BotFather

```
1. Telegram → busca → "@BotFather"
2. Iniciar conversa (/start)
3. /newbot
```

### 2. Definir nome e username

```
BotFather: Alright, a new bot. How are we going to call it?
Gustavo:  Cartório 2º Notas - Uberlândia

BotFather: Good. Now let's choose a username for your bot.
           It must end in 'bot'. Like this, for example: TetrisBot or tetris_bot.
Gustavo:  test_cartorio_bot

BotFather: Done! Congratulations on your new bot.
           You will find it at t.me/test_cartorio_bot

           Use this token to access the HTTP API:
           8859206262:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

           Keep your token secure and store it safely.
```

### 3. Configurar descrição e about

```
/setdescription
@CartorioBot
"Assistente virtual do 2º Ofício de Notas de Uberlândia/MG.
Atendimento em PT-BR com LGPD-by-design (3 camadas de PII scrubbing)."

/setabouttext
"Bot oficial do cartório. Agendamento, consulta de protocolo,
emolumento e handoff para escrevente humano."

/setuserpic
[upload logo do cartório]
```

### 4. Registrar comandos (menu)

```
/setcommands
@CartorioBot

start - Iniciar (aviso LGPD + Agent AI)
menu - Atalhos opcionais
humano - Atendimento humano (HITL)
cancelar - Cancelar e limpar conversa
lgpd - Privacidade e direitos LGPD
voz - Ouvir última resposta em áudio
```

### 5. Gerar webhook secret (backend)

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: kJ8sH2kF4nQ... (32+ chars)
```

### 6. Registrar webhook (curl)

```bash
# Substituir <TOKEN> e <SECRET>
TOKEN="<token-do-botfather>"
SECRET="<webhook-secret-gerado>"

curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://api.2notasudi.com.br/api/v1/telegram/webhook\",
    \"secret_token\": \"${SECRET}\",
    \"allowed_updates\": [\"message\", \"callback_query\", \"my_chat_member\"],
    \"drop_pending_updates\": true
  }"

# Esperado: {"ok":true,"result":true,"description":"Webhook was set"}
```

### 7. Validar webhook

```bash
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
# Esperado: url correto, pending_update_count=0, last_error_date vazio
```

---

## Webhook handler — mapa do backend

Arquivo: [`backend/app/api/v1/telegram.py`](file:///Users/gustavoalmeida/projetos/Cartorio/backend/app/api/v1/telegram.py)

### Fluxo (POST /api/v1/telegram/webhook)

```
1. Request chega
   └─► verify_telegram_secret()   ← valida X-Telegram-Bot-Api-Secret-Token
       └─► HMAC compare_digest    ← timing-safe (linha 2267-2275)

2. Parsing update
   ├─ message (texto livre, foto, doc, audio, voice)
   ├─ callback_query (botao inline)
   └─ my_chat_member (bot entrou/saiu de grupo)

3. Extract attachments (linha 1890-1946)
   ├─ photo[]    → maior foto
   ├─ document   → 1 doc
   ├─ video      → 1 video
   ├─ audio      → 1 audio
   └─ voice      → handler proprio (linha 1864-1886)

4. Idempotency check (linha 2010-2014)
   └─► Redis SETNX `tg:idem:{update_id}` TTL 10min
       └─► se ja processado → return duplicate

5. Group gate (linha 1974-2004)
   └─► supergroup sem @mencion ou /comando → react eyes + orientacao
       (anti-spam grupo; orientacao 1x a cada 5min)

6. PII Scrub input layer (linha 2021-2026)
   └─► scrub(text).text   ← app/services/pii.py
       └─► CPF/RG/email/telefone → [CPF_REDACTED] etc.

7. Routing (linha 2028-2230)
   ├─ callback  → _handle_callback()
   ├─ /comando  → _handle_command() (whitelist ALLOWED_COMMANDS)
   ├─ state!=IDLE → _handle_state() (wizard agendar/protocolo/humano)
   └─ free text → background_tasks.add_task(_process_telegram_debounce, ...)

8. Debounce 3s (background)
   └─► _process_telegram_debounce(chat_id)
       ├─► sleep(DEBOUNCE_WINDOW=1.2s)  ← coleta msgs
       ├─► typing_loop (refresh 4s)
       ├─► _resumir_mensagens()         ← anti-spam 10msg/5s → 2 resumo
       ├─► _extract_client_fields()     ← CPF/email/phone (perfil Redis)
       ├─► _check_rate_limit(3s)        ← sliding window
       └─► _call_cartorio_agent()       ← MiniMax-M3 + tools

9. PII Scrub output layer (linha 1683-1684)
   └─► format_bot_text() + scrub_bot_outbound()
       └─► protege dpo@2notasudi.com.br antes do scrub generico

10. Send via pool HTTP singleton
    └─► _send_message(chat_id, text)
        └─► POST https://149.154.166.110/bot<TOKEN>/sendMessage
            (direct IP — bypass macOS DNS broken 2026-07-08)
```

### Pontos críticos (LGPD / segurança)

| Linha | Função | Regra |
|-------|--------|-------|
| 2267-2275 | `_verify_telegram_secret` | HMAC compare_digest (timing-safe) |
| 368-389 | `_check_idempotency` | Redis SETNX TTL 10min |
| 2021-2026 | `scrub(text)` antes de tudo | PII layer 1 (input) |
| 1172 | `_hist_append` com `scrub(text).text[:400]` | PII layer 2 (storage) |
| 1684 | `scrub_bot_outbound(response_text)` | PII layer 3 (output) |
| 141-181 | `_OFFICIAL_OUTBOUND_PROTECT` | protege DPO email |
| 2081-2096 | TTS `/voz` | só narra texto já scrubado |

---

## 20 cenários smoke test

Referência: [`backend/tests/smoke/`](file:///Users/gustavoalmeida/projetos/Cartorio/backend/tests/smoke/) + [`test_telegram_webhook.py`](file:///Users/gustavoalmeida/projetos/Cartorio/backend/tests/test_telegram_webhook.py).

### Comandos nativos

1. `/start` → LGPD notice + menu
2. `/menu` → atalhos com botão Cancelar
3. `/cancelar` → limpa estado + memória multi-turn
4. `/humano` → cria ticket HITL (POST /atendimento)
5. `/protocolo` → pede número do protocolo
6. `/lgpd` → re-imprime notice LGPD
7. `/voz` → TTS MiniMax da última resposta
8. `/agendar` → wizard 5 serviços (reconhecimento_firma, autenticacao, etc.)

### Comportamento de botões

9. Callback `agendar` → mostra menu de serviços
10. Callback `cancelar` → limpa e mostra menu
11. Callback `serv:1` → seleciona reconhecimento_firma
12. Callback `agendar:confirmar` → POST /agendamento

### Texto livre (free-form)

13. "Quanto custa uma certidão?" → agent MiniMax-M3 responde emolumento
14. "Meu CPF é 123.456.789-09..." → PII scrubado + handoff HITL
15. "Quero falar com humano" → action=humano + Chatwoot handoff
16. Mensagem supergroup sem `@mencion` → react eyes + orientação (1x/5min)

### Erro / edge cases

17. Webhook com secret errado → 401
18. Webhook sem header secret (mas secret configurado) → 401
19. `update_id` duplicado (replay) → status=duplicate
20. Bot entra em grupo (`my_chat_member` join) → welcome + LGPD

---

## LGPD — PII scrubbing em 3 camadas

### Camada 1: Input
```python
scrub_result = scrub(text)
text_scrubbed = scrub_result.text  # CPF → [CPF_REDACTED]
```
[`app/services/pii.py`](file:///Users/gustavoalmeida/projetos/Cartorio/backend/app/services/pii.py) — regex CPF/RG/CNH/email/phone.

### Camada 2: Pre-LLM (history storage)
```python
async def _hist_append(bus, key, role, text):
    snippet = scrub(text).text[:400]  # PII scrub antes de gravar Redis
    hist.append(f"{role}: {snippet}")
```

### Camada 3: Output (anti-echo)
```python
def scrub_bot_outbound(text):
    protected = text
    for real, tok in _OFFICIAL_OUTBOUND_PROTECT:  # protege DPO email
        protected = protected.replace(real, tok)
    scrubbed = scrub(protected).text
    # restaura DPO email (lesson 162 fix)
    return scrubbed
```

**Plus**:
- CPF vai pro Redis apenas como SHA-256 hash truncado (32 chars) via `_client_profile_upsert`
- `_persist_conversa` grava só `raw_message_hash` (SHA-256 do scrubado) — não o raw original

---

## Fallback chain: OpenClaw → LiteLLM → opencode_free_1

Definido em [`.secrets/opencode-go.env`](file:///Users/gustavoalmeida/projetos/Cartorio/.secrets/opencode-go.env) + `app/services/cartorio_agent.py`.

```
OpenClaw Gateway (agent.2notasudi.com.br)
   ↓ timeout/5xx
LiteLLM Proxy (LITELLM_FALLBACK_CHAIN):
   1. opencode_free_1 (nemotron)
   2. mimo
   3. deepseek
   4. opencode-go
   5. mistral-free
   6. openrouter-free
   7. gemini-free
```

---

## Cross-ref Lessons

| Lesson | Tópico |
|--------|--------|
| [[lesson-150-incident-vps-down-telegram-2026-07-08]] | VPS down → Telegram webhook offline |
| [[lesson-151-cloudflare-tunnel-rescue-2026-07-08]] | Cloudflare Tunnel como backup HTTPS |
| [[lesson-152-telegram-my-chat-member-group-migration-2026-07-08]] | Bot saiu/entrou de grupo -5319980720 → -1004331849032 |
| [[lesson-160-telegram-hitl-fn-auto-audit-2026-07-09]] | HITL function calling + auto audit |
| [[lesson-161-telegram-memory-catalog-series-2026-07-10]] | Memory multi-turn + catalog series |
| [[lesson-162-telegram-porn-format-dados-2026-07-10]] | Anti-porn + format dados + DPO email |
| [[lesson-170-lobechat-agent-fix-2026-07-14]] | LobeChat Custom OpenAI provider fix |
| [[lesson-178-lobechat-telegram-snapshot-2026-07-15]] | F4 [P1] RETRY snapshot — LobeChat/Telegram status + gap list |

---

## Monitoramento

Monitor Uptime Kuma configurado em [`infra/lobechat/monitors.json`](file:///Users/gustavoalmeida/projetos/Cartorio/infra/lobechat/monitors.json):

- **Monitor ID**: `telegram-webhook-prod`
- **Probe**: `GET https://api.2notasudi.com.br/api/v1/telegram/health` (esperado 200)
- **Interval**: 120s · **Retry**: 60s · **Max retries**: 3 · **Timeout**: 10s
- **Current status (2026-07-15 14:45 BRT)**: `DOWN_5XX` — token revogado por Gustavo. Endpoint health UP (200), mas bot MORTO até regenerar token via @BotFather.
- **Alertas Telegram**: chat_id `6682284055` (DPO Gustavo), MarkdownV2 parse mode

### Validar manualmente

```bash
# Health check (independente do token)
curl -fsS https://api.2notasudi.com.br/api/v1/telegram/health
# Esperado: {"status":"ok", ...}

# Webhook info (precisa do token)
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
# Esperado: url correto, pending_update_count=0, last_error_date vazio

# Verificar se token está vivo
curl "https://api.telegram.org/bot<TOKEN>/getMe"
# Esperado: {"ok":true,"result":{"id":8859206262,"username":"test_cartorio_bot",...}}
```

---

## Modified by Gustavo Almeida — 2026-07-15 14:45 BRT — F4 [P1] RETRY