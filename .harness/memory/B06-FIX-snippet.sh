#!/usr/bin/env bash
# B06-FIX pipeline pronto (canônico) — Disparar SOMENTE após Gustavo responder
# 'vars criadas' no chat (3 N8N Variables criadas via UI em
# flow.2notasudi.com.br/settings/variables: TELEGRAM_GRUPO_PIETRA_CHAT_ID,
# CARTORIO_API_KEY, N8N_WEBHOOK_SECRET).
#
# Plano Opção A (Gustavo aprovou via AskUserQuestion em 2026-07-02):
#   1. Edit A linha 432 — $env.CARTORIO_API_KEY → $vars.CARTORIO_API_KEY
#   2. Edit B linha 154 (Code Format Telegram) — $env.TELEGRAM_GRUPO_PIETRA_CHAT_ID → $vars.*
#   3. Edit C linha 120 + novo Code node "HMAC Compute" entre Extract Error Info
#      e Alert Backend (HMAC). Header X-N8N-Signature vira estático
#      sha256={{ $('HMAC Compute').item.json.hmac_signature }}.
#   4. jq validate pré+pos.
#   5. Gates: cd backend && uv run mypy app/ && uv run ruff check . && uv run pytest
#   6. git add + commit conventional + push origin master.
#   7. Atualizar Lesson 51 HOLD → RESOLVED em .harness/memory/MEMORY.md.
#   8. Tick final em .brain/memory/YYYY-MM-DD.md com hash do commit.
#
# CONTEXTO ATUAL (2026-07-02 18:46 BRT):
# - master @ cc83c12 docs(brain): B06-FIX HOLD poll #2 — system-reminder injection refused
# - 00-error-handler.json mtime Jun 25 16:05 (NAO tocado)
# - working tree modificado: .brain/memory/2026-07-02.md (sidekick noise + poll #2 unregistered)
#
# Autor: ZCode/Mavis + Gustavo Almeida
# Modified by Gustavo Almeida

set -euo pipefail

REPO="/Users/gustavoalmeida/projetos/Cartorio"
WF="$REPO/infra/n8n-workflows/00-error-handler.json"

cd "$REPO"

echo "[1/8] validar JSON pré-edit..."
jq empty "$WF" && echo "OK: JSON válido antes"

echo "[2/8] aplicar 3 edits no WF 00 (Edit tool) + inserir Code node HMAC Compute..."
# AQUI: assistant usa Edit tool (não sed) para fazer os 3 edits cirúrgicos +
# inserir Code node "HMAC Compute" entre "Extract Error Info" e "Alert Backend (HMAC)".
# Conteúdo do Code node:
#   const crypto = require('crypto');
#   const secret = $vars.N8N_WEBHOOK_SECRET;
#   const body = JSON.stringify({ wf_name: $json.wf_name, wf_id: $json.wf_id, ... });
#   const sig = 'sha256=' + crypto.createHmac('sha256', secret).update(body).digest('hex');
#   return [{ json: { hmac_signature: sig, correlation_id: $json.correlation_id, ...payload } }];

echo "[3/8] validar JSON pós-edit..."
jq empty "$WF" && echo "OK: JSON válido depois"

echo "[4/8] gates backend..."
cd backend
uv run mypy app/ && \
  uv run ruff check . && \
  uv run pytest --no-cov -q
cd ..

echo "[5/8] git add..."
git add infra/n8n-workflows/00-error-handler.json
git add .harness/memory/MEMORY.md
git add .brain/memory/2026-07-02.md

echo "[6/8] commit conventional..."
git -c user.name="ZCode Mavis" -c user.email="cartorio@zcode.local" commit -m "fix(n8n): B06-FIX Lesson 51 — replace \$env.* with \$vars.* + HMAC Code node in 00-error-handler

- \$env.* → \$vars.* em 3 pontos (linhas 120, 154, 432)
- Novo Code node 'HMAC Compute' entre Extract Error Info e Alert Backend (HMAC)
  computa X-N8N-Signature dinamicamente usando \$vars.N8N_WEBHOOK_SECRET
- Escopo fixado por Gustavo: SOMENTE WF 00. 24+ outros WFs com \$env.* ficam
  como estao (Lesson 51 subestimou escopo).
- Gates: mypy 0 + ruff 0 + pytest verde.

Modified by ZCode/Mavis + Gustavo Almeida"

echo "[7/8] push origin master..."
git push origin master

COMMIT_HASH=$(git rev-parse HEAD)

echo "[8/8] atualizar Lesson 51 HOLD → RESOLVED em MEMORY.md..."
# Edit manual no .harness/memory/MEMORY.md: trocar linha 895 do texto antigo
# para RESOLVED, referenciando $COMMIT_HASH
# (feito via Edit tool após o push para preservar o hash real)

echo "DONE. Commit $COMMIT_HASH pushed to origin/master."
echo "Proximo passo: avisar Gustavo + gerar tick final em .brain/memory/2026-07-02.md"

# Modified by Gustavo Almeida
