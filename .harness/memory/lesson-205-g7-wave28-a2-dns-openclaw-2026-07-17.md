---
name: g7-wave28-a2-dns-openclaw
description: Wave 28 cartorio-sre — DNS soft/strict check (7 core OK exit 0), live A-record snapshot 3 NXDOMAIN HOLD, OpenClaw operator token scopes runbook.
type: project
date: 2026-07-17
agent: cartorio-sre
wave: G7-W28
tags: [g7, sre, dns, soft-mode, cloudflare, openclaw, scopes, hold-gustavo]
---

# Lesson 205 — G7 Wave 28 A2 DNS + OpenClaw scopes (2026-07-17)

## TL;DR

| Task | Deliverable | Status |
|------|-------------|--------|
| G7.12.T1 | `docs/DNS_A_RECORDS_WAVE28_G7.md` + live dig | **[~]** 3 NXDOMAIN (honest) |
| G7.12.T2 | `scripts/check_dns_health.sh` MODE soft\|strict + `make dns-check` / `dns-check-strict` | **[x]** soft exit 0 |
| G7.14.T4 | `docs/OPENCLAW_OPERATOR_TOKEN_SCOPES_G7.md` | **[x]** runbook; token live HOLD |

## Dig live (Wave28 ~17:02 UTC)

- **7 CORE OK** → `187.77.236.77` (api, flow, whatsapp, chat, agent, supbase, easypanel) em 1.1.1.1 e 8.8.8.8
- **3 OPTIONAL NXDOMAIN** → chatwoot, n8n, supabase
- **NS observados:** `lunar.dns-parking.com` / `solar.dns-parking.com` (nao Cloudflare `*.ns.cloudflare.com` dos docs 2026-07-15)
- Sem `CLOUDFLARE_API_TOKEN`: agent **nao** cria records → mark [~]

## Key lessons

1. **Soft vs strict DNS gate** — CI local/`make dns-check` deve ser verde no HOLD 7/10; strict (`DNS_CHECK_STRICT=1`) so quando Gustavo provisionar os 3 A. Evita falso vermelho no loop G7.
2. **Sempre `dig NS` antes do painel** — runbook Cloudflare pode estar desatualizado se NS migraram para parking/Hostinger. Criar A no painel errado = zero efeito (Lesson 142/179).
3. **OpenClaw scopes=[] e health-only** — `hello-ok.auth.scopes` vazio bloqueia `agents.create` mesmo se connect.params pede read/write (Lesson 177). DoD = scopes non-empty com `operator.read`+`operator.write`.
4. **No secret commits** — token operator so vault / EasyPanel / `.secrets/` gitignored; docs so placeholders + drill.

## Offline validation

```bash
make dns-check            # exit 0 (soft, 7/7 core)
make dns-check-strict     # exit 1 ate 10/10
# scopes drill: ver docs/OPENCLAW_OPERATOR_TOKEN_SCOPES_G7.md secao A (env HOLD)
```

## HOLD-GUSTAVO

- UI: 3 A records chatwoot/n8n/supabase → `187.77.236.77` (confirmar painel via dig NS)
- Runtime: operator token com scopes non-empty + re-run WS drill
- Opcional: Traefik routers merge se HTTPS 404/502 apos DNS OK

## Cross-refs

- `infra/dns/CLOUDFLARE_RUNBOOK.md`
- `infra/dns/CLOUDFLARE_DNS_RECORDS.md`
- Lesson 177 OpenClaw E8 scopes
- Lesson 179 DNS Cloudflare fixos
- Lesson 201 Wave27 Traefik obs (sibling SRE)

**Modified by Gustavo Almeida — G7 Wave 28 cartorio-sre**
