# Skills Index — Cartório 2º Notas Uberlândia (G7 Wave 15)

> **Catálogo central** de skills em `.agents/skills/`.  
> **Integração total** mapeada em `docs/INTEGRATION_MATRIX_G7.md`.  
> **Última atualização**: 2026-07-16 (G7.15.T1)

## Legenda

| Tag | Categoria |
|---|---|
| `LLM` | LLMs, agentes de IA |
| `INFRA` | VPS, Docker Swarm, deploy |
| `DATABASE` | Postgres, Redis, Supabase |
| `MONITORING` | Prometheus, Sentry, Grafana |
| `NETWORKING` | Tailscale, DNS, proxy |
| `SECURITY` | LGPD, PII, audit |
| `WORKFLOW` | N8N, orquestração |
| `INTEGRATION` | WhatsApp, Telegram, Chatwoot, API |
| `OPS` | Operação, runbooks |
| `AGENT` | Multi-agent / OpenClaw |

---

## Catálogo (12 skills)

| Skill | Categoria | Status | Descrição | Path |
|---|---|---|---|---|
| `api` | INTEGRATION | ✅ | FastAPI REST + WS + MCP cartorio (radar, LGPD, Telegram) | [api/SKILL.md](api/SKILL.md) |
| `chatwoot` | INTEGRATION | 🟡 | CRM handoff (prod 502/DNS HOLD) | [chatwoot/SKILL.md](chatwoot/SKILL.md) |
| `n8n` | WORKFLOW | 🟡 | 37 WFs; flow path 404 HOLD | [n8n/SKILL.md](n8n/SKILL.md) |
| `supabase` | DATABASE | ✅ | Postgres self-hosted + RLS | [supabase/SKILL.md](supabase/SKILL.md) |
| `easypanel` | INFRA | ✅ | Deploy Swarm / env UI | [easypanel/SKILL.md](easypanel/SKILL.md) |
| `hostinger` | INFRA / NETWORKING | 🟡 | VPS + Tailscale (TS offline 2d+) | [hostinger/SKILL.md](hostinger/SKILL.md) |
| `minimax-m3` | LLM | ✅ | MiniMax-M3 via LiteLLM | [minimax-m3/SKILL.md](minimax-m3/SKILL.md) |
| `coding-vps-21` | AGENT / LLM | ✅ | 21+ coding agents | [coding-vps-21/SKILL.md](coding-vps-21/SKILL.md) |
| `coding-vps-tools-100` | INFRA | ✅ | Catálogo ~62 tools MCP (nome histórico 100) | [coding-vps-tools-100/SKILL.md](coding-vps-tools-100/SKILL.md) |
| `coding-vps-orchestrator` | AGENT | ✅ | MCP orchestrator CLI/HTTP | [coding-vps-orchestrator/SKILL.md](coding-vps-orchestrator/SKILL.md) |
| `coding-vps-deploy` | INFRA | ✅ | Deploy agents Docker | [coding-vps-deploy/SKILL.md](coding-vps-deploy/SKILL.md) |
| `coding-vps-monitor` | MONITORING | ✅ | Health 89 serviços | [coding-vps-monitor/SKILL.md](coding-vps-monitor/SKILL.md) |

---

## Mapa skill → stack G7

| Stack layer | Skill(s) | Harness rein |
|-------------|----------|--------------|
| API / Swagger / Postman | `api` | cartorio-dev |
| Telegram / WhatsApp | `api` + `n8n` | cartorio-evolution / n8n |
| Chatwoot handoff | `chatwoot` | cartorio-n8n |
| LobeChat / OpenClaw | `minimax-m3` + `api` | cartorio-dev |
| Redis / Postgres | `supabase` | cartorio-data / dev |
| MCP tools | `api` + coding-vps-* | cartorio-dev |
| DNS / Tailscale / Proxy | `hostinger` + `easypanel` | cartorio-sre |
| Brain / harness | (repo `.brain` + `.harness`) | all reins |
| LGPD | (code + docs/lgpd) | cartorio-lgpd |

**OpenClaw cartorio-bot config (não é skill folder):**  
`infra/openclaw/cartorio-bot.openclaw.json` + `docs/openclaw/E6-cartorio-bot-spec.md`

---

## Super orquestração

| Artefato | Uso |
|----------|-----|
| `SUPER_PLANO_G7_100_TASKS.md` | 100 tasks / 25 squads |
| `SUPER_GOALS_G7.md` | goals G7.1–G7.12 |
| `scripts/g7_super_validator.py` | `make g7-validate` |
| `docs/G7_SUI_WAVE14_CHECKLIST.md` | SUI Gustavo |
| `.harness/loop-engineer/` | cron + state machine |

---

## Como adicionar skill

1. `mkdir -p .agents/skills/<name>`
2. `SKILL.md` com frontmatter (`name`, `description`)
3. Atualizar **esta** tabela
4. Cross-ref em `docs/INTEGRATION_MATRIX_G7.md` se tocar canal prod

---

**Modified by Gustavo Almeida — G7.15.T1 Wave 15 (2026-07-16)**
