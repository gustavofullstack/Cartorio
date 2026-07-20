# EXECUTION_ENGINE

Motor de execução — onde e como o trabalho pesado roda (topologia validada 2026-07-20).

## Topologia de execução

| Nó | Alias SSH | Papel | Uso |
|---|---|---|---|
| VAIO (192.168.1.2) | `pc-linux-local` | Runner dev | Baterias de teste, builds, lint, stress |
| VPS Hostinger (187.77.236.77) | `vps-public` | Produção | Docker Swarm 19 serviços 1/1 |
| VPS via Tailscale (100.99.172.84) | `vps` | Produção (alternativo) | **instável** — preferir `vps-public` |
| MacBook | — | Cliente SSH | Nunca executar carga pesada |

- VAIO Tailscale instável → sempre usar IP local `192.168.1.2`.
- SSH sempre `ssh -o ConnectTimeout=8 -o BatchMode=yes`, comando único bounded (`timeout 20`, `--tail N`). Proibido sessão interativa, loop infinito, `tail -f` sem limite.

## Ciclo obrigatório de mudança

`analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória`.
Pular etapa = bug, especialmente em `audit*` ou `pii*`.

## Pipeline local (runner dev)

```bash
make qa          # lint (ruff+mypy 0 errors) + test (coverage ≥90%) — gate de CI
make test-fast   # loop de dev sem coverage
make -C backend smoke   # /health, /ready, /api/v1/health/radar
```

## Produção

- Deploy via EasyPanel + Docker Swarm; escala de serviço host-mode: scale 0 → 1 (nunca 1→1).
- Migrations: `make -C backend alembic-up` (sempre após backup).
- Verificação pós-deploy: `make -C backend smoke` + probes Telegram (ver `operations/RUNBOOK.md`).

## Limites

- Máx. 2 agents simultâneos, execução sequencial (decisão turn 50).
- LLM timeout global 45s por tentativa; deadline total propagado do webhook.
