# RUNTIMES

Runtimes de execução suportados (2026-07-20).

## Runtimes ativos

| Runtime | Onde | Função |
|---|---|---|
| Python 3.11+ (uv) | VAIO + VPS | Backend FastAPI, testes, scripts |
| Uvicorn | VPS (4 workers prod) | ASGI server da API |
| Docker Swarm | VPS | Orquestração dos 19 serviços |
| Node (n8n) | VPS container | Workflows e automações de canal |
| OpenClaw gateway | VPS container | Runtime de agente conversacional |

## Matriz de capacidade por nó

| Capacidade | MacBook | VAIO (`pc-linux-local`) | VPS (`vps-public`) |
|---|---|---|---|
| Cliente SSH | ✅ | ✅ | ✅ |
| Bateria pytest 1000+ | ❌ | ✅ | ✅ (off-hours) |
| Build Docker | ❌ | ✅ | ✅ |
| Servir produção | ❌ | ❌ | ✅ |
| Stress prod assinado | ❌ | ✅ (origem) | alvo |

## Gestão de ambiente Python

- Deps exclusivamente via `uv` (lockfile `backend/uv.lock`) — nunca pip/poetry.
- Extra E2E: `uv sync --extra e2e` (Playwright + chromium em `~/.cache/ms-playwright/`, nunca commitado).
- Conftest duplo: `backend/conftest.py` (workarounds py3.11.15+pytest 9.1.1 — não remover) e `backend/tests/conftest.py` (força `LLM_DEFAULT_PROVIDER=opencode_go` — isolar testes de LLM real).

## Portabilidade

- Tudo que roda no VAIO roda na VPS (mesma stack uv/Debian-like).
- Migração de runtime e abstração em `runtimes/MIGRATION.md` e `runtimes/RUNTIME_ABSTRACTION.md`.
