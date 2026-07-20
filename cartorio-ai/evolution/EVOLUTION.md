# EVOLUTION

Evolução contínua do sistema (2026-07-20).

## Ciclo de aprendizado

1. Toda sessão termina com lição em `.harness/memory/MEMORY.md` (cross-rein, commitada).
2. Fatos de sessão em `.brain/memory/AAAA-MM-DD.md` (ex.: `2026-07-20.md`).
3. Regressões viram teste primeiro (TDD): bug → teste que falha → fix → teste verde.

## Mudanças recentes incorporadas (2026-07-20)

- Webhook Telegram nunca-5xx + sync com secret obrigatório + debounce por `chat_id:user_id` (commit `d642e0e`).
- LLM: 3 contas OpenCode Zen com slots coerentes, timeout 45s, payload por provider (`bc9823c`).
- Endpoint CNJ massive-dump com streaming + scrub + gate audit (`ff599aa`, `0d15da6`, `6c029fc`).
- Núcleo `cartorio-ai/` preenchido; plano G9 reformatado para 10 squads × 10 tasks.

## Promoção de mudanças

- Experimentos em branch; canary apenas com aprovação do dono (`evolution/CANARY.md`).
- Otimização de prompts: versionada em `prompts/PROMPT_VERSIONING.md`, com testes de regressão.
- Novas skills: `skills/SKILL_CREATION.md` → revisão → registry → CI gate.

## Anti-regressão

- CI bloqueia: cobertura < 90%, lint/mypy > 0, teste de regressão falho, arquivo-núcleo `cartorio-ai/` virando placeholder.
- Lições numeradas ativas (109-118+) em memória de projeto; consulta obrigatória antes de retrabalho.
