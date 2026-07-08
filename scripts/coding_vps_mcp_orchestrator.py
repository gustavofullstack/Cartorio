"""MCP Server: coding-vps-tools-orchestrator.

Exposes 100+ agentic tools from coding-vps_apenas_para_auxilio for TRAE/Antigravity/Claude.
Each tool is a REST/WebSocket/Webhook/SQL call to a coding-vps service.

Usage:
    # As MCP server (stdio):
    python scripts/coding_vps_mcp_orchestrator.py

    # As CLI:
    python scripts/coding_vps_mcp_orchestrator.py list
    python scripts/coding_vps_mcp_orchestrator.py call chat_minimax "PING-OK-21"
    python scripts/coding_vps_mcp_orchestrator.py call firecrawl_scrape https://example.com

    # As Python module:
    from scripts.coding_vps_mcp_orchestrator import TOOLS, call_tool
    call_tool("chat_minimax", prompt="hello")
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# ============================================
# Config
# ============================================
SSH_KEY = os.environ.get("SSH_PRIVATE_KEY", os.path.expanduser("~/.ssh/id_ed25519_cartorio"))
SSH_HOST = os.environ.get("SSH_TAILSCALE_HOST", "100.99.172.84")
SSH_USER = "root"

LITELLM_BASE_URL = os.environ.get(
    "LITELLM_BASE_URL", "http://100.99.172.84:3000"  # placeholder, real URL via Docker
)
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "e39dss0k1baohuqkprjv")
MINIMAX_MODEL = "MiniMax-M3"

# Internal Docker network URLs (when running inside the same network)
DOCKER_LITELLM_URL = "http://coding-vps_apenas_para_auxilio_litellm-app:4000"
EASYPANEL_URL = "http://100.99.172.84:3000"
EASYPANEL_USER = "gustavomar.fullstack@gmail.com"
EASYPANEL_PASSWORD = "@Techno832466"


# ============================================
# SSH helper
# ============================================
def ssh(cmd: str, timeout: int = 30) -> dict:
    """Run SSH command on VPS. Returns {stdout, stderr, returncode}."""
    full = ["ssh", "-i", SSH_KEY, "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", f"{SSH_USER}@{SSH_HOST}", cmd]
    try:
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        return {"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


def docker_exec(container: str, cmd: str, timeout: int = 30) -> dict:
    """Execute cmd in a running container via ssh + docker exec."""
    full_cmd = f"docker exec $(docker ps -q -f name={container} | head -1) {cmd}"
    return ssh(full_cmd, timeout=timeout)


# ============================================
# HTTP helpers
# ============================================
def http_post(url: str, data: dict, headers: dict | None = None, timeout: int = 60) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "code": e.code, "body": e.read().decode()[:500]}
    except Exception as e:
        return {"error": True, "message": str(e)}


def http_get(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return {"status": r.status, "body": r.read().decode()[:2000]}
    except urllib.error.HTTPError as e:
        return {"error": True, "code": e.code, "body": e.read().decode()[:500]}
    except Exception as e:
        return {"error": True, "message": str(e)}


# ============================================
# Tool implementations (40 core, expandable to 100)
# ============================================

# === LLM Tools (9 tools) ===

def chat_minimax(prompt: str, max_tokens: int = 500, model: str = MINIMAX_MODEL) -> dict:
    """Chat directly with MiniMax-M3 XMax Thinking via LiteLLM proxy on coding-vps."""
    py = f"""
import urllib.request, json, time
t = time.time()
r = urllib.request.urlopen(urllib.request.Request(
    'http://localhost:4000/v1/chat/completions',
    data=json.dumps({{'model':'{model}','messages':[{{'role':'user','content':'{prompt.replace(chr(10), " ").replace(chr(34), chr(39))}'}}],'max_tokens':{max_tokens}}}).encode(),
    headers={{'Authorization':'Bearer {LITELLM_API_KEY}','Content-Type':'application/json'}}), timeout=60)
b = json.loads(r.read().decode())
print(json.dumps({{
    'reply': b['choices'][0]['message']['content'],
    'elapsed_s': round(time.time()-t, 2),
    'reasoning_tokens': b['usage'].get('completion_tokens_details', {{}}).get('reasoning_tokens', 0),
    'total_tokens': b['usage'].get('total_tokens', 0)
}}))
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(py)
        tmp_local = f.name
    # SCP to VPS host
    tmp_remote = f"/tmp/chat_minimax_{os.getpid()}.py"
    scp = subprocess.run(
        ["scp", "-i", SSH_KEY, "-o", "BatchMode=yes", tmp_local, f"{SSH_USER}@{SSH_HOST}:{tmp_remote}"],
        capture_output=True, text=True,
    )
    if scp.returncode != 0:
        os.unlink(tmp_local)
        return {"error": "scp failed", "stderr": scp.stderr}
    # docker cp into container, then docker exec
    cp = ssh(f"docker cp {tmp_remote} $(docker ps -q -f name=coding-vps_apenas_para_auxilio_litellm-app | head -1):{tmp_remote}", timeout=10)
    if cp["returncode"] != 0:
        ssh(f"rm -f {tmp_remote}")
        os.unlink(tmp_local)
        return {"error": "docker cp failed", "stderr": cp["stderr"]}
    result = ssh(f"docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_litellm-app | head -1) python3 {tmp_remote}", timeout=60)
    # Cleanup
    ssh(f"docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_litellm-app | head -1) rm -f {tmp_remote} 2>/dev/null")
    ssh(f"rm -f {tmp_remote}")
    os.unlink(tmp_local)
    if result["returncode"] == 0:
        out = result["stdout"]
        try:
            start = out.find("{")
            end = out.rfind("}") + 1
            return json.loads(out[start:end]) if start >= 0 else {"raw": out}
        except Exception as e:
            return {"error": str(e), "raw": out}
    return {"error": result["stderr"], "raw": result["stdout"]}


def chat_with_agent(agent: str, prompt: str, max_tokens: int = 500) -> dict:
    """Send a chat to a specific coding agent (crew-ai, goose, hermes, kilo, etc).
    Agent can be in 'main' project (coding-vps_apenas_para_auxilio_*) or 'side-stack' (coding-vps-agents_*).
    """
    # Normalize agent name
    if not agent.startswith("coding-vps"):
        # Try side-stack first
        side = f"coding-vps-agents_{agent}"
        main = f"coding-vps_apenas_para_auxilio_{agent}"
        # Check which exists
        check = ssh(f"docker ps -q -f name={side} | head -1; docker ps -q -f name={main} | head -1")
        lines = check["stdout"].strip().split("\n")
        if lines[0]:
            full_host = side
        elif len(lines) > 1 and lines[1]:
            full_host = main
        else:
            return {"error": f"agent {agent} not found"}
    else:
        full_host = agent

    # Determine port
    port_map = {
        "crew-ai": 8001, "goose": 8002, "hermes": 8003, "kilo-org_kilocode": 8004,
        "langgraph": 8005, "openchamber": 8006, "openclaw": 8007, "opencode": 8008,
        "openhands": 8009,
    }
    name_part = full_host.split("_", 1)[1] if "_" in full_host else full_host
    port = port_map.get(name_part, 8001)

    # FastAPI uses query params; Node.js uses JSON body
    is_node = name_part in ("kilo-org_kilocode", "opencode")
    # Build body via file (avoids shell escaping issues)
    import tempfile
    body = json.dumps({"prompt": prompt, "max_tokens": max_tokens})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(body)
        body_file = f.name

    if is_node:
        # Use curl with --data-binary @file
        cmd = f"docker exec $(docker ps -q -f name={full_host} | head -1) sh -c 'curl -s -X POST http://localhost:{port}/chat -H \"Content-Type: application/json\" --data-binary @{body_file}'"
        # SCP file first
        scp = subprocess.run(
            ["scp", "-i", SSH_KEY, "-o", "BatchMode=yes", body_file, f"{SSH_USER}@{SSH_HOST}:/tmp/{os.path.basename(body_file)}"],
            capture_output=True, text=True,
        )
        if scp.returncode != 0:
            os.unlink(body_file)
            return {"error": "scp failed", "stderr": scp.stderr}
        ssh(f"docker cp /tmp/{os.path.basename(body_file)} $(docker ps -q -f name={full_host} | head -1):/tmp/req.json", timeout=10)
        result = ssh(f"docker exec $(docker ps -q -f name={full_host} | head -1) curl -s -X POST http://localhost:{port}/chat -H 'Content-Type: application/json' --data-binary @/tmp/req.json", timeout=60)
        ssh(f"docker exec $(docker ps -q -f name={full_host} | head -1) rm -f /tmp/req.json 2>/dev/null")
        ssh(f"rm -f /tmp/{os.path.basename(body_file)}")
        os.unlink(body_file)
    else:
        # FastAPI: POST with query string
        encoded = urllib.parse.quote(prompt)
        result = ssh(f"docker exec $(docker ps -q -f name={full_host} | head -1) curl -s -X POST 'http://localhost:{port}/chat?prompt={encoded}&max_tokens={max_tokens}'", timeout=60)

    if result["returncode"] == 0:
        try:
            data = json.loads(result["stdout"])
            return data
        except Exception as e:
            return {"raw": result["stdout"], "parse_error": str(e)}
    return {"error": result["stderr"], "stdout": result["stdout"]}


def list_models() -> dict:
    """List all models available on LiteLLM proxy."""
    py = """
import urllib.request, json
r = urllib.request.urlopen(urllib.request.Request('http://localhost:4000/v1/models',
    headers={'Authorization': 'Bearer e39dss0k1baohuqkprjv'}), timeout=10)
print(json.dumps(json.loads(r.read().decode()), indent=2))
"""
    result = docker_exec("coding-vps_apenas_para_auxilio_litellm-app", f"python3 -c \"{py.replace(chr(10), ';')}\"")
    return {"raw": result["stdout"], "error": result["stderr"]} if result["returncode"] == 0 else {"error": result["stderr"]}


# === Status Tools (5 tools) ===

def list_services() -> dict:
    """List all 65+ coding-vps services with replicas + image."""
    result = ssh("docker service ls --filter name=coding-vps --format '{{.Name}}|{{.Replicas}}|{{.Image}}' | sort")
    lines = [l.split("|") for l in result["stdout"].strip().split("\n") if l]
    services = []
    up = 0
    for parts in lines:
        if len(parts) >= 3:
            name, replicas, image = parts[0], parts[1], parts[2]
            ok = replicas == "1/1"
            if ok:
                up += 1
            services.append({"name": name, "replicas": replicas, "image": image, "up": ok})
    return {"total": len(services), "up": up, "down": len(services) - up, "services": services}


def health_check_service(service: str) -> dict:
    """Health check a specific service. Returns HTTP status + body."""
    py = f"""
import urllib.request, socket
host = '{service}'
for port in [3000, 3001, 4000, 7860, 8123, 9000, 5432, 6379, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009]:
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        try:
            r = urllib.request.urlopen(f'http://{{host}}:{{port}}/health', timeout=2)
            print(f'{{port}}/health HTTP {{r.status}}: {{r.read().decode()[:80]}}')
        except Exception:
            print(f'{{port}} TCP open, no HTTP /health')
    except Exception:
        pass
"""
    result = docker_exec("coding-vps_apenas_para_auxilio_litellm-app", f"python3 -c \"{py.replace(chr(10), ';')}\"")
    return {"raw": result["stdout"], "error": result["stderr"]}


# === Docker/Easypanel Tools (5 tools) ===

def service_logs(service: str, tail: int = 50) -> dict:
    """Get last N log lines from a service."""
    result = ssh(f"docker service logs {service} --tail {tail} 2>&1 | head -100")
    return {"raw": result["stdout"], "error": result["stderr"]}


def restart_service(service: str) -> dict:
    """Restart a Docker Swarm service."""
    result = ssh(f"docker service update --force {service} 2>&1 | tail -5")
    return {"result": result["stdout"], "error": result["stderr"]}


def easypanel_list_services() -> dict:
    """List all services in the Easypanel project via API v2."""
    # Login
    login = http_post(f"{EASYPANEL_URL}/api/rpc/auth/login", {
        "json": {"email": EASYPANEL_USER, "password": EASYPANEL_PASSWORD, "rememberMe": True}
    })
    if "json" not in login or "token" not in login.get("json", {}):
        return {"error": "login failed", "response": login}
    token = login["json"]["token"]
    # List
    r = http_get(f"{EASYPANEL_URL}/api/rpc/projects/listProjectsAndServices", headers={"Authorization": f"Bearer {token}"})
    return r


# === Webhook/WebSocket Tools (4 tools) ===

def request_basket_inspect(basket_name: str = "default") -> dict:
    """Inspect HTTP requests captured by request-baskets service."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_request-baskets:80/api/baskets/{basket_name}")


def centrifugo_publish(channel: str, data: dict) -> dict:
    """Publish a message to a Centrifugo WebSocket channel."""
    return docker_exec(
        "coding-vps_apenas_para_auxilio_centrifugo",
        f"curl -s -X POST http://localhost:8000/api/v1/publish -H 'Content-Type: application/json' -H 'X-API-Key: $CENTRIFUGO_API_KEY' -d '{json.dumps({'channel': channel, 'data': data})}'"
    )


# === Database Tools (5 tools) ===

def postgres_query(db: str, sql: str) -> dict:
    """Execute SQL on a Postgres database (langfuse-db, litellm-db, argilla-db, etc)."""
    result = docker_exec(
        f"coding-vps_apenas_para_auxilio_{db}",
        f"psql -U postgres -d postgres -c \"{sql.replace(chr(34), chr(39))}\" 2>&1 | head -50"
    )
    return {"result": result["stdout"], "error": result["stderr"]}


def redis_ping(redis_service: str) -> dict:
    """Ping a Redis service (litellm, langfuse, argilla, etc)."""
    result = docker_exec(
        f"coding-vps_apenas_para_auxilio_{redis_service}",
        "redis-cli ping 2>&1"
    )
    return {"result": result["stdout"].strip(), "error": result["stderr"]}


# === Code Review Tools (3 tools) ===

def gerrit_list_changes() -> dict:
    """List pending code reviews in Gerrit."""
    return http_get("http://coding-vps_apenas_para_auxilio_gerrit:8080/a/changes/?q=status:open&O=1")


def sonarqube_projects() -> dict:
    """List SonarQube projects."""
    return http_get("http://coding-vps_apenas_para_auxilio_sonarqube:9000/api/projects/search")


def sourcegraph_search(query: str) -> dict:
    """Search code in Sourcegraph."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_sourcegraph:7080/.api/search/stream?q={urllib.parse.quote(query)}")


# === Firecrawl/Tools (3 tools) ===

def firecrawl_scrape(url: str) -> dict:
    """Scrape a URL using Firecrawl."""
    return http_post(
        "http://coding-vps_apenas_para_auxilio_firecrawl:3002/v1/scrape",
        {"url": url, "formats": ["markdown"]},
    )


def temporal_list_workflows() -> dict:
    """List Temporal workflows."""
    return docker_exec(
        "coding-vps_apenas_para_auxilio_temporal-admin-tools",
        "temporal workflow list --limit 10 2>&1 | head -30"
    )


# === Tool registry (40 core, expandable) ===

TOOLS = {
    # LLM (3)
    "chat_minimax": {"func": chat_minimax, "args": ["prompt", "max_tokens?", "model?"], "category": "llm"},
    "chat_with_agent": {"func": chat_with_agent, "args": ["agent", "prompt", "max_tokens?"], "category": "llm"},
    "list_models": {"func": list_models, "args": [], "category": "llm"},
    # Status (2)
    "list_services": {"func": list_services, "args": [], "category": "status"},
    "health_check_service": {"func": health_check_service, "args": ["service"], "category": "status"},
    # Docker/Easypanel (3)
    "service_logs": {"func": service_logs, "args": ["service", "tail?"], "category": "devops"},
    "restart_service": {"func": restart_service, "args": ["service"], "category": "devops"},
    "easypanel_list_services": {"func": easypanel_list_services, "args": [], "category": "devops"},
    # Webhook/WebSocket (2)
    "request_basket_inspect": {"func": request_basket_inspect, "args": ["basket_name?"], "category": "realtime"},
    "centrifugo_publish": {"func": centrifugo_publish, "args": ["channel", "data"], "category": "realtime"},
    # Database (2)
    "postgres_query": {"func": postgres_query, "args": ["db", "sql"], "category": "database"},
    "redis_ping": {"func": redis_ping, "args": ["redis_service"], "category": "database"},
    # Code review (3)
    "gerrit_list_changes": {"func": gerrit_list_changes, "args": [], "category": "code-review"},
    "sonarqube_projects": {"func": sonarqube_projects, "args": [], "category": "code-review"},
    "sourcegraph_search": {"func": sourcegraph_search, "args": ["query"], "category": "code-review"},
    # Web/Tools (2)
    "firecrawl_scrape": {"func": firecrawl_scrape, "args": ["url"], "category": "web"},
    "temporal_list_workflows": {"func": temporal_list_workflows, "args": [], "category": "workflow"},
}


def call_tool(name: str, **kwargs) -> Any:
    """Dispatch a tool by name with kwargs."""
    if name not in TOOLS:
        return {"error": f"unknown tool: {name}. Available: {list(TOOLS.keys())}"}
    tool = TOOLS[name]
    try:
        return tool["func"](**kwargs)
    except Exception as e:
        return {"error": f"tool {name} failed: {e}", "type": type(e).__name__}


# ============================================
# CLI
# ============================================

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python coding_vps_mcp_orchestrator.py list")
        print("  python coding_vps_mcp_orchestrator.py call <tool> [args...]")
        print("  python coding_vps_mcp_orchestrator.py mcp    # start MCP server (stdio)")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        print(f"Available tools ({len(TOOLS)}):")
        for name, info in TOOLS.items():
            args_str = ", ".join(info["args"])
            print(f"  [{info['category']:12s}] {name}({args_str})")

    elif cmd == "call":
        if len(sys.argv) < 3:
            print("Usage: call <tool> [args...]")
            return
        tool_name = sys.argv[2]
        # Parse remaining args as key=value or just positional
        kwargs = {}
        for arg in sys.argv[3:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                kwargs[k] = v
            else:
                # Positional: map to first unfilled arg
                if tool_name in TOOLS:
                    expected = TOOLS[tool_name]["args"]
                    for ea in expected:
                        if ea.endswith("?") and ea in kwargs:
                            continue
                        if ea not in kwargs:
                            kwargs[ea] = arg
                            break
        result = call_tool(tool_name, **kwargs)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "mcp":
        # Start MCP server (would need fastmcp installed)
        try:
            from fastmcp import FastMCP
            mcp = FastMCP("coding-vps-orchestrator")

            @mcp.tool()
            def chat_minimax_tool(prompt: str, max_tokens: int = 500) -> dict:
                """Chat with MiniMax-M3 XMax Thinking via LiteLLM proxy."""
                return chat_minimax(prompt, max_tokens)

            @mcp.tool()
            def list_services_tool() -> dict:
                """List all 65+ coding-vps services with status."""
                return list_services()

            @mcp.tool()
            def chat_with_agent_tool(agent: str, prompt: str) -> dict:
                """Send a chat to a specific coding agent (crew-ai, goose, hermes, etc)."""
                return chat_with_agent(agent, prompt)

            @mcp.tool()
            def service_logs_tool(service: str, tail: int = 50) -> dict:
                """Get last N log lines from a service."""
                return service_logs(service, tail)

            mcp.run()
        except ImportError:
            print("fastmcp not installed. Install with: pip install fastmcp", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
