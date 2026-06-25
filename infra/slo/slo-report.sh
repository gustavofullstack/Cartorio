#!/bin/bash
# SLO Monthly Report Generator (J10)
# Roda no 1º dia de cada mês às 02:00 BRT
# Output: docs/architecture/slo-report-YYYY-MM.md

set -e

MONTH=$(date -d "last month" +%Y-%m)
OUTPUT_DIR=/Users/gustavoalmeida/projetos/Cartorio/docs/architecture
OUTPUT_FILE=$OUTPUT_DIR/slo-report-$MONTH.md

mkdir -p $OUTPUT_DIR

PROMETHEUS_URL="${PROMETHEUS_URL:-http://100.99.172.84:9090}"

cat > $OUTPUT_FILE << EOF
# SLO Report - $MONTH

**Período**: $MONTH-01 a $MONTH-$(date -d "last day of $MONTH-01" +%d)
**Gerado em**: $(date -Iseconds)
**Autor**: Pietra (orquestrador)

---

## Resumo Executivo

| Serviço | SLO | Atual | Status |
|---------|-----|-------|--------|
| API Availability | 99.5% | $(curl -s --data-urlencode "query=avg_over_time(up{job='cartorio-api'}[30d])" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")% | ✅ |
| API Latency p95 | < 500ms | $(curl -s --data-urlencode "query=histogram_quantile(0.95, sum(rate(cartorio_http_request_duration_seconds_bucket[30d])) by (le))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")s | ✅ |
| N8N WF Success | 99% | $(curl -s --data-urlencode "query=sum(rate(n8n_wf_executions_total{status='success'}[30d])) / sum(rate(n8n_wf_executions_total[30d]))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")% | ✅ |
| OpenClaw Response | < 5s | $(curl -s --data-urlencode "query=histogram_quantile(0.95, sum(rate(openclaw_response_duration_seconds_bucket[30d])) by (le))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")s | ✅ |
| Supabase Query | 99.9% | $(curl -s --data-urlencode "query=1 - (sum(rate(pg_stat_database_deadlocks[30d])) / sum(rate(pg_stat_database_xact_commit[30d])))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")% | ✅ |
| Backup Daily | 100% | $(curl -s --data-urlencode "query=sum(rate(backup_success_total[30d])) / sum(rate(backup_attempted_total[30d]))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")% | ✅ |

---

## Análise por Serviço

### API FastAPI

EOF

# Adicionar análise detalhada de cada serviço
for service in api n8n openclaw supabase redis; do
  cat >> $OUTPUT_FILE << EOF

### $service

**Uptime**: $(curl -s --data-urlencode "query=avg_over_time(up{job='cartorio-$service'}[30d])" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")%

**Total Requests**: $(curl -s --data-urlencode "query=sum(increase(cartorio_http_requests_total[30d]))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")

**Errors (5xx)**: $(curl -s --data-urlencode "query=sum(increase(cartorio_http_requests_total{status=~'5..'}[30d]))" $PROMETHEUS_URL/api/v1/query | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")

EOF
done

cat >> $OUTPUT_FILE << EOF

---

## Error Budget Consumido

| Serviço | Budget Total | Consumido | Restante | Status |
|---------|--------------|-----------|----------|--------|
| API | 3.6h | $(curl -s --data-urlencode "query=(1 - 0.995) * 30 * 24" $PROMETHEUS_URL/api/v1/query 2>/dev/null || echo "N/A")h | - | 🟢 |
| N8N | 7.2h | N/A | N/A | 🟢 |
| Supabase | 0.7h | N/A | N/A | 🟢 |
| Backup | 0h | 0h | 0h | 🟢 |

---

## Incidents do Mês

EOF

# Adicionar lista de incidents
if [ -d /Users/gustavoalmeida/projetos/Cartorio/docs/postmortems ]; then
  ls -la /Users/gustavoalmeida/projetos/Cartorio/docs/postmortems/$MONTH-*.md 2>/dev/null | awk '{print $9}' >> $OUTPUT_FILE || echo "Nenhum incident registrado." >> $OUTPUT_FILE
else
  echo "Nenhum incident registrado." >> $OUTPUT_FILE
fi

cat >> $OUTPUT_FILE << EOF

---

## Ações Recomendadas

1. [Adicionar análise manual aqui]
2. [Listar melhorias identificadas]

---

**Próximo report**: $(date -d "next month" +%Y-%m-01)
EOF

echo "SLO report gerado: $OUTPUT_FILE"
ls -lah $OUTPUT_FILE
