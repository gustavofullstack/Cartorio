# AGENT_REGISTRY

Registro de agentes do projeto (estado 2026-07-20).

## Agentes de atendimento (prod)

| Agente | Canal | Runtime | Estado |
|---|---|---|---|
| Pietra Cartório (bot) | Telegram `@test_cartorio_bot` | FastAPI + cartorio_agent | ✅ validado 2026-07-20 (`/start` → `response_sent=true`) |
| Pietra Cartório (bot) | WhatsApp (Evolution API) | FastAPI + n8n | ⏸ aguardando QR (SUI, ação do dono) |
| Atendimento humano | Chatwoot 4.x | Swarm service | ✅ 1/1 (handoff HITL) |

## Reins de engenharia (`.harness/`)

| Rein | Escopo | Acionado quando |
|---|---|---|
| `cartorio-dev` | Backend FastAPI, SQLAlchemy, audit, PII | Mudança em `backend/app/` |
| `cartorio-n8n` | Workflows n8n, Evolution, OpenClaw, multi-canal | Workflow ou deploy de canal |
| `cartorio-lgpd` | LGPD, RIPD, retenção, erasure, privacy | Qualquer mudança tocando PII, `audit*`, `pii*` |

## Regras de colaboração

- Mudança em `audit*`/`pii*`: `cartorio-dev` implementa + `cartorio-lgpd` revisa e assina.
- Workflow n8n que toca PII: `cartorio-n8n` implementa + `cartorio-lgpd` revisa.
- Orquestrador delega com role label único (ex.: `A4_Docs_Expansion`), contexto e missão explícitos.
- Subagents não falam com o usuário final nem comitam — entregam relatório ao orquestrador.

## Ciclo de vida

Spawn (prompt com role+contexto+missão) → execução bounded → relatório → validação do orquestrador → integração. Heartbeat e supervisão em `agents/HEARTBEAT.md` e `agents/SUPERVISION.md`.
