# TOOL_REGISTRY

Ferramentas operacionais disponíveis aos agentes (2026-07-20).

## Ferramentas de infra (SSH bounded)

| Tool | Host | Uso |
|---|---|---|
| `ssh vps-public` | 187.77.236.77 (root) | Swarm ops, logs, deploy — estável |
| `ssh pc-linux-local` | 192.168.1.2 | Runner dev (testes pesados) |
| `ssh vps` | 100.99.172.84 (Tailscale) | ⚠️ instável — evitar |

Sempre `ssh -o ConnectTimeout=8 -o BatchMode=yes` + comando único bounded. Proibido interativo/loop/watch.

## Ferramentas de banco e cache

- `make -C backend shell` — ipython com `SessionLocal` (queries read-only por padrão em prod).
- `make -C backend alembic-up|alembic-new|alembic-history` — migrations.
- Redis CLI via service exec — inspeção de idempotency keys (TTL 24h) e rate-limit buckets.

## Ferramentas de qualidade

- `make lint` / `make format` — ruff (line-length 100, py311) + mypy strict.
- `make test` / `make test-fast` / `make test-one TEST=...` — pytest, markers `smoke|integration|e2e` off por default.
- `scripts/check_no_literal_keys.py` — gate de segredos literais (hex-64 incluso).

## Ferramentas de observabilidade

- `curl localhost:8000/metrics` — Prometheus (na VPS).
- Radar: `/api/v1/health/radar` — saúde agregada dos 19 serviços.
- Sentry com `before_send` scrubber (PII nunca sai raw).

## Custos e limites

- LLM: timeout 45s/tentativa; budget de tokens em `tools/TOOL_COSTS.md`.
- Rate limit API: 60/min IP; por key — N8N 600, DPO 60, default 30 (3-tier).
