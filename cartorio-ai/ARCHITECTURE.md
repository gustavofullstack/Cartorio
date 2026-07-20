# cartorio-ai · ARCHITECTURE

## Posição no repositório

```
Cartorio/
├── AGENTS.md                 # spec compacto (fonte de verdade operacional)
├── SUPER_PLANO_G9_100_TASKS.md  # plano ativo (100 tasks / 25 squads)
├── backend/                  # FastAPI app (código de produção)
│   ├── app/api/v1/           # routers: telegram, lgpd (Art.18 + cnj-exports), auth, BRAIN
│   ├── app/services/         # audit*, pii.py, emolumento.py, lgpd*, cartorio_agent.py
│   ├── app/models/           # SQLAlchemy 2.0 typed (cliente, conversa, protocolo, audit_log...)
│   └── mcp_server.py         # FastMCP montado em /mcp
├── .harness/                 # orquestrador + 9 reins + STANDARDS + memory cross-rein + TASKS.md
├── .brain/                   # loop-state, api-specs, memory diária (YYYY-MM-DD.md)
├── infra/                    # n8n-workflows, supabase, dns, traefik, lobechat
├── docs/                     # ARCHITECTURE (C4+ADRs), ROADMAP 12 semanas, runbooks, SUI packs
├── scripts/                  # operação: deploy, backup, check_no_literal_keys.py
└── cartorio-ai/              # ESTE pacote: identidade/memória/governança (docs, não código)
```

## Integrações externas (produção — EasyPanel + Docker Swarm + Traefik)

| Serviço | Papel | Domínio |
|---|---|---|
| cartorio_api | backend FastAPI | api.2notasudi.com.br |
| Evolution 2.3.7 | WhatsApp (QR pendente — `state=close`) | whatsapp.2notasudi.com.br |
| N8N | workflows/automação | flow.2notasudi.com.br (DNS pendente G9.16) |
| Chatwoot 3.x | handoff humano (precisa pgvector) | chat.2notasudi.com.br (DNS pendente) |
| OpenClaw 0.4.x | agente LLM | agent.2notasudi.com.br |
| Supabase | Postgres 16 self-hosted | supbase.2notasudi.com.br (typo ACEITO) |

## Fluxos críticos

1. **Telegram webhook** — `POST /api/v1/telegram/webhook` exige header
   `X-Telegram-Bot-Api-Secret-Token` (401 sem ele; sempre-200 nos demais casos — regra G9).
   Re-sync via `POST /api/v1/telegram/set-webhook` com `X-API-Key` (commit `96fedc9`).
   Debounce async 1.2s por `chat_id:user_id` (regressão A5: metadata estava por `chat_id`).
2. **LLM chain** — `cartorio_agent.py`: 3 contas OpenCode Zen (free slots 1/2/3) com fallback;
   PII scrub pré-LLM obrigatório; output scrub (LGPD-015) no G9 Squad 06.
3. **CNJ export** — `/api/v1/lgpd/cnj-exports/massive-dump`: streaming `yield_per(1000)`,
   API key + JWT DPO, scrub de payload, audit gate; dupla aprovação DPO no fluxo com pedido.
4. **Audit chain** — append-only SHA256+HMAC; dead-man's switch a cada 15min; retenção LGPD 03:00 BRT.

## Middleware chain (ordem importa)

`RequestContext → Idempotency → RateLimitByKey → RateLimit → SlowLog → CORS`
