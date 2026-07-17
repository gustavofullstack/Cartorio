# MagicDNS / private routing (G8.09.T2)

Objetivo: DB, Redis e API interna **não** usam IP público no app.

## Mapa recomendado

| Serviço | Host:porta |
|---------|------------|
| API | `cartorio-api:8000` (swarm) |
| Postgres | `cartorio_postgres:5432` |
| Redis | `cartorio_redis:6379` |
| SSH admin | `100.99.172.84:22` (Tailscale) |

## Validação local

```bash
cd backend && unset PYTHONPATH && .venv312/bin/python -m pytest tests/test_magicdns_inventory_g8.py --no-cov -q
```

## Regras

1. `DATABASE_URL` / `REDIS_URL` em prod: DNS interno ou Tailscale, nunca `187.x` se existir mesh.
2. MagicDNS Tailscale: preferir nomes `*.ts.net` quando multi-host.
3. Probe: `app/services/tailscale_probe.py` (G8.09.T1).

Modified by Gustavo Almeida — Wave 40.
