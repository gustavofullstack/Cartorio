"""MCP Server: coding-vps-orchestrator
Tools para gerenciar coding agents da coding-vps_apenas_para_auxilio via Easypanel API v2.
"""

import json
import subprocess
import urllib.request
from typing import Any

# Easypanel config
BASE = "http://100.99.172.84:3000"
USER = "gustavomar.fullstack@gmail.com"
PASSWORD = "@Techno832466"
PROJECT = "coding-vps_apenas_para_auxilio"
SSH_KEY = "~/.ssh/id_ed25519_cartorio"
SSH_HOST = "root@100.99.172.84"
MINIMAX_API_KEY = "sk-cp-kRIbiqKy9F-0aN0rrWUAHSAvNc_e0e00Gr1U4QlYWi_CIgguvXKr7gNLBo6DaEVU7JpY0GnJFinOFMOhBMNFD6Sp8pMuN9UEXyNR4mMi4V4hqm9eUr_7j5s"
MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"


def http(
    method: str, url: str, data: dict | None = None, token: str | None = None
) -> dict:
    """HTTP JSON request."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "code": e.code, "body": e.read().decode()}


def ssh(cmd: str, timeout: int = 60) -> dict:
    """Run SSH command on VPS."""
    full = ["ssh", "-i", SSH_KEY, "-o", "ConnectTimeout=8", SSH_HOST, cmd]
    r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return {
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip(),
        "returncode": r.returncode,
    }


def easypanel_login() -> str:
    """Login to Easypanel and return token."""
    r = http(
        "POST",
        f"{BASE}/api/rpc/auth/login",
        {"json": {"email": USER, "password": PASSWORD, "rememberMe": True}},
    )
    return r["json"]["token"]


def easypanel_list_services(token: str) -> list[dict]:
    """List all services in project."""
    r = http("GET", f"{BASE}/api/rpc/projects/listProjectsAndServices", token=token)
    services = r.get("json", {}).get("services", [])
    return services


def docker_service_update(
    service: str, env_add: dict[str, str] | None = None, image: str | None = None
) -> dict:
    """Update docker service via SSH."""
    cmd = f"docker service update"
    if image:
        cmd += f" --image {image}"
    if env_add:
        for k, v in env_add.items():
            cmd += f' --env-add "{k}={v}"'
    cmd += f" {service}"
    return ssh(cmd)


# ===== MCP TOOLS =====


def tool_coding_vps_status() -> dict[str, Any]:
    """Get status of all coding-vps coding agents."""
    token = easypanel_login()
    services = easypanel_list_services(token)
    coding_vps = [
        s
        for s in services
        if s.get("projectName") == PROJECT or "coding-vps" in s.get("name", "")
    ]
    result = ssh(
        "docker service ls --filter name=coding-vps_apenas_para_auxilio --format '{{.Name}}|{{.Replicas}}|{{.Image}}'"
    )
    lines = [l.split("|") for l in result["stdout"].split("\n") if l]
    status = {}
    up_count = 0
    for name, replicas, image in lines:
        ok = replicas == "1/1"
        if ok:
            up_count += 1
        status[name] = {"replicas": replicas, "image": image, "up": ok}
    return {
        "project": PROJECT,
        "total_services": len(lines),
        "up_count": up_count,
        "down_count": len(lines) - up_count,
        "services": status,
        "score": f"{up_count}/{len(lines)}",
    }


def tool_minimax_chat(prompt: str, max_tokens: int = 200) -> dict:
    """Chat with MiniMax-M3 XMax Thinking via LiteLLM proxy."""
    cid_result = ssh(
        "docker ps -q -f name=coding-vps_apenas_para_auxilio_litellm-app | head -1"
    )
    cid = cid_result["stdout"]
    if not cid:
        return {"error": "litellm-app container not running"}
    py = f"""
import urllib.request, json, time
t = time.time()
r = urllib.request.urlopen(urllib.request.Request(
    'http://localhost:4000/v1/chat/completions',
    data=json.dumps({{'model':'MiniMax-M3','messages':[{{'role':'user','content':'{prompt}'}}],'max_tokens':{max_tokens}}}).encode(),
    headers={{'Authorization':'Bearer e39dss0k1baohuqkprjv','Content-Type':'application/json'}}), timeout=30)
b = json.loads(r.read().decode())
print(json.dumps({{
    'reply': b['choices'][0]['message']['content'],
    'time_s': round(time.time()-t, 2),
    'reasoning_tokens': b['usage']['completion_tokens_details']['reasoning_tokens'],
    'total_tokens': b['usage']['total_tokens']
}}))
"""
    result = ssh(
        f'docker exec {cid} python3 -c "{py.replace(chr(10), " ").replace(chr(34), chr(34) + chr(34))}"'
    )
    try:
        # Extract JSON from output
        out = result["stdout"]
        # Find first { and parse
        start = out.find("{")
        if start >= 0:
            data = json.loads(out[start : out.rfind("}") + 1])
            return data
        return {"error": "parse failed", "stdout": out}
    except Exception as e:
        return {"error": str(e), "stdout": result["stdout"]}


def tool_configure_agent_minimax(service_name: str) -> dict[str, Any]:
    """Add MiniMax-M3 env vars to a coding-vps service."""
    full_service = (
        f"{PROJECT}_{service_name}"
        if not service_name.startswith(PROJECT)
        else service_name
    )
    env_vars = {
        "MINIMAX_API_KEY": MINIMAX_API_KEY,
        "MINIMAX_BASE_URL": MINIMAX_BASE_URL,
        "MINIMAX_MODEL": "MiniMax-M3",
        "LITELLM_BASE_URL": "http://coding-vps_apenas_para_auxilio_litellm-app:4000",
        "LITELLM_API_KEY": "e39dss0k1baohuqkprjv",
        "LLM_THINKING": "true",
        "LLM_DEFAULT_PROVIDER": "minimax",
    }
    result = docker_service_update(full_service, env_add=env_vars)
    return {
        "service": full_service,
        "env_added": env_vars,
        "result": result,
    }


def tool_health_check_all() -> dict[str, Any]:
    """Health check all coding agents."""
    agents = [
        "litellm-app",
        "anything-llm",
        "langflow",
        "langflow-db",
        "langfuse-web",
        "langfuse-worker",
        "langfuse-db",
        "langfuse-clickhouse",
        "langfuse-minio",
        "langfuse-redis",
    ]
    results = {}
    for agent in agents:
        cid_result = ssh(
            f"docker ps -q -f name=coding-vps_apenas_para_auxilio_{agent} | head -1"
        )
        if not cid_result["stdout"]:
            results[agent] = {"status": "DOWN"}
            continue
        cid = cid_result["stdout"]
        # Try Python health check
        ports = {
            "litellm-app": 4000,
            "anything-llm": 3001,
            "langflow": 7860,
            "langfuse-web": 3000,
            "langfuse-worker": 3030,
            "langfuse-clickhouse": 8123,
            "langfuse-minio": 9000,
        }
        path = {
            "litellm-app": "/health/liveliness",
            "anything-llm": "/api/ping",
            "langflow": "/health",
            "langfuse-web": "/api/public/health",
            "langfuse-worker": "/health",
            "langfuse-clickhouse": "/ping",
            "langfuse-minio": "/minio/health/live",
        }
        if agent not in ports:
            results[agent] = {"status": "DB/Redis", "note": "needs different check"}
            continue
        py = f"import urllib.request; r=urllib.request.urlopen('http://localhost:{ports[agent]}{path[agent]}', timeout=3); print(r.status)"
        r = ssh(f'docker exec {cid} python3 -c "{py}"')
        if "200" in r["stdout"]:
            results[agent] = {"status": "UP", "http": 200}
        else:
            results[agent] = {
                "status": "FAIL",
                "output": r["stdout"][:100],
                "stderr": r["stderr"][:100],
            }
    up = sum(1 for v in results.values() if v.get("status") == "UP")
    return {
        "checked": len(agents),
        "up": up,
        "down": len(agents) - up,
        "results": results,
        "score": f"{up}/{len(agents)}",
    }


def tool_ask_minimax(prompt: str, max_tokens: int = 200) -> dict:
    """Alias for tool_minimax_chat."""
    return tool_minimax_chat(prompt, max_tokens)


# MCP Server (FastMCP 3.x)
try:
    from fastmcp import FastMCP

    mcp = FastMCP("coding-vps-orchestrator")

    @mcp.tool()
    def coding_vps_status() -> dict:
        """Get status of all 21+ coding agents in coding-vps project."""
        return tool_coding_vps_status()

    @mcp.tool()
    def health_check_all() -> dict:
        """Health check all running coding agents."""
        return tool_health_check_all()

    @mcp.tool()
    def chat_minimax(prompt: str, max_tokens: int = 200) -> dict:
        """Chat with MiniMax-M3 XMax Thinking via LiteLLM proxy."""
        return tool_minimax_chat(prompt, max_tokens)

    @mcp.tool()
    def configure_agent(service_name: str) -> dict:
        """Add MiniMax-M3 XMax Thinking env vars to a coding agent service."""
        return tool_configure_agent_minimax(service_name)

except ImportError:
    # No FastMCP available - just provide the functions
    pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(tool_coding_vps_status(), indent=2))
        elif cmd == "health":
            print(json.dumps(tool_health_check_all(), indent=2))
        elif cmd == "chat" and len(sys.argv) > 2:
            print(json.dumps(tool_minimax_chat(sys.argv[2]), indent=2))
        elif cmd == "configure" and len(sys.argv) > 2:
            print(json.dumps(tool_configure_agent_minimax(sys.argv[2]), indent=2))
    else:
        print(
            "Usage: python mcp_coding_vps.py {status|health|chat <prompt>|configure <service>}"
        )
        print("\n=== DEMO: status ===")
        print(json.dumps(tool_coding_vps_status(), indent=2))
