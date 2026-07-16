# Cloudflare DNS Records — 2notasudi.com.br

**Data:** 2026-07-15 BRT (atualizado ciclo 2 cartorio-sre F4 [P0] / T101) | **Owner:** Gustavo Almeida (UI manual) | **Requisito:** cartorio-sre F4 [P1] / T051-T060 + [P0] G1 ciclo 2
**VPS destino:** 187.77.236.77 (Hostinger h21) | **Dominio raiz:** 2notasudi.com.br
**Proxy status observado:** DNS-only (cinza) — `dig` retorna IP real `187.77.236.77` em ambos 1.1.1.1 e 8.8.8.8. **Recomendacao:** manter Proxied (laranja) para ativar WAF/DDoS/SSL universal. Gustavo pode alternar na UI sem perder o A record.

---

## ATENCAO — Provider atual e Cloudflare (NAO Hostinger)

Conflito historico com docs/RUNBOOK_DNS_HOSTINGER.md (2026-07-06). Verificacao 2026-07-15 via dig NS retorna nameservers ns.cloudflare.com — o dominio foi migrado para Cloudflare apos 2026-07-06. A UI antiga do Hostinger NAO controla mais os A records. Todos os procedimentos deste documento acontecem em dash.cloudflare.com.

> Lesson 142 (referencia): DNS provider mismatch — sempre verificar dig NS antes de assumir o provedor.

---

## Tabela canonica de A records (10 dominios)

Status validado em 2026-07-15 via dig +short A @1.1.1.1 e @8.8.8.8 (resolver cross-check):

| # | Host | Tipo | Conteudo esperado | Proxy | TTL | Status 2026-07-15 (dig) | Criado em (estimado) | Servico | Traefik router |
|---|---|---|---|---|---|---|---|---|---|
| 1 | api | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 (1.1.1.1 e 8.8.8.8) | 2026-06-24 (squad A deploy inicial) | cartorio_api | cartorio-api-https |
| 2 | flow | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 | 2026-06-24 | n8n workflow engine | cartorio-n8n-flow |
| 3 | whatsapp | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 | 2026-06-24 | Evolution API 2.3.7 | cartorio-evolution |
| 4 | chat | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 | 2026-06-24 (alias legado Chatwoot) | Chatwoot 3.x (legado) | cartorio-chatwoot-chat |
| 5 | agent | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 | 2026-06-24 | OpenClaw 0.4.x | cartorio-openclaw |
| 6 | supbase | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 | 2026-06-24 (typo aceito) | Supabase self-hosted (TYPO aceito) | cartorio-supabase-typo |
| 7 | easypanel | A | 187.77.236.77 | DNS-only (cinza) | Auto | **OK** — 187.77.236.77 | 2026-06-24 | Easypanel UI admin | easypanel-admin |
| 8 | chatwoot | A | 187.77.236.77 | PENDENTE | Auto | **NXDOMAIN** em 1.1.1.1 e 8.8.8.8 — `[HOLD-GUSTAVO-UI]` | N/A (nao criado) | Chatwoot canonico | cartorio-chatwoot (pendente merge) |
| 9 | n8n | A | 187.77.236.77 | PENDENTE | Auto | **NXDOMAIN** em 1.1.1.1 e 8.8.8.8 — `[HOLD-GUSTAVO-UI]` | N/A (nao criado) | N8N admin UI | cartorio-n8n (pendente merge) |
| 10 | supabase | A | 187.77.236.77 | PENDENTE | Auto | **NXDOMAIN** em 1.1.1.1 e 8.8.8.8 — `[HOLD-GUSTAVO-UI]` | N/A (nao criado) | Supabase canonico (TYPO canonico e supbase) | cartorio-supabase (pendente merge) |

### Resumo do estado (ciclo 2 — 2026-07-15 snapshot)

- **7 hosts resolvem para 187.77.236.77** (proxy OFF / DNS-only): api, flow, whatsapp, chat, agent, supbase, easypanel
- **3 hosts NXDOMAIN** (nao criados): chatwoot, n8n, supabase
- **Recomendacao SRE**: criar os 3 A records NA UI Cloudflare (`[HOLD-GUSTAVO-UI]`) — passo-a-passo em CLOUDFLARE_RUNBOOK.md. Apos criacao, rodar `make dns-check` para confirmar 10/10 OK.

> **Observacao tecnica:** O retorno `187.77.236.77` em ambos os resolvers cross-check indica que o proxy Cloudflare esta **DESLIGADO** (cinza / DNS-only). Em condicao normal com proxy ligado (laranja / Proxied), `dig +short` retorna IP Cloudflare edge (104.21.x.x ou 172.67.x.x). Isso e apenas cosmético para `dig` — o Traefik continua funcionando via Cloudflare proxy (que faz TCP/443 forward para a origin). Porem, perder o proxy remove a protecao WAF/DDoS. Gustavo pode ativar proxy em cada record sem perder o IP de destino.

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

Scripts canonicos:
- `scripts/check_dns_health.sh` (Makefile target: `make dns-check`) — shellcheck OK, validacao rapida
- `infra/dns/SCRIPT_AUTO_VALIDATE.sh` (novo, ciclo 2 / T102) — suporta `--watch` (60s) e `--once` com JSON output estruturado
- `infra/dns/PROMETHEUS_EXPORTER.py` (novo, ciclo 2 / T103) — exporter Prometheus custom para `/metrics`
- `tests/manual/verify_dns_records.sh` (integration test, manual)

```bash
make dns-check                          # saida humana, exit 0/1
bash infra/dns/SCRIPT_AUTO_VALIDATE.sh --once   # mesma saida + JSON
bash infra/dns/SCRIPT_AUTO_VALIDATE.sh --watch  # loop 60s
python3 infra/dns/PROMETHEUS_EXPORTER.py        # sobe HTTP :9919/metrics
```

Esperado apos Gustavo criar os 3 records (todos em 1.1.1.1):

```
[OK]   api.2notasudi.com.br      -> 187.77.236.77
[OK]   flow.2notasudi.com.br     -> 187.77.236.77
[OK]   whatsapp.2notasudi.com.br -> 187.77.236.77
[OK]   chat.2notasudi.com.br     -> 187.77.236.77
[OK]   agent.2notasudi.com.br    -> 187.77.236.77
[OK]   supbase.2notasudi.com.br  -> 187.77.236.77
[OK]   easypanel.2notasudi.com.br -> 187.77.236.77
[OK]   chatwoot.2notasudi.com.br -> <IP Cloudflare ou 187.77.236.77>  (NOVO)
[OK]   n8n.2notasudi.com.br      -> <IP Cloudflare ou 187.77.236.77>  (NOVO)
[OK]   supabase.2notasudi.com.br -> <IP Cloudflare ou 187.77.236.77>  (NOVO)
```

---

## Planilha CSV (parseavel por jq/awk)

Ver `infra/dns/dns_records.csv` — fonte canonica estruturada com colunas:

```
domain,type,value,proxy,ttl,status,created_at_estimated,service
```

Atualizar manualmente via UI apos Gustavo criar os 3 records. Script `SCRIPT_AUTO_VALIDATE.sh --once` regenera coluna `status` automaticamente.

---

## Tabela historica (timestamps de criacao)

Datas sao **estimadas** baseadas em lesson-179 e logs do squad A (2026-06-24 deploy window):

| # | Host | Criado em (BRT, UTC-3) |
|---|---|---|
| 1 | api | 2026-06-24 ~14:00 |
| 2 | flow | 2026-06-24 ~14:05 |
| 3 | whatsapp | 2026-06-24 ~14:10 |
| 4 | chat | 2026-06-24 ~14:15 |
| 5 | agent | 2026-06-24 ~14:20 |
| 6 | supbase | 2026-06-24 ~14:25 |
| 7 | easypanel | 2026-06-24 ~14:30 |
| 8 | chatwoot | PENDENTE |
| 9 | n8n | PENDENTE |
| 10 | supabase | PENDENTE |

**Apos Gustavo concluir**, registrar timestamps reais consultando UI Cloudflare (cada record mostra "Date added"). Atualizar esta tabela e o CSV.

---

## Cross-refs

- infra/dns/CLOUDFLARE_RUNBOOK.md — passo-a-passo UI Gustavo (5min)
- infra/dns/DOMAIN_TYPO_DECISION.md — typo supbase aceito
- infra/dns/SCRIPT_AUTO_VALIDATE.sh — script auto-validate com `--watch`/`--once` (ciclo 2)
- infra/dns/PROMETHEUS_EXPORTER.py — exporter Prometheus :9919 (ciclo 2)
- infra/dns/ALERT_RULES.yaml — regras Alertmanager (ciclo 2, `[HOLD-GUSTAVO-DEPLOY]`)
- infra/dns/MONITORING_DASHBOARD.json — dashboard Grafana 4 panels (ciclo 2)
- infra/dns/dns_records.csv — planilha estruturada (ciclo 2)
- infra/traefik/ROUTERS_PENDENTES.yaml — Traefik routers para os 3 novos hosts
- infra/traefik/MIDDLEWARES_TEMPLATES.yaml — middlewares 3-tier (ciclo 2)
- infra/traefik/DEPLOY_RUNBOOK.md — passo-a-passo merge Traefik VPS (ciclo 2, `[HOLD-GUSTAVO-DEPLOY]`)
- scripts/check_dns_health.sh — script principal (atualizado ciclo 2 com Traefik + JSON)
- .harness/memory/lesson-179-dns-cloudflare-fixos-2026-07-15.md — lesson SRE (ciclo 1)
- .harness/memory/lesson-172-p0-outage-r8-actions.md — outage original
- .harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md — recovery

Modified by Gustavo Almeida
