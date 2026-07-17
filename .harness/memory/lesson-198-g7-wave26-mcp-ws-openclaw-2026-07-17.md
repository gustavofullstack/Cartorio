# Lesson 198 — G7 Wave 26: MCP + WS + OpenClaw + N8N KISS (2026-07-17)

Type: project + reference

## 4 slots

| Slot | Tasks | Result |
|------|-------|--------|
| A1 | G7.09.T3/T4 | cartorio MCP 13 tools; coding-vps 63≥62; mount wiring OK |
| A2 | G7.10.T4 + G7.11.* | 6 WS ping tests; Tailscale restore runbook HOLD live |
| A3 | G7.14.T2/T3 + G7.19.T4 | skills registry sync; context 1M; 25 PII fields |
| A4 | G7.20.T4 + G7.22.T3 + G7.24.T2 | N8N 1 archive; pre-commit doc; TG1000 31/31 |

## Validação

```bash
cd backend && uv run pytest -q --no-cov tests/test_mcp_mount_smoke.py tests/test_ws_ping_g7.py
# 35 passed (with wave24) / MCP+WS subset green
python3 scripts/mcp_tools_inventory.py
python3 scripts/telegram_1000_subset_check.py  # 31/31
```

## Notas

- MCP live StreamableHTTP handshake = HOLD prod
- Tailscale restore = HOLD-GUSTAVO (docs only)
- OpenClaw cartorio-bot deploy still SUI
- Skills platform (.agents) ≠ OpenClaw runtime skills — two layers by design

**Modified by Gustavo Almeida — G7 Wave 26**
