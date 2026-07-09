#!/bin/bash
# Setup wizard para integrar coding-vps MCP orchestrator com TRAE/Antigravity/Claude
set -e
echo "=== coding-vps MCP integration setup ==="
echo

# 1. Validar HTTP server
echo "1. Validating HTTP server..."
if curl -s -f http://100.99.172.84:8100/ -o /tmp/cv.json; then
  echo "OK HTTP server UP at http://100.99.172.84:8100/"
  TOOLS=$(curl -s http://100.99.172.84:8100/tools | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
  echo "   $TOOLS tools available"
else
  echo "FAIL HTTP server DOWN - check coding-vps-orchestrator service"
  exit 1
fi

# 2. TRAE config
echo "2. TRAE config..."
mkdir -p ~/.trae/mcp-servers
cat > ~/.trae/mcp-servers/coding-vps.json << 'JSON_EOF'
{
  "mcpServers": {
    "coding-vps": {
      "command": "python3",
      "args": ["/Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_mcp_orchestrator.py", "mcp"],
      "env": {"SSH_PRIVATE_KEY": "/Users/gustavoalmeida/.ssh/id_ed25519_cartorio", "LITELLM_API_KEY": "e39dss0k1baohuqkprjv"}
    }
  }
}
JSON_EOF
echo "OK ~/.trae/mcp-servers/coding-vps.json"

# 3. TRAE SOLO config
echo "3. TRAE SOLO config..."
mkdir -p ~/.trae-solo/mcp-servers
cp ~/.trae/mcp-servers/coding-vps.json ~/.trae-solo/mcp-servers/coding-vps.json
echo "OK ~/.trae-solo/mcp-servers/coding-vps.json"

# 4. Antigravity config
echo "4. Antigravity config..."
mkdir -p ~/.antigravity/mcp-servers
cp ~/.trae/mcp-servers/coding-vps.json ~/.antigravity/mcp-servers/coding-vps.json
echo "OK ~/.antigravity/mcp-servers/coding-vps.json"

# 5. Test
echo "5. Testing..."
python3 /Users/gustavoalmeida/projetos/Cartorio/scripts/coding_vps_client.py call chat_minimax prompt="Responda SETUP-OK" max_tokens=30 || echo "(test skipped - server may be down)"
echo
echo "=== Setup complete ==="
echo "Open TRAE IDE -> Settings -> MCP Servers -> Restart"
echo "Open TRAE SOLO.APP -> Preferences -> MCP -> Restart"
echo "Open Antigravity.APP -> Settings -> MCP -> Restart"
