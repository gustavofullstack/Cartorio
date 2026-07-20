# cartorio-ai · MANIFEST

| Campo | Valor |
|---|---|
| Pacote | `cartorio-ai/` — camada de identidade, memória e governança |
| Projeto | Backend API 2º Serviço Notarial de Uberlândia (Cartório 2º Notas) |
| Dono | Gustavo Almeida |
| Criado | 2026-07-20 (scaffold) · Núcleo preenchido 2026-07-20 (sessão C4 / G9.11–G9.12) |
| Expandido | 2026-07-20 (sessão A4 / G9.S6) — 25 registries de domínio + `execution/` + `docs/` (28 arquivos) |
| Status | **Núcleo completo (15 arquivos) + camada de registries (28 arquivos)** · Layout estendido restante pendente (ver `ROADMAP.md`) |
| Tipo | Documentação viva — nenhum código executável |
| Licença/Uso | Interno do serventia; contém referências a dados sensíveis (nunca valores) |

## Escopo do núcleo

Raiz: `AGENTS.md`, `README.md`, `ARCHITECTURE.md`, `MANIFEST.md`, `INDEX.md`, `BOOTSTRAP.md`, `ROADMAP.md`
Domínio: `brain/BRAIN.md`, `identity/SOUL.md`, `identity/IDENTITY.md`,
`planning/GOALS.md`, `planning/TASKS.md`, `memory/MEMORY.md`,
`security/SECURITY.md`, `compliance/CNJ.md`

## Camada de registries (sessão A4, 2026-07-20)

Um arquivo real por diretório (15-40 linhas, PT-BR, fatos do projeto):
`governance/GOVERNANCE.md`, `knowledge/KNOWLEDGE_BASE.md`, `execution/EXECUTION_ENGINE.md`,
`agents/AGENT_REGISTRY.md`, `skills/SKILL_REGISTRY.md`, `tools/TOOL_REGISTRY.md`,
`mcp/MCP_REGISTRY.md`, `integrations/INTEGRATIONS.md`, `runtimes/RUNTIMES.md`,
`commands/COMMANDS.md`, `hooks/HOOKS.md`, `events/EVENTS.md`, `workflows/WORKFLOW_REGISTRY.md`,
`channels/CHANNELS.md`, `cartorio/CARTORIO.md`, `guardrails/GUARDRAILS.md`,
`models/MODEL_REGISTRY.md` (3 contas zen + fallback + circuit breaker), `prompts/PROMPTS.md`,
`contracts/CONTRACTS.md`, `observability/OBSERVABILITY.md`, `evaluation/EVALS.md`,
`operations/RUNBOOK.md`, `autonomy/AUTONOMY.md`, `recovery/RECOVERY.md`, `evolution/EVOLUTION.md`,
`docs/DECISIONS.md` (ADRs 2026-07-20), `docs/CHANGELOG.md`, `docs/TEST-REPORT.md`.
Índice navegável completo em `INDEX.md`.

## Fora de escopo (fase posterior)

Os demais arquivos irmãos não-núcleo/não-registry dentro de todos os diretórios
(~400 arquivos). Detalhes e critérios de promoção em `ROADMAP.md`.

## Dependências de verdade

- `../AGENTS.md`, `../.harness/AGENTS.md` — regras operacionais (vencem em conflito).
- `../SUPER_PLANO_G9_100_TASKS.md` — plano ativo referenciado por `planning/TASKS.md`.
- `../.harness/memory/MEMORY.md` e `../.brain/memory/` — memória de projeto/sessão.
