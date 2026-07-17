# SSH Tailscale ACL (G8.09.T4)

Objetivo: validar que o acesso SSH à VPS só parte de **nós autorizados** na mesh Tailscale.

## Inventário canônico

| name | IP | role |
|------|-----|------|
| vps-cartorio | `100.99.172.84` | admin |
| macbook-pro-gus | `100.83.180.16` | admin |
| iphone-17-pro | `100.122.101.33` | device |
| iphone-andre | `100.74.36.41` | device |
| triqhub | `100.110.127.44` | ops |

Fonte: `PROMPT.json` → `infrastructure.tailscale.nodes`. Código: `app/services/ssh_tailscale_acl.py`.

## API

- `is_ssh_source_allowed(source_ip)` — exact match no inventário.
- `validate_sshd_match_block(config_text)` — soft parse: exige `Match Address 100.*` **e** `AllowUsers`.
- `recommended_sshd_snippet()` — template (não aplica config na VPS).

## Validação local

```bash
cd backend && unset PYTHONPATH && .venv312/bin/python -m pytest tests/test_ssh_tailscale_acl_g8.py --no-cov -q
```

## Regras operacionais

1. SSH admin preferencial via Tailscale (`100.99.172.84:22`), não IP público.
2. Atualizar `DEFAULT_PEERS` quando um nó entrar/sair da tailnet.
3. Complementa G8.09.T1 (`tailscale_probe`) e G8.09.T2 (`magicdns_inventory`).

Modified by Gustavo Almeida — G8.09.T4.
