# Fail2ban — Cartório 2notas (PR DRAFT, READ-ONLY)

> **STATUS**: PRONTO PARA REVISÃO + APLICAÇÃO MANUAL POR GUSTAVO.
> NÃO APLICADO. NÃO EXECUTADO. Files locais em `infra/security/fail2ban/`.

## Escopo

3 jails contra brute-force / scraping em serviços públicos:

| Jail | Alvo | Log path (VPS) | Porta pública |
|------|------|----------------|---------------|
| `traefik-auth` | brute-force em endpoints `/api/v1/auth/*`, `/login`, `/admin` | `/var/log/traefik/access.log` | 18789 (Traefik → API) |
| `traefik-444` | scraping/scanners que batem 444 (closed by Traefik) ou 403 | `/var/log/traefik/access.log` | 18789, 8080 |
| `easypanel-auth` | brute-force no painel Easypanel | `/var/log/easypanel/*.log` | 3000 (Easypanel UI) |

## Pré-requisitos (VPS)

```bash
# Já deve estar instalado. Se não:
apt-get update && apt-get install -y fail2ban
systemctl enable fail2ban && systemctl start fail2ban
```

## Como aplicar (Gustavo, manual via SSH)

```bash
# 1. Copiar filter.d para /etc/fail2ban/
scp infra/security/fail2ban/filter.d/*.conf root@100.99.172.84:/etc/fail2ban/filter.d/

# 2. Copiar jail.local para /etc/fail2ban/
scp infra/security/fail2ban/jail.local root@100.99.172.84:/etc/fail2ban/jail.local

# 3. Validar config
ssh root@100.99.172.84 "fail2ban-client -d"

# 4. Reload fail2ban
ssh root@100.99.172.84 "systemctl reload fail2ban"

# 5. Verificar jails ativos
ssh root@100.99.172.84 "fail2ban-client status"
# esperado: 3 jails (traefik-auth, traefik-444, easypanel-auth)

# 6. Smoke test (deve banir IP após 5 falhas)
ssh root@100.99.172.84 "fail2ban-client set traefik-auth banip 192.0.2.1"
ssh root@100.99.172.84 "fail2ban-client status traefik-auth"
```

## Rollback

```bash
ssh root@100.99.172.84 "fail2ban-client unban --all"
ssh root@100.99.172.84 "rm /etc/fail2ban/jail.local /etc/fail2ban/filter.d/traefik-*.conf /etc/fail2ban/filter.d/easypanel-*.conf"
ssh root@100.99.172.84 "systemctl reload fail2ban"
```

## Observações

1. **Whitelist obrigatória**: API Cartório é consumida por Evolution API (webhook) + Chatwoot + N8N. Se o IP do Meta (whatsapp) cair em jail, webhook PIX/WA quebra. Ver `whitelist.local` (a criar) com IPs:
   - Meta WhatsApp Business API: 31.13.x.x, 66.220.x.x, 69.63.x.x, 69.171.x.x (oficial, mas validar)
   - Cloudflare (se aplicável): ranges em https://www.cloudflare.com/ips/
   - Tailscale: 100.64.0.0/10
2. **LGPD**: jails não logam PII. Só IP + timestamp + path. Compatível com `audit_log` (LGPD compliant).
3. **Backup scripts (item meu)**: 5 scripts prontos e validados estruturalmente:
   - `scripts/backup_n8n_workflows.sh`
   - `scripts/backup_postgres_a14.sh`
   - `infra/scripts/backup_n8n.sh`
   - `infra/scripts/check_backup.sh` (watchdog read-only)
   - `infra/scripts/monitor_services.sh` (health check curl-only)

## NÃO-INCLUÍDO nesta PR (depende de outras decisões)

- `whitelist.local` (precisa Gustavo confirmar IPs Meta + Cloudflare + Tailscale)
- `iptables` allowlist (M2.7 está preparando)
- Traefik middleware ratelimit (M2.7 está preparando)
- Cloudflare WAF (BLOQUEADO — apex NS em Hostinger Parking, não Cloudflare; ver Lesson 249)

Modified by Gustavo Almeida