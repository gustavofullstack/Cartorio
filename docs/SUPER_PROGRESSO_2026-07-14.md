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

### 2026-07-14 18:35 BRT — Ciclo 1 fechado (S0-T001 + S0-T004)

- T001: drift de versão corrigido (`app.__version__` canônica → main + mcp_server + radar).
  - `app/main.py` agora importa `__version__ as APP_VERSION` e usa em `FastAPI(...)`, `/health`, `/`,
    `/mcp-servers` e `audit.api.startup`.
  - `mcp_server.py` alinha `version="0.6.0"` (era `0.4.0`).
  - `/mcp-servers` corrige `tools_count: 7 → 13` (valor medido).
- T004: gate `mutmut` verde — `uv pip install 'mutmut>=3.6.0'` (test_mutmut_installed_version passou).
- Suite consolidada: `2626 passed, 19 skipped, 49 deselected, 0 failed`.
- Cobertura: 95,10% (gate 90% PASS).
- ruff=0, mypy=0 (128 arquivos).
- 6 testes de versão/OpenAPI/MCP/radar: 29 passed, 1 skipped.
- Commit: `9d82e97 fix(observability): consolidar versão 0.6.0 em main.py + mcp_server + radar (S0-T001)`.

Modified by Gustavo Almeida — auditoria automatizada 2026-07-14 18:35 BRT
