# Tailscale — restore VPS, MagicDNS, ACL, radar (G7.11.T1 / T2 / T4)

| Campo | Valor |
|-------|--------|
| **Tasks** | G7.11.T1 restore online · G7.11.T2 SSH+MagicDNS no radar · G7.11.T4 ACL least-privilege |
| **Wave** | G7 Wave 26 (agent-side docs) |
| **Rein** | cartorio-sre |
| **Live restore** | **HOLD** — requer SSH/console VPS + conta Tailscale admin (Gustavo) |
| **Fallback já documentado** | `docs/platforms/TAILSCALE_OFFLINE_FALLBACK.md` (G7.11.T3 Wave 17) |
| **Regra desta entrega** | Sem SSH. Sem `tailscale up` remoto. Só runbook + hooks de radar. |

---

## 0. Status e HOLD

| Item | Estado |
|------|--------|
| Tailscale mesh prod (histórico) | VPS `100.99.172.84` · tailnet `*.tail2fe279.ts.net` · node `vps-cartorio` |
| Lesson 176 | Offline 2d+; SSH público Hostinger `187.77.236.77` ainda serve fallback |
| Radar expanded `tailscale` check | Código em `health_radar_expanded.py` (TCP `:22` no IP CGNAT) |
| **G7.11.T1 live restore** | **HOLD-GUSTAVO** (este doc = procedimento) |
| **G7.11.T2 live MagicDNS health** | **HOLD** até T1; radar TCP já existe |
| **G7.11.T4 ACL audit apply** | **HOLD** admin console; matriz ACL abaixo é o target |
| G7.11.T3 offline fallback | **DONE** Wave 17 |

**Não é P0** se API pública (`https://api.2notasudi.com.br`) e EasyPanel estiverem UP. Tailscale é **bypass seguro** para SSH/admin, não path de cliente final do cartório.

---

## 1. Inventário canônico

| Recurso | Valor |
|---------|--------|
| VPS público | `187.77.236.77` (Hostinger) |
| VPS Tailscale IPv4 | `100.99.172.84` (CGNAT 100.x — não rotear na internet) |
| MagicDNS hostname | `vps-cartorio.tail2fe279.ts.net` |
| Porta SSH | `22` (preferir **só** via tailnet; público = fallback) |
| WireGuard TS | UDP `41641` (egress/ingress se NAT estrito) |
| Cert HTTPS TS (OpenClaw) | `infra/traefik/TAILSCALE_OPENCLAW.md` — cert **não** renova sozinho eternamente |
| SSH config sample | `docs/INCIDENTE_SSH_2026-06-23.md` (`Host vps-tailscale`) |

Peers históricos (sessões 2026-06): MacBook `100.83.180.x` + VPS. Revalidar com `tailscale status` após restore.

---

## 2. G7.11.T1 — Restore Tailscale no VPS (procedimento)

> **HOLD live.** Executar só com acesso (SSH público ou console Hostinger).

### 2.1 Pré-checks (do laptop admin)

```bash
# Fallback público ainda vivo?
ssh -i ~/.ssh/id_ed25519_cartorio root@187.77.236.77 'echo ok && uptime'

# Mesh já voltou sozinho?
ping -c 2 100.99.172.84 || true
tailscale status 2>/dev/null | head -20 || true
```

Se `100.99…` já responde e `tailscale status` no Mac mostra o peer VPS **active**, pular para §2.4 validação.

### 2.2 No VPS — daemon e login

```bash
# Serviço
sudo systemctl status tailscaled --no-pager
sudo systemctl enable --now tailscaled
sudo systemctl restart tailscaled

# Binário / versão
tailscale version

# Subir nó (reauth se key expirou)
# Preferir auth key one-off reusável NO — use auth key tagged se CI; interativo se admin no tty:
sudo tailscale up \
  --accept-dns=true \
  --accept-routes=false \
  --ssh=false \
  --hostname=vps-cartorio

# Se pedir URL de login: abrir no browser admin tailnet, aprovar device.
# Alternativa (ops): TS_AUTHKEY=tskey-auth-... sudo -E tailscale up --authkey="$TS_AUTHKEY" ...

tailscale status
tailscale ip -4    # expectativa: 100.99.172.84 (pode mudar se nó recriado — atualizar docs/radar)
tailscale ip -6 || true
```

Notas:

- `--accept-routes=false` no VPS evita puxar subnets de laptops (least surprise).
- `--ssh=false` se SSH nativo do SO já é o controle; Tailscale SSH é opcional e amplia superfície.
- Se o IP CGNAT **mudar**, atualizar `RADAR_TAILSCALE_HOST` em `backend/app/api/v1/health_radar_expanded.py` e este doc.

### 2.3 Firewall / UDP

```bash
# Hostinger / ufw — permitir WireGuard TS se peers não estabelecem
sudo ufw status || true
# Se ufw ativo e mesh falha:
# sudo ufw allow 41641/udp comment 'tailscale'
# sudo ufw reload

# NAT check
tailscale netcheck
```

### 2.4 Validação pós-restore

```bash
# Do Mac (Tailscale client up)
tailscale status | grep -i vps
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 'hostname; tailscale ip -4'
# MagicDNS
ssh -i ~/.ssh/id_ed25519_cartorio root@vps-cartorio.tail2fe279.ts.net 'echo magicdns-ok'

# Radar (após API enxergar o IP — pode ser down se o check roda dentro do VPS sem hairpin)
curl -sS https://api.2notasudi.com.br/api/v1/health/radar/expanded \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('categories',{}).get('ssh', d))"
```

### 2.5 Rollback / se der errado

1. Manter SSH público `187.77.236.77` aberto com chave (já é o fallback G7.11.T3).  
2. `sudo systemctl stop tailscaled` se o daemon degradar a rede do host (raro).  
3. Não remover chaves SSH host enquanto valida mesh.  
4. EasyPanel / API pública **não** dependem de Tailscale.

---

## 3. MagicDNS (G7.11.T2)

### 3.1 Admin console

1. https://login.tailscale.com/admin/dns  
2. **MagicDNS**: ON  
3. **Override local DNS**: prefer OFF no VPS (evita quebrar resolve de `*.2notasudi.com.br` via stub).  
4. Nameservers split: só se houver necessidade de resolver zonas internas; default tailnet basta.  
5. HTTPS certs Tailscale: opcional para `vps-cartorio.tail2fe279.ts.net` (ver `infra/traefik/TAILSCALE_OPENCLAW.md`).

### 3.2 Verificação no nó

```bash
tailscale status --json | jq '{BackendState, Self: .Self.DNSName, Magicsock: .Self.Online}'
# Resolve
getent hosts vps-cartorio.tail2fe279.ts.net || dig +short vps-cartorio.tail2fe279.ts.net
```

### 3.3 O que entra no radar (já implementado)

Código: `backend/app/api/v1/health_radar_expanded.py`

| Constante | Default | Check |
|-----------|---------|--------|
| `RADAR_SSH_HOST` | `187.77.236.77` | TCP connect `:22` → `categories.ssh.ssh_vps` |
| `RADAR_TAILSCALE_HOST` | `100.99.172.84` | TCP connect `:22` → `categories.ssh.tailscale` |
| `RADAR_TAILSCALE_PORT` | `22` | mesmo |

Endpoint: `GET /api/v1/health/radar/expanded`

```json
{
  "status": "green|yellow|red",
  "categories": {
    "ssh": {
      "ssh_vps": {"status": "up|down", "latency_ms": 0, "detail": "..."},
      "tailscale": {"status": "up|down", "latency_ms": 0, "detail": "..."}
    }
  },
  "metadata": {
    "ssh_host": "187.77.236.77",
    "tailscale_host": "100.99.172.84"
  }
}
```

**Interpretação SRE:**

| ssh_vps | tailscale | Ação |
|---------|-----------|------|
| up | up | Normal |
| up | down | Mesh/TS down — **não P0** se API pública OK; abrir G7.11.T1 |
| down | up | Firewall público / sshd bind? investigar, admin ainda via TS |
| down | down | Usar console Hostinger / EasyPanel; ver fallback offline |

Agregação: tailscale `down` sozinho → overall **yellow** (não red). Red só se `health.database` ou `health.redis` down.

### 3.4 Extensão futura MagicDNS no radar (opcional)

Hoje o check é **IP fixo + TCP 22**, não resolve MagicDNS. Se quiser G7.11.T2 “completo” em código depois do restore:

1. Env `RADAR_TAILSCALE_HOST=vps-cartorio.tail2fe279.ts.net` **só funciona** se o processo API resolver MagicDNS (geralmente **não** — container sem cliente TS).  
2. Preferir: sidecar/cron no **host** (`scripts/` ops) que faz `tailscale status --json` e empurra métrica, **ou** manter IP CGNAT atualizado.  
3. Não bloquear T2 doc: health hook TCP no IP **é** o contrato atual.

### 3.5 Alerting

- Tailscale down **&gt; 1h** e SSH público up → ticket SRE rotina (não pager 3am).  
- Ambos down **e** EasyPanel inacessível → escalar (outage acesso admin).  
- N8N workflow radar (#30 se existir) deve tratar `tailscale` como **degraded**, não **critical**.

---

## 4. G7.11.T4 — ACL least-privilege (target)

> Apply no https://login.tailscale.com/admin/acls — **HOLD** live. Abaixo = política alvo auditável.

### 4.1 Princípios

1. Só devices do Gustavo (e automação se houver) + VPS cartório no tailnet.  
2. Tags, não users soltos em grants amplos.  
3. **Não** expor Redis `6379`, Postgres `5432`, ou portas Swarm na interface Tailscale sem auth de aplicação.  
4. SSH admin: user/tag → VPS `:22` apenas.  
5. Aut spoofing: `autoApprovers` mínimo; sem `exit node` no VPS a menos que necessário.

### 4.2 Tags propostas

| Tag | Quem | Uso |
|-----|------|-----|
| `tag:cartorio-prod` | VPS Hostinger | destino SSH / admin |
| `tag:dev-laptop` | MacBook Gustavo | origem admin |
| `tag:ci-runner` | (se existir) | só o que for estritamente necessário |

### 4.3 Esqueleto ACL (huJSON)

```jsonc
// Target ACL — revisar IPs/users reais antes de Save.
// NÃO copiar cegamente se o tailnet já tem policy diferente.
{
  "tagOwners": {
    "tag:cartorio-prod": ["autogroup:admin"],
    "tag:dev-laptop": ["autogroup:admin"],
    "tag:ci-runner": ["autogroup:admin"]
  },

  // Preferir grants (ACL moderna). ssh opcional.
  "grants": [
    {
      "src": ["tag:dev-laptop"],
      "dst": ["tag:cartorio-prod"],
      "ip": ["22"]
    },
    {
      // OpenClaw / UI só se exposto no IP TS — preferir Traefik público auth
      "src": ["tag:dev-laptop"],
      "dst": ["tag:cartorio-prod"],
      "ip": ["18789"]
    }
  ],

  "ssh": [
    // Se Tailscale SSH enabled:
    // { "action": "check", "src": ["tag:dev-laptop"], "dst": ["tag:cartorio-prod"], "users": ["root", "ubuntu"] }
  ],

  "autoApprovers": {
    "routes": {},
    "exitNode": []
  },

  // Opcional: negar default-ish — grants acima são allowlist
  "hosts": {
    "vps-cartorio": "100.99.172.84"
  }
}
```

### 4.4 Checklist de auditoria (manual)

- [ ] Listar devices em https://login.tailscale.com/admin/machines — remover stale  
- [ ] Cada device com tag correta (`cartorio-prod` / `dev-laptop`)  
- [ ] Nenhum `*` → `*:*` residual  
- [ ] Key expiry ON para laptops; server key expiry policy documentada  
- [ ] Auth keys one-off para reinstall; **nunca** commitar `tskey-` no repo (`scripts/check_no_literal_keys.py`)  
- [ ] Redis/Postgres **não** em grants  
- [ ] Compartilhamento externo (node share) = none  
- [ ] MFA na conta admin Tailscale  

### 4.5 Superfície que **não** deve ir pro tailnet sem auth

| Serviço | Porta típica | Expor na TS? |
|---------|--------------|--------------|
| Postgres Supabase | 5432 | **Não** (só rede Docker) |
| Redis | 6379 | **Não** |
| API interna | 8000 | Evitar; usar `api.` TLS |
| N8N | 5678 | Prefer `flow.` + auth |
| OpenClaw gateway | 18789 | Só se ACL + token; ver TAILSCALE_OPENCLAW |
| SSH | 22 | Sim, ACL-limited |

---

## 5. Integração com fallback offline

Ordem se Tailscale cair (detalhe em `docs/platforms/TAILSCALE_OFFLINE_FALLBACK.md`):

1. SSH `root@187.77.236.77` (chave)  
2. EasyPanel `https://easypanel.2notasudi.com.br`  
3. API pública / Cloudflare Tunnel dev  
4. Depois: este runbook §2 para restore  

---

## 6. Definition of Done

| Task | Agent-side (Wave 26) | Live |
|------|----------------------|------|
| G7.11.T1 restore procedure | **este doc §2** | **HOLD-GUSTAVO** |
| G7.11.T2 radar SSH+TS | **documentado §3** + código `health_radar_expanded` | HOLD validar yellow→green pós T1 |
| G7.11.T3 offline fallback | DONE Wave 17 | — |
| G7.11.T4 ACL least-privilege | **matriz + esqueleto §4** | **HOLD** apply no admin console |

---

## 7. Referências

- `docs/platforms/TAILSCALE_OFFLINE_FALLBACK.md` — G7.11.T3  
- `infra/traefik/TAILSCALE_OPENCLAW.md` — HTTPS MagicDNS + cert  
- `backend/app/api/v1/health_radar_expanded.py` — `RADAR_TAILSCALE_*`  
- `backend/tests/test_health_radar_expanded.py` — asserts host/metadata  
- `docs/INCIDENTE_SSH_2026-06-23.md` — SSH config  
- `docs/DNS_TRAEFIK_SUI_PACK_G7.md` — edge público  
- Lesson 176 — Tailscale offline / fallback público  

**Modified by Gustavo Almeida + cartorio-sre — G7 Wave 26**
