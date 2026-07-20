# CHANGELOG — cartorio-ai

## 2026-07-20 (sessão A4 — expansão de documentação)

### Adicionado

- `execution/EXECUTION_ENGINE.md` — topologia de execução (VAIO runner dev, VPS prod, MacBook cliente SSH).
- `docs/DECISIONS.md` — 5 ADRs do dia (webhook nunca-5xx, secret obrigatório, debounce por conv, slots zen, CNJ dump).
- `docs/TEST-REPORT.md` — consolidado das baterias (1000 PASS, E2E 18/20, probes prod).
- Conteúdo real (15-40 linhas, PT-BR) em 25 registries que eram placeholders de 1 linha:
  `governance/GOVERNANCE`, `knowledge/KNOWLEDGE_BASE`, `agents/AGENT_REGISTRY`,
  `skills/SKILL_REGISTRY`, `tools/TOOL_REGISTRY`, `mcp/MCP_REGISTRY`, `integrations/INTEGRATIONS`,
  `runtimes/RUNTIMES`, `commands/COMMANDS`, `hooks/HOOKS`, `events/EVENTS`,
  `workflows/WORKFLOW_REGISTRY`, `channels/CHANNELS`, `cartorio/CARTORIO`, `guardrails/GUARDRAILS`,
  `models/MODEL_REGISTRY`, `prompts/PROMPTS`, `contracts/CONTRACTS`, `observability/OBSERVABILITY`,
  `evaluation/EVALS`, `operations/RUNBOOK`, `autonomy/AUTONOMY`, `recovery/RECOVERY`, `evolution/EVOLUTION`.

### Alterado (raiz do repo)

- `PROMPT.MD` → v4.6.0: seção estado atual 2026-07-20 (telegram validado HEAD `6967b71`, zen 3 contas, topologia).
- `PROMPT.json` → 4.6.0 e `PROMPT-2.json` → 2.1: bump + changelog curto (JSON validado).
- `PROMPT-2.MD` → v2.1: mesma seção de estado na camada de infra.
- `docs/PROMPTS-INDEX.md` — versões sincronizadas (4.6.0 / 2.1).
- `SUPER_PLANO_G9_100_TASKS.md` — reformatado de 25 squads × 4 para **10 squads × 10 tasks**;
  25 tasks `[x]` preservadas com IDs antigos entre parênteses; contador corrigido 14 → 25 conforme evidência.
- `cartorio-ai/INDEX.md` e `MANIFEST.md` — nova árvore refletida.

### Fatos de referência (HEAD `6967b71`)

- `d642e0e` fix(telegram): webhook nunca 5xx, sync com secret obrigatório, debounce por conv.
- `bc9823c` feat(agent): slots zen coerentes, timeout 45s, payload por provider + scrub de secrets em scripts.
