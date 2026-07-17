# Playbook — 502 vs NXDOMAIN vs Connection Refused (G7.13.T3)

| Campo | Valor |
|-------|--------|
| **Task** | G7.13.T3 — 502 vs NXDOMAIN playbook |
| **Wave** | G7 Wave 24 |
| **Agente** | cartorio-sre (slot A2) |
| **Fontes** | Lesson 176, Lesson 172, `OUTAGE_RECOVERY_RUNBOOK`, `DNS_TRAEFIK_SUI_PACK_G7`, probe 2026-07-17 |
| **Regra** | Diagnóstico **sem mutar prod** até causa classificada; SSH só com autorização Gustavo |

---

## 0. TL;DR (30 segundos)

```
curl falhou?
  │
  ├─ dig A vazio / NXDOMAIN ──────────────► DNS (Cloudflare/Hostinger) — NÃO é Traefik
  ├─ dig OK + curl code 000 / refused ────► rede / firewall / host down / TLS hang
  ├─ dig OK + TLS OK + HTTP 502 ──────────► Traefik UP, upstream DOWN ou misconfig
  ├─ dig OK + HTTP 404 (easypanel page) ──► router/serviço ausente no Traefik
  └─ dig OK + HTTP 200/301/302 ───────────► edge OK — olhar app/auth, não DNS
```

**Nunca** reinicie Traefik como primeiro passo em 502 isolado.  
**Sempre** leia o **backend name** no access log do Traefik (Lesson 176).

---

## 1. Matriz de sintomas

| Sintoma observado | `dig +short FQDN A` | `curl -sk -o /dev/null -w '%{http_code}' https://FQDN/` | Camada culpada | Ação típica |
|-------------------|---------------------|----------------------------------------------------------|----------------|-------------|
| **NXDOMAIN** | vazio | `000` (resolve fail) | **DNS** | Criar A record → `187.77.236.77` |
| **Connection refused** | IP ok | `000` + `Connection refused` | Host/porta 80/443 | VPS down, Traefik 0/1, firewall |
| **Timeout / hang** | IP ok | `000` + timeout | Rede/path/MTU/WAF | traceroute, Cloudflare proxy, VPS |
| **502 Bad Gateway** | IP ok | `502` | **Upstream** (app Swarm) | Logs backend + env DB (Lesson 176) |
| **404 easypanel error-page** | IP ok | `404` | Router Traefik / label | Merge `ROUTERS_PENDENTES.yaml` |
| **503 Service Unavailable** | IP ok | `503` | Backend sem tasks healthy | `docker service ps` |
| **200 / 302** | IP ok | `200`/`302` | OK na borda | Problema é app/auth/conteúdo |

### 1.1 Domínios canônicos vs alias

| FQDN | Função | DNS típico (2026-07) | HTTP típico se app down |
|------|--------|----------------------|-------------------------|
| `api.2notasudi.com.br` | FastAPI | OK → 187.77.236.77 | 502 se `cartorio_api` 0/1 |
| `flow.2notasudi.com.br` | N8N (canônico) | OK | 502/404 se n8n down |
| `n8n.2notasudi.com.br` | N8N alias desejado | **NXDOMAIN** | 000 |
| `chat.2notasudi.com.br` | Chatwoot (canônico) | OK | **502** se chatwoot 0/1 |
| `chatwoot.2notasudi.com.br` | Chatwoot alias | **NXDOMAIN** | 000 |
| `whatsapp.2notasudi.com.br` | Evolution | OK | **502** se evolution 0/1 |
| `agent.2notasudi.com.br` | OpenClaw | OK | 502 se gateway down |
| `supbase.2notasudi.com.br` | Supabase (**typo aceito**) | OK | 404/502 conforme router |
| `supabase.2notasudi.com.br` | Alias “correto” | **NXDOMAIN** | 000 |
| `easypanel.2notasudi.com.br` | Painel | OK | 502 se easypanel down |

### 1.2 Probe de referência (Wave 24 — 2026-07-17, sem SSH)

| Host | dig @1.1.1.1 | HTTP |
|------|--------------|------|
| api | 187.77.236.77 | **200** |
| flow | 187.77.236.77 | **404** |
| whatsapp | 187.77.236.77 | **502** |
| chat | 187.77.236.77 | **502** |
| agent | 187.77.236.77 | **200** |
| supbase | 187.77.236.77 | **404** |
| easypanel | 187.77.236.77 | **200** |
| **chatwoot** | **NXDOMAIN** | **000** |
| **n8n** | **NXDOMAIN** | **000** |
| **supabase** | **NXDOMAIN** | **000** |

Interpretação rápida:

- `whatsapp`/`chat` **502** = DNS+Traefik edge OK → **upstream** evolution/chatwoot (padrão Lesson 176: DB env).
- `chatwoot`/`n8n`/`supabase` **NXDOMAIN** = **não** é bug do container — falta A record (HOLD-GUSTAVO UI).
- `flow` **404** com DNS OK = edge responde, rota/serviço N8N incompleta ou error-page EasyPanel (não confundir com NXDOMAIN).

---

## 2. Traefik access log — padrão de backend name (Lesson 176)

### 2.1 Regra de ouro

> **Traefik 502 ≠ Traefik down.**  
> Se o access log mostra request HTTP/2 e status 502 com backend `http-cartorio_<serviço>-0@file` (ou `https-cartorio_…@file`), o proxy **roteou** e o **upstream** falhou.

Padrões observados em prod:

| Padrão no log | Significado |
|---------------|-------------|
| `http-cartorio_api-0@file` / service cartorio_api | Upstream API |
| `http-cartorio_chatwoot-0@file` | Upstream Chatwoot → 502 se 0/1 ou crashloop |
| `http-cartorio_evolution-api-0@file` | Upstream Evolution |
| `https-cartorio_supabase-1@file` | Router Supabase (já houve mis-label apontando p/ `easypanel:3000`) |
| 200 em `/health` + 502 em outros hosts | Traefik saudável; só alguns backends |

### 2.2 Como ler (VPS — somente com SSH autorizado)

```bash
# Logs Traefik (últimas linhas com 502)
docker service logs easypanel-traefik --tail 200 --no-trunc 2>&1 | grep -E '502|cartorio_'

# Routers/services (se API Traefik local habilitada)
curl -fsS http://localhost:8080/api/http/routers 2>/dev/null | jq '.[].name' | head

# Réplicas
docker service ls --format 'table {{.Name}}\t{{.Replicas}}' | grep -E 'cartorio|traefik'
```

### 2.3 Anti-padrões

| Erro comum | Por que é errado |
|------------|------------------|
| `docker service update --force easypanel-traefik` no primeiro 502 | Lesson 176: Traefik estava 1/1; causa era DB env dos apps |
| `docker service update --force` no app sem checar env | Env errada **persiste** após force |
| Tratar NXDOMAIN como 502 | Reiniciar stack não cria A record |
| Assumir “lockout N8N” sem dig | Caso real: user usou `n8n.*` (NXDOMAIN) em vez de `flow.*` |

---

## 3. DNS — 3× NXDOMAIN (chatwoot / n8n / supabase)

### 3.1 HOLD-GUSTAVO (UI)

Criar **3 A records** na zona do domínio (provedor efetivo: validar NS — Hostinger **ou** Cloudflare; Lesson 142: **sempre** `dig NS` antes):

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `chatwoot` | `187.77.236.77` | Proxied **ou** DNS-only (ver TLS) |
| A | `n8n` | `187.77.236.77` | idem |
| A | `supabase` | `187.77.236.77` | alias; **typo `supbase` permanece canônico** |

Pack one-pager: [`docs/DNS_TRAEFIK_SUI_PACK_G7.md`](DNS_TRAEFIK_SUI_PACK_G7.md)  
Runbook DNS: [`docs/RUNBOOK_DNS_HOSTINGER.md`](RUNBOOK_DNS_HOSTINGER.md)  
Check: `bash scripts/check_dns_health.sh`

### 3.2 Pós-DNS

1. Traefik/ACME emite cert (pode falhar enquanto NXDOMAIN).
2. Merge routers pendentes: `infra/traefik/ROUTERS_PENDENTES.yaml`.
3. Smoke HTTPS nos 3 FQDNs.
4. Não esperar que DNS sozinho suba app em 502 — são problemas **ortogonais**.

### 3.3 Canônicos que já funcionam (workaround)

| Precisa de | Use enquanto NXDOMAIN |
|------------|------------------------|
| N8N UI/API | `https://flow.2notasudi.com.br` |
| Chatwoot | `https://chat.2notasudi.com.br` **ou** host EasyPanel `*.easypanel.host` |
| Supabase | `https://supbase.2notasudi.com.br` (typo aceito — `DOMAIN_TYPO_DECISION`) |

---

## 4. Árvore de decisão ordenada

### Passo 0 — Classificar o sintoma (local, sem SSH)

```bash
FQDN=chat.2notasudi.com.br   # exemplo

echo "=== DNS ==="
dig +short "$FQDN" A @1.1.1.1
dig +short "$FQDN" AAAA @1.1.1.1

echo "=== HTTP ==="
curl -sk -o /dev/null -m 8 -w 'code=%{http_code} time=%{time_total} err=%{errormsg}\n' \
  "https://$FQDN/"

echo "=== batch canônico ==="
for d in api flow whatsapp chat agent supbase easypanel chatwoot n8n supabase; do
  r=$(dig +short $d.2notasudi.com.br A @1.1.1.1 | head -1)
  c=$(curl -sk -o /dev/null -m 5 -w '%{http_code}' https://$d.2notasudi.com.br/ || echo 000)
  printf '%-10s dig=%-16s http=%s\n' "$d" "${r:-NXDOMAIN}" "$c"
done

# opcional
bash scripts/check_dns_health.sh
```

### Passo 1 — NXDOMAIN

1. Confirmar NS: `dig NS 2notasudi.com.br +short`
2. Abrir UI do provedor correto (não assumir Cloudflare se NS = Hostinger).
3. Criar A record (§3).
4. Aguardar propagação; revalidar `dig @1.1.1.1`.
5. **Stop** — não mexer em Swarm por causa de NXDOMAIN.

### Passo 2 — dig OK + code 000 (refused/timeout)

1. Ping/TCP 443 ao `187.77.236.77`.
2. Se Tailscale offline → `ssh cartorio-public` / `vps-public` (Lesson 176).
3. No VPS: `docker service ls | grep traefik` — se 0/1, aí sim recuperar Traefik (`OUTAGE_RECOVERY_RUNBOOK` §2).
4. Se Traefik 1/1 mas 000 externo → firewall / Cloudflare orange-cloud / IP errado no A record.

### Passo 3 — dig OK + HTTP 502

1. **Não** force Traefik ainda.
2. Ver quais hosts 502 vs 200 (matriz §1.2).
3. Com SSH:  
   - `docker service ls` → réplicas 0/1?  
   - `docker service logs <svc> --tail 100`  
   - Access log Traefik → backend `http-cartorio_X-0@file`
4. Se log app mostra **Postgres unreachable / password auth failed** → **Lesson 176 path**:
   - DATABASE_URL com IP externo (`10.11.211.12`) → trocar para `cartorio_supabase`
   - user/senha drift (`supabase_admin` vs `admin`) → alinhar via EasyPanel UI ou `--env-add`
   - **`docker service update --force` sozinho NÃO corrige env**
5. Se app crash por outro motivo (OOM, migrate, missing secret) → fix específico; só então force.
6. Smoke: `curl` nos FQDNs + `GET /api/v1/health/radar`.

### Passo 4 — dig OK + HTTP 404 (error-page EasyPanel)

1. Router ausente ou Host rule errada.
2. Aplicar/merge `infra/traefik/ROUTERS_PENDENTES.yaml`.
3. Confirmar labels EasyPanel do serviço.
4. Diferente de NXDOMAIN: DNS já aponta para a VPS.

### Passo 5 — Múltiplos canais 502 (P0 edge-wide)

1. Seguir [`docs/OUTAGE_RECOVERY_RUNBOOK.md`](OUTAGE_RECOVERY_RUNBOOK.md).
2. Se SSH bloqueado por auto-mode → **Lesson 172**: só artefatos + HOLD-GUSTAVO (não fingir recovery).
3. Ordem redeploy: data layer saudável → api → canais → CRM → LLM/UI.

---

## 5. Caminhos de correção (fix paths)

| Diagnóstico | Fix path | Owner |
|-------------|----------|-------|
| A record ausente | UI DNS + `check_dns_health.sh` | **HOLD-GUSTAVO** |
| Traefik 0/1 / porta 80-443 | scale 0→1 Traefik; ver runbook outage | Gustavo / sre+SSH |
| App 0/1 por env DB | EasyPanel Env → DNS interno + credenciais alinhadas | **HOLD-GUSTAVO** (Lesson 176) |
| App 0/1 por bug deploy | rollback imagem / logs | dev + sre |
| Router 404 | merge ROUTERS_PENDENTES + redeploy labels | sre |
| Cert ACME falhou | DNS deve existir primeiro; depois logs Traefik ACME | sre |
| User usa FQDN errado | educar: `flow` não `n8n.*` até DNS criado | support |

### Checklist pós-fix

```bash
# Edge
for d in api flow whatsapp chat agent supbase easypanel; do
  curl -sk -o /dev/null -m 8 -w "$d: %{http_code}\n" "https://$d.2notasudi.com.br/"
done

# API radar
curl -fsS https://api.2notasudi.com.br/api/v1/health/radar | jq .

# DNS pendentes (meta: deixar de ser NXDOMAIN)
bash scripts/check_dns_health.sh
```

---

## 6. Links para runbooks existentes

| Documento | Quando usar |
|-----------|-------------|
| [`docs/OUTAGE_RECOVERY_RUNBOOK.md`](OUTAGE_RECOVERY_RUNBOOK.md) | P0 multi-canal 502; restart Traefik; ordem redeploy |
| [`docs/DNS_TRAEFIK_SUI_PACK_G7.md`](DNS_TRAEFIK_SUI_PACK_G7.md) | One-pager DNS + routers + radar |
| [`docs/RUNBOOK_DNS_HOSTINGER.md`](RUNBOOK_DNS_HOSTINGER.md) | Passo a passo A records |
| [`docs/RUNBOOK_VPS.md`](RUNBOOK_VPS.md) | SSH aliases (`cartorio` vs stale `vps`) |
| [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md) | Troubleshooting geral |
| [`docs/CANAL_HEALTH_MATRIX.md`](CANAL_HEALTH_MATRIX.md) | Matriz de canais (probe histórico) |
| [`docs/EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md`](EVOLUTION_DATABASE_URL_QR_CHECKLIST_G7.md) | Evolution DB URL + QR |
| [`docs/CHATWOOT_HANDOFF_G7.md`](CHATWOOT_HANDOFF_G7.md) | Chatwoot handoff |
| [`infra/traefik/ROUTERS_PENDENTES.yaml`](../infra/traefik/ROUTERS_PENDENTES.yaml) | Routers a mergear |
| [`scripts/check_dns_health.sh`](../scripts/check_dns_health.sh) | Health DNS 10 hosts |
| [`.harness/memory/lesson-176-…502-recovery.md`](../.harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md) | Causa raiz DB env + log backend |
| [`.harness/memory/lesson-172-…r8-actions.md`](../.harness/memory/lesson-172-p0-outage-r8-actions.md) | SSH bloqueado → só artefatos |
| [`.harness/SUI_CHECKLIST.md`](../.harness/SUI_CHECKLIST.md) | SUI pre-deploy (inclui 3 NXDOMAIN) |

---

## 7. Diagrama (resumo)

```
                    ┌─────────────┐
   Cliente ────────►│  DNS public │
                    └──────┬──────┘
               NXDOMAIN    │ A/AAAA OK
                  │        ▼
                  │  ┌──────────┐     refused/timeout
                  │  │ Cloudflare│─────────────────────► rede / VPS / FW
                  │  │ / edge IP │
                  │  └────┬─────┘
                  │       ▼
                  │  ┌──────────┐
                  │  │ Traefik  │── 404 error-page ──► router missing
                  │  │ TLS OK   │
                  │  └────┬─────┘
                  │       │ route match
                  │       ▼
                  │  ┌──────────┐
                  │  │ Upstream │── 502 ──► service 0/1, crashloop, DB env
                  │  │ Swarm    │── 200 ──► OK
                  │  └──────────┘
                  ▼
            Criar A record
         (chatwoot/n8n/supabase)
```

---

## 8. Definition of Done (G7.13.T3)

| Item | Estado |
|------|--------|
| Matriz 502 vs NXDOMAIN vs 000 | ✅ |
| Padrão backend Traefik access log | ✅ Lesson 176 |
| 3 NXDOMAIN documentados + fix | ✅ |
| Árvore ordenada + fix paths | ✅ |
| Links runbooks | ✅ |
| SSH / mutação prod nesta wave | ❌ proibido / não feito |

---

**Modified by Gustavo Almeida** — cartorio-sre G7 Wave 24 (G7.13.T3)
