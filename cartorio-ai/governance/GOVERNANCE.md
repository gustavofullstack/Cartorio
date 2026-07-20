# GOVERNANCE

Governança operacional do ecossistema de agentes do Cartório 2º Notas (estado 2026-07-20).

## Autoridade

| Nível | Quem | Poder |
|---|---|---|
| L0 | Gustavo Almeida (dono/CEO) | Decisão final, rotação de chaves, deploy prod, QR WhatsApp, DNS |
| L1 | Orquestrador (harness + reins) | Decomposição de tasks, delegação a subagents, gates de qualidade |
| L2 | Reins especialistas | `cartorio-dev`, `cartorio-n8n`, `cartorio-lgpd` — execução dentro do escopo |
| L3 | Bot/agente em prod | Responde FAQ e triagem; **nunca** decide ato jurídico |

## Decisões que exigem L0 (dono)

- Rotação de qualquer chave/token/secret (proibido sem ordem expressa).
- Push direto em `master` (proibido; sempre branch + PR + 1 review).
- Mudança em `audit*` ou `pii*` sem sign-off `cartorio-lgpd`.
- Ações SUI: scan QR Evolution, A records DNS, restore Tailscale.

## Gates formais

- `make qa` verde (ruff 0 errors + mypy 0 errors + pytest com coverage ≥ 90%) antes de PR.
- PR template completo (`.github/pull_request_template.md`) — checklist, LGPD, rollback.
- Honesty gate: checkbox de plano só marca `[x]` com evidência de 1 linha.
- Audit log append-only: qualquer ação jurídica gera entrada SHA256+HMAC encadeada.

## Registro de mudanças

- Conventional Commits terminando com `Modified by Gustavo Almeida`.
- Decisões arquiteturais recentes em `cartorio-ai/docs/DECISIONS.md`.
- Changelog de governança em `GOVERNANCE_CHANGELOG.md` (mesmo diretório).
