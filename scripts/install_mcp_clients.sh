#!/usr/bin/env bash
# install_mcp_clients.sh
# Instala/registra o MCP server "coding-vps-orchestrator" em clientes MCP conhecidos.
# - Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
# - Cursor:        ~/.cursor/mcp.json (Linux) ou %USERPROFILE%/.cursor/mcp.json (Windows)
# - TRAE IDE / Antigravity: detectam configs no mesmo formato
# Uso: bash scripts/install_mcp_clients.sh [install|uninstall|status]

set -euo pipefail

PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRATOR="$SCRIPT_DIR/coding_vps_mcp_orchestrator.py"
SSH_KEY="${HOME}/.ssh/id_ed25519_cartorio"

ACTION="${1:-install}"

write_claude_desktop() {
  local cfg="$1/Claude/claude_desktop_config.json"
  mkdir -p "$(dirname "$cfg")"
  python3 - "$cfg" "$ORCHESTRATOR" "$PYTHON_BIN" "$SSH_KEY" <<'PYEOF'
import json, sys
path, orch, py, key = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
config = {"mcpServers": {"coding-vps-orchestrator": {
    "command": py, "args": [orch, "mcp"],
    "env": {"SSH_PRIVATE_KEY": key, "SSH_TAILSCALE_HOST": "100.99.172.84"},
}}}
with open(path, "w") as f:
    json.dump(config, f, indent=2)
PYEOF
  echo "[ok] Claude Desktop config -> $cfg"
}

write_cursor() {
  local cfg="$1"
  mkdir -p "$(dirname "$cfg")"
  python3 - "$cfg" "$ORCHESTRATOR" "$PYTHON_BIN" "$SSH_KEY" <<'PYEOF'
import json, sys
path, orch, py, key = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
config = {"mcpServers": {"coding-vps-orchestrator": {
    "command": py, "args": [orch, "mcp"],
    "env": {"SSH_PRIVATE_KEY": key, "SSH_TAILSCALE_HOST": "100.99.172.84"},
}}}
with open(path, "w") as f:
    json.dump(config, f, indent=2)
PYEOF
  echo "[ok] Cursor config -> $cfg"
}

write_trae_local() {
  local cfg="$1/.trae/mcp.json"
  mkdir -p "$(dirname "$cfg")"
  python3 - "$cfg" "$ORCHESTRATOR" "$PYTHON_BIN" "$SSH_KEY" <<'PYEOF'
import json, sys
path, orch, py, key = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
config = {"mcpServers": {"coding-vps-orchestrator": {
    "command": py, "args": [orch, "mcp"],
    "env": {"SSH_PRIVATE_KEY": key, "SSH_TAILSCALE_HOST": "100.99.172.84"},
}}}
with open(path, "w") as f:
    json.dump(config, f, indent=2)
PYEOF
  echo "[ok] TRAE local config -> $cfg"
}

case "$ACTION" in
  install)
    echo "== installing coding-vps MCP into clients =="
    write_claude_desktop "$HOME/Library/Application Support"
    write_cursor "$HOME/.cursor/mcp.json"
    write_trae_local "$HOME"
    echo ""
    echo "Done. Reinicie o client MCP para carregar o server."
    echo "Validate: $PYTHON_BIN $ORCHESTRATOR mcp    # deve mostrar '100/100 tools registered'"
    ;;
  uninstall)
    echo "== uninstall coding-vps MCP =="
    rm -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    rm -f "$HOME/.cursor/mcp.json"
    rm -f "$HOME/.trae/mcp.json"
    echo "Done."
    ;;
  status)
    echo "== status =="
    echo "Server: $ORCHESTRATOR"
    test -f "$ORCHESTRATOR" && echo "  exists" || echo "  MISSING"
    "$PYTHON_BIN" -c "import fastmcp; print(f'  fastmcp {fastmcp.__version__}')" 2>/dev/null || echo "  fastmcp: NOT INSTALLED"
    test -f "$SSH_KEY" && echo "  SSH key OK: $SSH_KEY" || echo "  SSH key MISSING: $SSH_KEY (crie com: ssh-keygen -t ed25519 -f $SSH_KEY)"
    echo ""
    echo "Configs em uso:"
    test -f "$HOME/Library/Application Support/Claude/claude_desktop_config.json" && echo "  [installed] Claude Desktop" || echo "  [missing]   Claude Desktop"
    test -f "$HOME/.cursor/mcp.json" && echo "  [installed] Cursor" || echo "  [missing]   Cursor"
    test -f "$HOME/.trae/mcp.json" && echo "  [installed] TRAE local" || echo "  [missing]   TRAE local"
    echo ""
    echo "Test server start (5s timeout):"
    timeout 5 "$PYTHON_BIN" "$ORCHESTRATOR" mcp 2>&1 | grep -E "registered|Error" | head -3
    ;;
  *)
    echo "Usage: $0 [install|uninstall|status]"
    exit 2
    ;;
esac
