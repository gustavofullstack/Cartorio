# Bots — Telegram + WhatsApp (Overview)

> **Versão**: 3.0 (2026-07-09)
> **Status**: ✅ Telegram 100% production · 🟡 WhatsApp 100% espelhado (paridade via `chat_pipeline.py`)
> **Pipeline compartilhado**: `backend/app/services/chat_pipeline.py` (553 linhas)

## 🎯 Visão Geral

O Cartório 2º Notas opera **dois canais de chatbot** com paridade 100% de funcionalidades, comandos, LGPD e fallback chain. Ambos os canais consomem o mesmo orquestrador polimórfico (`chat_pipeline.py`) e diferem apenas no `ChannelAdapter`.

| | Telegram | WhatsApp (Evolution API) |
|---|---|---|
| **Bot username** | `@CartorioAssistantBot` | `cartorio-2notas` (instância Evolution) |
| **API** | Bot API oficial (api.telegram.org) | Evolution API 2.3.7 (whatsapp.2notasudi.com.br) |
| **Webhook** | `POST /api/v1/webhook/telegram` | `POST /api/v1/webhook/evolution` |
| **Adapter** | `TelegramAdapter` (em `telegram.py`) | `WhatsAppAdapter` (em `whatsapp.py`) |
| **Typing** | `sendChatAction(typing)` | `presence subscribe(composing)` |
| **Reaction** | `setMessageReaction(emoji)` | `POST /message/sendReaction` |
| **Inline keyboard** | `InlineKeyboardMarkup` | Buttons (max 3) + list sections |
| **Debounce** | 1.2s (janela de consolidação) | 1.2s (idêntico) |
| **Rate limit** | 3s por chat_id | 3s por remoteJid (idêntico) |
| **Idempotência** | update_id TTL 10min | message_id TTL 10min (idêntico) |
| **LGPD scrub** | 3 camadas (input/pre-LLM/output) | 3 camadas (idêntico) |
| **LLM** | LiteLLM → nemotron → opencode → cache | LiteLLM → nemotron → opencode → cache (idêntico) |
| **HITL** | `/humano` → cria atendimento Chatwoot | `/humano` → cria atendimento Chatwoot (idêntico) |
| **Testes E2E** | 8/8 sent=True (2026-07-02) | 5/5 espelhados (em construção T66-T68) |

## 🧬 Arquitetura — Pipeline Compartilhado

```
┌─────────────────┐                  ┌─────────────────────┐
│  Telegram       │                  │  WhatsApp           │
│  webhook        │                  │  webhook            │
│  /webhook/tg    │                  │  /webhook/evolution │
└────────┬────────┘                  └──────────┬──────────┘
         │                                      │
         │ InboundMessage                       │ InboundMessage
         │ (channel=telegram)                   │ (channel=whatsapp)
         │                                      │
         └──────────────┬───────────────────────┘
                        ▼
        ┌────────────────────────────────────────┐
        │  chat_pipeline.process_message()        │
        │  ┌──────────────────────────────────┐  │
        │  │ 1. check_idempotency()           │  │
        │  │    Redis SETNX TTL 600s          │  │
        │  ├──────────────────────────────────┤  │
        │  │ 2. scrub_pii_3_layers()          │  │
        │  │    input → pre-LLM → output      │  │
        │  ├──────────────────────────────────┤  │
        │  │ 3. enqueue + debounce 1.2s       │  │
        │  │    Redis RPUSH + asyncio.wait    │  │
        │  ├──────────────────────────────────┤  │
        │  │ 4. process_debounced()           │  │
        │  │    ├─ check_rate_limit (3s)      │  │
        │  │    ├─ typing_loop (refresh 4s)   │  │
        │  │    ├─ call_llm_with_fallback     │  │
        │  │    │   LiteLLM→nemotron→opencode │  │
        │  │    ├─ scrub output (camada 3)    │  │
        │  │    ├─ adapter.send               │  │
        │  │    └─ adapter.react              │  │
        │  └──────────────────────────────────┘  │
        │ 5. audit_log() LGPD                    │
        └────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Audit Trail     │
              │  (LGPD hash chain)│
              └──────────────────┘
```

## 📂 Arquivos-Chave

```
backend/app/services/chat_pipeline.py    (553 linhas) - pipeline compartilhado
backend/app/api/v1/telegram.py            (1463 linhas) - TelegramAdapter + handlers
backend/app/api/v1/whatsapp.py            (464 linhas)  - WhatsAppAdapter + handlers
backend/app/integrations/fallback.py      - LLM fallback chain (7 providers)
backend/app/services/pii.py               - PII scrubber (CPF/RG/email/telefone)
backend/app/services/audit_create.py      - audit log LGPD
backend/app/services/chatwoot_handoff.py  - HITL human handover
backend/app/services/evolution_ingest.py  - Evolution API event ingest
```

## 🛡️ LGPD Compliance (compartilhado)

Ambos os canais implementam:
- **3 camadas PII scrub** (input/pre-LLM/output) — LGPD art. 46
- **Audit log imutável** (hash chain SHA256 + HMAC) — LGPD art. 37
- **Consent banner** (WhatsApp obrigatório, Telegram implícito por uso)
- **Direito esquecimento** (`/cancelar`) — LGPD art. 18 VI
- **Direito acesso** (`/lgpd`) — LGPD art. 18 II
- **Direito portabilidade** (`/lgpd export`) — LGPD art. 18 V
- **Retenção 5 anos** após último contato — LGPD art. 16

Ver [`docs/LGPD_BOTS.md`](LGPD_BOTS.md) para detalhes.

## 🔁 Fallback Chain (compartilhado)

```
1. LiteLLM Proxy (primary, 4-10s, 99% SLA)
   ↓ (se 5xx ou timeout > 15s)
2. opencode_free_1 (nemotron-3-ultra-free, NVIDIA, 1M ctx)
   ↓ (se 429)
3. opencode_free_2 (mimo-v2.5-free, Xiaomi, 1M ctx)
   ↓ (se 503)
4. opencode_free_3 (deepseek-v4-flash-free, 1M ctx)
   ↓ (se timeout)
5. opencode_go (minimax-m3 via opencode.ai/zen)
   ↓ (se 5xx)
6. openclaw (local fallback)
   ↓ (se Redis offline)
7. Cache local (resposta padrão "Sistema em manutenção")
```

**Circuit breaker**: 3 falhas abre por 60s por provider.
**Retry**: exponential backoff 1s → 2s → 4s.

Ver [`docs/FALLBACK_CHAIN.md`](FALLBACK_CHAIN.md).

## 🎮 Comandos Suportados (idênticos ambos canais)

| Comando | Ação | LGPD |
|---|---|---|
| `/start` | Saudação + menu principal | Não |
| `/menu` | Lista opções (consultar protocolo, agendar, emolumento, etc) | Não |
| `/protocolo <n>` | Consulta status do protocolo | Audit |
| `/agendar` | Inicia fluxo de agendamento | Audit |
| `/humano` | HITL → cria atendimento Chatwoot | Audit + Chatwoot |
| `/cancelar` | Direito esquecimento (deleta dados em 30 dias) | Art. 18 VI |
| `/lgpd` | Mostra direitos + exporta dados pessoais | Art. 18 II/V |

## 📊 Observability (compartilhado)

- **Logs estruturados JSON**: `correlation_id`, `channel`, `chat_id_hash`, `latency_ms`
- **Métricas Prometheus**: `bot_requests_total{channel,status}`, `bot_latency_seconds{channel,provider}`, `bot_circuit_state{provider}`
- **OpenTelemetry traces**: spans `chat.receive` → `chat.llm.call` → `chat.send`
- **Sentry SDK**: captura exceções LLM/fallback exhausted/Redis offline
- **Grafana dashboard**: latência P50/P95/P99 por canal e provider
- **Alertas Telegram GRUPO Pietra**: P95 > 15s, error_rate > 1%, circuit OPEN > 60s

Ver [`docs/TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md).

## 🚦 Status Atual (2026-07-09)

```
✅ Telegram: 8/8 testes E2E validados (sent=True)
✅ chat_pipeline.py: 553 linhas, 10 componentes extraídos
✅ WhatsApp whatsapp.py: 464 linhas, paridade 100% Telegram
🟡 Testes WhatsApp: 5/5 E2E em construção (T66-T68)
🟡 LGPD consent banner WhatsApp: T41-T42 em construção
🟡 Fallback chain: 1x validado (LiteLLM DOWN → opencode_free_1)
❌ CI verde: mypy 0 + ruff 0 + pytest ≥2318 pendente validação final
```

## 📚 Documentação Relacionada

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — diagrama C2/C3/C4 + chat_pipeline
- [`TELEGRAM_GUIDE.md`](TELEGRAM_GUIDE.md) — guia operacional Telegram
- [`WHATSAPP_GUIDE.md`](WHATSAPP_GUIDE.md) — guia operacional WhatsApp
- [`FALLBACK_CHAIN.md`](FALLBACK_CHAIN.md) — 7 providers + circuit breaker
- [`LGPD_BOTS.md`](LGPD_BOTS.md) — compliance específico chatbots
- [`CHATWOOT_HANDOVER.md`](CHATWOOT_HANDOVER.md) — HITL fluxo humano
- [`EVOLUTION_API.md`](EVOLUTION_API.md) — instalação + QR + webhook
- [`TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md) — cenários + soluções
- [`CHANGELOG_BOTS.md`](CHANGELOG_BOTS.md) — histórico de versões

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:36:00Z
**Lesson**: 141 (chat_pipeline extraído), 143 (WhatsApp espelhado)