# Status Telegram + MiniMax Coding Plan — auditoria 100%

**Data:** 2026-07-10  
**Foco:** entrega teste bot Telegram (WhatsApp depois)

---

## 1. Ambiente (papo reto)

| Componente | Estado | Nota |
|------------|--------|------|
| cartorio_api | **1/1 UP** | Agent MiniMax-M3 |
| Redis | online | hist + perfil cliente |
| Supabase/PG | online | HITL atendimentos |
| OpenClaw | online | opcional |
| Chatwoot | online | CRM |
| LiteLLM coding-vps | **1/1** | master key `e39dss…` OK |
| MiniMax API direta | **200 OK** | sk-cp Coding Plan |
| N8N | offline | **nao bloqueia** Telegram |
| Evolution WhatsApp | **0/1** | hold proposital |
| Radar API | red | n8n+evolution |

### MiniMax Coding Plan — o que **ja** esta integrado

| Capacidade | Status | Como |
|------------|--------|------|
| MiniMax-M3 chat | **LIVE** | `minimax_direct` + fallback LiteLLM |
| XMax Thinking | **ON** | `thinking: adaptive` + strip `<think>` |
| Tool calling (4 tools) | **LIVE** | catalogo, preco, info, iniciar_fluxo |
| TTS Speech | **LIVE** | `/voz` → `speech-2.6-turbo` sendVoice |
| STT (voz→texto) | **parcial** | voice ack; STT full backlog |
| Multimodal imagem | **nao** | backlog (foto doc) |
| Video Hailuo | **nao** | fora de escopo cartorio |
| Music | **nao** | n/a |

Docs oficiais usadas:
- https://platform.minimax.io/docs/api-reference/text-openai-api  
- https://platform.minimax.io/docs/api-reference/speech-t2a-http  
- Tool Use / Interleaved Thinking (M3)

### Gaps ate “100% papo reto”

1. STT: aceitar voice note e transcrever (ASR MiniMax se disponivel no plano, senao Whisper self-host)  
2. Agent sempre tools (loop 3 rounds) — **feito**  
3. Foto de documento (image_url MiniMax-M3)  
4. Preco sempre via tool (nao inventar) — **feito**  
5. Evolution WhatsApp so apos TG validado  
6. OpenClaw 1M context como 2a camada (opcional)  
7. Painel/N8N se quiser orquestrar UI  

---

## 2. Comportamento bot (pos fixes)

| User diz | Esperado |
|----------|----------|
| Oi / free text | MiniMax Agent (tools se preciso) |
| quanto custa X | tool preco → valor oficial |
| Tudo bem? | smalltalk curto |
| Muito grosso | desculpa humana |
| Audio voice | ack + pedir texto; `/voz` depois |
| /voz | TTS MiniMax da ultima resposta |
| CPF | LGPD ack + hash Redis |

---

## 3. Score estimado entrega teste TG

| Area | % |
|------|---|
| Infra webhook/API | 98 |
| Agent MiniMax real | 85 → **92** (tools+direct) |
| LGPD/dados | 95 |
| Formatação/anti-spam | 95 |
| Voz TTS | 70 (STT falta) |
| HITL/agendar FSM | 90 |
| WhatsApp | 0 (hold) |
| **Telegram pronto p/ validacao humana** | **~90%** |

Modified by Gustavo Almeida
