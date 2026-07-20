# SKILL_REGISTRY

Registro de skills internas do projeto (2026-07-20). Skills globais do cliente Kimi/Claude não são listadas aqui.

## Skills de projeto (`.harness/`, `scripts/`, `backend/Makefile`)

| Skill | Entrada | Função |
|---|---|---|
| Validação full | `make qa` | ruff + mypy + pytest com coverage ≥ 90% (gate CI) |
| Smoke prod | `make -C backend smoke` | `/health`, `/ready`, `/api/v1/health/radar` |
| Shell carregado | `make -C backend shell` | ipython com app, SessionLocal, settings |
| Audit deps | `make -C backend audit` | pip-audit de vulnerabilidades |
| n8n ops | `make n8n-list/export/test` | Inventário, export e E2E dos workflows |
| Checker de segredos | `scripts/check_no_literal_keys.py` | Bloqueia chaves literais (incl. padrão hex-64) |

## Skills de domínio (embutidas no backend)

- `app/services/emolumento.py` — cálculo tabela MG 2026 (faixas, isenção, urgência, mínimo/teto).
- `app/services/pii.py` — scrubbing 3 camadas (input, pre-LLM, output).
- `app/services/audit*.py` — hash chain SHA256 + HMAC, verificação de integridade.
- `app/services/lgpd*.py` — direitos Art. 18 (7 operações) + export CNJ massive-dump.

## Governança de skills

- Criação/alteração segue `skills/SKILL_CREATION.md`; versionamento em `SKILL_VERSIONING.md`.
- Toda skill que toca LLM passa por revisão de PII antes de ir a prod.
- Teste obrigatório por skill crítica: emolumento (bordas), audit (regressão t024/t025), pii (canary).
