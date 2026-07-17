# DNS A Records — Wave 28 G7.12.T1 snapshot

**Data:** 2026-07-17 ~14:02 BRT (17:02 UTC)  
**Owner SRE:** cartorio-sre (agent) · **UI provision:** HOLD-GUSTAVO  
**Task:** G7.12.T1 — 3 A records chatwoot / n8n / supabase  
**Status task:** **[~] Wave28 live snapshot** — records **ainda NXDOMAIN** (nao criados na UI)

> Agents **nao** criam DNS sem token Cloudflare (regra: no secrets / no blind mutate).  
> Este doc captura o **estado live** + passos UI exatos (refresh do runbook).

---

## Live dig results (Wave 28)

Command:

```bash
bash scripts/check_dns_health.sh
# + cross-check:
for h in api flow whatsapp chat agent supbase easypanel chatwoot n8n supabase; do
  r1=$(dig +short $h.2notasudi.com.br A @1.1.1.1 | head -1)
  r8=$(dig +short $h.2notasudi.com.br A @8.8.8.8 | head -1)
  echo "$h | 1.1.1.1=${r1:-NXDOMAIN} | 8.8.8.8=${r8:-NXDOMAIN}"
done
dig +short NS 2notasudi.com.br @1.1.1.1
```

### Tabela (2026-07-17)

| # | FQDN | dig @1.1.1.1 | dig @8.8.8.8 | Role | Status |
|---|------|--------------|--------------|------|--------|
| 1 | api.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE | **OK** |
| 2 | flow.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE | **OK** |
| 3 | whatsapp.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE | **OK** |
| 4 | chat.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE | **OK** |
| 5 | agent.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE | **OK** |
| 6 | supbase.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE (typo aceito) | **OK** |
| 7 | easypanel.2notasudi.com.br | 187.77.236.77 | 187.77.236.77 | CORE | **OK** |
| 8 | chatwoot.2notasudi.com.br | *(empty)* | *(empty)* | OPTIONAL | **NXDOMAIN** |
| 9 | n8n.2notasudi.com.br | *(empty)* | *(empty)* | OPTIONAL | **NXDOMAIN** |
| 10 | supabase.2notasudi.com.br | *(empty)* | *(empty)* | OPTIONAL | **NXDOMAIN** |

**Resumo:** **7 OK / 3 FAIL** — exactamente o HOLD esperado desde 2026-07-15 (ciclo F4 / G6).

`scripts/check_dns_health.sh` (pre-soft): exit **1** com mensagem de provisionar via runbook.

### NS observados (honestidade)

```
dig +short NS 2notasudi.com.br @1.1.1.1
# lunar.dns-parking.com.
# solar.dns-parking.com.
```

Docs historicos (`infra/dns/CLOUDFLARE_DNS_RECORDS.md`) citavam nameservers `*.ns.cloudflare.com`.  
**Wave28 dig** retornou **dns-parking** (Hostinger parking NS). Ainda assim os 7 A records CORE resolvem para `187.77.236.77`.

**Acao Gustavo antes de clicar DNS:**

1. Confirmar **onde** a zona autoritativa esta hoje:
   - Cloudflare dash (`dash.cloudflare.com`) **ou**
   - Hostinger hPanel DNS **ou**
   - outro painel apontado pelos NS atuais
2. `dig NS 2notasudi.com.br` deve bater com o painel onde se edita A records.
3. Se NS ainda forem parking e o objetivo for Cloudflare, primeiro migrar NS (propagacao 1–24h), **depois** criar os 3 A.

Nao assumir Cloudflare so porque o runbook antigo diz Cloudflare — **sempre `dig NS` primeiro** (Lesson 142 / 179).

---

## Os 3 A records a criar (alvo)

| Name | Type | IPv4 | Proxy recomendado | Comment |
|------|------|------|-------------------|---------|
| `chatwoot` | A | `187.77.236.77` | Proxied (laranja) se CDN/WAF desejado; DNS-only se paridade com os 7 atuais | Chatwoot 3.x canonico |
| `n8n` | A | `187.77.236.77` | idem | N8N UI admin (separado de `flow`) |
| `supabase` | A | `187.77.236.77` | idem | Supabase canonico (separado de typo `supbase`) |

**Nao apagar** `supbase` (typo ratificado G7.12.T4 / `infra/dns/DOMAIN_TYPO_DECISION.md`).

---

## Passo-a-passo UI (refresh CLOUDFLARE_RUNBOOK)

Fonte canonica: [`infra/dns/CLOUDFLARE_RUNBOOK.md`](../infra/dns/CLOUDFLARE_RUNBOOK.md).  
Se a zona **nao** estiver na Cloudflare, adaptar os cliques para o painel que `dig NS` indicar (Hostinger DNS etc.) — os **campos** (Type/Name/IPv4) sao iguais.

### Se zona em Cloudflare

1. Abrir https://dash.cloudflare.com → login da conta dona de `2notasudi.com.br`
2. Selecionar dominio → **DNS → Records**
3. Confirmar os 7 A existentes: `api`, `flow`, `whatsapp`, `chat`, `agent`, `supbase`, `easypanel`
4. **Add record** ×3:

#### Record 1 — chatwoot

- Type: **A**
- Name: **chatwoot**
- IPv4 address: **187.77.236.77**
- Proxy status: **Proxied** (laranja) recomendado; ou DNS-only para paridade com snapshot atual
- TTL: Auto
- Comment: `Chatwoot 3.x canonic — G7.12.T1`
- Save

#### Record 2 — n8n

- Type: **A**
- Name: **n8n**
- IPv4: **187.77.236.77**
- Proxy/TTL: igual ao anterior
- Comment: `N8N UI admin — G7.12.T1`
- Save

#### Record 3 — supabase

- Type: **A**
- Name: **supabase**
- IPv4: **187.77.236.77**
- Proxy/TTL: igual
- Comment: `Supabase canonic (not supbase typo) — G7.12.T1`
- Save

Propagacao tipica: 30s–5min (proxy Cloudflare); ate 24h em caches de ISP.

### Se zona em Hostinger / outro

1. hPanel (ou painel do NS) → Dominios → `2notasudi.com.br` → DNS / Zone Editor
2. Add **A** records com os mesmos Name/IPv4 da tabela
3. Nao criar CNAME colidindo com A no mesmo label

### API Cloudflare (opcional — HOLD token)

```bash
# NAO commitar token. Arquivo local gitignored:
# .secrets/cloudflare.env → CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ZONE_ID=...
# bash scripts/cloudflare_dns.sh   # se disponivel e token valido
```

Sem `CLOUDFLARE_API_TOKEN` valido o agent **marca [~]** e para.

---

## Validacao pos-criacao

```bash
# Soft (default Wave28): exit 0 se core 7 OK mesmo com 3 HOLD
make dns-check

# Strict: exit 0 so com 10/10
make dns-check-strict
# ou: MODE=strict bash scripts/check_dns_health.sh
# ou: DNS_CHECK_STRICT=1 bash scripts/check_dns_health.sh

for h in chatwoot n8n supabase; do
  echo "$h -> $(dig +short $h.2notasudi.com.br A @1.1.1.1 | head -1 || echo NXDOMAIN)"
done
```

Esperado apos UI:

- dig nao-vazio (187.77.236.77 **ou** IP Cloudflare 104.x/172.x se Proxied)
- `make dns-check-strict` → exit 0
- Marcar G7.12.T1 **[x]** no `SUPER_PLANO_G7_100_TASKS.md` so apos dig live 10/10

HTTPS 502 apos DNS OK = Traefik router / backend (ver `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md` + `infra/traefik/ROUTERS_PENDENTES.yaml`) — **nao** e falha de DNS.

---

## Criterio de honestidade (agent close)

| Condicao dig | Marcacao G7.12.T1 |
|--------------|-------------------|
| 3 FQDNs resolvem | **[x]** Wave28 (ou data live) |
| 3 ainda NXDOMAIN | **[~]** Wave28 live snapshot (este doc) |
| Token Cloudflare usado e records criados | **[x]** + atualizar tabela + CSV |

**Wave28 close:** **[~]** — dig confirma NXDOMAIN em chatwoot/n8n/supabase.

---

## Cross-refs

- `infra/dns/CLOUDFLARE_RUNBOOK.md` — UI 5min
- `infra/dns/CLOUDFLARE_DNS_RECORDS.md` — tabela canonica 10 hosts
- `infra/dns/DOMAIN_TYPO_DECISION.md` — supbase aceito
- `scripts/check_dns_health.sh` — soft/strict (G7.12.T2)
- `docs/DNS_TRAEFIK_SUI_PACK_G7.md` — pack DNS+Traefik
- `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`
- Lesson 179 DNS Cloudflare fixos; Lesson 142 provider mismatch

**Modified by Gustavo Almeida — G7 Wave 28 cartorio-sre G7.12.T1**
