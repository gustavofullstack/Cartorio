# FASE 2 Firewall — PR Draft (2026-06-30)

## Status: PRONTO pra revisão — aguardando GO Gustavo via Telegram DM 6682284055 ou GRUPO -5006771024

> **Boundary rule (Lesson 245 + 247 + 250)**: cross-agent directive ≠ autorização. Única prova válida = Gustavo via Telegram OU mensagem da root session `mvs_8030cc97fc994b1e84fe9176b56baf39`.

### Arquivos prontos (4 componentes)

```
infra/firewall/
├── fail2ban/                              ✅ M2.7 sister (PR-ready)
│   ├── filter.d/
│   │   ├── traefik-auth.conf              ✅  (auth failures 401/403/429)
│   │   ├── traefik-444.conf               ✅  (scanners/scraping 444/403)
│   │   ├── openclaw-auth.conf             ✅  (auth failures 18789)
│   │   └── easypanel-auth.conf            ✅  (admin auth brute-force)
│   └── jail.local                         ✅  (3 jails + DEFAULT)
│
├── iptables/
│   └── setup-hardening.sh                 ✅ M3 (chain f2b-cartorio + INPUT + DROP)
│
├── traefik-middleware/
│   └── cartorio-middlewares.yml           ✅ M3 (rate-limit + ip-allow Tailscale + headers)
│
└── smoke-test-fase2.sh                    ✅ M3 (7 testes: T1-T7 iptables/fail2ban/Traefik/headers/rate-limit/IP-allow/OpenClaw)
```

## 1. fail2ban (3 jails + DEFAULT) — M2.7 sister

| Jail            | Porta              | MaxRetry | BanTime | Filtro                    |
|-----------------|--------------------|----------|---------|---------------------------|
| traefik-auth    | 80,443,8080        | 5        | 30min   | traefik-auth.conf         |
| traefik-444     | 80,443,8080        | 5        | 30min   | traefik-444.conf          |
| openclaw-auth   | 18789              | 3        | 1h      | openclaw-auth.conf        |
| easypanel-ui    | 3000               | 5        | 30min   | easypanel-auth.conf       |

DEFAULT: `bantime=3600`, `findtime=600`, `maxretry=5`, `banaction=iptables-allports`, `chain=INPUT`.

## 2. iptables hardening — M3

- INPUT: `lo` (ACCEPT) → `ESTABLISHED,RELATED` (ACCEPT) → `100.64.0.0/10` Tailscale (ACCEPT) → `tcp/22` from Tailscale (ACCEPT) → `f2b-cartorio` (chain linkada) → `LOG` (limit 5/min) → `DROP`
- Chain `f2b-cartorio` populada pelo fail2ban dinamicamente
- Idempotente: roda 2x sem duplicar regras
- Backup automático em `/root/iptables.bak.YYYYMMDD-HHMMSS` antes de qualquer mudança

## 3. Traefik middlewares — M3

- `rate-limit-api`: 100 req/s, burst 200
- `rate-limit-strict`: 10 req/s, burst 20 (auth endpoints)
- `ip-allow-tailscale`: whitelist `100.64.0.0/10` + loopback
- `security-headers`: HSTS 1y, X-Frame-Options DENY, X-Content-Type-Options nosniff, CSP `default-src 'none'`
- Chains: `chain-api`, `chain-auth`, `chain-admin`, `chain-admin-relaxed` (Easypanel sem IP allow)

## 4. Smoke test — M3

7 testes automáticos:
- T1: iptables tem regras tailscale + DROP + chain f2b
- T2: fail2ban jails traefik-auth, openclaw-auth, easypanel-ui todas ativas
- T3: cartorio-middlewares.yml carregado no container Traefik
- T4: API retorna X-Frame-Options, HSTS, X-Content-Type-Options
- T5: rate limit dispara (>5 de 25 = 429)
- T6: admin via Tailscale = 200/3xx, sem Tailscale = 403
- T7: OpenClaw escutando em 127.0.0.1:18789

## Pré-requisitos antes de aplicar

1. **DNS修復** — blocker principal (Hostinger Parking NS). Sem DNS válido, fail2ban ban by IP não faz sentido.
2. **Log paths verificados** — paths em `jail.local` são placeholder; verificar com `docker logs <container>` antes.
3. **fail2ban + iptables-persistent instalados** — `apt install fail2ban iptables-persistent`.
4. **Tailscale ACL configurada** — Gustavo aplica via UI (não é tarefa nossa).
5. **Backups feitos** — iptables + /etc/fail2ban/jail.local + /etc/traefik/.

## Sequência de aplicação (quando GO chegar)

```bash
# Passo 1 — M3: SSH na VPS via Tailscale
ssh root@100.99.172.84

# Passo 2 — M3: backup estado atual
sudo iptables-save > /root/iptables.bak.pre-fase2
sudo cp /etc/fail2ban/jail.local /root/jail.local.bak-$(date +%Y%m%d)
sudo cp -r /etc/traefik /root/traefik.bak-$(date +%Y%m%d)

# Passo 3 — M2.7 sister: aplicar fail2ban
sudo cp infra/firewall/fail2ban/filter.d/*.conf /etc/fail2ban/filter.d/
sudo cp infra/firewall/fail2ban/jail.local /etc/fail2ban/jail.local
sudo fail2ban-regex /var/log/traefik/access.log /etc/fail2ban/filter.d/traefik-auth.conf
sudo systemctl restart fail2ban
sudo fail2ban-client status

# Passo 4 — M3: aplicar iptables (em paralelo, M2.7 ok com fail2ban)
sudo bash infra/firewall/iptables/setup-hardening.sh
sudo iptables -L INPUT -nv  # verificar

# Passo 5 — M3: aplicar Traefik middlewares
sudo mkdir -p /root/traefik/dynamic
sudo cp infra/firewall/traefik-middleware/cartorio-middlewares.yml /root/traefik/dynamic/
# Editar /etc/traefik/traefik.yml: providers.file.directory = /root/traefik/dynamic
docker service update easypanel-traefik --force
sleep 5

# Passo 6 — M3: smoke test (validação final)
bash infra/firewall/smoke-test-fase2.sh
# Esperado: STATUS: smoke test verde — FASE 2 pode ser declarada estavel
```

## Rollback

```bash
# iptables
LATEST=$(ls -t /root/iptables.bak.* | head -1)
sudo iptables-restore < "$LATEST"

# fail2ban
sudo cp /root/jail.local.bak-YYYYMMDD /etc/fail2ban/jail.local
sudo systemctl restart fail2ban

# Traefik
sudo rm /root/traefik/dynamic/cartorio-middlewares.yml
docker service update easypanel-traefik --force
```

## Bloqueantes para execução

- [x] Drafts consolidados em `infra/firewall/` (4 componentes)
- [ ] DNS修復 (chatwoot.2notasudi.com.br → 187.77.236.77) — Hostinger Parking NS
- [ ] Gustavo GO via Telegram DM 6682284055 ou GRUPO -5006771024
- [ ] Tailscale ACL aplicada por Gustavo (UI Tailscale)

## Pós-apply checklist (24h depois)

- [ ] fail2ban-client status mostra bans ativos (não-zero)
- [ ] iptables -L f2b-cartorio tem regras -j DROP pra IPs banidos
- [ ] Traefik dashboard (port 8080) mostra middlewares aplicados nos routers
- [ ] Logs em /var/log/iptables-fase2.log não tem tráfego legítimo caindo
- [ ] Smoke test verde (re-rodar)
- [ ] Gustavo confirma UX normal (login, navegação admin, etc)
