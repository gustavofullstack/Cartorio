# Tailscale Offline Fallback (G7.11.T3)

**Contexto:** Lesson 176 — Tailscale offline 2d+; acesso via `vps-public` Hostinger
(`187.77.236.77`) ainda funciona. MagicDNS `*.tail2fe279.ts.net` fica inutilizável.

---

## Sintomas

| Check | Offline TS | Online TS |
|-------|------------|-----------|
| `tailscale status` | idle / stopped / no peer | peers active |
| SSH `100.99.172.84` | timeout | ok |
| SSH `187.77.236.77` | ok (se firewall libera) | ok |
| Radar expanded tailscale port | down | up |

---

## Fallback operacional (ordem)

1. **SSH público** (preferir chave, não password):
   ```bash
   ssh -i ~/.ssh/<key> root@187.77.236.77
   # ou user configurado no Hostinger
   ```
2. **EasyPanel UI** — `https://easypanel.2notasudi.com.br` (Traefik, não depende de TS).
3. **Cloudflare Tunnel** (dev local → API) — Lesson 151:
   ```bash
   nohup cloudflared tunnel --url http://localhost:8000 &
   ```
4. **API pública** — `https://api.2notasudi.com.br` (sem Tailscale).

---

## Restaurar Tailscale (quando tiver acesso)

```bash
# No VPS
sudo systemctl status tailscaled
sudo systemctl restart tailscaled
sudo tailscale up --accept-routes
tailscale status
tailscale ip -4   # deve ~100.99.172.84
```

Firewall Hostinger: permitir UDP 41641 se necessário.

---

## ACL least-privilege (G7.11.T4 backlog)

- Só machines do Gustavo + VPS cartório no tailnet.
- Tags: `tag:cartorio-prod`, `tag:dev-laptop`.
- Não expor Redis/Postgres na interface Tailscale sem auth.

---

## Integração com radar

- `RADAR_TAILSCALE_HOST=100.99.172.84` em `health_radar_expanded.py`.
- Se down por >1h: alert SRE, **não** escala P0 se API pública 200.

---

**Modified by Gustavo Almeida + cartorio-sre — G7 Wave 17**
