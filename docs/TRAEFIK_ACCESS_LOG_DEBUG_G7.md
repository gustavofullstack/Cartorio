# Traefik Access Log — Backend Name Debug Panel (G7.13.T2)

| Campo | Valor |
|-------|--------|
| **Task** | G7.13.T2 — Access log backend name debug panel |
| **Wave** | G7 Wave 27 |
| **Agente** | cartorio-sre (slot A2) |
| **Fontes** | Lesson 176, `PLAYBOOK_502_VS_NXDOMAIN_G7`, `infra/traefik/` |
| **Regra** | Diagnóstico **sem mutar prod**; SSH só com autorização Gustavo |
| **Helper** | `scripts/traefik_access_log_parse.py` (`--demo` offline) |

---

## 0. TL;DR (30 segundos)

```
HTTP 502 no browser/curl?
  │
  ├─ dig NXDOMAIN ────────────────────► DNS — NÃO é Traefik (ver playbook G7.13.T3)
  ├─ Traefik access log SEM linha ────► request não chegou (edge/CF/firewall)
  ├─ access log COM backend + 502 ────► Traefik ROTEOU; upstream DOWN/misconfig
  └─ access log COM backend + 200 ────► edge OK — olhar app/auth
```

**Regra de ouro (Lesson 176):**  
> Traefik 502 ≠ Traefik down.  
> Se o access log mostra `http-cartorio_<serviço>-0@file` + status `502`, o proxy **roteou** e o **upstream** falhou.

Helper offline:

```bash
python3 scripts/traefik_access_log_parse.py --demo
# ou pipe de logs:
docker service logs easypanel-traefik --tail 200 --no-trunc 2>&1 \
  | python3 scripts/traefik_access_log_parse.py --filter-status 502
```

---

## 1. Formato do backend name (EasyPanel + Traefik file provider)

EasyPanel gera services Traefik via provider `file` / labels. Em prod o padrão observado é:

```
{scheme}-cartorio_{service}-{index}@file
```

| Token | Exemplo | Significado |
|-------|---------|-------------|
| `scheme` | `http` / `https` | Esquema do service Traefik (não confunda com entrypoint TLS) |
| `cartorio_` | prefixo stack/projeto | Projeto EasyPanel `cartorio` |
| `{service}` | `api`, `chatwoot`, `evolution-api`, `n8n` | Nome do serviço Swarm |
| `{index}` | `0`, `1` | Índice do backend/server no loadBalancer |
| `@file` | provider | Config vinda do provider **file** (não Docker labels em alguns paths) |

### 1.1 Mapa canônico (prod cartório)

| Backend no access log | Serviço Swarm | FQDN típico | Porta interna típica |
|-----------------------|---------------|-------------|----------------------|
| `http-cartorio_api-0@file` | `cartorio_api` | `api.2notasudi.com.br` | 8000 |
| `http-cartorio_n8n-0@file` | `cartorio_n8n` | `flow.2notasudi.com.br` | 5678 |
| `http-cartorio_chatwoot-0@file` | `cartorio_chatwoot` | `chat.2notasudi.com.br` | 3000 |
| `http-cartorio_evolution-api-0@file` | `cartorio_evolution-api` | `whatsapp.2notasudi.com.br` | 8080 |
| `http-cartorio_openclaw-gateway-0@file` (ou similar) | `cartorio_openclaw-gateway` | `agent.2notasudi.com.br` | gateway port |
| `https-cartorio_supabase-1@file` | `cartorio_supabase` / Kong | `supbase.2notasudi.com.br` | 5432/8000 (cuidado mis-label) |
| `http-easypanel-0@file` (variante) | `easypanel` | `easypanel.2notasudi.com.br` | 3000 |

> **Nota Lesson 176:** já houve mis-label de router Supabase apontando para `easypanel:3000`. Se o backend name no log for `easypanel` mas o Host for `supbase.*`, é **router errado**, não “Postgres down”.

---

## 2. Onde está o access log

| Ambiente | Como obter |
|----------|------------|
| Docker Swarm (prod) | `docker service logs easypanel-traefik --tail N --no-trunc` |
| Container one-shot | `docker logs $(docker ps -q -f name=easypanel-traefik \| head -1) --tail N` |
| EasyPanel UI | Project → **easypanel-traefik** → Logs (filtro `502` / host) |
| Arquivo (se accessLog.filePath configurado) | path no `traefik.yml` / static config — **não hardcode**; inspecionar config viva |

Access log JSON (Traefik v2/v3) costuma incluir campos como:

| Campo JSON | Uso debug |
|------------|-----------|
| `RequestHost` | FQDN do cliente |
| `RequestPath` / `RequestMethod` | rota |
| `DownstreamStatus` | status visto pelo cliente (502, 404, 200…) |
| `OriginStatus` | status do upstream (se chegou) |
| `ServiceName` / `ServiceURL` | **backend name** (`http-cartorio_X-0@file`) |
| `RouterName` | router que casou |
| `Duration` / `OriginDuration` | latência total vs upstream |
| `ClientAddr` / `ClientHost` | IP (pode ser CF/proxy) |
| `RequestCount` | contagem |

Em logs **CLF/text**, o backend aparece embutido na linha; o parser em `scripts/traefik_access_log_parse.py` tenta JSON e regex de fallback.

---

## 3. jq / grep — receitas operacionais

### 3.1 Últimos 502 com backend

```bash
docker service logs easypanel-traefik --tail 500 --no-trunc 2>&1 \
  | grep -E '"DownstreamStatus":502|"OriginStatus":502| 502 ' \
  | tail -50
```

### 3.2 JSON → backend + host + path (jq)

```bash
docker service logs easypanel-traefik --tail 1000 --no-trunc 2>&1 \
  | grep -E '^\{' \
  | jq -r 'select(.DownstreamStatus == 502 or .OriginStatus == 502)
      | "\(.ServiceName // .service // "?")\t\(.RequestHost // .Host // "?")\t\(.RequestMethod // "?") \(.RequestPath // .RequestUri // "?")\tstatus=\(.DownstreamStatus)"' \
  | sort | uniq -c | sort -rn
```

### 3.3 Contagem de backends em 502 (últimos 15 min de log)

```bash
docker service logs easypanel-traefik --since 15m --no-trunc 2>&1 \
  | grep -E '^\{' \
  | jq -r 'select(.DownstreamStatus == 502) | .ServiceName // "unknown"' \
  | sort | uniq -c | sort -rn
```

### 3.4 Correlacionar Host → backend (matrix)

```bash
docker service logs easypanel-traefik --tail 2000 --no-trunc 2>&1 \
  | grep -E '^\{' \
  | jq -r '[.RequestHost // "?", .ServiceName // "?", (.DownstreamStatus|tostring)] | @tsv' \
  | sort | uniq -c | sort -rn | head -40
```

### 3.5 Parser do repo (recomendado para on-call)

```bash
# Demo offline (sem SSH)
python3 scripts/traefik_access_log_parse.py --demo

# Arquivo salvo
python3 scripts/traefik_access_log_parse.py /tmp/traefik-access.jsonl --filter-status 502

# Stdin
docker service logs easypanel-traefik --tail 300 --no-trunc 2>&1 \
  | python3 scripts/traefik_access_log_parse.py --summary
```

---

## 4. EasyPanel — painel de debug (sem SSH)

1. Abrir `https://easypanel.2notasudi.com.br` (auth HOLD-GUSTAVO).
2. Stack / projeto **cartorio**.
3. Serviço **traefik** (nome prod: `easypanel-traefik`):
   - **Logs** → filtrar `502` ou o FQDN (`chat.`, `whatsapp.`).
   - Procurar token `cartorio_` + `@file`.
4. Anotar o **ServiceName** (`http-cartorio_chatwoot-0@file` etc.).
5. Ir ao serviço Swarm correspondente (`cartorio_chatwoot`):
   - **Replicas** 0/1? → upstream morto.
   - **Env** DATABASE_URL / POSTGRES_HOST com IP externo? → Lesson 176.
   - **Logs** do app (Prisma P1001, password auth failed, etc.).
6. **Não** clicar “Restart” no Traefik como primeiro passo (playbook G7.13.T3).

### 4.1 Checklist visual (debug panel mental)

| Check | Onde | Pass |
|-------|------|------|
| DNS A record | dig / Cloudflare | IP 187.77.236.77 ou CF proxy |
| TLS handshake | curl -v | cert LE válido |
| Access log line exists | Traefik logs | request chegou |
| Backend name legível | ServiceName | mapeia §1.1 |
| Status 502 + backend X | access log | upstream X |
| Réplicas X | `docker service ls` / EasyPanel | 1/1 |
| DB env alinhado | EasyPanel Env | DNS interno `cartorio_supabase` |

---

## 5. Mapeamento comum 502 → causa → ação

| Sintoma access log | Réplicas | Logs app típicos | Causa | Ação |
|--------------------|----------|------------------|-------|------|
| `http-cartorio_chatwoot-0@file` + 502 | 0/1 | `Host is unreachable` / IP `10.x` | DB host IP externo | EasyPanel Env → `cartorio_supabase` (Lesson 176) |
| `http-cartorio_evolution-api-0@file` + 502 | 0/1 | Prisma `P1001` | DB unreachable | Idem + checklist Evolution G7 |
| `http-cartorio_n8n-0@file` + 502 | 1/1 crashloop | `password authentication failed` | credential drift | alinhar user/pass com Postgres real |
| `http-cartorio_api-0@file` + 502 | 0/1 | OOM / migrate fail | deploy/API | rollback imagem; **não** force Traefik |
| Backend `easypanel` mas Host `supbase.*` | — | HTML EasyPanel | **router misconfig** | corrigir service URL no dynamic config |
| Sem backend / 404 error-page | — | — | router ausente | merge `ROUTERS_PENDENTES.yaml` |
| Nenhum log Traefik para o Host | — | — | DNS/CF/firewall | dig + playbook NXDOMAIN |

### 5.1 Anti-padrões

| Erro | Por quê |
|------|---------|
| `docker service update --force easypanel-traefik` no primeiro 502 | Lesson 176: Traefik estava 1/1 |
| Force no app sem ler backend name | pode reiniciar o serviço **errado** |
| Tratar NXDOMAIN como 502 | restart Swarm não cria A record |
| Assumir “API down” porque um FQDN 502 | correlacionar **ServiceName** por host |

---

## 6. Fluxo de decisão (access-log first)

```
curl https://FQDN → 502
        │
        ▼
  dig A FQDN OK?
   no ──► DNS playbook
   yes
        ▼
  Traefik access log tem linha p/ Host?
   no ──► edge/CF/firewall / Traefik 0/1
   yes
        ▼
  Extrair ServiceName (backend)
        │
        ▼
  Mapear §1.1 → serviço Swarm
        │
        ▼
  docker service ls / EasyPanel replicas
        │
   0/1 ──► logs do serviço (DB env, crash)
   1/1 ──► health interno + mis-label / timeout upstream
```

---

## 7. Relação com outros docs

| Documento | Uso |
|-----------|-----|
| [`docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`](PLAYBOOK_502_VS_NXDOMAIN_G7.md) | Classificar 502 vs DNS vs refused |
| [`docs/DNS_TRAEFIK_SUI_PACK_G7.md`](DNS_TRAEFIK_SUI_PACK_G7.md) | One-pager DNS + routers |
| [`docs/OUTAGE_RECOVERY_RUNBOOK.md`](OUTAGE_RECOVERY_RUNBOOK.md) | P0 multi-canal |
| [`docs/TRAEFIK_EDGE_RATE_LIMIT_G7.md`](TRAEFIK_EDGE_RATE_LIMIT_G7.md) | Rate-limit na borda (opcional) |
| [`infra/traefik/ROUTERS_PENDENTES.yaml`](../infra/traefik/ROUTERS_PENDENTES.yaml) | Routers HOLD merge |
| [Lesson 176](../.harness/memory/lesson-176-sre-incident-2026-07-14-502-recovery.md) | 502 recovery DB env |
| [`scripts/traefik_access_log_parse.py`](../scripts/traefik_access_log_parse.py) | Parser + demo |

---

## 8. HOLD / não fazer neste task

- Não habilitar dashboard Traefik público sem auth.
- Não commitar dumps reais de access log com IP de cliente se forem sensíveis em contexto LGPD (preferir agregados).
- Não alterar static config Traefik em prod sem GO Gustavo.

**Modified by Gustavo Almeida — G7 Wave 27 cartorio-sre**
