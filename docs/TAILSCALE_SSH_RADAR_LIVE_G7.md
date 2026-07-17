# Tailscale SSH + Radar live validation (G7.11.T1 / G7.11.T2)

| Campo | Valor |
|-------|--------|
| **Tasks** | G7.11.T1 restore online · G7.11.T2 SSH 22 + MagicDNS health no radar |
| **Wave pack** | **Wave28 SUI pack refreshed** (2026-07-17) |
| **Runbook completo** | [`TAILSCALE_RESTORE_G7.md`](TAILSCALE_RESTORE_G7.md) (**sólido** Wave26) |
| **Fallback offline** | [`platforms/TAILSCALE_OFFLINE_FALLBACK.md`](platforms/TAILSCALE_OFFLINE_FALLBACK.md) (G7.11.T3 DONE) |
| **Live** | **[~] HOLD-GUSTAVO** — agent não roda `tailscale up` no VPS |
| **Rein** | cartorio-sre |

Este one-pager é a **folha de validação pós-restore**. Procedimento completo de restore/ACL permanece em `TAILSCALE_RESTORE_G7.md`.

---

## Inventário canônico

| Recurso | Valor |
|---------|--------|
| VPS público (fallback SSH) | `187.77.236.77` |
| Tailscale IPv4 | `100.99.172.84` |
| MagicDNS | `vps-cartorio.tail2fe279.ts.net` |
| SSH port | `22` |
| WireGuard TS | UDP `41641` |
| Radar code | `backend/app/api/v1/health_radar_expanded.py` |
| Defaults | `RADAR_SSH_HOST=187.77.236.77` · `RADAR_TAILSCALE_HOST=100.99.172.84` · port `22` |

**Não é P0 cliente:** se API pública e EasyPanel OK, mesh down = yellow/rotina SRE.

---

## 0. Antes do restore

```bash
# Fallback público ainda vivo?
ssh -i ~/.ssh/id_ed25519_cartorio root@187.77.236.77 'echo ok && uptime'

# Mesh já voltou?
ping -c 2 100.99.172.84 || true
tailscale status 2>/dev/null | head -20 || true
```

Se peer VPS já **active**, pular para §2. Senão: executar **§2** de `docs/TAILSCALE_RESTORE_G7.md` (systemctl + `tailscale up --hostname=vps-cartorio`).

---

## 1. Comandos de validação pós-restore (G7.11.T1)

Rodar **do laptop admin** com cliente Tailscale up:

```bash
# 1.1 Status mesh
tailscale status | grep -iE 'vps|cartorio|100\.99'

# 1.2 IP do peer
# expectativa histórica: 100.99.172.84 (se mudou, atualizar RADAR_TAILSCALE_HOST + docs)

# 1.3 SSH por CGNAT
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 'hostname; tailscale ip -4; uptime'

# 1.4 SSH por MagicDNS
ssh -i ~/.ssh/id_ed25519_cartorio root@vps-cartorio.tail2fe279.ts.net 'echo magicdns-ok; tailscale status | head -5'

# 1.5 No VPS — daemon saudável
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 \
  'systemctl is-active tailscaled && tailscale version && tailscale netcheck | head -20'
```

| Check | Pass |
|-------|------|
| `tailscale status` peer active | sim |
| SSH `100.99.172.84` | shell ok |
| SSH MagicDNS | shell ok |
| `tailscaled` active | yes |

---

## 2. Radar expanded — SSH + Tailscale (G7.11.T2)

Pré-req: endpoint em prod (se 404 → `docs/RADAR_EXPANDED_REDEPLOY_G7.md`).

```bash
# 2.1 Endpoint vivo
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://api.2notasudi.com.br/api/v1/health/radar/expanded
# meta: 200

# 2.2 Categoria ssh
curl -sS https://api.2notasudi.com.br/api/v1/health/radar/expanded | jq '{
  status: .status,
  ssh: .categories.ssh,
  meta: {ssh_host: .metadata.ssh_host, ts: .metadata.tailscale_host}
}'
```

Formato esperado (campos):

```json
{
  "categories": {
    "ssh": {
      "ssh_vps": {"status": "up|down", "latency_ms": 0},
      "tailscale": {"status": "up|down", "latency_ms": 0}
    }
  },
  "metadata": {
    "ssh_host": "187.77.236.77",
    "tailscale_host": "100.99.172.84"
  }
}
```

### Interpretação

| ssh_vps | tailscale | Significado | Ação |
|---------|-----------|-------------|------|
| up | up | Normal | — |
| up | down | Mesh off, admin público ok | reabrir restore §2 RESTORE_G7 |
| down | up | SSH público filtrado; TS ok | preferir TS; checar ufw/sshd |
| down | down | Sem admin SSH | console Hostinger / EasyPanel; fallback offline |

Agregação: só tailscale down → overall **yellow** (não red). Red se DB/Redis down.

```bash
# 2.3 One-liner pass/fail (exit 0 se ambos up)
curl -sS https://api.2notasudi.com.br/api/v1/health/radar/expanded \
  | python3 -c "
import sys, json
d=json.load(sys.stdin)
ssh=d.get('categories',{}).get('ssh',{})
a=ssh.get('ssh_vps',{}).get('status')
b=ssh.get('tailscale',{}).get('status')
print('ssh_vps', a, 'tailscale', b)
sys.exit(0 if a=='up' and b=='up' else 1)
"
```

### Nota MagicDNS no radar

O check atual é **TCP :22 no IP CGNAT**, não resolve MagicDNS de dentro do container API (sem cliente TS).  
Isso **é** o contrato T2 de código. MagicDNS valida-se no laptop (§1.4).  
Se o IP CGNAT mudar após reauth, atualizar env/`RADAR_TAILSCALE_HOST` e este inventário.

---

## 3. Smoke paralelo (não bloqueia T1/T2)

```bash
# API pública não depende de TS
curl -sS https://api.2notasudi.com.br/health | jq .
curl -sS -o /dev/null -w 'easypanel:%{http_code}\n' https://easypanel.2notasudi.com.br/

# ACL (G7.11.T4 skeleton já em RESTORE_G7) — apply HOLD admin console
# https://login.tailscale.com/admin/acls
```

---

## 4. Se falhar — ordem de fallback

1. SSH `root@187.77.236.77` (chave)  
2. EasyPanel UI  
3. Cloudflare Tunnel dev (Lesson 151)  
4. Depois: re-run restore `TAILSCALE_RESTORE_G7.md`  
5. Detalhe offline: `TAILSCALE_OFFLINE_FALLBACK.md`

Não desligar chaves SSH host enquanto valida mesh.

---

## Definition of Done

| Item | Agent | Live |
|------|-------|------|
| Runbook restore + ACL | [x] Wave26 RESTORE_G7 | — |
| Radar hooks TCP 22 | [x] código expanded | — |
| One-pager validação Wave28 | [x] este doc | — |
| Mesh online + SSH TS | — | [~] |
| Radar ssh_vps+tailscale up | — | [~] |
| SUPER_PLANO T1/T2 → `[x]` | — | só após live |

---

## Cross-refs

- `docs/TAILSCALE_RESTORE_G7.md`  
- `docs/platforms/TAILSCALE_OFFLINE_FALLBACK.md`  
- `docs/RADAR_EXPANDED_REDEPLOY_G7.md`  
- `docs/platforms/API_HEALTH_RADAR.md`  
- `infra/traefik/TAILSCALE_OPENCLAW.md`  
- Lesson 176 (TS offline 2d+) · 151 (tunnel rescue)

**Modified by Gustavo Almeida — G7 Wave28 SUI pack refreshed**
