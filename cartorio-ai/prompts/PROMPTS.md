# PROMPTS

Gestão de prompts do agente (2026-07-20).

## Hierarquia de prompts

1. **System** (`prompts/SYSTEM.md`): identidade Pietra Cartório, regras P0 (HITL, PII, audit), tom profissional cartorário.
2. **Developer** (`prompts/DEVELOPER.md`): formato de resposta por canal, restrições de parse (Telegram HTML), tool-use.
3. **User context** (`prompts/USER_CONTEXT.md`): dados de sessão minimizados — nunca PII raw.

## Regras de composição

- PII entra sempre mascarada no contexto do LLM (camada 2 de `pii.py`).
- Output passa por sanitização de tags antes do Telegram (`think`/`reasoning` quebram `parse_mode=HTML`).
- Disclaimer jurídico injetado em respostas de orientação; estimativas de emolumento com ressalva de conferência.
- Prompt injection defense: instruções de usuário nunca sobrescrevem system/developer (`prompts/PROMPT_INJECTION_DEFENSE.md`).

## Documentos mestre de contexto (raiz do repo)

| Arquivo | Versão | Escopo |
|---|---|---|
| `PROMPT.MD` / `PROMPT.json` | 4.6.0 (2026-07-20) | Aplicação/negócio — estado telegram + zen 3 contas |
| `PROMPT-2.MD` / `PROMPT-2.json` | 2.1 (2026-07-20) | Infra Easypanel/Swarm — topologia VPS do Cartório |
| `docs/PROMPTS-INDEX.md` | sincronizado | Índice cruzado e divergências |

## Versionamento

- Bump documentado em `prompts/PROMPT_CHANGELOG.md` e no cabeçalho de cada arquivo mestre.
- Testes de prompt (regressão de comportamento) em `prompts/PROMPT_TESTS.md`.
