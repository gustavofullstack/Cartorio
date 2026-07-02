#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR: ZCode.APP (ZCode agent CLI ACPX)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
OUT="/tmp/cartorio-validator-zcode-$(date +%Y%m%d-%H%M%S).json"

cat > "$OUT" <<'JSON'
{
  "platform": "ZCode.APP",
  "model": "Minimax-M3 via ACPX",
  "role": "Alternative coding agent (parallel tasks)",
  "remote_session": true,
  "checks_spec_for_zcode_session": [
    "✓ ZCode cli ativo e autenticado",
    "✓ context window 1M ativo",
    "✓ minimax API key configurada",
    "✓ /goal handler pronto",
    "✓ Acesso a .harness/agents/ para orquestração"
  ],
  "contract_with_minimax": "ZCode pode rodar tasks paralelas com task-id prefixo ZC-, reportar progresso via paperclip-board/board.json, e commitar com suffix [ZC-XXX]",
  "verdict": "SPEC_PROVIDED",
  "note": "ZCode opera em sessão paralela. Use o spec acima para self-validate."
}
JSON

cat "$OUT"
