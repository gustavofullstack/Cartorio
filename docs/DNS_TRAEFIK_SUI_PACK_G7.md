# DNS + Traefik SUI Pack (G7.05.T1 / G7.12 / G7.18.T1)

**One-pager** para Gustavo fechar canais offline. Tempo total ~15–25 min.

---

## 1. Cloudflare DNS (5 min)

Zona `2notasudi.com.br` → criar se NXDOMAIN:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | chatwoot | 187.77.236.77 | Proxied |
| A | n8n | 187.77.236.77 | Proxied |
| A | supabase | 187.77.236.77 | Proxied (alias; typo `supbase` permanece canônico) |

Validar:
```bash
bash scripts/check_dns_health.sh
dig +short chatwoot.2notasudi.com.br A
```

Runbook detalhado: `infra/dns/CLOUDFLARE_RUNBOOK.md`  
Typo: `infra/dns/DOMAIN_TYPO_DECISION.md` (supbase ACEITO)

---

## 2. Traefik routers (5–10 min)

Arquivo: `infra/traefik/ROUTERS_PENDENTES.yaml`  
Merge no dynamic config EasyPanel/Traefik. O router Supabase cobre os dois
aliases públicos (`supbase` canônico legado e `supabase` ortográfico), além de
`chatwoot` e `n8n`.

Canônicos já em uso e OK em geral: `api`, `chat`, `flow`, `whatsapp`, `agent`, `easypanel`, `supbase`.

---

## 3. Redeploy API — radar expanded (2 min)

Código em master local tem `GET /api/v1/health/radar/expanded`  
**Prod ainda 404** → redeploy imagem API após merge.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://api.2notasudi.com.br/api/v1/health/radar/expanded
# meta: 200
make radar-smoke
```

---

## 4. Ordem com Evolution/Chatwoot env

Depois do DNS: corrigir `DATABASE_URL` (Lesson 176) → scale 0→1 se preciso → QR WhatsApp.

Ver: `docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md` · `docs/CHATWOOT_HANDOFF_G7.md`

---

## Definition of Done SUI pack

- [ ] dig chatwoot/n8n/supabase ≠ NXDOMAIN  
- [ ] radar classic: n8n/evolution/chatwoot online  
- [ ] radar expanded HTTP 200  
- [ ] `make g7-validate` deixa de HOLD em dns (ou melhora)

**Modified by Gustavo Almeida + cartorio-sre — G7 Wave 22**
