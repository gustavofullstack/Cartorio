---
id: lesson-179
title: DNS Cloudflare fixos para os 3 NXDOMAIN (chatwoot / n8n / supabase)
date: 2026-07-15
type: project + reference
scope: cartorio-sre
task: F4 [P1] / T051-T060
---

# Lesson 179 — DNS Cloudflare fixos (3 NXDOMAIN → 10/10 OK)

## Contexto

Em 2026-07-15 a missao F4 [P1] do cartorio-sre identificou 3 subdominios prod com NXDOMAIN persistente (chatwoot.2notasudi.com.br, n8n.2notasudi.com.br, supabase.2notasudi.com.br). Os outros 7 subdominios (api/flow/whatsapp/chat/agent/supbase/easypanel) ja estavam apontando corretamente para 187.77.236.77.

Verificacao (dig +short A @1.1.1.1 em 2026-07-15):
- 7/10 com IP (187.77.236.77 ou IP Cloudflare proxy)
- 3/10 vazio (NXDOMAIN)

Causa raiz: os 3 A records correspondentes nao existem no Cloudflare. UI manual do Gustavo e o caminho — sem Cloudflare API key configurada em .secrets/.

## Acao

Suite F4 produziu 8 entregaveis:

1. **infra/dns/CLOUDFLARE_DNS_RECORDS.md** — tabela canonica com 10 hosts e seus status, IPs esperados, e servico backend
2. **infra/dns/CLOUDFLARE_RUNBOOK.md** — passo-a-passo UI Gustavo (5min) para adicionar os 3 A records
3. **infra/dns/DOMAIN_TYPO_DECISION.md** — formaliza a decisao de manter supbase (typo) e nao renomear
4. **infra/traefik/ROUTERS_PENDENTES.yaml** — template Traefik routers para os 3 hosts (HOLD-GUSTAVO-DEPLOY ate merge manual)
5. **scripts/check_dns_health.sh** — script bash que itera os 10 hosts e reporta OK/NXDOMAIN (Makefile target: make dns-check)
6. **tests/manual/verify_dns_records.sh** — integration test manual que assume DNS criado e valida
7. **Makefile raiz** — adicionado target dns-check
8. **Esta lesson** — referencia cross-rein para o fix

## Validacao executada (2026-07-15)

```bash
for h in api flow whatsapp chat agent supbase easypanel chatwoot n8n supabase; do
  result=$(dig +short $h.2notasudi.com.br A @1.1.1.1)
  echo "$h.2notasudi.com.br -> ${result:-NXDOMAIN}"
done
```

Resultado (antes do Gustavo criar):
- api.2notasudi.com.br -> 187.77.236.77 [OK]
- flow.2notasudi.com.br -> 187.77.236.77 [OK]
- whatsapp.2notasudi.com.br -> 187.77.236.77 [OK]
- chat.2notasudi.com.br -> 187.77.236.77 [OK]
- agent.2notasudi.com.br -> 187.77.236.77 [OK]
- supbase.2notasudi.com.br -> 187.77.236.77 [OK]
- easypanel.2notasudi.com.br -> 187.77.236.77 [OK]
- chatwoot.2notasudi.com.br -> [NXDOMAIN]
- n8n.2notasudi.com.br -> [NXDOMAIN]
- supabase.2notasudi.com.br -> [NXDOMAIN]

Pos-fix Gustavo (esperado):
- 10/10 com IP. make dns-check retorna exit 0.

## Lições criticas

### L1 — DNS provider mudou silenciosamente (NAO e mais Hostinger)

docs/RUNBOOK_DNS_HOSTINGER.md (2026-07-06) instruia Gustavo a adicionar A records via hpanel.hostinger.com. Porem, em algum momento entre 2026-07-06 e 2026-07-15, o dominio 2notasudi.com.br foi migrado para Cloudflare (NS agora aponta para ns.cloudflare.com). A UI antiga do Hostinger NAO funciona mais para DNS.

**Regra canonica (reforca Lesson 142):** SEMPRE verificar `dig NS <dominio> @1.1.1.1` antes de assumir o provedor. DNS provider mismatch e causa raiz de incidentes silenciosos.

### L2 — Traefik 404 != Traefik down (reforca Lesson 172/176)

Apos criar os A records no Cloudflare, o teste mais rapido para validar que DNS resolveu e o app backend esta OK:

```bash
curl -sk -o /dev/null -w "%{http_code} %{size_download}\n" --max-time 10 https://chatwoot.2notasudi.com.br/
```

Resultados possiveis:
- 000 = DNS NAO resolveu (NXDOMAIN ou timeout) — problema de DNS
- 502/503 = Traefik alcancou o backend mas o backend retornou erro — problema de app
- 404 com body HTML (size > 1000) = Traefik roteou mas nenhum router faz match para este Host — problema de router (ver infra/traefik/ROUTERS_PENDENTES.yaml)
- 200/301/302 = sucesso

**Health check SEMPRE em duas etapas:**
1. DNS resolve? (`dig +short` nao vazio)
2. Router existe? (`cat /etc/traefik/dynamic/main.yaml | grep Host`)

Nunca declarar app down antes de checar o router.

### L3 — Typo aceito nao e vergonha, e decisao de produto

supbase.2notasudi.com.br (typo) virou canonico. Foi decidido em 2026-06-25 e reconfirmado em 2026-07-15. Renomear agora = breaking change massivo (signed URLs do storage PII + referencias em 6+ arquivos + audit log + LGPD). Custo >> beneficio. Principio da menor mudanca vence.

## Cross-refs

- infra/dns/CLOUDFLARE_DNS_RECORDS.md
- infra/dns/CLOUDFLARE_RUNBOOK.md
- infra/dns/DOMAIN_TYPO_DECISION.md
- infra/traefik/ROUTERS_PENDENTES.yaml
- scripts/check_dns_health.sh
- tests/manual/verify_dns_records.sh
- .harness/memory/lesson-142-quinzenal-report-2026-07-06.md — DNS provider mismatch
- .harness/memory/lesson-172-p0-outage-r8-actions.md — Traefik 502 outage
- .harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md — Traefik 502 recovery
- .harness/memory/MEMORY.md — secao 2026-07-15 (atualizar com este lesson)

## Status

- [x] Documentacao criada
- [x] Script validacao criado
- [x] Makefile target criado
- [x] Cross-refs registrados
- [HOLD-GUSTAVO] Criar 3 A records no Cloudflare UI
- [HOLD-GUSTAVO] Mergear infra/traefik/ROUTERS_PENDENTES.yaml no /etc/traefik/dynamic/main.yaml

Modified by Gustavo Almeida
