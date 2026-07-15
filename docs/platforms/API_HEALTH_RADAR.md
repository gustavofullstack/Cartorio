# API Health Radar — Guia Operacional

> Guia de interpretacao, alerting e extensao do Health Radar (regular + expanded).
> v0.6.0 — 2026-07-15 / Missao F6 [P2] / Squad cartorio-front + cartorio-sre.

## Endpoints

| Endpoint | Categorias | Auth | Descricao |
|----------|------------|------|-----------|
| `GET /health` | 1 (liveness) | Publico | Probe basico FastAPI |
| `GET /ready` | 1 (readiness) | Publico | DB + audit chain init |
| `GET /api/v1/health/radar` | 1 (7 servicos) | Publico | Multi-servico resumido |
| `GET /api/v1/health/radar/expanded` | 6 (health/dns/traefik/ssh/tailscale/disk) | Publico | Radar extendido F6 [P2] |
| `GET /api/v1/health/integracoes` | 8 (latencia+auth) | Publico | Workflow N8N #30 usa |
| `GET /api/v1/health/db` | 1 (PostgreSQL) | Publico | DB ping |
| `GET /api/v1/health/redis` | 1 (Redis) | Publico | Redis ping |
| `GET /api/v1/health/llm` | 1 (LLM provider) | Publico | OpenCode-Go/OpenClaw ping |

## Status codes interpretados

### Radar regular (`/health/radar`)

```json
{
  "status": "green" | "red",
  "services": {
    "database": "online" | "offline",
    "redis": "online" | "offline",
    "openclaw": "online" | "offline",
    "chatwoot": "online" | "offline",
    "supabase": "online" | "offline",
    "n8n": "online" | "offline",
    "evolution": "online" | "offline"
  }
}
```

- `green` = todos `online`.
- `red` = pelo menos um `offline`.
- HTTP 200 SEMPRE (fail-open). Endpoint nunca retorna 500.

### Radar expanded (`/health/radar/expanded`)

```json
{
  "status": "green" | "yellow" | "red",
  "categories": {
    "health": {"<service>": {"status": "up|down|warn", "latency_ms": int, "detail": "..."}},
    "dns": {"<domain>": {...}},
    "traefik": {"<domain>": {...}},
    "ssh": {"ssh_vps": {...}, "tailscale": {...}},
    "disk": {"docker_volumes": {...}}
  },
  "metadata": {"version": "0.6.0", "domain_count_dns": 10, ...}
}
```

### Categoria `up` vs `warn` vs `down`

| Status | Significado | Latencia esperada | Acao |
|--------|-------------|-------------------|------|
| `up` | Servico/check saudavel | < 500ms (health), < 1000ms (DNS), < 3000ms (SSH) | Nenhuma |
| `warn` | Degradado mas funcional | Acima do normal OU metodo nao permitido OU rota sem match | Investigar (alert amarelo) |
| `down` | Indisponivel | Timeout OU connection refused NXDOMAIN | Alert vermelho + runbook |

### Logica de agregacao `radar/expanded`

```
status = red  se health.database OU health.redis == down  (critico)
status = yellow se QUALQUER check == down  (nao-critico) OU QUALQUER == warn
status = green se TODOS up
```

### DNS checks (`health_radar_expanded.py`)

- `up`: `dig +short <domain>` retorna IP. `latency_ms` <= 1000ms tipico.
- `down`: NXDOMAIN (rc=9) OU timeout > 3s.
- `warn`: `dig` binary nao instalado (Docker slim image). Nao conta como failure.

### Traefik router checks

- `up`: HEAD retorna HTTP 200/301/302.
- `warn`: HTTP 404 + `content-length=2901` (Traefik "router not matched"). Indica dominio sem router configurado OU servico backend offline.
- `down`: HTTP 5xx OU ConnectError (DNS resolvido mas conexao recusada).

### SSH checks

- `up`: TCP connect em `187.77.236.77:22` (VPS Hostinger) ou `100.99.172.84:22` (Tailscale) bem-sucedido. Timeout 3s.
- `down`: ConnectionRefusedError, TimeoutError, OSError. Latencia reportada ate o timeout.

### Disk check

- `up`: < 85% usado.
- `warn`: >= 85% usado OU path inexistente (host sem `/var/lib/docker/volumes`).
- Path canonico: `/var/lib/docker/volumes`.

## Alert routing

### Workflow N8N #30 (Health Deep Check 15min)

Cron: a cada 15min. Coleta `/health/integracoes`. Se qualquer servico != ok:
1. Log estruturado com `status_code`, `latency_ms`, `erro`.
2. Envia mensagem para Chatwoot inbox do escrevente responsavel.
3. Cria ticket no Sentry (warn/error conforme severidade).

### PagerDuty integration (recomendado para radar expanded)

Trigger condition:
- `radar_expanded.status == "red"` por 2 ciclos consecutivos (30min).
- `radar_expanded.status == "yellow"` por 4 ciclos consecutivos (60min) com mesmo check falhando.

Webhook URL: `https://events.pagerduty.com/v2/enqueue` (routing key via env `PAGERDUTY_ROUTING_KEY`).

### Telegram alert (bot escrevevente)

```
CRITICAL: cartorio-api health/database DOWN
Detail: OperationalError: connection to server at "127.0.0.1", port 5432 failed
Latency: 5000ms (timeout)
Action: Verificar PostgreSQL no EasyPanel + logs docker service postgresql
Runbook: docs/RUNBOOK_VPS.md#postgres-down
```

Chat ID: env `TELEGRAM_ALERT_CHAT_ID` (default: chat do Gustavo admin).

### Email digest (diario)

Cron: 08:00 BRT. Envia resumo agregado das ultimas 24h (radar regular + expanded).
Para: `dpo@2notasudi.com.br`, `suporte@2notasudi.com.br`.

## Como adicionar um novo check (template)

1. **Defina a funcao de check** em `backend/app/api/v1/health_radar_expanded.py`:

```python
async def _check_minha_categoria(target: str) -> dict[str, Any]:
    """Check de exemplo: TCP socket ou HTTP request."""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"https://{target}/health")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            return {"status": "up", "latency_ms": elapsed_ms, "detail": f"HTTP 200"}
        return {"status": "down", "latency_ms": elapsed_ms, "detail": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "down", "latency_ms": int((time.perf_counter() - start) * 1000),
                "detail": f"{type(exc).__name__}: {str(exc)[:120]}"}
```

2. **Adicione a constante** com a lista de targets:

```python
RADAR_MINHA_CATEGORIA_TARGETS: tuple[str, ...] = (
    "target1.example.com",
    "target2.example.com",
)
```

3. **Adicione a funcao de categoria** em batch:

```python
async def _check_minha_categoria_category() -> dict[str, dict[str, Any]]:
    """Coleta checks de minha_categoria em paralelo."""
    coros = [_check_minha_categoria(t) for t in RADAR_MINHA_CATEGORIA_TARGETS]
    statuses = await asyncio.gather(*coros, return_exceptions=True)
    out: dict[str, dict[str, Any]] = {}
    for target, status in zip(RADAR_MINHA_CATEGORIA_TARGETS, statuses, strict=True):
        if isinstance(status, Exception):
            out[target] = {"status": "down", "latency_ms": 0, "detail": f"gather exception: {status!r}"}
        else:
            out[target] = status
    return out
```

4. **Adicione ao aggregator** no endpoint principal:

```python
@expanded_router.get("/health/radar/expanded", ...)
async def health_radar_expanded() -> dict[str, Any]:
    # ... existing ...
    minha = _check_minha_categoria_category()
    health, dns, traefik, ssh, disk, minha = await asyncio.gather(
        health_coro, dns_coro, traefik_coro, ssh_coro, disk_coro, minha,
        return_exceptions=True,
    )
    categories["minha_categoria"] = _coerce(minha, {})
    # ...
```

5. **Adicione testes** em `backend/tests/test_health_radar_expanded.py`:

```python
def test_minha_categoria_check_returns_up():
    """Mock HTTP 200."""
    ...

def test_minha_categoria_check_returns_down_on_5xx():
    """Mock HTTP 500."""
    ...
```

6. **Atualize o catalog** em `.brain/api-specs/catalog.py` se adicionar um endpoint dedicado. Para o radar expanded, NAO precisa catalog separado — eh agregado.

## Runbooks relacionados

- `docs/RUNBOOK_VPS.md` — Postgres/Redis/Traefik down
- `docs/RUNBOOK_DNS_HOSTINGER.md` — DNS propagation issues
- `docs/RUNBOOK_OPERACIONAL.md` — General ops
- `docs/RUNBOOK_VALIDACAO_1000_PONTOS.md` — Full validation suite
- `docs/OUTAGE_RECOVERY_RUNBOOK.md` — Disaster recovery

## Metricas Prometheus

Endpoint `/api/v1/metrics/prometheus` expoe:

- `cartorio_health_check_total{status="up|down|warn",category="health|dns|..."}` (counter)
- `cartorio_health_check_duration_seconds{category="..."}` (histogram)
- `cartorio_radar_expanded_overall_status{status="green|yellow|red"}` (gauge)

Workflow N8N #30 scrape + alerta via Prometheus Alertmanager.

## Cross-references

- API Guide: [API_GUIDE.md](../API_GUIDE.md)
- Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Catalog: [.brain/api-specs/catalog.py](../../.brain/api-specs/catalog.py)
- Incident post-mortems: [POSTMORTEMS.md](../POSTMORTEMS.md)

Modified by Gustavo Almeida.