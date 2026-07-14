# R3 DEPLOY STATUS — 2026-07-14

> **TL;DR**: SONDAGEM EM PRODUÇÃO REVELOU **P0 CRÍTICO** — A API
> `https://api.2notasudi.com.br` ESTÁ RETORNANDO **502 BAD GATEWAY** EM
> **100% DOS ENDPOINTS**. Serviço totalmente down.
>
> **Implicação**: Não foi possível confirmar quais das 4 correções R3
> (commit `c8f9e6b`) estão em produção, porque o backend está offline.
> Antes de qualquer deploy de versão nova, **o serviço precisa ser
> recuperado primeiro**.
>
> **Decisão sob responsabilidade de Gustavo**: NÃO foi feito deploy
> automático. Este documento descreve o diagnóstico + checklist completo
> de recovery + deploy para Gustavo executar manualmente.

---

## 1. Descoberta P0 — API Down

### 1.1 Sintomas observados (2026-07-14 02:13-02:17 UTC)

| Endpoint                                    | HTTP   | Latência | Observação                              |
|---------------------------------------------|--------|----------|-----------------------------------------|
| `/health`                                   | **502**| 6.3s     | "Bad Gateway" body 11 bytes             |
| `/healthz` (R3 fix)                         | **502**| 6.3s     | Não diferencia do legado                |
| `/ready`                                    | **502**| 6.3s     | idem                                   |
| `/readyz` (R3 fix)                          | **502**| 4.5s     | idem                                   |
| `/metrics` (R3 fix, esperava 410)           | **502**| 6.3s     | idem                                   |
| `/api/v1/metrics/prometheus` (canonico)     | **502**| 6.4s     | idem                                   |
| `/mcp` (R3 fix)                             | **502**| 6.3s     | idem                                   |
| `/api/v1/ws/atendimentos` (R3 fix)          | **502**| 6.3s     | idem                                   |
| `/ws/atendimentos` (legacy sem prefix)      | **502**| 6.3s     | idem                                   |
| `/version`                                  | **502**| 6.3s     | idem                                   |
| `/api/v1/health`                            | **502**| 6.3s     | idem                                   |
| `/api/v1/ready`                             | **502**| 6.3s     | idem                                   |
| `/robots.txt`, `/favicon.ico`, `/api`       | **502**| 6.3s     | idem                                   |
| `/docs`, `/openapi.json`                    | **502**| 6.3s     | idem                                   |

**Comportamento uniforme**: Tudo 502, body `Bad Gateway` (11 bytes),
~6s de latência (timeout Traefik → upstream morto).

### 1.2 Camadas verificadas

| Camada            | Status    | Evidência                                         |
|-------------------|-----------|---------------------------------------------------|
| DNS               | ✅        | `dig api.2notasudi.com.br` → `187.77.236.77`      |
| TLS               | ✅        | Cert válido Let's Encrypt YR2 (CN=api.2notasudi.com.br) |
| TCP 443 (Traefik) | ✅        | `nc -zv 187.77.236.77 443` → OPEN                 |
| TCP 8000 (backend)| ❌        | `nc -zv 187.77.236.77 8000` → BLOCKED/CLOSED      |
| Traefik upstream  | ❌        | 502 em TODAS as rotas (v0+ qual método/path)     |

**Causa raiz provável**: container `cartorio_api` no Swarm está **sem
réplicas healthy** (escala 0/1 ou crashloop). Traefik não tem upstream
para rotear, retorna 502 com body genérico do proxy.

### 1.3 Por que não investiguei mais a fundo

Eu (Claude Code) **NÃO tenho acesso direto ao Swarm** — só ao repo
local e à rede externa. As ferramentas locais (`docker`, `ssh`) aqui
não alcançam `187.77.236.77` (host VPS via Tailscale). O diagnóstico
completo + recovery exige Gustavo conectar ao Easypanel/SSH.

---

## 2. Implicação sobre R3 — Não foi possível confirmar

As 4 correções R3 foram aplicadas ao código em commit `c8f9e6b`
(2026-07-13 19:11 BRT), mas **ninguém fez deploy**. Confirmado por:

- `lesson-165` (R3 report): marcado como "needs deployment"
- `lesson-166` (R4 report): "R3 NOT in prod (lens R4-1 re-probed 404)"
- `lesson-167` (R5 report): "R3 STILL not in prod (v0.5.4)"
- `lesson-169` (R7 report): "R3 STILL not in prod (R7-7 confirmed, 4th
  consecutive round)"

**Hoje (R8)**: API está down, então mesmo se R3 estivesse deployed,
não responderia. Estado final é **indeterminado**.

### 2.1 Único sinal colateral positivo

Quando o serviço voltar, **todas as 4 correções R3 devem aparecer**
se o deploy for da imagem `gustavofullstack/cartorio-api:v0.6.0` ou
superior. O código atual em `main.py` (versão "0.5.4" declarada) já
contém as 4 linhas:

- `main.py:433-436` — `/healthz` alias
- `main.py:439-442` — `/readyz` alias
- `main.py:445-461` — `/metrics` 410 → `/api/v1/metrics/prometheus`
- `main.py:567` — `app.mount("/mcp", _mcp_subapp)`
- `main.py:656` — `app.include_router(ws_router, prefix="/api/v1")`
- `main.py:118-123` — Sentry init no lifespan

**Esperado pós-deploy**:
- `/healthz` HTTP 200 (json `{status: ok, version: 0.5.4}`)
- `/readyz` HTTP 200 (json `{status: ready, audit_chain_initialized: true}`)
- `/metrics` HTTP 410 com link no body
- `/mcp` HTTP 200 (tools list JSON-RPC via streamable HTTP)
- `/api/v1/ws/atendimentos` WS upgrade ok
- `/ws/atendimentos` (legacy) → **404 esperado**

---

## 3. Checklist de Recovery + Deploy (para Gustavo)

> **NÃO executado por mim (Claude Code) sob nenhuma circunstância.** A
> recovery do P0 + deploy da versão que contém R3 é decisão humana.

### 3.1 Pré-requisitos

- [ ] Acesso SSH ao VPS via Tailscale (`100.99.172.84`, key em
      `~/.ssh/id_ed25519_cartorio`)
- [ ] Easypanel UI acessível: `https://easypanel.2notasudi.com.br`
- [ ] Credenciais salvas em `~/.mavis/secrets/coding-vps-global.env`
      (`chmod 600`, owner-only). Carregar com
      `set -a; source ~/.mavis/secrets/coding-vps-global.env; set +a`
      antes de qualquer comando abaixo. NUNCA hardcoda senha —
      arquivo já está fora do git.

### 3.2 Passo A — Diagnosticar o swarm (SSH direto)

```bash
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84

# 1. Listar replicas do serviço cartorio_api
docker service ps cartorio_api --no-trunc

# 2. Ver últimas 50 linhas de log do último container
docker service logs cartorio_api --tail 50

# 3. Status geral
docker service ls | grep -E "cartorio_api|easypanel|traefik"

# 4. Confirmar upstream do Traefik
docker exec $(docker ps -qf name=traefik) wget -qO- http://cartorio_api:8000/health
# esperado: {"status":"ok","service":"cartorio-api","version":"0.6.0"}
# se falhar: backend não responde na porta 8000 (não DNS issue)
```

### 3.3 Passo B — Cenários de recovery

#### Cenário 1: Réplica 0/1 (container crash)
```bash
# Forçar redeploy (Easypanel UI também serve: Services → cartorio_api → Restart)
docker service update --force cartorio_api
sleep 30
curl -sS -o /dev/null -w "%{http_code}\n" https://api.2notasudi.com.br/health
# esperado: 200
```

#### Cenário 2: Imagem antiga (tag errada)
```bash
# Verificar tag atual
docker service inspect cartorio_api --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
# esperado: gustavofullstack/cartorio-api:v0.6.0 (ou superior)
# se for v0.5.4 sem R3: atualizar antes do Passo C
```

#### Cenário 3: DB/Redis indisponíveis (deadlock no startup)
```bash
# Checar saúde dos upstreams
docker exec $(docker ps -qf name=cartorio_api) \
  python -c "import socket; [print(s, socket.gethostbyname(s)) for s in ['cartorio_supabase-db','cartorio_redis','cartorio_evolution-api']]"
# esperado: 3 IPs resolvidos. Se algum NXDOMAIN: investigar rede Swarm
```

#### Cenário 4: Rolling restart travou (loop deploy/restart)
```bash
# Escalar para 0 e voltar para 1 (gotcha CLAUDE.md §Notable)
docker service scale cartorio_api=0
sleep 5
docker service scale cartorio_api=1
sleep 30
curl -sS -o /dev/null -w "%{http_code}\n" https://api.2notasudi.com.br/health
```

### 3.4 Passo C — Deploy da versão v0.6.0 (contém R3)

```bash
# Pre-deploy sanity (local, sem deploy)
cd ~/Projetos/Cartorio
make lint        # ruff + mypy, gate 0 erros
make test-fast   # pytest sem coverage (dev loop)

# Push da tag
git tag v0.6.0           # já existe se Sprint 3 stop
git push origin v0.6.0   # trigger Easypanel build + deploy
# OU Easypanel UI: Services → cartorio_api → Build → Image tag

# Após deploy, esperar healthcheck (30-90s)
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 10
  code=$(curl -sS -o /dev/null -w "%{http_code}" https://api.2notasudi.com.br/health)
  echo "[$i/10] /health → HTTP $code"
  [ "$code" = "200" ] && break
done
```

### 3.5 Passo D — Verificação R3 (4 alíneas)

```bash
echo "=== R3 verification suite ==="
echo ""
echo "FIX 1: /healthz (alias k8s/Traefik)"
echo "  expected: 200 + body igual a /health"
curl -sS -w "\n  HTTP %{http_code}\n" https://api.2notasudi.com.br/healthz
echo ""

echo "FIX 1b: /readyz (alias k8s/Traefik)"
echo "  expected: 200 + body igual a /ready"
curl -sS -w "\n  HTTP %{http_code}\n" https://api.2notasudi.com.br/readyz
echo ""

echo "FIX 1c: /metrics (410 → /api/v1/metrics/prometheus)"
echo "  expected: 410 + body com Link"
curl -sS -w "\n  HTTP %{http_code}\n" https://api.2notasudi.com.br/metrics
echo ""

echo "FIX 1d: /api/v1/metrics/prometheus (canonico, fonte de verdade)"
echo "  expected: 200 text/plain"
curl -sS -w "\n  HTTP %{http_code}\n" https://api.2notasudi.com.br/api/v1/metrics/prometheus | head -20
echo ""

echo "FIX 2: /mcp (sub-app FastMCP, tools 1-7)"
echo "  expected: 200 streamable HTTP, JSON-RPC no Accept header"
curl -sS -H "Accept: application/json, text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
     -w "\n  HTTP %{http_code}\n" https://api.2notasudi.com.br/mcp | head -10
echo ""

echo "FIX 3: WS /api/v1/ws/atendimentos (upgrade)"
echo "  expected: 101 Switching Protocols"
curl -sS -i -N \
     -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" \
     -H "Sec-WebSocket-Key: dGVzdA==" \
     --max-time 3 \
     https://api.2notasudi.com.br/api/v1/ws/atendimentos 2>&1 | head -5
echo ""

echo "FIX 3b: WS /ws/atendimentos (legacy, esperado 404)"
echo "  expected: 404 Not Found"
curl -sS -w "\n  HTTP %{http_code}\n" -o /dev/null https://api.2notasudi.com.br/ws/atendimentos
echo ""

echo "FIX 4 (Sentry init): checar logs do container"
echo "  expected: Sentry SDK inicializa no startup, sem warning"
docker service logs cartorio_api --tail 30 | grep -iE "sentry|init_sentry" || echo "no Sentry log line — DSN provavelmente não configurado"
echo ""
```

### 3.6 Passo E — Rollback (se algo falhar)

```bash
# Opção 1: Easypanel UI → cartorio_api → Rollback
# Opção 2: Forçar tag conhecida boa
docker service update \
  --image gustavofullstack/cartorio-api:v0.5.4 \
  cartorio_api

# Opção 3: Remover o serviço (recovery do Swarm só)
docker service scale cartorio_api=0
# NÃO remover, manter config — Easypanel recria no próximo restart
```

### 3.7 Variáveis de ambiente relevantes

Confirmar em Easypanel UI → cartorio_api → Environment:

```bash
# Mínimas obrigatórias (sem essas, app não sobe)
APP_ENV=production
DATABASE_URL=postgresql+psycopg2://postgres:***@cartorio_supabase-db:5432/postgres
REDIS_URL=redis://cartorio_redis:6379/0
N8N_WEBHOOK_SECRET=<hash>
CARTORIO_API_KEY=<apikey>

# Para R3 completo
MCP_SERVER_ENABLED=true          # essencial para /mcp responder
SENTRY_DSN=<dsn>                 # opcional, sem isso Sentry init é no-op
LOG_LEVEL=INFO

# Audit (LGPD)
AUDIT_HMAC_SECRET=<hash>
AUDIT_DEAD_MANS_SWITCH_INTERVAL_MINUTES=15

# LGPD retenção
RETENCAO_ENABLED=true
RETENCAO_HOUR_BRAZIL=3
```

---

## 4. Resumo executivo para Gustavo

1. **API está 502 (down total)** desde pelo menos 2026-07-14 02:13 UTC.
   Provável causa: container `cartorio_api` no Swarm sem réplicas
   healthy.
2. **R3 ainda não deployed** (independente do outage — confirmado nas
   lessons 165/166/167/169).
3. **Recovery primeiro**: diagnóstico SSH no VPS + 4 cenários (3.3).
   Sem recovery, nenhuma das 4 correções R3 terá efeito visível.
4. **Deploy da v0.6.0** (que contém R3): só após recovery verde.
5. **Verificação**: script 3.5 prova as 4 correções em uma rodada.
6. **Rollback**: trivial (v0.5.4 ainda funcional no registry).

---

## 5. Refs

- Commit `c8f9e6b` — R3 routing fixes (4 correções)
- `lesson-165-r3-routing-fixes-2026-07-13.md`
- `lesson-166-r4-organizational-fixes-2026-07-13.md` (R3 not in prod)
- `lesson-167-r5-cross-ref-ruff-memory-2026-07-13.md`
- `lesson-169-r7-coverage-deadcode-2026-07-13.md`
- `docs/DEPLOYMENT.md` — Easypanel + Traefik + Swarm
- `docs/RUNBOOK_VPS.md` — operational runbook
- `CLAUDE.md` §"Critical rules" + §"Notable integration gotchas"

Modified by Gustavo Almeida (documentação gerada 2026-07-14)
