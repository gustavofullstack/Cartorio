# Cloudflare DNS Records — 2notasudi.com.br

**Data:** 2026-07-15 BRT | **Owner:** Gustavo Almeida (UI manual) | **Requisito:** cartorio-sre F4 [P1] / T051-T060
**VPS destino:** 187.77.236.77 (Hostinger h21) | **Dominio raiz:** 2notasudi.com.br

---

## ATENCAO — Provider atual e Cloudflare (NAO Hostinger)

Conflito historico com docs/RUNBOOK_DNS_HOSTINGER.md (2026-07-06). Verificacao 2026-07-15 via dig NS retorna nameservers ns.cloudflare.com — o dominio foi migrado para Cloudflare apos 2026-07-06. A UI antiga do Hostinger NAO controla mais os A records. Todos os procedimentos deste documento acontecem em dash.cloudflare.com.

> Lesson 142 (referencia): DNS provider mismatch — sempre verificar dig NS antes de assumir o provedor.

---

## Tabela canonica de A records (10 dominios)

Status validado em 2026-07-15 via dig +short A:

| # | Host | Tipo | Conteudo | Proxy | TTL | Status 2026-07-15 | Servico | Traefik router |
|---|---|---|---|---|---|---|---|---|
| 1 | api | A | 187.77.236.77 | Proxied | Auto | OK | cartorio_api | cartorio-api-https |
| 2 | flow | A | 187.77.236.77 | Proxied | Auto | OK | n8n workflow engine | cartorio-n8n-flow |
| 3 | whatsapp | A | 187.77.236.77 | Proxied | Auto | OK | Evolution API 2.3.7 | cartorio-evolution |
| 4 | chat | A | 187.77.236.77 | Proxied | Auto | OK | Chatwoot 3.x (legado) | cartorio-chatwoot-chat |
| 5 | agent | A | 187.77.236.77 | Proxied | Auto | OK | OpenClaw 0.4.x | cartorio-openclaw |
| 6 | supbase | A | 187.77.236.77 | Proxied | Auto | OK | Supabase self-hosted (TYPO aceito) | cartorio-supabase-typo |
| 7 | easypanel | A | 187.77.236.77 | Proxied | Auto | OK | Easypanel UI admin | easypanel-admin |
| 8 | chatwoot | A | 187.77.236.77 | Proxied | Auto | NXDOMAIN — CRIAR | Chatwoot canonico | cartorio-chatwoot (pendente merge) |
| 9 | n8n | A | 187.77.236.77 | Proxied | Auto | NXDOMAIN — CRIAR | N8N admin UI | cartorio-n8n (pendente merge) |
| 10 | supabase | A | 187.77.236.77 | Proxied | Auto | NXDOMAIN — CRIAR | Supabase canonico | cartorio-supabase (pendente merge) |

---

## Por que 3 A records novos?

chatwoot, n8n e supabase (canonicos) NAO existem no Cloudflare hoje. Causa raiz mapeada por F2 (2026-07-15):

1. Em 2026-06-24 a squad A configurou Cloudflare com apenas 7 subdominios apontando para 187.77.236.77.
2. chat.2notasudi.com.br ficou como alias legado do Chatwoot.
3. n8n.2notasudi.com.br e supabase.2notasudi.com.br (canonicos) foram planejados mas NAO foram criados por Gustavo na UI do Cloudflare.
4. supbase (typo) virou padrao de fato e esta documentado como DECISAO ACEITA — ver infra/dns/DOMAIN_TYPO_DECISION.md.

Resultado: 7 servicos rodando (api/flow/whatsapp/chat/agent/supbase/easypanel), 3 NXDOMAIN (chatwoot/n8n/supabase) que dependem de Gustavo clicar 3x no botao Add Record.

---

## Validacao automatica apos criacao

Script canonico: scripts/check_dns_health.sh (Makefile target: make dns-check).

```bash
make dns-check
# Esperado apos Gustavo criar os 3 records:
#   [OK]   api.2notasudi.com.br      -> 187.77.236.77
#   [OK]   flow.2notasudi.com.br     -> 187.77.236.77
#   [OK]   whatsapp.2notasudi.com.br -> 187.77.236.77
#   [OK]   chat.2notasudi.com.br     -> 187.77.236.77
#   [OK]   agent.2notasudi.com.br    -> 187.77.236.77
#   [OK]   supbase.2notasudi.com.br  -> 187.77.236.77
#   [OK]   easypanel.2notasudi.com.br -> 187.77.236.77
#   [OK]   chatwoot.2notasudi.com.br -> 187.77.236.77  (NOVO)
#   [OK]   n8n.2notasudi.com.br      -> 187.77.236.77  (NOVO)
#   [OK]   supabase.2notasudi.com.br -> 187.77.236.77  (NOVO)
```

Ver tambem: tests/manual/verify_dns_records.sh (integration test, manual).

---

## Cross-refs

- infra/dns/CLOUDFLARE_RUNBOOK.md — passo-a-passo UI Gustavo
- infra/dns/DOMAIN_TYPO_DECISION.md — typo supbase aceito
- infra/traefik/ROUTERS_PENDENTES.yaml — Traefik routers para os 3 novos hosts
- .harness/memory/lesson-179-dns-cloudflare-fixos-2026-07-15.md — lesson SRE
- .harness/memory/lesson-172-p0-outage-r8-actions.md — outage original
- .harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md — recovery

Modified by Gustavo Almeida
