# cartorio-ai · INDEX

Índice navegável do pacote. Núcleo preenchido em 2026-07-20 (sessão C4); **registries de
domínio preenchidos em 2026-07-20 (sessão A4)**. Arquivos fora desta lista seguem placeholders —
ver `ROADMAP.md`.

## Raiz
- [AGENTS.md](AGENTS.md) — regras de operação dos agentes, P0, reins, comandos.
- [README.md](README.md) — visão geral do pacote e estado do projeto.
- [ARCHITECTURE.md](ARCHITECTURE.md) — mapa do repo, integrações, fluxos críticos.
- [MANIFEST.md](MANIFEST.md) — inventário, status, escopo.
- [BOOTSTRAP.md](BOOTSTRAP.md) — onboarding de agente novo (<10 min).
- [ROADMAP.md](ROADMAP.md) — expansão futura do layout (~400 arquivos).

## Núcleo (C4)
- [brain/BRAIN.md](brain/BRAIN.md) — workflow obrigatório, honesty gate, gestão de contexto.
- [identity/SOUL.md](identity/SOUL.md) · [identity/IDENTITY.md](identity/IDENTITY.md) — propósito, valores, tom de voz.
- [planning/GOALS.md](planning/GOALS.md) · [planning/TASKS.md](planning/TASKS.md) — metas G9 e ponte para o SUPER PLANO.
- [memory/MEMORY.md](memory/MEMORY.md) — fatos-chave 2026-07-20 e ponteiros de memória.
- [security/SECURITY.md](security/SECURITY.md) — segredos, PII, audit chain.
- [compliance/CNJ.md](compliance/CNJ.md) — export CNJ, DPO, hash chain.

## Registries de domínio (A4, 2026-07-20)
- [governance/GOVERNANCE.md](governance/GOVERNANCE.md) — autoridade L0–L3, gates formais.
- [knowledge/KNOWLEDGE_BASE.md](knowledge/KNOWLEDGE_BASE.md) — fontes canônicas e prioridade.
- [execution/EXECUTION_ENGINE.md](execution/EXECUTION_ENGINE.md) — topologia VAIO/VPS/MacBook, ciclo de mudança.
- [agents/AGENT_REGISTRY.md](agents/AGENT_REGISTRY.md) — agentes prod + reins de engenharia.
- [skills/SKILL_REGISTRY.md](skills/SKILL_REGISTRY.md) — skills de projeto e de domínio.
- [tools/TOOL_REGISTRY.md](tools/TOOL_REGISTRY.md) — ferramentas SSH/banco/qualidade/obs.
- [mcp/MCP_REGISTRY.md](mcp/MCP_REGISTRY.md) — servidor `/mcp` (FastMCP, 14 tools), regras de segurança.
- [integrations/INTEGRATIONS.md](integrations/INTEGRATIONS.md) — matriz Telegram/Evolution/n8n/Chatwoot/OpenClaw/Supabase/Redis.
- [runtimes/RUNTIMES.md](runtimes/RUNTIMES.md) — runtimes, matriz de capacidade por nó, uv.
- [commands/COMMANDS.md](commands/COMMANDS.md) — Makefile canônico + comandos do bot.
- [hooks/HOOKS.md](hooks/HOOKS.md) — hooks de mensagem, engenharia e lifespan.
- [events/EVENTS.md](events/EVENTS.md) — barramento, eventos de domínio, garantias.
- [workflows/WORKFLOW_REGISTRY.md](workflows/WORKFLOW_REGISTRY.md) — workflows n8n + fluxos internos.
- [channels/CHANNELS.md](channels/CHANNELS.md) — matriz de canais e regras por canal.
- [cartorio/CARTORIO.md](cartorio/CARTORIO.md) — núcleo de domínio notarial, regras de ouro.
- [guardrails/GUARDRAILS.md](guardrails/GUARDRAILS.md) — hard/soft limits, anti-alucinação.
- [models/MODEL_REGISTRY.md](models/MODEL_REGISTRY.md) — 3 contas zen, fallback chain, circuit breaker, timeout 45s.
- [prompts/PROMPTS.md](prompts/PROMPTS.md) — hierarquia e composição de prompts.
- [contracts/CONTRACTS.md](contracts/CONTRACTS.md) — contratos HTTP/mensagem/persistência/LLM.
- [observability/OBSERVABILITY.md](observability/OBSERVABILITY.md) — métricas, tracing, alertas, LGPD em telemetria.
- [evaluation/EVALS.md](evaluation/EVALS.md) — baterias, markers de regressão, gates.
- [operations/RUNBOOK.md](operations/RUNBOOK.md) — acessos bounded, incidentes, rotinas.
- [autonomy/AUTONOMY.md](autonomy/AUTONOMY.md) — níveis A0–A3, kill switch, stop conditions.
- [recovery/RECOVERY.md](recovery/RECOVERY.md) — estratégias por falha, modo degradado, rollback.
- [evolution/EVOLUTION.md](evolution/EVOLUTION.md) — ciclo de aprendizado, anti-regressão.

## docs/ (A4, 2026-07-20)
- [docs/DECISIONS.md](docs/DECISIONS.md) — ADRs 2026-07-20 (webhook, secret, debounce, slots zen, CNJ).
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — changelog do pacote cartorio-ai.
- [docs/TEST-REPORT.md](docs/TEST-REPORT.md) — 1000 PASS, E2E 18/20, probes prod.
