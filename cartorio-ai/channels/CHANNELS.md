# CHANNELS

Canais de atendimento (estado validado 2026-07-20).

## Matriz de canais

| Canal | Identificador | Estado | Observações |
|---|---|---|---|
| Telegram | `@test_cartorio_bot` | ✅ prod validado | `/start` real → `response_sent=true`; webhook secret OK; `pending=0` |
| WhatsApp | Evolution `cartorio-2notas` | ⏸ QR pendente | Canal oficial futuro; parser dual-format pronto |
| WebChat | site 2notasudi.com.br | ✅ via API | Mesmo pipeline do Telegram |
| Chatwoot | chat.2notasudi.com.br | ✅ handoff humano | DNS A record pendente (SUI) |

## Regras por canal

- **Telegram**: `parse_mode=HTML` — output LLM com tags `think`/`reasoning` quebra o parser (502 silencioso); sanitizar antes de enviar. Debounce 1.2s por `chat_id:user_id`. Não poluir chats com mensagens de teste.
- **WhatsApp**: TTL rígido 24h de mensagens; retenção validada em staging; ativação depende de QR (ação do dono, runbook `docs/WA_EMOLUMENTO_LIVE_SUI_G7.md`).
- **Handoff**: qualquer canal → Chatwoot; takeover humano = mute imediato do bot (registrado em audit).

## Política de resposta

- Idioma PT-BR, tom profissional cartorário; disclaimer jurídico em todo ato orientativo.
- Nunca ecoar CPF/RG/protocolo raw — sempre mascarado (`***.***.***-**`).
- Silêncio nunca é resposta: falha de LLM → mensagem de degradação amigável.
- Horário de atendimento humano e SLA em `channels/BUSINESS_HOURS.md` e `channels/SLA.md`.
