# Cloudflare Runbook — Adicionar 3 A records (chatwoot / n8n / supabase)

**Data:** 2026-07-15 BRT | **Owner:** Gustavo Almeida | **Tempo estimado:** 5min
**Requisito:** cartorio-sre F4 [P1] / T052 | **Refs:** infra/dns/CLOUDFLARE_DNS_RECORDS.md

---

## Pre-requisitos

- Login em dash.cloudflare.com com a conta que controla o dominio 2notasudi.com.br
- Acesso a UI de DNS (permissao de edicao na zone)
- Confirmar que NAO esta em hpanel.hostinger.com (Provider antigo — NAO funciona mais)

---

## Passo-a-passo UI (3 minutos para criar os 3)

### Step 1 — Login Cloudflare
1. Abrir https://dash.cloudflare.com
2. Login com email da conta (gustavomar.fullstack@gmail.com ou similar — confirmar com Gustavo)
3. Selecionar a conta que possui o dominio 2notasudi.com.br (workspace)

### Step 2 — Selecionar dominio
1. Na home, clicar em 2notasudi.com.br
2. No menu lateral esquerdo, clicar em DNS → Records
3. Voce deve ver os 7 A records ja existentes: api, flow, whatsapp, chat, agent, supbase, easypanel

### Step 3 — Adicionar A record #1: chatwoot
1. Clicar no botao laranja Add record
2. Preencher o formulario:
   - Type: A
   - Name: chatwoot
   - IPv4 address: 187.77.236.77
   - Proxy status: Proxied (laranja — manter, ativa Cloudflare proxy + WAF + SSL)
   - TTL: Auto
   - Comment (opcional): Chatwoot 3.x canonic
3. Clicar Save
4. Confirmar que aparece na lista como: chatwoot.2notasudi.com.br | A | 187.77.236.77 | Proxied

### Step 4 — Adicionar A record #2: n8n
1. Repetir Step 3 com:
   - Name: n8n
   - IPv4 address: 187.77.236.77
   - Comment (opcional): N8N UI admin (separado de flow)

### Step 5 — Adicionar A record #3: supabase
1. Repetir Step 3 com:
   - Name: supabase
   - IPv4 address: 187.77.236.77
   - Comment (opcional): Supabase canonico (separado de supbase typo)

### Step 6 — Salvar tudo e aguardar propagacao
1. Cloudflare salva instantaneamente (NAO precisa de Save geral)
2. Propagacao tipica: 30s para o proxy da Cloudflare, ate 5min para ISPs brasileiros
3. Cloudflare proxy (laranja) faz com que o IP publico visto seja IP Cloudflare (104.x ou 172.x) e NAO 187.77.236.77 — isso e NORMAL.

---

## Validacao pos-criacao

### Validacao 1 — DNS resolve (dig)

```bash
for h in chatwoot n8n supabase; do
  result=$(dig +short $h.2notasudi.com.br A @1.1.1.1)
  echo "$h.2notasudi.com.br -> ${result:-NXDOMAIN}"
done
```

Resultados esperados (com Cloudflare proxy):
- chatwoot.2notasudi.com.br -> 104.21.x.x ou 172.67.x.x (IP Cloudflare — proxy ON)
- n8n.2notasudi.com.br -> idem
- supabase.2notasudi.com.br -> idem

OU (se proxy estiver DNS-only, cinza):
- 187.77.236.77 (IP real)

Em QUALQUER caso, NAO pode retornar vazio.

### Validacao 2 — HTTPS endpoint

```bash
for h in chatwoot n8n supabase; do
  echo "=== $h ==="
  curl -sk -o /dev/null -w "HTTP %{http_code} em %{time_total}s\n" \
    --max-time 10 https://$h.2notasudi.com.br/
done
```

Resultados esperados:
- HTTP 200, 301, 302 ou 404 com body HTML (NUNCA 502/503/000)
- Se 404 com body HTML = Traefik router sem match (ver lesson 172) — isso significa DNS resolveu OK mas router Traefik ainda precisa ser mergeado (ver infra/traefik/ROUTERS_PENDENTES.yaml)
- Se 502/503/000 = app backend down (NAO problema de DNS)

### Validacao 3 — Script canonico

```bash
make dns-check
```

Deve retornar exit 0 com 10/10 OK.

### Validacao 4 — Integration test manual

```bash
bash tests/manual/verify_dns_records.sh
```

Deve imprimir [WORK] para os 3 novos.

---

## Troubleshooting

### Problema: "I dont see Add record button"

Causa: voce esta como Read-only ou em outra zona. Resolucao: pedir ao owner da zone (Gustavo) para promover o seu usuario a Owner/Administrator em Account Home → Members.

### Problema: dig retorna 187.77.236.77 mas curl retorna 502

Isso NAO e problema de DNS. Ver lesson 172-p0-outage-r8-actions.md. Verificar:
1. Traefik esta UP (docker ps | grep traefik)
2. Router Traefik para o host existe em /etc/traefik/dynamic/main.yaml (ver infra/traefik/ROUTERS_PENDENTES.yaml)
3. App backend esta UP (docker ps | grep cartorio_<servico>)

### Problema: dig retorna IP Cloudflare mas curl retorna ERR_CONNECTION_REFUSED

Causa: TLS/SSL no Cloudflare proxy aponta para porta 443 do Traefik mas o Traefik nao esta escutando ou nao tem router. Ver /var/log/traefik/access.log no VPS (via Gustavo).

### Problema: dominio nao aparece na lista do Cloudflare

Causa: o dominio pode ter sido transferido para outra conta. Ver Account Home → Manage domains.

---

## Seguranca

- Cloudflare API tokens NAO devem ser commitados no repo (regra 4 do AGENTS.md)
- Proxy deve permanecer Proxied (laranja) para ativar WAF + DDoS mitigation + SSL universal
- DNS-only (cinza) so para servicos que NAO devem passar pela CDN Cloudflare (ex: servicos internos como backend Postgres)

---

## Cross-refs

- infra/dns/CLOUDFLARE_DNS_RECORDS.md — tabela canonica
- infra/dns/DOMAIN_TYPO_DECISION.md — typo supbase aceito
- infra/traefik/ROUTERS_PENDENTES.yaml — Traefik routers pendentes
- .harness/memory/lesson-179-dns-cloudflare-fixos-2026-07-15.md — lesson SRE
- .harness/memory/lesson-172-p0-outage-r8-actions.md — outage original
- .harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md — recovery

Modified by Gustavo Almeida
