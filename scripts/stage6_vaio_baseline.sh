#!/usr/bin/env bash
# stage6_vaio_baseline.sh — Stage 6 Phase 1/3: VAIO Arch baseline (read-only)
# Uso: rodar NO VAIO (ou via ssh agent-os 'bash -s' < stage6_vaio_baseline.sh)
# Saída: JSON em stdout. NÃO coleta secrets nem conteúdo de .env.
set -u

esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
cmd() { command -v "$1" >/dev/null 2>&1 && echo true || echo false; }
run() { if command -v timeout >/dev/null 2>&1; then timeout 10 bash -c "$1" 2>/dev/null | head -5; else bash -c "$1" 2>/dev/null | head -5; fi; }

CPU=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || true); CPU=${CPU:-null}
MEM=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || true); MEM=${MEM:-null}
DISK=$(df -m / 2>/dev/null | awk 'NR==2{print $4}' || true); DISK=${DISK:-null}

echo "{"
echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
echo "  \"hostnamectl\": \"$(esc "$(run hostnamectl | tr '\n' ' ')")\","
echo "  \"os_release\": \"$(esc "$(run 'grep -E "^(NAME|VERSION)=" /etc/os-release' | tr '\n' ' ')")\","
echo "  \"kernel\": \"$(esc "$(uname -srmo)")\","
echo "  \"user\": \"$(esc "$(id -un) ($(id -u)) groups=$(id -Gn | tr ' ' ',')")\","
echo "  \"uptime\": \"$(esc "$(run 'uptime -p || uptime')")\","
echo "  \"cpu_cores\": $CPU,"
echo "  \"mem_mb\": $MEM,"
echo "  \"disk_root_avail_mb\": $DISK,"
echo "  \"tools\": {"
echo "    \"systemctl\": $(cmd systemctl), \"python3\": $(cmd python3), \"node\": $(cmd node),"
echo "    \"bun\": $(cmd bun), \"uv\": $(cmd uv), \"git\": $(cmd git), \"docker\": $(cmd docker),"
echo "    \"tailscale\": $(cmd tailscale), \"sshd\": $(cmd sshd)"
echo "  },"
echo "  \"tailscaled_active\": $(systemctl is-active tailscaled 2>/dev/null | grep -q active && echo true || echo false),"
echo "  \"sshd_active\": $(systemctl is-active sshd 2>/dev/null | grep -q active && echo true || echo false),"
echo "  \"tailscale_ip4\": \"$(esc "$(tailscale ip -4 2>/dev/null | head -1)")\","
echo "  \"port22_listen\": $( (ss -lnt 2>/dev/null | grep -q ':22 ' || ss -lnt 2>/dev/null | grep -q ':22$') && echo true || echo false),"
echo "  \"hermes_installed\": $(test -d "$HOME/.hermes/hermes-agent" && echo true || echo false),"
echo "  \"hermes_profiles\": \"$(esc "$(ls "$HOME/.hermes/profiles" 2>/dev/null | tr '\n' ',')")\","
echo "  \"spectrum_reachable\": $(curl -s -o /dev/null -m 8 -w '%{http_code}' https://spectrum.photon.codes/ 2>/dev/null | grep -qE '^[0-9]' && echo true || echo false),"
echo "  \"mcp_authority_reachable\": $(curl -s -o /dev/null -m 8 https://api.2notasudi.com.br/mcp/ 2>/dev/null && echo true || echo false)"
echo "}"
