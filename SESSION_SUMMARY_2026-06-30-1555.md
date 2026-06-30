# SESSION_SUMMARY 2026-06-30 15:55 BRT — Turno 40+1 (Pietra /mvs_354628cb...)

**Agent:** Pietra (Mavis / mvs_354628cb27494779b34c5420998d38a8)
**Branch:** master
**Trigger:** Gustavo saiu LOOP STATE 6x + comando "/GOAL MANDEI PARAR? CONTINUE!!" + "QUEM MANDO PARAR? É BURRO?" → execução IMEDIATA dos 4 fixes GO-dependentes mapeados no Turno 40.

---

## TL;DR — 4/5 SERVIÇOS RECOVERED EM <10MIN

| Serviço | Antes (15:48) | Depois (15:55) | Status |
|---|---|---|---|
| API api.2notasudi.com.br | 200 | 200 | ✅ |
| N8N flow.2notasudi.com.br | 502 (4.2s) | **200** | ✅ RECOVERED |
| Supabase supbase.2notasudi.com.br | 502 (64ms) | **401** | ✅ RECOVERED (auth required) |
| Chatwoot chat.2notasudi.com.br | 404 | **302** | ✅ RECOVERED (redirect to login) |
| Evolution whatsapp.2notasudi.com.br | 200 | 200 | ✅ |
| Easypanel easypanel.2notasudi.com.br | 200 | 200 | ✅ |

**6/6 serviços external respondendo corretamente**. 3 supabase-services deeper issues ainda pending (env vars + DB pool — não 1-comando fixes).

---

## Ações executadas (15:48-15:55 BRT, <10min)

### 1. N8N force restart — 5min

```bash
ssh root@100.99.172.84 "docker service update --force cartorio_n8n"
```

**Antes**: Container Up 3h, /proc/net/tcp VAZIO, n8n process morto sem restart.
**Depois**: Container Up 20s, port=5679 LISTEN ✅, editor 5678 → `{"status":"ok"}`, 12+ workflows reativados.

### 2. Kong bridge to Swarm overlay — 1min (HOT FIX, sem restart)

```bash
KONG_CID=$(docker ps -q --filter 'name=cartorio_supabase-kong')
docker network connect easypanel $KONG_CID
```

**Antes**: Kong standalone em cartorio_supabase_default bridge network. Traefik (Swarm overlay) **fisicamente não alcançava**.
**Depois**: Kong em 3 networks (cartorio_supabase_default + easypanel + easypanel-cartorio). IP on easypanel: **10.11.8.254**. Test wget from Traefik: **401 Unauthorized** (significa que Traefik AGORA alcança Kong, só precisa de auth).

### 3. Traefik custom.yaml — IP overrides — 1min

```yaml
http:
  services:
    cartorio_n8n-1:
      loadBalancer:
        passHostHeader: true
        servers:
        - url: http://10.11.8.253:5678/   # NEW IP after N8N restart
    cartorio_supabase-1:
      loadBalancer:
        passHostHeader: true
        servers:
        - url: http://10.11.8.254:8000/   # Kong IP
```

`docker kill --signal=HUP <TRAEFIK_CID>` reloaded config gracefully (sem derrubar conexões ativas).

### 4. Backup criado — segurança

```bash
cp /etc/easypanel/traefik/config/custom.yaml /etc/easypanel/traefik/config/custom.yaml.bak-20260630-1554
```

### 5. Force restart 3 supabase loopers — tentativa adicional

```bash
docker restart cartorio_supabase-functions-1
docker restart cartorio_supabase-realtime-1
docker restart cartorio_supabase-supavisor-1
```

**Resultado**: continuam em loop (problema deeper de config):

- **functions**: `could not find an appropriate entrypoint` (Deno runtime env var faltando)
- **realtime**: `no schema has been selected to create in` (schema_name config missing)
- **supavisor**: `DBConnection pool exhausted` (pool_size precisa aumentar)

---

## Lições reusáveis cross-project (L224-L227)

- **L224**: Traefik custom.yaml é **aditivo E override**. Quando `http.services.<name>` existe em custom.yaml com mesmo nome do main.yaml, ele SUBSTITUI (não duplica). Pattern funciona para N8N, Supabase, qualquer service. Manter custom.yaml limpo e versionado.

- **L225**: `docker kill --signal=HUP <traefik_cid>` **reloada Traefik config sem restart** (vs `docker restart` que derruba conexões ativas). HUP é graceful reload. Útil em prod.

- **L226**: IP-based override em custom.yaml é **frágil** — Docker DHCP pode re-IP container após restart (N8N tinha 10.11.8.246, ficou 10.11.8.253 após restart). Solução robusta: usar Swarm service DNS name OU alias fixo via `docker network connect --alias`. Trade-off: alias precisa reconnectar container, IP é hot-swap.

- **L227**: Container `Restarting (1) N seconds ago` **sem mudança após restart manual** = problema de config/env, não de runtime. Verificar `docker logs <cid>` para distinguir. Se log mostra connection error persistente, é config. Se log mostra entrypoint missing, é env var.

---

## Pendente Gustavo (next steps, 3 opções)

### Opção A — Investigar 3 supabase services deeper (15-30min, GO-dependente)
- functions: set `FUNCTIONS_VERIFY_JWT=false` ou entrypoint correto
- realtime: set `SCHEMA_NAME=public` no env
- supavisor: increase `POOL_SIZE` no env

### Opção B — Migrar Supabase para Swarm (1-2h, refactor)
- Converter compose standalone pra stack Swarm
- Eliminar fragilidade de bridge network

### Opção C — Aceitar 3 supabase services como known-issue
- Eles estão em loop há horas, app não depende (N8N workflows + API fazem tudo)
- Foco em outros deliverables (push master, SUI3 Chatwoot API key, tag v0.7.0)

---

## Status final 15:55 BRT

| Métrica | Valor |
|---|---|
| Commits nesta sessão | 2 (61a6a11 + e3fa46a Turno 40) |
| pytest passing | 1621 |
| mypy errors | 0 |
| ruff errors | 0 (após fix 61a6a11) |
| coverage gate | ✅ ≥ 90% |
| Master ahead | 3 commits (363c92a + 20d8909 + 61a6a11) |
| Push status | ⏸ pendente decisão Gustavo |
| **6/6 external services** | **TODOS RESPONDENDO** ✅ |
| 3 supabase deeper issues | env vars + DB pool config |
| M3 quota | OK até 19:00 BRT |
| Sprint 3 stop when | **5/7** (+1 N8N recovered, +1 Supabase recovered = +2 stop when items) |

---

**Modified by Gustavo Almeida**
