# Loki / Promtail — Sample Queries & Ingest Verify (G7.18.T4)

| Campo | Valor |
|-------|--------|
| **Task** | G7.18.T4 — Loki/Promtail ingest sample query |
| **Wave** | G7 Wave 27 |
| **Agente** | cartorio-sre |
| **Configs** | `infra/loki/*`, `infra/logging/*` |
| **Helper** | [`scripts/loki_sample_query.sh`](../scripts/loki_sample_query.sh) (dry-run friendly) |
| **Retention** | ~31d (`limits_config.retention_period: 744h`) — alinhado LGPD logs curtos |

---

## 0. TL;DR

```bash
# Só imprime queries / curls (não precisa Loki up)
bash scripts/loki_sample_query.sh --dry-run

# Se Loki local/port-forward:
export LOKI_URL=http://127.0.0.1:3100
bash scripts/loki_sample_query.sh --ready
bash scripts/loki_sample_query.sh --query api-502
```

LogQL abaixo assume labels típicas do Promtail cartório (`job`, `service`, `swarm_service`, `container`, `level`).  
Ajuste se o deploy live divergir (EasyPanel renomeia containers).

---

## 1. Inventário de config no repo

| Path | Papel |
|------|--------|
| [`infra/logging/loki-stack.yml`](../infra/logging/loki-stack.yml) | Compose J08: Loki 2.9.3 + Promtail, net `cartorio_monitoring` |
| [`infra/logging/promtail-config.yml`](../infra/logging/promtail-config.yml) | Docker SD + PII regex drop/replace |
| [`infra/loki/docker-compose.loki.yml`](../infra/loki/docker-compose.loki.yml) | Compose G6: Loki 3.0 + Promtail, net `cartorio-net` |
| [`infra/loki/loki-config.yaml`](../infra/loki/loki-config.yaml) | Retention 744h, tsdb v13, ruler → AlertManager |
| [`infra/loki/promtail-config.yaml`](../infra/loki/promtail-config.yaml) | Jobs `backend` / `n8n` / `syslog` + scrub CPF/CNPJ/email/phone |

> Podem existir **duas** gerações de stack (logging vs loki/). Em prod, confirmar **qual** está up antes de confiar em label names.

### 1.1 Labels esperadas (após relabel)

| Label | Origem típica |
|-------|----------------|
| `job` | `docker` / `backend` / `n8n` / `syslog` |
| `service` | compose service label ou static |
| `swarm_service` | `com.docker.swarm.service.name` (logging stack) |
| `container` | nome container |
| `level` | parse JSON/regex |
| `image` | image ref (logging stack) |

---

## 2. Verificar ingest (antes de culpar a query)

### 2.1 Ready / metrics

```bash
curl -fsS "${LOKI_URL:-http://127.0.0.1:3100}/ready"
# esperado: ready

curl -fsS "${LOKI_URL:-http://127.0.0.1:3100}/metrics" | grep -E 'loki_distributor_lines_received_total|loki_ingester_streams'
```

### 2.2 Labels / series

```bash
# Labels conhecidas
curl -fsS "${LOKI_URL}/loki/api/v1/labels" | jq .

# Valores de service (últimas 1h)
curl -fsS -G "${LOKI_URL}/loki/api/v1/label/service/values" \
  --data-urlencode 'start='$(date -u -v-1H +%s 2>/dev/null || date -u -d '1 hour ago' +%s)'000000000' \
  | jq .
```

### 2.3 Promtail → Loki

```bash
# Promtail ready (porta 9080 no container)
curl -fsS http://127.0.0.1:9080/ready

# Targets (se endpoint exposto)
curl -fsS http://127.0.0.1:9080/targets 2>/dev/null | head
```

Sinais de ingest quebrado:

| Sintoma | Causa comum |
|---------|-------------|
| `/ready` fail | Loki down / disco cheio |
| labels vazias | Promtail sem docker.sock / rede errada |
| só `syslog` | filter compose project não casa EasyPanel |
| delay > batchwait | `batchwait: 1m` na config `infra/loki/promtail-config.yaml` |

---

## 3. LogQL samples

Substitua a janela no Grafana Explore (`Last 15m`) ou use `query_range` via script.

### 3.1 cartorio_api — erros e 502

```logql
# Streams do serviço API (ajuste label se necessário)
{swarm_service="cartorio_api"}
# ou
{service=~"api|backend|cartorio_api"}
# ou
{container=~".*cartorio_api.*"}
```

```logql
# Linhas com 502 / Bad Gateway (app ou proxy logado no container)
{swarm_service="cartorio_api"} |= "502" or |= "Bad Gateway"
```

```logql
# Erros estruturados JSON (level)
{swarm_service="cartorio_api"} | json | level=~"(?i)error|critical"
```

```logql
# Trace de request lento (se logger emite duration)
{swarm_service="cartorio_api"} |~ "(?i)slow|timeout|timed out"
```

```logql
# Contagem aproximada de 502 em 5m (metric query no Grafana)
sum(count_over_time({swarm_service="cartorio_api"} |= "502" [5m]))
```

### 3.2 N8N — erros de workflow

```logql
{service="n8n"}
# ou
{swarm_service="cartorio_n8n"}
# ou
{container=~".*n8n.*"}
```

```logql
{swarm_service="cartorio_n8n"} |~ "(?i)error|failed|exception"
```

```logql
# DB init / password (padrão Lesson 176)
{swarm_service="cartorio_n8n"} |= "password authentication failed" or |= "error initializing DB"
```

```logql
# Workflow execution fail (texto varia por versão n8n)
{swarm_service="cartorio_n8n"} |~ "(?i)workflow.*(fail|error)|execution.*(error|crashed)"
```

### 3.3 Traefik / edge (se logs do container traefik estiverem no Promtail)

```logql
{container=~".*traefik.*"} |= "502"
```

```logql
{container=~".*traefik.*"} |~ "cartorio_(chatwoot|evolution-api|n8n)"
```

Correlacionar com o parser de access log: [`docs/TRAEFIK_ACCESS_LOG_DEBUG_G7.md`](TRAEFIK_ACCESS_LOG_DEBUG_G7.md).

### 3.4 Chatwoot / Evolution (upstream 502 clássico)

```logql
{swarm_service="cartorio_chatwoot"} |~ "(?i)PG::ConnectionBad|Host is unreachable|ActiveRecord"
```

```logql
{swarm_service="cartorio_evolution-api"} |= "P1001" or |= "Can't reach database"
```

---

## 4. Queries PII-safe (LGPD)

Promtail já tenta mascarar CPF/CNPJ/email/telefone em pipeline (`infra/loki/promtail-config.yaml` e `infra/logging/promtail-config.yml`).  
Ainda assim, **queries de explore** devem evitar puxar payloads de conversa.

### 4.1 Boas práticas

| Faça | Evite |
|------|--------|
| Filtrar por `level`, `status`, `workflow id` | `|= "cpf"` em log de conversa |
| Usar `line_format` só com campos técnicos | Dump de body de webhook com documento |
| Janela curta (15m–1h) em incidentes | Export 31d de logs de atendimento |
| Preferir métricas/contagens | Copiar log raw para ticket público |

### 4.2 Exemplos que evitam eco de PII

```logql
# Só level + logger (JSON), sem message completa
{swarm_service="cartorio_api"} | json | level="ERROR" | line_format "{{.level}} {{.logger}}"
```

```logql
# Detectar se PII cru ainda vaza (auditoria de pipeline) — rodar raro, acesso restrito
{job=~".+"} |~ `\d{3}\.\d{3}\.\d{3}-\d{2}`
# Se retornar hits: pipeline Promtail falhou ou path sem scrub — abrir task cartorio-lgpd
```

```logql
# Correlation id only (se app emite)
{swarm_service="cartorio_api"} | json | line_format "corr={{.correlation_id}} level={{.level}}"
```

### 4.3 O que NÃO colocar em dashboard público Grafana

- Painéis com `|=` em números de protocolo/escritura.
- Explore shared com “Share” público sem auth.
- Annotations com trecho de mensagem de cliente.

---

## 5. Grafana Explore — receita rápida

1. Grafana → Explore → datasource **Loki**.
2. Label browser: escolha `swarm_service` ou `container`.
3. Cole uma query §3.
4. Toggle **Live** só em incidentes (carga).
5. Para 502 multi-serviço: split view API + Traefik + chatwoot.

---

## 6. API query_range (curl)

```bash
LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
START_NS=$(( $(date -u +%s) - 900 ))000000000   # 15 min
END_NS=$(date -u +%s)000000000
QUERY='{container=~".*cartorio_api.*"} |= "502"'

curl -fsS -G "${LOKI_URL}/loki/api/v1/query_range" \
  --data-urlencode "query=${QUERY}" \
  --data-urlencode "start=${START_NS}" \
  --data-urlencode "end=${END_NS}" \
  --data-urlencode "limit=50" \
  | jq '.data.result | length'
```

O script `scripts/loki_sample_query.sh` encapsula isso com `--dry-run`.

---

## 7. Checklist “ingest OK”

- [ ] `GET /ready` → `ready`
- [ ] `GET /loki/api/v1/labels` retorna ≥1 label
- [ ] `label/service/values` ou `container` mostra serviços cartorio_*
- [ ] Query `{container=~".*cartorio_api.*"}` retorna linhas recentes
- [ ] Query PII-audit (§4.2) idealmente **0** hits de CPF formatado
- [ ] Retention/compactor sem erro nos logs do Loki

---

## 8. Cross-refs

| Doc | Uso |
|-----|-----|
| [`docs/TRAEFIK_ACCESS_LOG_DEBUG_G7.md`](TRAEFIK_ACCESS_LOG_DEBUG_G7.md) | 502 backend name |
| [`docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`](PLAYBOOK_502_VS_NXDOMAIN_G7.md) | Classificar edge |
| [`docs/ALERTMANAGER_TELEGRAM_G7.md`](ALERTMANAGER_TELEGRAM_G7.md) | Alertas métricos |
| Lesson 176 | Logs de DB env em n8n/chatwoot/evolution |

**Modified by Gustavo Almeida — G7 Wave 27 cartorio-sre**
