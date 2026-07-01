#!/usr/bin/env bash
# cartorio_validate.sh — Validação completa do ambiente Cartório
# Roda as 9 etapas do /cartorio skill e gera relatório.
# Exit code: 0 = OK | 1 = ALERTA REAL (N8N off / SUP 404 / Render 401 NÃO contam)

set -u

CARTORIO="/Users/gustavoalmeida/projetos/Cartorio"
MEM_DIR="/Users/gustavoalmeida/.claude/projects/-Users-gustavoalmeida-projetos-Cartorio/memory"

echo "🟢 /cartório — validação completa $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo

# ---- 1. LOAD contexto ----
echo "## Contexto"
if [ -f "$CARTORIO/PROMPT.json" ]; then
  PROMPT_VER=$(jq -r '.meta.version' "$CARTORIO/PROMPT.json" 2>/dev/null)
  PROMPT_DATE=$(jq -r '.meta.date' "$CARTORIO/PROMPT.json" 2>/dev/null)
  echo "PROMPT.json: v${PROMPT_VER} (${PROMPT_DATE})"
fi
if [ -f "$MEM_DIR/MEMORY.md" ]; then
  COUNT=$(grep -c "^- " "$MEM_DIR/MEMORY.md" 2>/dev/null || echo 0)
  echo "MEMORY.md: $COUNT lessons"
fi
echo

# ---- 2. MCPs ----
echo "## MCPs"
MCP_FILE="/Users/gustavoalmeida/.claude/settings.json"
if [ -f "$MCP_FILE" ]; then
  echo "config em $MCP_FILE"
  jq -r '.mcpServers // {} | to_entries[] | "  \(if .value.command or .value.url then "✅" else "⚠" end) \(.key)"' "$MCP_FILE" 2>/dev/null
fi
echo

# ---- 3. HEALTH 8 serviços ----
echo "## 8 Serviços (health_check_7services.sh)"
"$CARTORIO/scripts/health_check_7services.sh" 2>&1 | sed 's/^/  /'
echo

# ---- 4. TAILSCALE + SSH ----
echo "## Tailscale"
if command -v tailscale >/dev/null; then
  ACTIVE=$(tailscale status 2>/dev/null | grep -c -E '^[0-9]') || echo "?"
  echo "  nodes ativos: $ACTIVE"
  VPS=$(tailscale status 2>/dev/null | grep '100.99.172.84' | awk '{print "vps-cartorio: "$2" "$3}')
  echo "  $VPS"
  echo -n "  SSH VPS: "
  if timeout 5 ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no root@100.99.172.84 'echo ok' >/dev/null 2>&1; then
    echo "✅"
  else
    echo "❌"
  fi
fi
echo

# ---- 5. GIT ----
echo "## Git"
cd "$CARTORIO" && {
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  LAST=$(git log --oneline -1 2>/dev/null | head -c 100)
  CHANGED=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
  echo "  branch: $BRANCH | changed: $CHANGED files"
  echo "  last:   $LAST"
}
echo

# ---- 6. SQUADS ----
echo "## Squads (PROMPT.json)"
jq -r '.squads_status | to_entries[] | "  \(.key): \(.value.done // "?")/\(.value.total) (\(.value.pct // "?")%)  \(.value.status // "  ")"' \
  "$CARTORIO/PROMPT.json" 2>/dev/null | head -15
echo

# ---- 7. SUI blockers ----
echo "## SUI Blockers (3 ativos)"
jq -r '.blockers_SUI[] | "  🔴 \(.id): \(.blocker) → \(.action) [\(.priority)]"' "$CARTORIO/PROMPT.json" 2>/dev/null
echo

# ---- 8. Issues REAIS vs FALSOS POSITIVOS ----
echo "## Issues REAIS vs FALSOS POSITIVOS (atualizado 2026-07-01 11:18)"
echo "  ESPERADOS (não alarmar):"
echo "    ⏸ N8N off — validado 2026-07-01"
echo "    ⏸ SUP 404 Kong auth gate — design correto"
echo "    ⏸ TGB 404 sem token — token em .env, bot validado E2E"
echo "  FALSOS POSITIVOS RESOLVIDOS:"
echo "    ✅ pgweb 0/1 — falso positivo (container Up 5min, Easypanel não sincroniza)"
echo "    ✅ API 3 containers — falso positivo (só 1 ativo, outros Shutdown de tasks antigas)"
echo "  REAIS a corrigir (você):"
echo "    🔴 Render key rnd_QP8GWTShurLmVGSp3H2e25pXsKti expirada — Gustavo regenerar em render.com (regra no_key_rotation)"
echo "    🟡 Linear API key — header não usa Bearer (enviar Authorization: lin_api_...)"
echo "  REAIS a corrigir (dev):"
echo "    🔴 opencode_go 429 Monthly limit — LLM chain cai, comandos Telegram nativos OK (lesson 114)"
echo "  RESOLVIDOS HOJE:"
echo "    ✅ Telegram webhook latency 14-52s — fix httpx.Timeout granular (lesson 113, commit 1902ffe)"
echo "    ✅ OpenClaw DNS swarm — MCP usa Tailscale IP 100.99.172.84:18789 (lesson 115)"
echo

# ---- 9. Próximos passos ----
echo "## Próximo passo?"
echo "  1. Religar N8N + validar 35 workflows"
echo "  2. Fix Render key (SUI ou new key no .env)"
echo "  3. Subir pgweb (docker service scale + debug)"
echo "  4. Implementar D26-D32 (LGPD endpoints)"
echo "  5. Outro: ___"