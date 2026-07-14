# SUPER PROGRESSO — 2026-07-14 (snapshot pós-auditoria)

> Auto-save a cada ciclo. Append-only.

## 2026-07-14 18:15 BRT — Auditoria de Estado Real

### Análise (Gates)
| Item | Antes (documentado) | Depois (medido) |
|------|----------------------|-----------------|
| ruff errors | 0 | 0 ✅ |
| mypy errors | 0 | 0 (128 arquivos) ✅ |
| pytest passed | 2477 | 2625 |
| pytest failed | 0 | 1 (gate `mutmut` não instalado — não regressão) |
| coverage | 95,04% | 95,09% ✅ (gate ≥90% PASS) |
| `cartorio_api` Swarm | 1/1 | **11/1** ⚠️ (10 réplicas velhas) |
| `chatwoot` | 1/1 | 0/1 ⚠️ restart loop |
| `evolution-api` | 1/1 | 0/1 ⚠️ restart loop |
| `n8n` | 1/1 | 1/1 (login Postgres falha) ⚠️ |
| DNS públicos | 7/11 | 7/11 (faltam chatwoot/n8n/supabase/lobe) |
| Tailscale | online | logged out |

### Decisões
- **Versão correta** = `0.6.0` (consolidar `app/main.py` + `mcp_server.py` + OpenAPI).
- **Senha Postgres** = `@Techno832466` (não `supabase_admin`).
- **Host Postgres** = `cartorio_supabase` (overlay), nunca `10.11.211.12`.
- **Replicas API** = `1/1` (escalar o Swarm para 1).
- **LobeChat** sem DNS público até Gustavo criar A record.

### Próximas ações (4 squads, 2 paralelos)

**S0 Backend (cartorio-dev)** — T001–T010:
- T001: drift de versão (0.5.4 vs 0.6.0)
- T002: replicas 11→1
- T003: remover `verify=False` telegram.py
- T004: fixar gate `mutmut`
- T005: snapshot OpenAPI
- T006: `make test-loop`
- T007: scale `cartorio_api=1`
- T008: bloquear reload prod
- T009: `TrustedHostMiddleware`
- T010: `__version__` de pyproject

**S1 N8N (cartorio-n8n)** — T026–T030:
- T026: `POSTGRES_HOST` em chatwoot
- T027: idem evolution-api
- T028: senha n8n
- T029: `ENABLE_ACCOUNT_SIGNUP` em chatwoot/sidekiq
- T030: scale evolution-api=1

Modified by Gustavo Almeida — auditoria automatizada 2026-07-14 18:15 BRT
