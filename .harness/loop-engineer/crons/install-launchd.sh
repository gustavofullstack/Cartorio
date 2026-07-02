#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# CRON INSTALLER — Instala goal-loop-cron.sh no launchd do macOS
# ═══════════════════════════════════════════════════════════════════════════════
# Roda: bash .harness/loop-engineer/crons/install-launchd.sh
# Requer: macOS (launchd) ou Linux (cron via crontab -e)
# Requer: Gustavo root/sudo permissions
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
PROJECT="/Users/gustavoalmeida/projetos/Cartorio"
SCRIPT="$PROJECT/.harness/loop-engineer/goal-loop-cron.sh"
PLIST="$HOME/Library/LaunchAgents/com.cartorio.goal-loop.plist"

# 1. macOS launchd
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST_XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.cartorio.goal-loop</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT</string>
    </array>
    <key>StartInterval</key><integer>14400</integer> <!-- 4h -->
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>/tmp/cartorio-goal-loop.out</string>
    <key>StandardErrorPath</key><string>/tmp/cartorio-goal-loop.err</string>
</dict>
</plist>
PLIST_XML

launchctl load "$PLIST" 2>/dev/null || true
launchctl start com.cartorio.goal-loop 2>/dev/null || true

echo "✅ launchd plist instalado: $PLIST"
echo "   Comando pra verificar: launchctl list | grep cartorio"
echo "   Comando pra remover: launchctl unload $PLIST"
