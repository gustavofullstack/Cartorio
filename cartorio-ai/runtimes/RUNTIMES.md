# RUNTIMES

Runtimes de execução suportados (2026-07-20).

## Runtimes ativos

| Runtime | Onde | Função |
|---|---|---|
| Python 3.11+ (uv) | VPS + Dev local | Backend FastAPI, testes, scripts |
| Uvicorn | VPS (4 workers prod) | ASGI server da API |
| Docker Swarm | VPS | Orquestração dos serviços |
| Node (n8n) | VPS container | Workflows e automações de canal |
| OpenClaw gateway | VPS container | Runtime de agente conversacional |

## Matriz de capacidade por nó

| Capacidade | Dev local (MacBook/CI) | VPS Hostinger (`vps-public` / `187.77.236.77`) |
|---|---|---|
| Cliente SSH / Dev | ✅ | ✅ |
| Bateria pytest 1000+ | ✅ (local/CI) | ✅ (off-hours ou container CI) |
| Build Docker | ✅ (local) | ✅ (Swarm / EasyPanel) |
| Servir produção | ❌ | ✅ |
| Stress prod assinado | ❌ | ✅ (alvo) |

## Gestão de ambiente Python

- Deps exclusivamente via `uv` (lockfile `backend/uv.lock`) — nunca pip/poetry.
- Extra E2E: `uv sync --extra e2e` (Playwright + chromium em `~/.cache/ms-playwright/`, nunca commitado).
- Conftest duplo: `backend/conftest.py` (workarounds py3.11.15+pytest 9.1.1 — não remover) e `backend/tests/conftest.py` (força `LLM_DEFAULT_PROVIDER=opencode_go` — isolar testes de LLM real).

## Portabilidade

- Stack 100% conteinerizada (Docker Swarm na VPS) baseada em Debian/Ubuntu e gerida via uv.
- Migração de runtime e abstração em `runtimes/MIGRATION.md` e `runtimes/RUNTIME_ABSTRACTION.md`.
