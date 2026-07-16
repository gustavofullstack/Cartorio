# Lesson 186 — G6 Wave 13 + SUPER GOALS/PLANO G7 (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com super plano 100 tasks, super goals, 4 agents/squad,
loop até 100, integração total (API/Telegram/Chatwoot/LobeChat/Redis/Postgres/
MCP/WS/webhooks/Tailscale/proxy/DNS/OpenClaw/skills/brain/harness/Postman/
Swagger/radar + SOLID/DRY/KISS/CI/CD).

**Estado real pré-wave:** G6 waves 1-12 + commits extras (idempotency injector,
Loki) já em master; pytest ~2976+; prod radar red parcial (n8n/evo/chatwoot
offline); `/radar/expanded` **404 em prod** (código local existe, imagem antiga).

**Reality check (Lesson 185):** projeto prefere 1-2 agents paralelos reais;
orquestramos 4 *slots* (dev/n8n/lgpd/sre) no mesmo ciclo sequencial/paralelo
de arquivos.

## Wave 13 — 4 tasks × 4 reins

| Slot | Task | Rein | Entrega |
|------|------|------|---------|
| A1 | **G6.A.T7 / G7.01.T3** | cartorio-dev | `tests/test_audit_mutation_killers_g6.py` — hash/HMAC/canonical/D5 dual-IP/verify edges |
| A2 | **G6.D.T6 / G7.18.T2** | cartorio-sre | CANAL_HEALTH_MATRIX live 2026-07-16 + radar domains 12 DNS + smoke fallback `/radar` |
| A3 | **G6.C.T1 / G7.19.T1** | cartorio-lgpd | RIPD v1.4 + `docs/lgpd/RIPD_v1.4_ADDENDUM.md` (T13–T18) |
| A4 | **G6.C.T4 / G7.02.T2** | cartorio-lgpd | D5 IP regression tests (payload never leaks full IP) |

### Artefatos de orquestração G7
- `SUPER_GOALS_G7.md` — 12 goals + sprints S0–S9 + DoD
- `SUPER_PLANO_G7_100_TASKS.md` — 25 squads × 4 = 100 tasks
- `scripts/radar_smoke.py` — fallback 404 expanded → classic radar

## Validação

```
pytest mutation_killers + ip_truncation + health_radar_expanded + audit → 75 passed
radar_smoke → WARN 404 expanded, fallback /radar status=red (4 up / 3 down)
```

## Prod live (não inventado)

| Probe | Resultado |
|-------|-----------|
| `GET /health` | 200 ok v0.6.0 |
| `GET /health/radar` | red: db/redis/openclaw/supabase online; n8n/evo/chatwoot offline |
| `GET /health/radar/expanded` | **404** (redeploy pendente) |
| api/agent/easypanel | 200 |
| whatsapp/chat | 502 |
| flow/supbase | 404 |
| chatwoot/n8n/supabase DNS | NXDOMAIN |

## Lições cross-project

1. **Código em master ≠ prod** — expanded radar e testes verdes locais; prod 404 até redeploy Swarm/EasyPanel. Smoke scripts **devem** ter fallback.
2. **Radar "red" com db/redis up** — overall red se qualquer integração offline; não confundir com "API morta".
3. **Mutation killers unitários** matam mutantes de `_compute_hash`/`_compute_hmac` sem re-rodar mutmut full (caro). Report mutmut 73% ainda válido até re-run.
4. **4 agents/squad** = 4 *tasks com rein owner*, não necessariamente 4 processos LLM simultâneos (regra 1-2 paralelos).
5. **G7 plano 100** não reimplementa G6: herda done e lista só gaps de integração total + SUI.

## SUI Gustavo (ainda bloqueia green)

1. 3 A records Cloudflare (chatwoot/n8n/supabase)
2. DATABASE_URL evolution/chatwoot/n8n no Easypanel
3. Redeploy API (expanded radar)
4. Telegram token BotFather
5. LobeChat OPENAI_API_KEY
6. WhatsApp QR
7. OpenClaw cartorio-bot + operator scopes
8. DPA MiniMax assinatura

## Próxima wave (W14)

G7.18.T1 redeploy expanded · G7.12.T1 DNS · G7.04.T1 Evolution env · G7.03.T1 Telegram token  
(3/4 SUI-assisted — agent prepara runbook/checklists; Gustavo executa UI)

**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16**
