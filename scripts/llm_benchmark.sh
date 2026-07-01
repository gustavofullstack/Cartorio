#!/usr/bin/env bash
# llm_benchmark.sh — Benchmark de latência dos provedores LLM configurados

set +u  # disable unbound-var check (zsh/bash compat)

CARTORIO="/Users/gustavoalmeida/projetos/Cartorio"
ENV="$CARTORIO/.env"
[ -f "$ENV" ] || ENV="$CARTORIO/backend/.env"

PROMPT='Responda em 1 frase: qual o horário de atendimento do cartório?'

echo "🧪 LLM Benchmark — $(date '+%H:%M:%S')"
echo

# Formato: provedor|url|model|key (vazio = skip)
CONFIGS=(
  "opencode_go|${OPENCODE_GO_BASE_URL:-https://opencode.ai/zen/go/v1}|${OPENCODE_GO_MODEL:-deepseek-v4-flash}|${OPENCODE_GO_API_KEY:-}"
  "openclaw|${OPENCLAW_BASE_URL:-}|${OPENCLAW_MODEL_PRIMARY:-}|${OPENCLAW_API_KEY:-}"
)

for cfg in "${CONFIGS[@]}"; do
  IFS='|' read -r prov url model key <<< "$cfg"
  if [ -z "$url" ] || [ -z "$key" ]; then
    echo "  ⏸ $prov: não configurado (URL ou KEY vazia)"
    continue
  fi

  start=$(date +%s%N)
  resp=$(curl -sS -m 30 -o /tmp/llm_bench.out -w '%{http_code}|%{time_total}' \
    "${url%/}/chat/completions" \
    -H "Authorization: Bearer $key" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"max_tokens\":80,\"temperature\":0}" 2>&1)
  end=$(date +%s%N)
  elapsed_ms=$(( (end - start) / 1000000 ))
  code="${resp%%|*}"
  if [ "$code" = "200" ]; then
    content=$(jq -r '.choices[0].message.content // "?"' /tmp/llm_bench.out 2>/dev/null | head -c 80)
    echo "  ✅ $prov ($model): ${elapsed_ms}ms — \"$content...\""
  else
    err=$(head -c 100 /tmp/llm_bench.out 2>/dev/null)
    echo "  ❌ $prov ($model): ${elapsed_ms}ms code=$code — $err"
  fi
done

echo
echo "Meta-target: webhook < 5s end-to-end. Cada provider deve ficar < 3s."
rm -f /tmp/llm_bench.out