#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR: ZED.APP (editor + AI agent) — Validation contract
# ═══════════════════════════════════════════════════════════════════════════════
# Esta plataforma é EXTERNA a esta sessão. Validador produz SPEC
# para a sessão ZED validar-se a si mesma ao ser invocada.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
OUT="/tmp/cartorio-validator-zed-$(date +%Y%m%d-%H%M%S).json"

# Spec pra ZED rodar em sua sessão (não posso rodar daqui)
cat > "$OUT" <<'JSON'
{
  "platform": "ZED.APP",
  "model": "ZED-AI",
  "role": "Editor AI + quick refactoring",
  "remote_session": true,
  "checks_spec_for_zed_session": [
    "✓ ZED aberto com cartorio.workspace",
    "✓ git branch = master",
    "✓ ruff check backend/app/ → 0 errors",
    "✓ Backend linter clean",
    "✓ Edit permissions ativos"
  ],
  "contract_with_minimax": "ZED entrega patches em master como commits refactor: ... (Modified by Gustavo Almeida)",
  "verdict": "SPEC_PROVIDED",
  "note": "Esta plataforma roda em sua própria sessão. Use o spec acima para validar."
}
JSON

cat "$OUT"
