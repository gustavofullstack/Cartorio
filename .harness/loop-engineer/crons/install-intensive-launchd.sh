#!/usr/bin/env bash
set -uo pipefail
PROJECT="/Users/gustavoalmeida/projetos/Cartorio"
SCRIPT="$PROJECT/.harness/loop-engineer/crons/install-intensive.sh"
PLIST="$HOME/Library/LaunchAgents/com.cartorio.intensive.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.cartorio.intensive</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT</string>
    </array>
    <key>StartInterval</key><integer>1800</integer> <!-- 30 min -->
    <key>RunAtLoad</key><false/>
    <key>StandardOutPath</key><string>/tmp/cartorio-intensive.out</string>
    <key>StandardErrorPath</key><string>/tmp/cartorio-intensive.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST" 2>/dev/null || true
launchctl start com.cartorio.intensive 2>/dev/null || true
echo "✅ Intensive mode plist installed: $PLIST"
echo "   30min cycle (every 30 min while away)"
launchctl list 2>/dev/null | grep cartorio
