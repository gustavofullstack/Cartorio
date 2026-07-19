# Traefik ROUTERS_PENDENTES merge (G7.12.T3)

**Status:** `[x] Wave27` merge artifact ready — **deploy SUI** (não aplica no VPS sozinho)  
**Artifact:** [`infra/traefik/routers-merged-g7.yaml`](../infra/traefik/routers-merged-g7.yaml)  
**Source template:** [`infra/traefik/ROUTERS_PENDENTES.yaml`](../infra/traefik/ROUTERS_PENDENTES.yaml)  
**Date:** 2026-07-17  

---

## Objetivo

Fechar NXDOMAIN / 404 edge para:

| Host | Router name | Service Swarm | Porta |
|------|-------------|---------------|-------|
| `chatwoot.2notasudi.com.br` | `cartorio-chatwoot` | `cartorio_chatwoot` | 3000 |
| `n8n.2notasudi.com.br` | `cartorio-n8n` | `cartorio_n8n` | 5678 |
| `supbase.2notasudi.com.br` **e** `supabase.2notasudi.com.br` | `cartorio-supabase` | `cartorio_supabase` | 8000 (Kong) |

**Já OK (não re-mergear):** `api`, `chat`, `flow`, `whatsapp`, `agent`, `easypanel`
**Aliases:** `supbase` é canônico legado; o artefato cobre também `supabase` para
que os dois apontem ao mesmo Kong. O merge ainda é HOLD operacional.

---

## Pré-requisitos (não pular)

1. **DNS Cloudflare** (G7.12.T1) — runbook: `infra/dns/CLOUDFLARE_RUNBOOK.md`  
   Pack one-pager: `docs/DNS_TRAEFIK_SUI_PACK_G7.md`  
   ```bash
   dig +short chatwoot.2notasudi.com.br A @1.1.1.1
   dig +short n8n.2notasudi.com.br A @1.1.1.1
   dig +short supbase.2notasudi.com.br A @1.1.1.1
   dig +short supabase.2notasudi.com.br A @1.1.1.1
   bash scripts/check_dns_health.sh
   ```
2. Serviços UP no Swarm (`docker service ls | grep cartorio_`).  
3. SSH ou EasyPanel access (Tailscale se `docs/TAILSCALE_RESTORE_G7.md` ok).  
4. Middlewares `@file` (`default-security-headers`, `rate-limit-*`) existem no dynamic base.  
   Se faltarem → remover linhas `middlewares:` do snippet ou criar stubs.

---

## Merge steps (copy-paste VPS)

```bash
# 0) Artifact no repo (local)
ls infra/traefik/routers-merged-g7.yaml

# 1) No VPS — backup
cp /etc/traefik/dynamic/main.yaml{,.bak-$(date +%Y%m%d%H%M)}

# 2) Editar main.yaml: sob http.routers e http.services, colar as chaves de
#    routers-merged-g7.yaml SEM apagar routers existentes.
#    Alternativa: yq/merge se o layout for multi-file dynamic dir.

# 3) Validar sintaxe YAML
python3 -c "import yaml; yaml.safe_load(open('/etc/traefik/dynamic/main.yaml'))"

# 4) Reload Traefik (EasyPanel container name pode variar)
docker kill -s HUP easypanel-traefik
# ou: docker service update --force $(docker service ls -q -f name=traefik)

# 5) Validar edge
for h in chatwoot n8n supbase supabase; do
  code=$(curl -sk -o /dev/null -m 15 -w '%{http_code}' "https://$h.2notasudi.com.br/")
  echo "$h → $code"
done
```

Interpretação (`docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`):

| HTTP | Significado |
|------|-------------|
| 200/301/302 | Router + upstream OK |
| 502 | Router OK, **upstream** down/env errada (Lesson 176) |
| 404 EasyPanel | Router ainda ausente |
| 000 / NXDOMAIN | DNS (G7.12.T1), não Traefik |

---

## Rollback

```bash
cp /etc/traefik/dynamic/main.yaml.bak-YYYYMMDDHHMM /etc/traefik/dynamic/main.yaml
docker kill -s HUP easypanel-traefik
```

---

## Definition of Done

- [x] Artifact `routers-merged-g7.yaml` no repo  
- [x] Steps documentados + cross-ref DNS pack  
- [ ] DNS A records criados (SUI G7.12.T1)  
- [ ] Merge aplicado no VPS (SUI)  
- [ ] `curl` chatwoot/n8n ≠ 000/NXDOMAIN  

**Modified by Gustavo Almeida — G7 Wave 27**
