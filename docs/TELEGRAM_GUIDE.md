# Telegram Bot — Guia Operacional Completo

> **Versão**: 3.0 (2026-07-09)
> **Bot**: `@CartorioAssistantBot`
> **Production status**: ✅ 100% funcional (8/8 testes E2E sent=True)
> **Owner**: Gustavo Almeida (SUI para QR scan / BotFather / bloqueios)

## 📋 Sumário

1. [Setup inicial (SUI Gustavo)](#setup-inicial-sui-gustavo)
2. [Arquitetura](#arquitetura)
3. [Comandos](#comandos)
4. [Debounce + rate limit + idempotência](#debounce--rate-limit--idempotência)
5. [LGPD compliance](#lgpd-compliance)
6. [Deploy + monitoramento](#deploy--monitoramento)
7. [Troubleshooting](#troubleshooting)

## 🔧 Setup Inicial (SUI Gustavo)

### BotFather (uma vez)

1. Abrir `@BotFather` no Telegram
2. `/newbot` → nome: `Cartório 2º Notas Assistant`
3. Username: `CartorioAssistantBot`
4. Copiar **token** → env `TELEGRAM_BOT_TOKEN=...`
5. `/setprivacy` → **DISABLE** (bot precisa ver todas mensagens em grupos)
6. `/setcommands` → colar lista de comandos (ver abaixo)

### Webhook (no Cartório API)

```bash
# Configurar webhook (apontar para nosso endpoint)
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://api.2notasudi.com.br/api/v1/webhook/telegram"

# Verificar
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
# Resposta esperada: {"url": "https://api.2notasudi.com.br/api/v1/webhook/telegram", "pending_update_count": 0}
```

### Validation Gustavo (celular)

```
1. Abrir Telegram no celular
2. Buscar @CartorioAssistantBot
3. /start
4. Tempo esperado: < 10s (debounce 1.2s + LLM 4-8s + send 0.5s)
5. Se não responder em 15s → ver docs/TROUBLESHOOTING_BOTS.md
```

## 🏗️ Arquitetura

```
Cliente Telegram                Cartório Backend                    LiteLLM Proxy
   │                                  │                                   │
   │ 1. /start                        │                                   │
   ├─────────────────────────────────►│                                   │
   │                                  │ 2. POST /webhook/telegram         │
   │                                  │    (InboundMessage)               │
   │                                  │                                   │
   │                                  │ 3. check_idempotency              │
   │                                  │    Redis SETNX TTL 600s           │
   │                                  │                                   │
   │                                  │ 4. scrub_pii_3_layers             │
   │                                  │    (input → pre-LLM → output)     │
   │                                  │                                   │
   │                                  │ 5. enqueue + debounce 1.2s        │
   │                                  │    Redis RPUSH + asyncio.wait     │
   │                                  │                                   │
   │                                  │ 6. typing_loop (refresh 4s)       │
   │◄─────────────────────────────────┤    sendChatAction("typing")       │
   │  "Bot digitando..."              │                                   │
   │                                  │ 7. call_llm_with_fallback         │
   │                                  ├──────────────────────────────────►│
   │                                  │    POST /v1/chat/completions       │
   │                                  │    model: opencode-free-1         │
   │                                  │                                   │
   │                                  │ 8. response 4-10s                │
   │                                  │◄──────────────────────────────────┤
   │                                  │    text: "Olá! Sou o assistente..."│
   │                                  │                                   │
   │                                  │ 9. scrub output (camada 3)        │
   │                                  │                                   │
   │                                  │ 10. sendMessage                   │
   │◄─────────────────────────────────┤    (HTML parse_mode)              │
   │  Mensagem do bot                 │                                   │
   │                                  │                                   │
   │                                  │ 11. setMessageReaction            │
   │◄─────────────────────────────────┤    emoji: 👍                      │
   │  Reação                          │                                   │
   │                                  │ 12. audit_log (LGPD)              │
   │                                  │     hash chain + Redis pub/sub    │
```

## 🎮 Comandos Suportados

### `/start`

Saudação inicial + menu principal.

**Resposta**:
```
Olá! Sou o assistente virtual do Cartório 2º Notas 👋

Posso ajudar com:
📋 Consultar protocolo
📅 Agendar atendimento
💰 Consultar emolumento
⚖️ Tirar dúvidas jurídicas
👤 Falar com humano

Escolha uma opção ou digite sua dúvida.
```

### `/menu`

Reapresenta menu principal (idêntico `/start`).

### `/protocolo <número>`

Consulta status do protocolo no banco.

**Exemplo**: `/protocolo 12345`

**Resposta**:
```
📋 Protocolo 12345

Status: Em andamento
Abertura: 2026-06-15
Previsão: 2026-07-20
Etapa atual: Análise jurídica
Responsável: Escrevente Carla
```

**Erro**: `❌ Protocolo 12345 não encontrado. Verifique o número.`

### `/agendar`

Inicia fluxo de agendamento (escolha serviço → data → horário).

**Resposta inicial**:
```
📅 Agendamento

Qual serviço você precisa?
1. Reconhecimento de firma
2. Procuração
3. Testamento
4. Certidão
5. Outro

Digite o número da opção:
```

### `/humano`

HITL — cria atendimento no Chatwoot + notifica escrevente.

**Resposta**:
```
👤 Perfeito! Vou transferir você para um escrevente.

Em alguns minutos alguém vai responder aqui.
Tempo médio de espera: 5 minutos.

Se preferir, pode ligar (11) 1234-5678 ou enviar email atendimento@cartorio2notas.com.br.
```

### `/cancelar`

Direito esquecimento (LGPD art. 18 VI).

**Resposta**:
```
🗑️ Direito ao Esquecimento

Seus dados serão excluídos em até 30 dias conforme LGPD art. 18 VI.

Para confirmar, responda CONFIRMAR.
Para cancelar, responda CANCELAR.
```

Após `CONFIRMAR`: usuário vai pra fila de exclusão + audit log.

### `/lgpd`

Mostra direitos do titular + exporta dados pessoais.

**Resposta**:
```
🔒 Seus direitos LGPD (art. 18)

I   - Confirmação de existência de tratamento
II  - Acesso aos dados
III - Correção de dados incompletos
IV  - Anonimização, bloqueio ou eliminação
V   - Portabilidade
VI  - Eliminação (consentimento desnecessário)
VII - Informação sobre entidades públicas e privadas
VIII - Informação sobre possibilidade de não fornecer consentimento
IX  - Revogação do consentimento

Para exportar seus dados em JSON, digite: /lgpd export
Para solicitar eliminação: /cancelar
```

## ⏱️ Debounce + Rate Limit + Idempotência

### Debounce (1.2s)

Se cliente envia 3 mensagens em 1s, bot aguarda 1.2s para consolidar.

**Implementação** (`chat_pipeline.py`):
```python
DEBOUNCE_WINDOW_SEC = 1.2

async def process_debounced(messages: list[InboundMessage]) -> OutboundMessage:
    if len(messages) > 2:
        # Resume: junta todas mensagens em uma só
        joined = " | ".join(m.text for m in messages)
        text = f"[{len(messages)} mensagens] {joined[:600]}"
    else:
        text = messages[-1].text
    return await call_llm_with_fallback(text)
```

### Rate Limit (3s por chat_id)

Bot responde no máximo 1x a cada 3s por conversa.

**Implementação**:
```python
RATE_LIMIT_SECONDS = 3

async def check_rate_limit(conv_key: str, channel: Channel) -> bool:
    key = f"rl:{channel.value}:{conv_key}"
    is_new = await bus.client.set(key, "1", ex=RATE_LIMIT_SECONDS, nx=True)
    return bool(is_new)
```

### Idempotência (TTL 10min)

Mesmo `update_id` não processa 2x.

**Implementação**:
```python
IDEMPOTENCY_TTL_SEC = 600

async def check_idempotency(update_id: str, channel: Channel) -> bool:
    key = f"idem:{channel.value}:{update_id}"
    is_new = await bus.client.set(key, "1", ex=IDEMPOTENCY_TTL_SEC, nx=True)
    return not bool(is_new)  # True se já existia (pular)
```

## 🛡️ LGPD Compliance

### 3 Camadas PII Scrub

**Camada 1 (input)** — antes de logar:
```
Input: "Meu CPF é 123.456.789-09 e email teste@email.com"
Log:   "Meu CPF é [REDACTED:cpf] e email [REDACTED:email]"
```

**Camada 2 (pre-LLM)** — antes de enviar pra API pública:
```
LLM input: "Meu CPF é [REDACTED:cpf] e email [REDACTED:email]"
```

**Camada 3 (output)** — resposta do LLM não vaza:
```
LLM output: "Recebemos sua solicitação. Prazo: 5 dias úteis."
(verifica que output não contém CPF/RG/email)
```

**Implementação** (`app/services/pii.py`):
```python
def scrub(text: str) -> ScrubResult:
    patterns = [
        (r'\d{3}\.\d{3}\.\d{3}-\d{2}', '[REDACTED:cpf]'),
        (r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', '[REDACTED:cnpj]'),
        (r'\d{1,2}\.?\d{3}\.?\d{3}-?\d{0,2}', '[REDACTED:rg]'),
        (r'[\w.-]+@[\w.-]+\.\w+', '[REDACTED:email]'),
        (r'\(\d{2}\)\s*\d{4,5}-?\d{4}', '[REDACTED:phone]'),
    ]
    ...
```

### Audit Log LGPD (toda mensagem)

```
{
  "timestamp": "2026-07-09T16:30:00Z",
  "channel": "telegram",
  "chat_id_hash": "sha256:abc123...",
  "sender_name_hash": "sha256:def456...",
  "content_hash": "sha256:ghi789...",
  "scrubbed_text": "[REDACTED] Olá, gostaria de...",
  "intent": "saudacao",
  "provider_used": "litellm:opencode-free-1",
  "latency_ms": 8234,
  "audit_hash": "sha256:prev_hash + payload + timestamp",
  "audit_hmac": "hmac:key:audit_hmac"
}
```

## 🚀 Deploy + Monitoramento

### Deploy (Render)

```yaml
# .github/workflows/cd.yml
- name: Deploy Telegram bot
  run: |
    curl -X POST $RENDER_DEPLOY_HOOK \
      -d "serviceId=$RENDER_API_SERVICE_ID"
```

### Métricas Prometheus

```
# Counter
bot_requests_total{channel="telegram",status="ok"} 1234
bot_requests_total{channel="telegram",status="fallback"} 12
bot_requests_total{channel="telegram",status="error"} 3

# Histogram
bot_latency_seconds{channel="telegram",provider="litellm"} bucket=...

# Gauge
bot_circuit_state{provider="litellm"} 0
bot_active_typing{channel="telegram"} 2
```

### Alertas Telegram GRUPO Pietra

| Trigger | Threshold | Ação |
|---|---|---|
| Latência P95 | > 15s em 5min | Alerta GRUPO Pietra |
| Error rate | > 1% em 5min | Alerta GRUPO Pietra |
| Circuit OPEN | > 60s em qualquer provider | Alerta GRUPO Pietra |
| Audit log stale | > 15min sem novos | Dead man's switch A13 |
| Redis offline | > 30s | Alerta GRUPO Pietra |

## 🛠️ Troubleshooting

### Bot não responde em 15s

```bash
# 1. Verificar webhook configurado
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

# 2. Verificar API online
curl -sS https://api.2notasudi.com.br/api/v1/health/integracoes | jq .

# 3. Verificar LiteLLM proxy
curl -sS http://cartorio_litellm-app:4000/health/liveliness

# 4. Ver logs API
docker logs cartorio_api --since 5m 2>&1 | grep -E 'TG|telegram|webhook'
```

### LiteLLM DOWN

```bash
# Restart LiteLLM
docker service update --force cartorio_litellm-app

# OU ativar fallback manual (já automático)
# Bot vai tentar opencode_free_1 automaticamente
```

### Bot responde duplicado

```bash
# Verificar idempotência Redis
redis-cli GET "idem:telegram:12345"
# Deve retornar "1" se já processado
```

Ver [`TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md) para cenários avançados.

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview Telegram + WhatsApp
- [`FALLBACK_CHAIN.md`](FALLBACK_CHAIN.md) — 7 providers LLM
- [`LGPD_BOTS.md`](LGPD_BOTS.md) — compliance completo
- [`CHATWOOT_HANDOVER.md`](CHATWOOT_HANDOVER.md) — HITL
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — diagrama C2/C3/C4

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:36:30Z
**Lesson**: 141 (chat_pipeline extraído)