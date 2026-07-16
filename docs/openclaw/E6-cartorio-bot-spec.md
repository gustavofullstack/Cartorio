# E6 — OpenClaw CartorioBot Specification (G6.E.T6)

> **Status**: spec pronta — aguardando Gustavo provisionar (SUI-6)
> **Squad**: E (OpenClaw CartorioBot)
> **Versao**: 1.0 (2026-07-16)
> **Agente**: `cartorio-bot` (slug oficial)
> **Endpoint**: `wss://agent.2notasudi.com.br/v1/chat` (WebSocket only, lesson 64)

---

## Identidade

- **Nome**: cartorio-bot
- **Tipo**: assistant
- **Owner**: Gustavo Almeida (Cartorio 2o Notas Uberlandia)
- **Stack**: API+N8N+SUPABASE+REDIS+CHATWOOT+EVOLUTION+MCPS+TOOLS+PLUGINS+SKILLS+HOOKS

## Configuracao (openclaw.json)

```json
{
  "name": "cartorio-bot",
  "version": "1.0.0",
  "type": "assistant",
  "endpoint": "wss://agent.2notasudi.com.br/v1/chat",
  "owner": "gustavoalmeida",
  "system_prompt": "Voce eh o cartorio-bot, assistente oficial do 2o Tabelionato de Notas e Protesto de Uberlandia. Sempre use API+N8N+SUPABASE+REDIS+CHATWOOT+EVOLUTION+MCPS+TOOLS+PLUGINS+SKILLS+HOOKS para responder.",
  "providers": {
    "primary": "MiniMax-M3",
    "fallback": ["opencode-go", "mimo", "deepseek", "mistral-free", "openrouter-free", "gemini-free"],
    "no_network": "llama-3.1-8b-local"
  },
  "temperature": 0.2,
  "max_tokens": 2000,
  "context_window": 8000
}
```

## Tools (8 tools via OpenClaw)

1. **consultar_protocolo** — GET /api/v1/protocolo/{id}
2. **criar_protocolo** — POST /api/v1/protocolo (HITL required)
3. **consultar_emolumento** — GET /api/v1/emolumento/{tipo}
4. **agendar_atendimento** — POST /api/v1/agendamento
5. **lgpd_direitos** — POST /api/v1/lgpd/{direito} (7 direitos LGPD)
6. **consultar_cliente** — GET /api/v1/cliente/{cpf_hash}
7. **2_via_documento** — POST /api/v1/documento/segunda-via
8. **handoff_humano** — POST Chatwoot conversation (HITL obrigatorio LGPD)

## Skills (5 skills reusaveis)

1. **PII Scrubber** — mascara CPF/RG/email antes de enviar a LLM
2. **LGPD Consent Checker** — valida consentimento antes de qualquer ato
3. **Audit Logger** — append-only SHA256+HMAC chain
4. **Canned Response Matcher** — match contra 38 canned responses (28 v2 + 10 v3)
5. **HITL Router** — decide bot-vs-humano (consultar cenario)

## MCPS (3 MCPs integrados)

1. **cartorio_mcp_api** — wraps FastAPI endpoints
2. **cartorio_mcp_supabase** — wraps Supabase (Postgres + Storage + Auth)
3. **cartorio_mcp_chatwoot** — wraps Chatwoot REST API

## Hooks (4 hooks WebSocket)

1. **on_message_in** — PII scrub + audit log entry
2. **on_tool_call** — LGPD consent check + rate limit
3. **on_response_out** — canned response match + handoff decision
4. **on_error** — dead man's switch + Telegram GRUPO PIETRA alert

## Plugins (3 plugins)

1. **telegram_bridge** — Telegram bot @TestCartorioBot
2. **whatsapp_bridge** — Evolution API 2.3.7
3. **web_widget** — LobeChat embed

## Sub-processors (5 LLM providers via LiteLLM proxy)

| Provider | Status | Quando |
|---|---|---|
| MiniMax-M3 | OK (1o) | Default |
| opencode-go | OK (2o) | Default |
| mimo | BLOQUEADO | Sem DPA assinado |
| DeepSeek | OK (3o) | Fallback explicito |
| mistral-free | BLOQUEADO | Sem DPA assinado |
| openrouter-free | BLOQUEADO | Sem DPA assinado |
| gemini-free | BLOQUEADO | Sem DPA assinado |
| llama-3.1-8b-local | OK (4o) | Quando TODOS fallbacks falham |

## LGPD-by-design

- PII 3 camadas antes de qualquer chamada LLM
- Consentimento opt-in (cliente pode opor-se ao tratamento IA)
- HITL obrigatorio para atos juridicos (criar protocolo, escritura, etc)
- Audit log SHA256+HMAC chain imutavel
- Retencao 90 dias conversas IA

## Workflow de Deploy

1. Gustavo SSH no VPS Hostinger (Tailscale 100.99.172.84)
2. Copia este spec para `/home/node/.openclaw/openclaw.json`
3. Configura password no Control UI settings (SUI-5b)
4. Reinicia OpenClaw: `systemctl restart openclaw`
5. Verifica `/health` → 200
6. Testa WebSocket connection local
7. Configura routing no Traefik (router cartorio-bot)

## Compliance Checklist

- [ ] SSH VPS Hostinger (Gustavo)
- [ ] openclaw.json deploy (Gustavo)
- [ ] Password configurado (Gustavo)
- [ ] WebSocket test 200 OK
- [ ] Traefik router criado
- [ ] Telegram GRUPO PIETRA recebe alerts
- [ ] Audit log primeiro append
- [ ] Canned responses match (38 templates)

---

**Modified by Gustavo Almeida + cartorio-llm — G6 wave 9 (E6 cartorio-bot spec)**