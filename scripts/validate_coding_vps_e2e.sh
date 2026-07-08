#!/usr/bin/env bash
# validate_coding_vps_e2e.sh — E2E validation: 21 coding agents via MiniMax-M3 XMax Thinking
# Source: Lesson 159 (2026-07-08)
# Valida que cada coding agent está respondendo via LiteLLM proxy com o modelo MiniMax-M3
#
# Uso:  ./scripts/validate_coding_vps_e2e.sh
#       ./scripts/validate_coding_vps_e2e.sh --json
#       ./scripts/validate_coding_vps_e2e.sh --prompt "PING-OK-21"
#
# Requer: SSH key ~/.ssh/id_ed25519_cartorio + acesso Tailscale 100.99.172.84

set -uo pipefail

SSH_KEY="${SSH_PRIVATE_KEY:-~/.ssh/id_ed25519_cartorio}"
HOST="${SSH_TAILSCALE_HOST:-100.99.172.84}"
PROMPT="PING-OK-21"
JSON_MODE=0

for arg in "$@"; do
  case "$arg" in
    --json) JSON_MODE=1 ;;
    --prompt) shift; PROMPT="${1:-PING-OK-21}" ;;
    -h|--help) echo "Uso: $0 [--json] [--prompt 'PING-OK-21']"; exit 0 ;;
  esac
done

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Coding-VPS E2E Validation (MiniMax-M3 XMax Thinking) ==="
echo "Host: ${HOST} | Prompt: ${PROMPT}"
echo ""

# 1. Conectividade
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$SSH_KEY" "root@${HOST}" "echo connected" >/dev/null 2>&1; then
  echo -e "${RED}✗ SSH unreachable at ${HOST}${NC}"
  exit 1
fi
echo -e "${GREEN}✓ SSH connected${NC}"

# 2. Upload test script
LOCAL_SCRIPT="$(mktemp -t coding_vps_e2e_XXXXXX.py)"
cat > "$LOCAL_SCRIPT" <<'PYEOF'
"""E2E test all coding-vps agents via MiniMax-M3 XMax Thinking."""
import json
import sys
import time
import urllib.request
import urllib.parse

PROMPT = sys.argv[1] if len(sys.argv) > 1 else "PING-OK-21"

# Agents that expect POST + query string (FastAPI Python)
QUERY_PARAM_AGENTS = [
    ("side-stack", "coding-vps-agents_crew-ai", 8001),
    ("side-stack", "coding-vps-agents_goose", 8002),
    ("side-stack", "coding-vps-agents_hermes", 8003),
    ("side-stack", "coding-vps-agents_langgraph", 8005),
    ("side-stack", "coding-vps-agents_openchamber", 8006),
    ("side-stack", "coding-vps-agents_openclaw", 8007),
    ("side-stack", "coding-vps-agents_openhands", 8009),
    ("main", "coding-vps_apenas_para_auxilio_crew-ai", 8001),
    ("main", "coding-vps_apenas_para_auxilio_goose", 8002),
    ("main", "coding-vps_apenas_para_auxilio_hermes", 8003),
    ("main", "coding-vps_apenas_para_auxilio_kilo-org_kilocode", 8004),
    ("main", "coding-vps_apenas_para_auxilio_langgraph", 8005),
    ("main", "coding-vps_apenas_para_auxilio_openchamber", 8006),
    ("main", "coding-vps_apenas_para_auxilio_openclaw", 8007),
    ("main", "coding-vps_apenas_para_auxilio_openhands", 8009),
]

# Agents that expect POST + JSON body (Node.js server.js)
JSON_BODY_AGENTS = [
    ("side-stack", "coding-vps-agents_kilo-org_kilocode", 8004),
    ("side-stack", "coding-vps-agents_opencode", 8008),
]


def call_query(host, port, prompt, max_tokens=120):
    url = f"http://{host}:{port}/chat?prompt={urllib.parse.quote(prompt)}&max_tokens={max_tokens}"
    req = urllib.request.Request(url, method="POST")
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=30)
        body = json.loads(r.read().decode())
        return True, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return False, {"http": e.code, "body": e.read().decode()[:200]}, time.time() - t0
    except Exception as e:
        return False, {"error": str(e)[:200]}, time.time() - t0


def call_json(host, port, prompt, max_tokens=120):
    url = f"http://{host}:{port}/chat"
    body = json.dumps({"prompt": prompt, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=30)
        body = json.loads(r.read().decode())
        return True, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return False, {"http": e.code, "body": e.read().decode()[:200]}, time.time() - t0
    except Exception as e:
        return False, {"error": str(e)[:200]}, time.time() - t0


results = []
for proj, host, port in QUERY_PARAM_AGENTS:
    ok, body, elapsed = call_query(host, port, PROMPT)
    if ok:
        results.append({
            "project": proj, "host": host, "port": port, "ok": True, "method": "query",
            "reply": body.get("reply", "")[:60],
            "reasoning_tokens": body.get("reasoning_tokens", 0),
            "elapsed_s": round(elapsed, 2),
        })
    else:
        results.append({
            "project": proj, "host": host, "port": port, "ok": False, "method": "query",
            "error": str(body)[:120], "elapsed_s": round(elapsed, 2),
        })

for proj, host, port in JSON_BODY_AGENTS:
    ok, body, elapsed = call_json(host, port, PROMPT)
    if ok:
        results.append({
            "project": proj, "host": host, "port": port, "ok": True, "method": "json",
            "reply": body.get("reply", "")[:60],
            "reasoning_tokens": body.get("reasoning_tokens", 0),
            "elapsed_s": round(elapsed, 2),
        })
    else:
        results.append({
            "project": proj, "host": host, "port": port, "ok": False, "method": "json",
            "error": str(body)[:120], "elapsed_s": round(elapsed, 2),
        })

print(json.dumps(results, indent=2))

# Summary
total = len(results)
ok_n = sum(1 for r in results if r["ok"])
side = [r for r in results if r["project"] == "side-stack"]
main = [r for r in results if r["project"] == "main"]
print(f"\nSCORE: {ok_n}/{total}", file=sys.stderr)
print(f"  side-stack: {sum(1 for r in side if r['ok'])}/{len(side)}", file=sys.stderr)
print(f"  main:       {sum(1 for r in main if r['ok'])}/{len(main)}", file=sys.stderr)
sys.exit(0 if ok_n == total else 1)
PYEOF

# 3. SCP + run inside litellm-app container
REMOTE_TMP="/tmp/validate_coding_vps_e2e_$$.py"
scp -o BatchMode=yes -i "$SSH_KEY" "$LOCAL_SCRIPT" "root@${HOST}:${REMOTE_TMP}" 2>/dev/null

LITELLM_CID=$(ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" "docker ps -q -f name=coding-vps_apenas_para_auxilio_litellm-app | head -1" 2>/dev/null)
if [[ -z "$LITELLM_CID" ]]; then
  echo -e "${RED}✗ litellm-app container not running${NC}"
  rm -f "$LOCAL_SCRIPT"
  ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" "rm -f ${REMOTE_TMP}" 2>/dev/null
  exit 2
fi

# 4. Run test - capture JSON stdout + summary stderr separately
# Copy once, then run twice (once for stdout JSON, once for stderr summary) for clean separation
ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker cp ${REMOTE_TMP} ${LITELLM_CID}:/tmp/validate.py" >/dev/null 2>&1

JSON_BODY=$(ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker exec ${LITELLM_CID} python3 /tmp/validate.py '${PROMPT}' 2>/dev/null" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data, indent=2))
")

SUMMARY=$(ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker exec ${LITELLM_CID} python3 -c \"
import subprocess, sys
r = subprocess.run(['python3', '/tmp/validate.py', '${PROMPT}'], capture_output=True, text=True)
for line in r.stderr.splitlines():
    if line.startswith('SCORE') or line.startswith('  side') or line.startswith('  main'):
        print(line)
\"" 2>/dev/null)

# Cleanup
rm -f "$LOCAL_SCRIPT"
ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" "rm -f ${REMOTE_TMP}" 2>/dev/null

# Output
if [[ $JSON_MODE -eq 1 ]]; then
  echo "$JSON_BODY"
else
  echo ""
  echo "$JSON_BODY" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'{\"STATUS\":<6} {\"PROJECT\":<11} {\"AGENT\":<55} {\"REPLY\":<35} {\"REASONING\":>10} {\"TIME\":>8}')
print('-' * 130)
for r in data:
    if r['ok']:
        print(f\"{'OK':<6} {r['project']:<11} {r['host']:<55} {repr(r['reply'][:35]):<35} {r['reasoning_tokens']:>10} {r['elapsed_s']:>7.2f}s\")
    else:
        print(f\"{'FAIL':<6} {r['project']:<11} {r['host']:<55} {repr(r.get('error','')[:35]):<35} {'-':>10} {r['elapsed_s']:>7.2f}s\")
"
fi

echo ""
echo "=== Summary ==="
echo "$SUMMARY" | sed 's/^/  /'
echo ""
echo "=== Done ==="
