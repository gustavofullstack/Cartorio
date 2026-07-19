# Integration Matrix G7 — Stack Completo (Wave 15)

> **Arquitetura e histórico de Wave 15.** Para estado runtime corrente e datado,
> consulte [`RUNTIME_STATUS_2026-07-19.md`](RUNTIME_STATUS_2026-07-19.md). Os
> indicadores “Prod” abaixo representam a evidência disponível na Wave 15, não uma
> declaração de disponibilidade atual.

Mapa **driver de arquitetura** da integração total pedida no super plano.
Status live: 2026-07-17 Wave 32 (radar red 4↑3↓ · DNS soft 7/7 · N8N exports **38**).

---

## 1. Diagrama lógico (C4 L2 compacto)

```
                    ┌──────────── Cloudflare DNS / Traefik ────────────┐
                    │  api · agent · chat · flow · whatsapp · easypanel │
                    └───────────────┬──────────────────────────────────┘
                                    │
     ┌──────────┐   webhook    ┌────▼─────┐   tools    ┌─────────────┐
     │ Telegram │─────────────►│ FastAPI  │◄──────────►│ OpenClaw    │
     │ Bot      │              │ cartorio │   MCP/WS   │ agent.2notas│
     └──────────┘              │ + MCP    │            └──────┬──────┘
     ┌──────────┐   dual fmt   │ + WS     │                   │
     │ Evolution│─────────────►│          │            ┌──────▼──────┐
     │ WhatsApp │              └────┬─────┘            │ LobeChat UI │
     └──────────┘                   │                  └─────────────┘
     ┌──────────┐   handoff    ┌────▼─────┐
     │ Chatwoot │◄─────────────│  N8N 38  │
     └──────────┘              │ workflows│
                               └────┬─────┘
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
               ┌────────┐     ┌─────────┐     ┌──────────┐
               │ Redis 8│     │Postgres │     │ Skills / │
               │ SETNX  │     │Supabase │     │ harness  │
               └────────┘     └─────────┘     └──────────┘
```

---

## 2. Matriz componente × status

| Componente | Protocolo | Auth | PII | Prod | Agent task |
|------------|-----------|------|-----|------|------------|
| FastAPI | HTTPS REST | X-API-Key / JWT | 3-layer | 🟢 | G7.01 |
| Swagger/OpenAPI | HTTPS | try-it-out | scrub | 🟢 | G7.17 |
| Postman | collection | vars | — | 🟢 paths fixed W15 | G7.17 |
| Radar | GET | public | no | 🟡 red partial | G7.18 |
| WebSocket atendimentos | WSS | key | yes | 🟢 via API | G7.10 |
| Telegram webhook | HTTPS | secret_token | yes | 🔴 token HOLD | G7.03 |
| Evolution webhook | HTTPS | HMAC | yes | 🔴 502 | G7.04 |
| Chatwoot | HTTPS | api_token | yes | 🔴 502/DNS | G7.05 |
| LobeChat | HTTPS | OPENAI_KEY | scrub | 🟡 key HOLD | G7.06 |
| OpenClaw | WS+REST | bearer | scrub | 🟢 gateway / bot HOLD | G7.14 |
| Redis | TCP internal | — | no raw PII | 🟢 | G7.07 |
| Postgres/Supabase | TCP | scram | yes | 🟢 | G7.08 |
| MCP `/mcp` | HTTP | — | tool-scoped | 🟡 mount | G7.09 |
| N8N | HTTPS | API key | env | 🟡 flow 404 | G7.07 |
| Tailscale | WireGuard | ACL | — | 🔴 offline | G7.11 |
| DNS Cloudflare | A/AAAA | UI | — | 🟡 3 NXDOMAIN | G7.12 |
| Brain/Harness | files+API | — | no | 🟢 | G7.16 |
| Skills | markdown | — | — | 🟢 | G7.15 |
| CI/CD | GHA | secrets | scrub | 🟢 | G7.22 |

---

## 3. Princípios (SOLID / DRY / KISS / tipagem)

| Princípio | Aplicação no cartório |
|-----------|----------------------|
| **S** | Services por domínio (`audit`, `pii`, `emolumento`, `lgpd_*`) — não god-router |
| **O** | Novos canais = adapter webhook + shared pipeline, sem fork de scrub |
| **L** | Protocolo HITL: bot nunca substitui escrevente em ato jurídico |
| **I** | MCP tools finas (emolumento ≠ erase LGPD) |
| **D** | LiteLLM/OpenClaw atrás de interface provider; conftest isola testes |
| **DRY** | `truncate_ip` único; `audit_kwargs`; dual-format Evolution parse shared |
| **KISS** | SETNX 24h > saga distribuída; DRAFT + HITL > workflow 40 nodes |
| **Tipagem** | mypy strict `app/`; Pydantic v2 schemas em endpoints; `Mapped[]` ORM |

---

## 4. Super teste (ordem)

```bash
make g7-validate          # composite
make radar-smoke          # prod radar (+fallback)
make openapi-check        # contract
make n8n-validate         # WF rules
cd backend && uv run pytest -q --no-cov tests/test_audit.py tests/test_ip_truncation.py
PYTHONPATH=. uv run --directory backend pytest ../.brain/api-specs/test_catalog.py -q --no-cov
```

---

## 5. Scrum / MVP cut-line

**MVP (agora):** consulta emolumento + status protocolo read + handoff humano + audit/PII.  
**Não-MVP ainda:** emissão certidão autônoma, pagamento online, multi-cartório SaaS.

Board: `SUPER_PLANO_G7_100_TASKS.md` · Goals: `SUPER_GOALS_G7.md` · SUI: `docs/G7_SUI_WAVE14_CHECKLIST.md`

---

**Modified by Gustavo Almeida + Pietra orquestrador — G7 Wave 15**
