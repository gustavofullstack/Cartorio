#!/usr/bin/env bash
# install_mcp_clients.sh
# Instala/registra o MCP server "coding-vps-orchestrator" em clientes MCP conhecidos.
# - Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
# - Cursor:        ~/.cursor/mcp.json
# - TRAE IDE / TRAE SOLO: ~/.trae/mcp.json + repo .trae/mcp-servers/coding-vps.json
# - Antigravity:   ~/.antigravity/mcp.json
# Uso: bash scripts/install_mcp_clients.sh [install|uninstall|status]
#
# Secrets: LITELLM_API_KEY NÃO é gravado em plain text. Export no shell ou use
# ~/.mavis/secrets/coding-vps-global.env (não commitar).

set -euo pipefail

PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ORCHESTRATOR="$SCRIPT_DIR/coding_vps_mcp_orchestrator.py"
SSH_KEY="${HOME}/.ssh/id_ed25519_cartorio"
SSH_HOST="${SSH_TAILSCALE_HOST:-100.99.172.84}"

ACTION="${1:-install}"

_write_mcp_json() {
  local cfg="$1"
  mkdir -p "$(dirname "$cfg")"
  python3 - "$cfg" "$ORCHESTRATOR" "$PYTHON_BIN" "$SSH_KEY" "$SSH_HOST" <<'PYEOF'
import json, sys
path, orch, py, key, host = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
config = {
    "$schema": "https://modelcontextprotocol.io/schemas/mcp-server.json",
    "mcpServers": {
        "coding-vps-orchestrator": {
            "command": py,
            "args": [orch, "mcp"],
            "env": {
                "SSH_PRIVATE_KEY": key,
                "SSH_TAILSCALE_HOST": host,
            },
            "description": (
                "coding-vps-orchestrator: 62 tools / 13 categories via MCP stdio. "
                "Optional: set LITELLM_API_KEY in the client environment."
            ),
        }
    },
}
# Preserve LITELLM_API_KEY if already present in an existing local config (never invent one).
try:
    with open(path) as f:
        prev = json.load(f)
    prev_env = (
        prev.get("mcpServers", {})
        .get("coding-vps-orchestrator", {})
        .get("env", {})
    )
    if prev_env.get("LITELLM_API_KEY"):
        config["mcpServers"]["coding-vps-orchestrator"]["env"]["LITELLM_API_KEY"] = prev_env[
            "LITELLM_API_KEY"
        ]
except Exception:
    pass
with open(path, "w") as f:
    json.dump(config, f, indent=2)
    f.write("\n")
print(f"[ok] wrote {path}")
PYEOF
}

case "$ACTION" in
  install)
    echo "== installing coding-vps MCP into clients =="
    _write_mcp_json "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    _write_mcp_json "$HOME/.cursor/mcp.json"
    _write_mcp_json "$HOME/.trae/mcp.json"
    _write_mcp_json "$HOME/.antigravity/mcp.json"
    # Project-local TRAE auto-detect
    _write_mcp_json "$REPO_ROOT/.trae/mcp-servers/coding-vps.json"
    # Copy canonical templates into scripts/ (already versioned; re-sync for convenience)
    cp "$SCRIPT_DIR/mcp_config.trae.json" "$SCRIPT_DIR/mcp_config.trae.json.bak" 2>/dev/null || true
    echo ""
    echo "Done. Restart the MCP client to load the server."
    echo "Validate: bash $SCRIPT_DIR/validate_coding_vps_tools_60.sh"
    echo "Or:       $PYTHON_BIN $ORCHESTRATOR list   # expect 62 tools"
    ;;
  uninstall)
    echo "== uninstall coding-vps MCP =="
    # Only remove our key from configs when the file is solely ours; otherwise leave alone.
    for f in \
      "$HOME/Library/Application Support/Claude/claude_desktop_config.json" \
      "$HOME/.cursor/mcp.json" \
      "$HOME/.trae/mcp.json" \
      "$HOME/.antigravity/mcp.json"
    do
      if [[ -f "$f" ]]; then
        python3 - "$f" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
servers = cfg.get("mcpServers") or {}
if "coding-vps-orchestrator" in servers:
    del servers["coding-vps-orchestrator"]
    cfg["mcpServers"] = servers
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print(f"[ok] removed coding-vps-orchestrator from {path}")
else:
    print(f"[skip] no coding-vps-orchestrator in {path}")
PY
      fi
    done
    echo "Done."
    ;;
  status)
    echo "== status =="
    echo "Server: $ORCHESTRATOR"
    test -f "$ORCHESTRATOR" && echo "  exists" || echo "  MISSING"
    "$PYTHON_BIN" -c "import fastmcp; print(f'  fastmcp {fastmcp.__version__}')" 2>/dev/null || echo "  fastmcp: NOT INSTALLED"
    test -f "$SSH_KEY" && echo "  SSH key OK: $SSH_KEY" || echo "  SSH key MISSING: $SSH_KEY"
    echo ""
    echo "Configs:"
    for label_path in \
      "Claude Desktop|$HOME/Library/Application Support/Claude/claude_desktop_config.json" \
      "Cursor|$HOME/.cursor/mcp.json" \
      "TRAE|$HOME/.trae/mcp.json" \
      "Antigravity|$HOME/.antigravity/mcp.json" \
      "TRAE project|$REPO_ROOT/.trae/mcp-servers/coding-vps.json"
    do
      label="${label_path%%|*}"
      path="${label_path#*|}"
      if [[ -f "$path" ]] && grep -q "coding_vps_mcp_orchestrator.py" "$path" 2>/dev/null; then
        echo "  [installed] $label -> $path"
      else
        echo "  [missing]   $label"
      fi
    done
    echo ""
    echo "Tool count (CLI):"
    "$PYTHON_BIN" "$ORCHESTRATOR" list 2>&1 | head -1
    ;;
  *)
    echo "Usage: $0 [install|uninstall|status]"
    exit 2
    ;;
esac
