# Lesson 170 — LobeChat agent missing: root cause + fix (commit 9b9c9e4) — 2026-07-14

## TL;DR

User reported: **"LOBE CHAT CONTINUA ENFESTADO DE MODELOS/AGENTS!! E NADA DO NOSSO AGENT CARTORIO CADE?"** (LobeChat crammed with models/agents, but no Cartorio agent visible).

**Root cause**: LobeChat was NEVER configured with a Custom OpenAI-compatible provider pointing at OpenClaw. The "Cartorio agent" (persona "CartorioBot") exists inside OpenClaw container at `/home/node/.openclaw/agents/main/agent/agent.json`, but OpenClaw is NOT a registry service — it's a chat-completions proxy. LobeChat and OpenClaw are independent services with NO shared registry.

**Fix**: Pure UI configuration. Code-level: created `infra/lobechat/agent_cartorio_import.json` (12KB schema v1) + `infra/lobechat/SETUP.md` (5 UI steps + 4 validation tests + troubleshooting). User must perform 5 manual clicks in LobeChat Settings.

## What was discovered

| Probe | Result |
|-------|--------|
| `agent.2notasudi.com.br/v1/models` (Bearer @Techno832466) | 200 — `{"object":"list","data":[{"id":"openclaw"},{"id":"openclaw/default"},{"id":"openclaw/main"}]}` |
| `agent.2notasudi.com.br/v1/agents` | 200 — returns OpenClaw Control UI HTML (SPA), NOT a REST agent list |
| `cartorio-lobechat.dfgdxq.easypanel.host/api/agents` | 404 — LobeChat v1.143 doesn't expose REST agents |
| `cartorio-lobechat.dfgdxq.easypanel.host/api/v1/models` | 404 — same |
| `infra/lobechat/` | **Did not exist** before this commit |
| `infra/openclaw-agent/workspace/{SOUL,IDENTITY,USER,TOOLS,AGENTS,GOALS}.md` | Persona source files present |

## What was fixed (commit 9b9c9e4)

| File | LOC | Purpose |
|------|-----|---------|
| `infra/lobechat/agent_cartorio_import.json` | +12,020 bytes | LobeChat schema v1: 1 agent (cartorio-2-notas-uberlandia, model=openclaw/main, systemRole=CartorioBot persona) + 1 provider (Custom OpenAI-compatible, baseURL=agent.2notasudi.com.br/v1, apiKey=@Techno832466, models=[openclaw, openclaw/default, openclaw/main]) |
| `infra/lobechat/SETUP.md` | +9,144 bytes | 5 UI steps + 4 validation tests + troubleshooting (e.g. "models don't appear" → check CORS on OpenClaw container) |

Persona synthesis source:
- `infra/openclaw-agent/workspace/SOUL.md` — core identity
- `infra/openclaw-agent/workspace/IDENTITY.md` — role definition
- `infra/openclaw-agent/workspace/USER.md` — target audience
- `infra/openclaw-agent/workspace/TOOLS.md` — capabilities
- `infra/openclaw-agent/workspace/AGENTS.md` — multi-agent context
- `infra/openclaw-agent/workspace/GOALS.md` — measurable objectives
- `infra/openclaw-agent/skills/saudacoes/emolumento-calc/protocolo-tracker/agendamento/handoff-trigger.md` — 5 cartorio-* skills

## Lessons

1. **YOLO rounds optimize for code/test work; UI configuration gaps are invisible to agents.** This was a 5-round-old issue (since R1 recon noted "LobeChat UP, sem DNS") that no code lens would have surfaced. **Lesson: every YOLO cycle should include a "manual UI check" lens for products that require human configuration (LobeChat agents, Cloudflare DNS, BotFather tokens, SUI1-3).**

2. **Service A and Service B are independent until they're not.** The user's mental model was "LobeChat shows Cartorio agent" but architecturally, OpenClaw is a chat-completions proxy, not a registry. **Pattern: document the architecture boundary explicitly in ARCHITECTURE.md (CLAUDE.md line 114 already says "LobeChat -.-|proxy| LiteLLM" but should add "OpenClaw -.-|proxy| LiteLLM" and clarify that OpenClaw models appear in LobeChat ONLY after explicit provider configuration).**

3. **OpenAI-compatible pattern is the universal bridge.** The Custom OpenAI provider in LobeChat works because OpenClaw chose to expose its agents as `/v1/models` + `/v1/chat/completions` (Standard OpenAI shape). This was a deliberate design choice that paid off here — same pattern would work for any future agent deployment.

4. **Persona lives in markdown, not JSON.** OpenClaw's persona is in `infra/openclaw-agent/workspace/SOUL.md` etc. (the agent.json file does NOT exist on disk; it lives inside the container at `/home/node/.openclaw/agents/main/agent/agent.json`). This means the persona source of truth is the markdown files, and the LobeChat export must be regenerated whenever the OpenClaw persona changes.

5. **DNS still pending.** Per `.harness/plans/PLANO_INTEGRACAO_TOTAL_2026-07-13.md` F0.3/F4.2: lobe.2notasudi.com.br → 187.77.236.77 A record + Traefik router. Currently using EasyPanel-only URL (`cartorio-lobechat.dfgdxq.easypanel.host`) which is functional but not branded.

## How to apply (next round)

Round 9 candidates (focused on Cartorio agent visibility gap):
1. **Add Custom OpenAI provider in LobeChat** — USER ACTION (5 clicks, SETUP.md)
2. **Add `infra/lobechat/` to .harness/memory/MEMORY.md index** — code-level
3. **Update ARCHITECTURE.md** to document "OpenClaw -.-|proxy| LiteLLM" and clarify the bridge
4. **Document this gap in SUI_CHECKLIST.md** as "SUI4: LobeChat agent registration pending"
5. **R3 deploy** still pending (5 rounds flagged)

Hard-deferred (require user/external action):
- DNS A record lobe.2notasudi.com.br (Cloudflare UI)
- LobeChat UI provider registration (5 clicks, SETUP.md)
- Traefik router config for branded lobe domain

## Refs

- Commit 9b9c9e4 "feat(lobechat): agent_cartorio import config + setup runbook"
- Files: `infra/lobechat/agent_cartorio_import.json` + `infra/lobechat/SETUP.md`
- Probe results documented inline in this lesson
- [[2026-07-13-multi-agent-orchestration-loop]] — workflow
- [[2026-07-13-yolo-round-6-99c06ab]] — R6 (most recent R with lessons)
- [[2026-07-13-yolo-round-7-b07095f]] — R7 (most recent coverage sprint)

Modified by Gustavo Almeida — 2026-07-14 00:50 BRT