# Cert Let's Encrypt — Expiry Monitor (G7.13.T1)

| Campo | Valor |
|-------|--------|
| **Task** | G7.13.T1 — Cert LE expiry monitor |
| **Wave** | G7 Wave 25 (doc; automação leve) |
| **Rein** | cartorio-sre |
| **Edge** | Traefik (`easypanel-traefik`) + resolver `letsencrypt` |
| **Regra** | Sem mutar prod; checagens são read-only (`openssl` / HTTPS) |

---

## 0. TL;DR

Traefik renova LE automaticamente via ACME. O risco operacional é **falha silenciosa de renew** (DNS, rate-limit LE, volume `acme.json` corrompido). Monitor = **alertar se `notAfter` &lt; 21 dias** em qualquer FQDN canônico.

---

## 1. Domínios a vigiar

| FQDN | Serviço atrás |
|------|----------------|
| `api.2notasudi.com.br` | cartorio_api |
| `flow.2notasudi.com.br` | n8n |
| `whatsapp.2notasudi.com.br` | evolution |
| `chat.2notasudi.com.br` | chatwoot |
| `agent.2notasudi.com.br` | openclaw |
| `supbase.2notasudi.com.br` | supabase kong |
| `easypanel.2notasudi.com.br` | painel |

Aliases com NXDOMAIN (`chatwoot` / `n8n` / `supabase`) **não** entram no monitor até o DNS existir (`docs/DNS_TRAEFIK_SUI_PACK_G7.md`).

---

## 2. Check manual (qualquer laptop com openssl)

```bash
check_le() {
  local host="$1"
  echo "=== $host ==="
  echo | openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null \
    | openssl x509 -noout -dates -subject 2>/dev/null || echo "FAIL: TLS/handshake"
}

for h in api flow whatsapp chat agent supbase easypanel; do
  check_le "${h}.2notasudi.com.br"
done
```

### 2.1 Dias restantes (one-liner)

```bash
host=api.2notasudi.com.br
end=$(echo | openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null \
  | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
# end ex: "Oct 12 12:00:00 2026 GMT"
python3 - <<PY
from datetime import datetime, timezone
import os
end = os.environ.get("END") or """$end"""
# fallback parse via dateutil-less:
from email.utils import parsedate_to_datetime
try:
    dt = parsedate_to_datetime(end) if False else datetime.strptime(end, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
except Exception as e:
    # openssl format: "Oct 12 12:00:00 2026 GMT"
    dt = datetime.strptime(end.strip(), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
now = datetime.now(timezone.utc)
print(f"days_left={(dt-now).days} notAfter={dt.isoformat()}")
PY
```

Simpler portable:

```bash
echo | openssl s_client -servername api.2notasudi.com.br -connect api.2notasudi.com.br:443 2>/dev/null \
  | openssl x509 -noout -checkend $((21*86400)) \
  && echo "OK: >21d" || echo "ALERT: expira em <=21 dias ou cert ilegível"
```

- Exit **0** do `-checkend` = ainda válido além da janela.
- Exit **1** = **ALERTA** (renovar / investigar Traefik ACME).

---

## 3. Onde mora o material ACME (VPS — read-only)

```bash
# Via SSH Tailscale (autorizado)
ssh root@100.99.172.84

# Caminhos típicos EasyPanel/Traefik (validar no host):
# - volume acme.json do service easypanel-traefik
# - /letsencrypt/acme.json (alguns layouts)
docker service ps easypanel-traefik
# docker exec <traefik_task> ls -la /letsencrypt/ 2>/dev/null || true
```

> Tool legado `letsencrypt_list` no coding-vps MCP foi **deprecated** — usar `openssl` externo ou `docker exec` + `acme.json` (ver `scripts/coding_vps_mcp_orchestrator.py`).

**Não** commitar `acme.json` (chaves privadas).

---

## 4. Monitor automatizado (recomendado)

### 4.1 Cron local / VPS (diário)

```bash
# /etc/cron.d/cartorio-le-expiry  (exemplo — instalar só com aprovação)
# 0 7 * * * root /usr/local/bin/cartorio-le-check.sh
```

Script sugerido (`scripts/check_le_expiry.sh` — criar no host ou no repo se ainda não existir):

```bash
#!/usr/bin/env bash
set -euo pipefail
WINDOW_DAYS="${WINDOW_DAYS:-21}"
SECS=$((WINDOW_DAYS * 86400))
FAIL=0
for h in api flow whatsapp chat agent supbase easypanel; do
  fqdn="${h}.2notasudi.com.br"
  if echo | openssl s_client -servername "$fqdn" -connect "${fqdn}:443" 2>/dev/null \
      | openssl x509 -noout -checkend "$SECS" >/dev/null 2>&1; then
    echo "OK  $fqdn (>$WINDOW_DAYS d)"
  else
    echo "ALERT $fqdn (<=$WINDOW_DAYS d ou TLS fail)"
    FAIL=1
  fi
done
exit $FAIL
```

### 4.2 Alert routing

| Severidade | Condição | Ação |
|------------|----------|------|
| **P2** | qualquer host ≤21d | Telegram GRUPO ops + issue GitHub |
| **P1** | qualquer host ≤7d | page Gustavo + checar Traefik logs ACME |
| **P0** | cert expirado (browser NET::ERR) | recovery: forçar renew Traefik / fix DNS |

Notificação pode reutilizar o mesmo padrão de `deploy.yml` (Telegram bot secrets) ou N8N cron workflow.

### 4.3 Prometheus (futuro)

Exporter `ssl_exporter` / blackbox `module=tls` com alerta:

```yaml
# esboço — não aplicado neste doc
- alert: CertExpiringSoon
  expr: probe_ssl_earliest_cert_expiry - time() < 21 * 24 * 3600
  labels: {severity: p2}
```

---

## 5. Runbook se ALERT

1. Confirmar com `openssl s_client` (§2) — não confiar só no browser cache.
2. DNS do host ainda aponta para `187.77.236.77`? (`dig +short`)
3. Traefik 1/1? `docker service ps easypanel-traefik`
4. Logs ACME: `docker service logs --tail 200 easypanel-traefik | grep -i acme`
5. Rate-limit Let's Encrypt? aguardar / usar staging só em lab.
6. Volume `acme.json` legível e não truncado?
7. **Não** apagar `acme.json` sem backup — perde todos os certs e pode estourar rate limit.
8. Após fix: re-rodar §2; documentar em incident se P1+.

Playbook irmão: `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md` (se o sintoma for 000/502, pode ser upstream, não cert).

---

## 6. Aceite da task G7.13.T1

- [x] Domínios canônicos listados
- [x] Comando read-only de checagem documentado (`openssl -checkend`)
- [x] Limiares 21d / 7d definidos
- [x] Runbook de falha de renew
- [ ] (Opcional follow-up) script commitado em `scripts/check_le_expiry.sh` + cron VPS + alerta Telegram

---

## 7. Referências

- `docs/DEPLOYMENT.md` — Traefik + LE
- `infra/traefik/ROUTERS_PENDENTES.yaml` — `certResolver: letsencrypt`
- `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`
- `docs/MONITORING_GUIDE.md`

---

**Modified by Gustavo Almeida** — G7 Wave 25 (G7.13.T1)
