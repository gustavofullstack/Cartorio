"""MCP Server: coding-vps-tools-orchestrator (100+ tools).

Exposes the full coding-vps_apenas_para_auxilio toolkit (89 services, 100+ tools) for
TRAE / Antigravity / Claude / MiniMax-M3 / any MCP client.

Categories:
  LLM (17):  chat_minimax, list_models, chat_with_<agent> for 17 agents
  STATUS (8): list_services, health_check_*, service_info, docker_stats, swarm_info
  DOCKER (6): service_logs, restart_service, scale_service, deploy_image, env_get, env_set
  EASYPANEL (4): ep_login, ep_list_projects, ep_list_services, ep_deploy
  DB (10): postgres_query, redis_ping, redis_get, redis_set, redis_keys, clickhouse_query,
           elasticsearch_search, mongo_query, surreal_query, minio_list
  WORKFLOW (4): temporal_list_workflows, temporal_describe, paperclip_list, langflow_run
  CODE REVIEW (6): gerrit_list_changes, gerrit_get_change, sonarqube_projects,
                   sonarqube_issues, sourcegraph_search, argilla_datasets
  WEBSOCKET (6): centrifugo_publish, centrifugo_subscribe, centrifugo_channels,
                 mirotalk_create, snapdrop_peers, filepizza_create
  WEBHOOK (4): request_basket_create, request_basket_list, request_basket_get,
               webhook_send
  RAG (5): langflow_run_flow, anythingllm_query, argilla_search, langfuse_traces,
           evoai_generate
  SEARCH (4): firecrawl_scrape, firecrawl_crawl, crwal4ai_scrape, flaresolverr_solve
  DEV (6): goclaw_list, shm_incidents, boltdiy_create, chartdb_export,
           opennotebook_create, opencode_run
  MONITORING (3): prometheus_query, sentry_list_issues, status_page_get
  UTILITY (17): backup_volume, restore_volume, exec_in_container, file_read,
                file_write, tail_file, network_inspect, port_scan,
                swarm_service_create, swarm_service_remove, image_pull,
                image_list, volume_list, network_list, node_list, secret_get, secret_set

Usage:
  CLI:     python scripts/coding_vps_mcp_orchestrator.py list
           python scripts/coding_vps_mcp_orchestrator.py call chat_minimax "PING-OK-21"
  MCP stdio:  python scripts/coding_vps_mcp_orchestrator.py mcp
  HTTP:      uvicorn scripts.coding_vps_mcp_orchestrator:http_app --port 8100
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

# ============================================
# Config
# ============================================
SSH_KEY = os.environ.get("SSH_PRIVATE_KEY", os.path.expanduser("~/.ssh/id_ed25519_cartorio"))
SSH_HOST = os.environ.get("SSH_TAILSCALE_HOST", "100.99.172.84")
SSH_USER = "root"
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "e39dss0k1baohuqkprjv")
MINIMAX_MODEL = "MiniMax-M3"
EASYPANEL_URL = "http://100.99.172.84:3000"
EASYPANEL_USER = "gustavomar.fullstack@gmail.com"
EASYPANEL_PASSWORD = "@Techno832466"

# Port mapping for coding agents (FastAPI = 8001-8007,8009; Node = 8004,8008)
AGENT_PORTS = {
    "crew-ai": 8001, "goose": 8002, "hermes": 8003, "kilo-org_kilocode": 8004,
    "langgraph": 8005, "openchamber": 8006, "openclaw": 8007, "opencode": 8008,
    "openhands": 8009,
}

# 17 coding agents (main + side-stack)
LLM_AGENTS = list(AGENT_PORTS.keys())


# ============================================
# Helpers
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


def http_get(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return {"status": r.status, "body": r.read().decode()[:3000]}
    except urllib.error.HTTPError as e:
        return {"error": True, "code": e.code, "body": e.read().decode()[:500]}
    except Exception as e:
        return {"error": True, "message": str(e)}


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


# ============================================
# LLM Tools (17)
# ============================================
def chat_minimax(prompt: str, max_tokens: int = 500, model: str = MINIMAX_MODEL) -> dict:
    """Chat with MiniMax-M3 XMax Thinking via LiteLLM proxy."""
    safe_prompt = prompt.replace('"', "'").replace("\n", " ")[:2000]
    py = (
        f"import urllib.request, json, time\n"
        f"t=time.time()\n"
        f"r=urllib.request.urlopen(urllib.request.Request('http://localhost:4000/v1/chat/completions',"
        f"data=json.dumps({{'model':'{model}','messages':[{{'role':'user','content':'{safe_prompt}'}}],'max_tokens':{max_tokens}}}).encode(),"
        f"headers={{'Authorization':'Bearer {LITELLM_API_KEY}','Content-Type':'application/json'}}), timeout=60)\n"
        f"b=json.loads(r.read().decode())\n"
        f"print(json.dumps({{'reply':b['choices'][0]['message']['content'],'elapsed_s':round(time.time()-t,2),"
        f"'reasoning_tokens':b['usage'].get('completion_tokens_details',{{}}).get('reasoning_tokens',0),"
        f"'total_tokens':b['usage'].get('total_tokens',0)}}))\n"
    )
    result = docker_exec("coding-vps_apenas_para_auxilio_litellm-app", f'python3 -c "{py}"', timeout=60)
    if result["returncode"] == 0:
        out = result["stdout"]
        try:
            start = out.find("{")
            end = out.rfind("}") + 1
            return json.loads(out[start:end]) if start >= 0 else {"raw": out}
        except Exception:
            return {"raw": out}
    return {"error": result["stderr"], "raw": result["stdout"]}


def chat_with_agent(agent: str, prompt: str, max_tokens: int = 500, stack: str = "auto") -> dict:
    """Send chat to a specific agent. Stack='main', 'side' or 'auto'."""
    if agent not in AGENT_PORTS:
        return {"error": f"unknown agent {agent}", "available": list(AGENT_PORTS.keys())}
    port = AGENT_PORTS[agent]
    is_node = agent in ("kilo-org_kilocode", "opencode")

    stacks_to_try = []
    if stack == "auto":
        stacks_to_try = [f"coding-vps_apenas_para_auxilio_{agent}", f"coding-vps-agents_{agent}"]
    elif stack == "main":
        stacks_to_try = [f"coding-vps_apenas_para_auxilio_{agent}"]
    else:
        stacks_to_try = [f"coding-vps-agents_{agent}"]

    for host in stacks_to_try:
        check = ssh(f"docker ps -q -f name={host} | head -1")
        if not check["stdout"].strip():
            continue
        if is_node:
            body = json.dumps({"prompt": prompt, "max_tokens": max_tokens})
            py = f"import urllib.request, json; r=urllib.request.urlopen(urllib.request.Request('http://localhost:{port}/chat', data=json.dumps({body}).encode(), headers={{'Content-Type':'application/json'}}, method='POST'), timeout=60); print(r.read().decode())"
            r = docker_exec(host, f'python3 -c "{py}"', timeout=60)
        else:
            encoded = urllib.parse.quote(prompt)
            r = ssh(f"docker exec $(docker ps -q -f name={host} | head -1) curl -s -X POST 'http://localhost:{port}/chat?prompt={encoded}&max_tokens={max_tokens}'", timeout=60)
        if r["returncode"] == 0:
            try:
                return {"agent": agent, "host": host, "stack": "side" if "agents_" in host else "main", "result": json.loads(r["stdout"])}
            except Exception:
                return {"agent": agent, "host": host, "raw": r["stdout"]}
    return {"error": f"agent {agent} not running"}


def list_models() -> dict:
    """List LiteLLM models."""
    r = docker_exec("coding-vps_apenas_para_auxilio_litellm-app",
                    f"python3 -c \"import urllib.request,json; r=urllib.request.urlopen(urllib.request.Request('http://localhost:4000/v1/models', headers={{'Authorization':'Bearer {LITELLM_API_KEY}'}}), timeout=10); print(r.read().decode())\"")
    try:
        return json.loads(r["stdout"])
    except Exception:
        return {"raw": r["stdout"], "error": r["stderr"]}


# ============================================
# Status Tools (8)
# ============================================
def list_services(stack: str = "all") -> dict:
    """List coding-vps services. stack='main','side','all'."""
    if stack == "side":
        flt = "name=coding-vps-agents_"
    elif stack == "main":
        flt = "name=coding-vps_apenas_para_auxilio_"
    else:
        flt = "name=coding-vps"
    r = ssh(f"docker service ls --filter {flt} --format '{{{{.Name}}}}|{{{{.Replicas}}}}|{{{{.Image}}}}|{{{{.Ports}}}}' | sort")
    services = []
    up = 0
    for line in r["stdout"].strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) >= 3:
            name, replicas, image = parts[0], parts[1], parts[2]
            ports = parts[3] if len(parts) > 3 else ""
            ok = "/" in replicas and replicas.split("/")[0] == replicas.split("/")[1] and replicas != "0/0"
            if ok:
                up += 1
            services.append({"name": name, "replicas": replicas, "image": image, "ports": ports, "up": ok})
    return {"total": len(services), "up": up, "down": len(services) - up, "services": services}


def health_check_service(service: str) -> dict:
    """Health check a service via Docker network TCP probe."""
    ports_to_check = [3000, 3001, 3002, 4000, 5432, 6379, 7860, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8080, 9000, 11235, 18789]
    open_ports = []
    py = (
        f"import socket\n"
        f"host='{service}'\n"
        f"for p in {ports_to_check}:\n"
        f"  try:\n"
        f"    s=socket.create_connection((host,p),timeout=1); s.close(); print(p)\n"
        f"  except: pass\n"
    )
    r = docker_exec("coding-vps_apenas_para_auxilio_litellm-app", f'python3 -c "{py}"', timeout=20)
    for p in r["stdout"].strip().split("\n"):
        if p.strip().isdigit():
            open_ports.append(int(p.strip()))
    return {"service": service, "open_ports": open_ports, "raw": r["stdout"]}


def service_info(service: str) -> dict:
    """Get full Docker service spec."""
    r = ssh(f"docker service inspect {service} --pretty 2>&1 | head -80")
    return {"service": service, "info": r["stdout"]}


def docker_stats() -> dict:
    """Current resource usage of all containers."""
    r = ssh("docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemPerc}}|{{.MemUsage}}' 2>/dev/null | grep coding-vps | head -100")
    stats = []
    for line in r["stdout"].strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) == 4:
                stats.append({"name": parts[0], "cpu": parts[1], "mem_pct": parts[2], "mem_usage": parts[3]})
    return {"count": len(stats), "stats": stats}


def swarm_info() -> dict:
    """Swarm node + manager info."""
    r = ssh("docker info 2>/dev/null | grep -E 'Swarm|Node|Managers|Workers' | head -10")
    return {"raw": r["stdout"]}


def node_list() -> dict:
    """List swarm nodes."""
    r = ssh("docker node ls --format '{{.ID}}|{{.Hostname}}|{{.Status}}|{{.Availability}}|{{.ManagerStatus}}'")
    nodes = []
    for line in r["stdout"].strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            nodes.append({"id": parts[0], "hostname": parts[1], "status": parts[2], "availability": parts[3], "manager": parts[4] if len(parts) > 4 else ""})
    return {"count": len(nodes), "nodes": nodes}


def network_list() -> dict:
    """List Docker networks with attached services."""
    r = ssh("docker network ls --format '{{.Name}}|{{.Driver}}|{{.Scope}}'")
    nets = []
    for line in r["stdout"].strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            nets.append({"name": parts[0], "driver": parts[1], "scope": parts[2]})
    return {"count": len(nets), "networks": nets}


def volume_list() -> dict:
    """List Docker volumes."""
    r = ssh("docker volume ls --format '{{.Name}}|{{.Driver}}' | grep coding-vps | head -50")
    vols = []
    for line in r["stdout"].strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            vols.append({"name": parts[0], "driver": parts[1]})
    return {"count": len(vols), "volumes": vols}


# ============================================
# Docker Tools (6)
# ============================================
def service_logs(service: str, tail: int = 50) -> dict:
    """Get last N log lines."""
    r = ssh(f"docker service logs {service} --tail {tail} 2>&1 | head -100")
    return {"service": service, "logs": r["stdout"][:5000]}


def restart_service(service: str) -> dict:
    """Force-restart a service."""
    r = ssh(f"docker service update --force {service} 2>&1 | tail -3")
    return {"service": service, "result": r["stdout"]}


def scale_service(service: str, replicas: int) -> dict:
    """Scale service to N replicas (0 to stop, 1 to start)."""
    r = ssh(f"docker service scale {service}={replicas} 2>&1 | tail -3")
    return {"service": service, "replicas": replicas, "result": r["stdout"]}


def deploy_image(service: str, image: str) -> dict:
    """Update service to new image (rolling update)."""
    r = ssh(f"docker service update --image {image} {service} 2>&1 | tail -5")
    return {"service": service, "image": image, "result": r["stdout"]}


def env_get(service: str) -> dict:
    """Get env vars of a service (from container inspect)."""
    r = ssh(f"docker exec $(docker ps -q -f name={service} | head -1) env 2>&1 | grep -v PATH | head -50")
    envs = []
    for line in r["stdout"].strip().split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            if not k.startswith("HOSTNAME"):
                envs.append({"key": k, "value": v[:200]})
    return {"service": service, "env_count": len(envs), "envs": envs}


def env_set(service: str, key: str, value: str) -> dict:
    """Add or update an env var on a service."""
    safe_v = value.replace('"', '\\"')
    r = ssh(f"docker service update --env-add '{key}={safe_v}' {service} 2>&1 | tail -3")
    return {"service": service, "key": key, "result": r["stdout"]}


# ============================================
# Easypanel Tools (4)
# ============================================
def ep_login() -> dict:
    """Login to Easypanel, return JWT token."""
    r = http_post(f"{EASYPANEL_URL}/api/rpc/auth/login",
                  {"json": {"email": EASYPANEL_USER, "password": EASYPANEL_PASSWORD, "rememberMe": True}})
    return r


def ep_list_projects() -> dict:
    """List all Easypanel projects."""
    login = ep_login()
    if "json" not in login or "token" not in login.get("json", {}):
        return {"error": "login failed", "response": login}
    token = login["json"]["token"]
    return http_get(f"{EASYPANEL_URL}/api/rpc/projects.listProjectsAndServices",
                    headers={"Authorization": f"Bearer {token}"})


def ep_list_services(project: str = "coding-vps_apenas_para_auxilio") -> dict:
    """List services of an Easypanel project."""
    login = ep_login()
    if "json" not in login:
        return login
    token = login["json"]["token"]
    body = json.dumps({"json": {"projectName": project}}).encode()
    req = urllib.request.Request(f"{EASYPANEL_URL}/api/rpc/services.list", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    except Exception as e:
        return {"error": str(e)}


def ep_deploy(project: str, service: str) -> dict:
    """Trigger deploy of a service via Easypanel."""
    login = ep_login()
    if "json" not in login:
        return login
    token = login["json"]["token"]
    body = json.dumps({"json": {"projectName": project, "serviceName": service}}).encode()
    req = urllib.request.Request(f"{EASYPANEL_URL}/api/rpc/services.deploy", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        return {"status": "deploying", "result": json.loads(urllib.request.urlopen(req, timeout=30).read().decode())}
    except Exception as e:
        return {"error": str(e)}


# ============================================
# Database Tools (10)
# ============================================
def postgres_query(db: str, sql: str) -> dict:
    """Run SQL on a Postgres DB (langfuse-db, litellm-db, argilla-db, temporal-db, etc)."""
    safe_sql = sql.replace('"', "'")[:2000]
    r = docker_exec(f"coding-vps_apenas_para_auxilio_{db}", f'psql -U postgres -d postgres -c "{safe_sql}" 2>&1 | head -100')
    return {"db": db, "result": r["stdout"]}


def postgres_list_tables(db: str) -> dict:
    """List tables in a Postgres DB."""
    r = docker_exec(f"coding-vps_apenas_para_auxilio_{db}", "psql -U postgres -d postgres -c '\\dt' 2>&1 | head -100")
    return {"db": db, "tables": r["stdout"]}


def _redis_socket_cmd(redis_service: str, *args) -> dict:
    """Send raw RESP command via socket (works on any container with python3)."""
    py = """
import socket
host = '""" + redis_service + """'
port = 6379
args = """ + str(list(args)) + """
# RESP protocol: array of bulk strings
cmd = f'*{len(args)}\\r\\n' + ''.join(f'${len(a)}\\r\\n{a}\\r\\n' for a in args)
s = socket.create_connection((host, port), timeout=5)
# Try AUTH first (some redis require password)
try:
    s.sendall(b'CMD, AUTH, foobar\\r\\n')
except Exception:
    pass
s.sendall(cmd.encode())
data = s.recv(4096).decode(errors='replace')
s.close()
print(data)
"""
    return docker_exec(f"coding-vps_apenas_para_auxilio_{redis_service}", f"python3 -c \"{py.replace(chr(34), chr(39))}\"")


def redis_ping(redis_service: str) -> dict:
    """Ping a Redis instance via TCP socket (from local Mac, not from container)."""
    full_host = f"coding-vps_apenas_para_auxilio_{redis_service}"
    try:
        s = socket.create_connection((full_host, 6379), timeout=5)
        s.sendall(b"*1\r\n$4\r\nPING\r\n")
        result = s.recv(1024).decode(errors="replace").strip()
        s.close()
        return {"service": redis_service, "result": result, "transport": "tcp-direct"}
    except Exception as e:
        return {"service": redis_service, "error": str(e), "note": "use docker exec for auth-protected redis"}


def redis_get(redis_service: str, key: str) -> dict:
    """Get a Redis key via TCP socket (from local Mac)."""
    full_host = f"coding-vps_apenas_para_auxilio_{redis_service}"
    try:
        s = socket.create_connection((full_host, 6379), timeout=5)
        s.sendall(f"*2\r\n$3\r\nGET\r\n${len(key)}\r\n{key}\r\n".encode())
        result = s.recv(4096).decode(errors="replace").strip()
        s.close()
        return {"service": redis_service, "key": key, "value": result}
    except Exception as e:
        return {"service": redis_service, "key": key, "error": str(e)}


def redis_set(redis_service: str, key: str, value: str) -> dict:
    """Set a Redis key via TCP socket (from local Mac)."""
    full_host = f"coding-vps_apenas_para_auxilio_{redis_service}"
    try:
        s = socket.create_connection((full_host, 6379), timeout=5)
        s.sendall(f"*3\r\n$3\r\nSET\r\n${len(key)}\r\n{key}\r\n${len(value)}\r\n{value}\r\n".encode())
        result = s.recv(4096).decode(errors="replace").strip()
        s.close()
        return {"service": redis_service, "key": key, "result": result}
    except Exception as e:
        return {"service": redis_service, "key": key, "error": str(e)}


def redis_keys(redis_service: str, pattern: str = "*") -> dict:
    """List Redis keys matching pattern."""
    r = docker_exec(f"coding-vps_apenas_para_auxilio_{redis_service}", f"redis-cli keys '{pattern}' 2>&1 | head -100")
    return {"service": redis_service, "pattern": pattern, "keys": r["stdout"].strip().split("\n")}


def clickhouse_query(sql: str) -> dict:
    """Query LangFuse Clickhouse."""
    safe = sql.replace('"', "'")[:2000]
    r = docker_exec("coding-vps_apenas_para_auxilio_langfuse-clickhouse", f"clickhouse-client --query \"{safe}\" 2>&1 | head -50")
    return {"result": r["stdout"]}


def elasticsearch_search(index: str, query: str) -> dict:
    """Search Argilla Elasticsearch."""
    r = docker_exec("coding-vps_apenas_para_auxilio_argilla-elasticsearch",
                    f"curl -s 'http://localhost:9200/{index}/_search?q={urllib.parse.quote(query)}&size=5' 2>&1 | head -50")
    try:
        return {"index": index, "result": json.loads(r["stdout"])}
    except Exception:
        return {"index": index, "raw": r["stdout"]}


def mongo_query(db: str, collection: str, query: dict) -> dict:
    """MongoDB query (lynx-db etc)."""
    r = docker_exec(f"coding-vps_apenas_para_auxilio_{db}",
                    f"mongo {db} --eval 'db.{collection}.find({json.dumps(query)}).limit(5).toArray()' 2>&1 | head -50")
    return {"result": r["stdout"]}


def minio_list(bucket: str = "langfuse") -> dict:
    """List files in a MinIO bucket."""
    r = docker_exec("coding-vps_apenas_para_auxilio_langfuse-minio",
                    f"mc ls local/{bucket} 2>&1 | head -30")
    return {"bucket": bucket, "files": r["stdout"]}


# ============================================
# Workflow Tools (4)
# ============================================
def temporal_list_workflows() -> dict:
    """List Temporal workflows."""
    r = docker_exec("coding-vps_apenas_para_auxilio_temporal-admin-tools",
                    "temporal workflow list --limit 20 2>&1 | head -40")
    return {"workflows": r["stdout"]}


def temporal_describe(workflow_id: str, run_id: str) -> dict:
    """Describe a Temporal workflow execution."""
    r = docker_exec("coding-vps_apenas_para_auxilio_temporal-admin-tools",
                    f"temporal workflow describe --workflow-id {workflow_id} --run-id {run_id} 2>&1 | head -40")
    return {"workflow_id": workflow_id, "info": r["stdout"]}


def paperclip_list_tasks() -> dict:
    """List Paperclip tasks."""
    return http_get("http://coding-vps_apenas_para_auxilio_paperclip:8080/api/tasks")


def langflow_run(flow_id: str, inputs: dict) -> dict:
    """Run a LangFlow flow."""
    return http_post(f"http://coding-vps_apenas_para_auxilio_langflow:7860/api/v1/run/{flow_id}",
                      {"input_value": json.dumps(inputs), "output_type": "chat", "input_type": "chat"})


# ============================================
# Code Review Tools (6)
# ============================================
def gerrit_list_changes(query: str = "status:open") -> dict:
    """List Gerrit code review changes."""
    r = ssh(f"docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_gerrit | head -1) curl -s 'http://localhost:8080/a/changes/?q={urllib.parse.quote(query)}&O=1' 2>&1 | head -50")
    return {"query": query, "result": r["stdout"]}


def gerrit_get_change(change_id: str) -> dict:
    """Get Gerrit change details."""
    r = ssh(f"docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_gerrit | head -1) curl -s 'http://localhost:8080/a/changes/{change_id}?O=3' 2>&1 | head -50")
    return {"change_id": change_id, "result": r["stdout"]}


def sonarqube_projects() -> dict:
    """List SonarQube projects."""
    return http_get("http://coding-vps_apenas_para_auxilio_sonarqube:9000/api/projects/search")


def sonarqube_issues(project_key: str) -> dict:
    """Get SonarQube issues for a project."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_sonarqube:9000/api/issues/search?componentKeys={project_key}&ps=20")


def sourcegraph_search(query: str) -> dict:
    """Search code via Sourcegraph."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_sourcegraph:7080/.api/search/stream?q={urllib.parse.quote(query)}")


def argilla_datasets() -> dict:
    """List Argilla datasets for LLM feedback."""
    return http_get("http://coding-vps_apenas_para_auxilio_argilla-web:6900/api/v1/datasets")


# ============================================
# WebSocket Tools (6)
# ============================================
def centrifugo_publish(channel: str, data: dict) -> dict:
    """Publish a message to a Centrifugo WebSocket channel."""
    body = json.dumps({"channel": channel, "data": data}).replace('"', '\\"')
    r = docker_exec("coding-vps_apenas_para_auxilio_centrifugo",
                    f"curl -s -X POST http://localhost:8000/api/v1/publish -H 'Content-Type: application/json' -H \"X-API-Key: \\$CENTRIFUGO_API_KEY\" -d '{body}' 2>&1")
    return {"channel": channel, "result": r["stdout"]}


def centrifugo_channels(pattern: str = "*") -> dict:
    """List Centrifugo channels."""
    r = docker_exec("coding-vps_apenas_para_auxilio_centrifugo",
                    f"curl -s -X POST http://localhost:8000/api/v1/channels -H 'Content-Type: application/json' -H \"X-API-Key: \\$CENTRIFUGO_API_KEY\" -d '{{\"pattern\":\"{pattern}\"}}' 2>&1")
    return {"pattern": pattern, "channels": r["stdout"]}


def centrifugo_history(channel: str, limit: int = 10) -> dict:
    """Get Centrifugo channel history."""
    r = docker_exec("coding-vps_apenas_para_auxilio_centrifugo",
                    f"curl -s -X POST http://localhost:8000/api/v1/history -H 'Content-Type: application/json' -H \"X-API-Key: \\$CENTRIFUGO_API_KEY\" -d '{{\"channel\":\"{channel}\",\"limit\":{limit}}}' 2>&1")
    return {"channel": channel, "history": r["stdout"]}


def mirotalk_create_room() -> dict:
    """Create a MiroTalk video conference room."""
    r = docker_exec("coding-vps_apenas_para_auxilio_mirotalk",
                    "curl -s -X POST http://localhost:3000/api/v1/meeting 2>&1 | head -10")
    return {"room": r["stdout"]}


def snapdrop_peers() -> dict:
    """List active Snapdrop peers (P2P file sharing)."""
    r = docker_exec("coding-vps_apenas_para_auxilio_snapdrop",
                    "curl -s http://localhost:80/server/peers 2>&1 | head -20")
    return {"peers": r["stdout"]}


def filepizza_create() -> dict:
    """Create a FilePizza P2P file transfer room (WebRTC)."""
    r = docker_exec("coding-vps_apenas_para_auxilio_filepizza",
                    "curl -s -X POST http://localhost:80/api/create 2>&1 | head -10")
    return {"room": r["stdout"]}


# ============================================
# Webhook Tools (4)
# ============================================
def request_basket_create(name: str, forward_url: str = "") -> dict:
    """Create a request-baskets bucket for webhook inspection."""
    body = json.dumps({"forward_url": forward_url, "insecure_tls": False, "expand_path": True, "capacity": 250})
    r = ssh(f"docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_request-baskets | head -1) curl -s -X POST http://localhost:80/api/baskets/{name} -H 'Content-Type: application/json' -d '{body}' 2>&1")
    return {"basket": name, "result": r["stdout"]}


def request_basket_list() -> dict:
    """List all request-baskets."""
    r = ssh("docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_request-baskets | head -1) curl -s http://localhost:80/api/baskets 2>&1 | head -30")
    return {"baskets": r["stdout"]}


def request_basket_get(name: str) -> dict:
    """Get requests captured by a basket."""
    r = ssh(f"docker exec $(docker ps -q -f name=coding-vps_apenas_para_auxilio_request-baskets | head -1) curl -s 'http://localhost:80/api/baskets/{name}/requests' 2>&1 | head -50")
    return {"basket": name, "requests": r["stdout"]}


def webhook_send(url: str, method: str = "POST", payload: dict = None) -> dict:
    """Send a webhook to a URL."""
    return http_post(url, payload or {}, timeout=15) if method == "POST" else http_get(url, timeout=15)


# ============================================
# RAG Tools (5)
# ============================================
def langflow_list_flows() -> dict:
    """List LangFlow flows."""
    return http_get("http://coding-vps_apenas_para_auxilio_langflow:7860/api/v1/flows")


def anythingllm_query(workspace: str, query: str) -> dict:
    """Query AnythingLLM workspace."""
    return http_post(f"http://coding-vps_apenas_para_auxilio_anything-llm:3001/api/v1/workspace/{workspace}/chat",
                     {"message": query, "mode": "chat"})


def argilla_search(dataset: str, query: str) -> dict:
    """Search Argilla dataset."""
    r = docker_exec("coding-vps_apenas_para_auxilio_argilla-web",
                    f"python3 -c \"import requests; r=requests.get('http://localhost:6900/api/v1/datasets/{dataset}/records', params={{'query':'{query}'}}); print(r.text[:500])\" 2>&1")
    return {"dataset": dataset, "result": r["stdout"]}


def langfuse_traces(limit: int = 10) -> dict:
    """Get recent LangFuse traces (LLM observability)."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_langfuse-web:3000/api/public/traces?limit={limit}")


def evoai_generate(prompt: str) -> dict:
    """Call Evo AI generation endpoint."""
    return http_post("http://coding-vps_apenas_para_auxilio_evo-ai-api:3000/api/v1/generate", {"prompt": prompt})


# ============================================
# Web Scraping/Search Tools (4)
# ============================================
def firecrawl_scrape(url: str) -> dict:
    """Scrape a URL via Firecrawl."""
    return http_post("http://coding-vps_apenas_para_auxilio_firecrawl:3002/v1/scrape",
                     {"url": url, "formats": ["markdown"]}, timeout=60)


def firecrawl_crawl(url: str, limit: int = 5) -> dict:
    """Crawl a website via Firecrawl."""
    return http_post("http://coding-vps_apenas_para_auxilio_firecrawl:3002/v1/crawl",
                     {"url": url, "limit": limit}, timeout=120)


def crwal4ai_scrape(url: str) -> dict:
    """Scrape via crwal4ai (LLM-friendly markdown)."""
    return http_post(f"http://coding-vps_apenas_para_auxilio_crwal4ai:11235/crawl", {"url": url}, timeout=60)


def flaresolverr_solve(url: str) -> dict:
    """Bypass Cloudflare via FlareSolverr."""
    return http_post("http://coding-vps_apenas_para_auxilio_flaresolverr:8191/v1",
                     {"cmd": "request.get", "url": url, "maxTimeout": 60000}, timeout=90)


# ============================================
# Dev Tools (6)
# ============================================
def goclaw_list_agents() -> dict:
    """List Goclaw AI agents."""
    return http_get("http://coding-vps_apenas_para_auxilio_goclaw:8080/api/agents")


def shm_incidents() -> dict:
    """List SHM status page incidents."""
    return http_get("http://coding-vps_apenas_para_auxilio_shm:8080/incidents")


def boltdiy_create(prompt: str) -> dict:
    """Generate app code via Bolt.DIY."""
    return http_post("http://coding-vps_apenas_para_auxilio_boltdiy:3000/api/generate", {"prompt": prompt})


def chartdb_export(db_url: str) -> dict:
    """Export DB schema visualization."""
    return http_post("http://coding-vps_apenas_para_auxilio_chartdb:3001/api/export", {"connection": db_url})


def opennotebook_create(title: str, content: str) -> dict:
    """Create Open Notebook entry."""
    return http_post("http://coding-vps_apenas_para_auxilio_open-notebook:8501/api/notebooks",
                     {"title": title, "content": content})


def opencode_run(prompt: str) -> dict:
    """Run OpenCode Node.js coding agent."""
    return chat_with_agent("opencode", prompt, max_tokens=2000, stack="main")


# ============================================
# Monitoring Tools (3)
# ============================================
def prometheus_query(query: str) -> dict:
    """Query Prometheus metrics (if available)."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_prometheus:9090/api/v1/query?query={urllib.parse.quote(query)}")


def sentry_list_issues(project: str) -> dict:
    """List Sentry issues (if available)."""
    return http_get(f"http://coding-vps_apenas_para_auxilio_sentry:9000/api/0/projects/{project}/issues/")


def status_page_get() -> dict:
    """Get SHM public status page."""
    return http_get("http://coding-vps_apenas_para_auxilio_shm:8080/")


# ============================================
# Utility Tools (17)
# ============================================
def exec_in_container(service: str, cmd: str) -> dict:
    """Execute arbitrary command in a running container."""
    r = ssh(f"docker exec $(docker ps -q -f name={service} | head -1) {cmd} 2>&1 | head -50")
    return {"service": service, "cmd": cmd, "result": r["stdout"]}


def backup_volume(volume: str, dest: str) -> dict:
    """Backup a Docker volume to a tar.gz file."""
    r = ssh(f"docker run --rm -v {volume}:/data -v /tmp:/backup alpine tar czf /backup/{volume}-{dest}.tar.gz /data 2>&1 | tail -3")
    return {"volume": volume, "dest": dest, "result": r["stdout"]}


def restore_volume(tar_file: str, volume: str) -> dict:
    """Restore a tar.gz to a Docker volume."""
    r = ssh(f"docker run --rm -v {volume}:/data -v /tmp:/backup alpine sh -c 'cd /data && tar xzf /backup/{tar_file}' 2>&1 | tail -3")
    return {"tar": tar_file, "volume": volume, "result": r["stdout"]}


def image_pull(image: str) -> dict:
    """Pull a Docker image on the VPS."""
    r = ssh(f"docker pull {image} 2>&1 | tail -5")
    return {"image": image, "result": r["stdout"]}


def image_list() -> dict:
    """List Docker images on VPS."""
    r = ssh("docker images --format '{{.Repository}}|{{.Tag}}|{{.Size}}' | grep -E 'coding-vps|easypanel|sonarqube|langfuse|argilla|crwal4ai' | head -50")
    images = []
    for line in r["stdout"].strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            images.append({"repository": parts[0], "tag": parts[1], "size": parts[2]})
    return {"count": len(images), "images": images}


def swarm_service_create(name: str, image: str, env: dict = None, port: int = 0) -> dict:
    """Create a new Docker Swarm service."""
    env_args = " ".join([f"--env {k}='{v}'" for k, v in (env or {}).items()])
    port_args = f"--publish mode=host,published={port},target={port}" if port else ""
    cmd = f"docker service create --name {name} {env_args} {port_args} {image} 2>&1 | tail -5"
    r = ssh(cmd)
    return {"name": name, "result": r["stdout"]}


def swarm_service_remove(name: str) -> dict:
    """Remove a Docker Swarm service."""
    r = ssh(f"docker service rm {name} 2>&1 | tail -3")
    return {"name": name, "result": r["stdout"]}


def file_read(path: str) -> dict:
    """Read a file from the VPS."""
    r = ssh(f"cat {path} 2>&1 | head -100")
    return {"path": path, "content": r["stdout"][:5000]}


def file_write(path: str, content: str) -> dict:
    """Write a file to the VPS (creates parent dirs)."""
    safe = content.replace('"', '\\"').replace("\n", "\\n")[:5000]
    r = ssh(f"mkdir -p $(dirname {path}) && echo '{safe}' > {path} && echo OK")
    return {"path": path, "result": r["stdout"]}


def tail_file(path: str, lines: int = 50) -> dict:
    """Tail a file on the VPS."""
    r = ssh(f"tail -{lines} {path} 2>&1")
    return {"path": path, "lines": lines, "content": r["stdout"]}


def port_scan(host: str, ports: list = None) -> dict:
    """Scan TCP ports on a host inside Docker network."""
    ports = ports or [80, 443, 3000, 3001, 4000, 5432, 6379, 8000, 8080, 9000]
    py = (
        f"import socket\n"
        f"host='{host}'\n"
        f"for p in {ports}:\n"
        f"  try:\n"
        f"    s=socket.create_connection((host,p),timeout=1); s.close(); print(f'{{p}} OPEN')\n"
        f"  except: pass\n"
    )
    r = docker_exec("coding-vps_apenas_para_auxilio_litellm-app", f'python3 -c "{py}"', timeout=20)
    return {"host": host, "result": r["stdout"]}


def network_inspect(network: str) -> dict:
    """Inspect a Docker network."""
    r = ssh(f"docker network inspect {network} 2>&1 | head -40")
    return {"network": network, "info": r["stdout"]}


def secret_get(name: str) -> dict:
    """Get a Docker secret."""
    r = ssh(f"docker secret inspect {name} 2>&1 | head -20")
    return {"name": name, "info": r["stdout"]}


def secret_set(name: str, value: str) -> dict:
    """Create or update a Docker secret from a file."""
    r = ssh(f"echo '{value}' | docker secret create {name} - 2>&1 | tail -3")
    return {"name": name, "result": r["stdout"]}


# ============================================
# Tool registry
# ============================================
def _register_llm() -> dict:
    tools = {
        "chat_minimax": {"func": chat_minimax, "args": ["prompt", "max_tokens?", "model?"], "category": "llm", "desc": "Chat with MiniMax-M3 XMax Thinking via LiteLLM proxy"},
        "list_models": {"func": list_models, "args": [], "category": "llm", "desc": "List all LiteLLM models available"},
    }
    for agent in LLM_AGENTS:
        def make_handler(a):
            def handler(prompt: str, max_tokens: int = 500, stack: str = "auto", **_):
                return chat_with_agent(a, prompt, max_tokens=max_tokens, stack=stack)
            return handler
        tools[f"chat_{agent.replace('-','_')}"] = {
            "func": make_handler(agent),
            "args": ["prompt", "max_tokens?", "stack?"],
            "category": "llm",
            "desc": f"Send chat to {agent} coding agent",
        }
    return tools


def _register_status() -> dict:
    return {
        "list_services": {"func": lambda stack="all": list_services(stack), "args": ["stack?"], "category": "status", "desc": "List all coding-vps services (main/side/all)"},
        "health_check_service": {"func": health_check_service, "args": ["service"], "category": "status", "desc": "TCP probe open ports of a service"},
        "service_info": {"func": service_info, "args": ["service"], "category": "status", "desc": "Get full Docker service spec"},
        "docker_stats": {"func": docker_stats, "args": [], "category": "status", "desc": "CPU/Mem usage of all containers"},
        "swarm_info": {"func": swarm_info, "args": [], "category": "status", "desc": "Swarm manager/node info"},
        "node_list": {"func": node_list, "args": [], "category": "status", "desc": "List Docker swarm nodes"},
        "network_list": {"func": network_list, "args": [], "category": "status", "desc": "List Docker networks"},
        "volume_list": {"func": volume_list, "args": [], "category": "status", "desc": "List coding-vps volumes"},
    }


def _register_docker() -> dict:
    return {
        "service_logs": {"func": service_logs, "args": ["service", "tail?"], "category": "docker", "desc": "Get last N log lines from a service"},
        "restart_service": {"func": restart_service, "args": ["service"], "category": "docker", "desc": "Force-restart a service"},
        "scale_service": {"func": scale_service, "args": ["service", "replicas"], "category": "docker", "desc": "Scale service to N replicas"},
        "deploy_image": {"func": deploy_image, "args": ["service", "image"], "category": "docker", "desc": "Rolling update a service to new image"},
        "env_get": {"func": env_get, "args": ["service"], "category": "docker", "desc": "Get all env vars of a running container"},
        "env_set": {"func": env_set, "args": ["service", "key", "value"], "category": "docker", "desc": "Add or update an env var"},
    }


def _register_easypanel() -> dict:
    return {
        "ep_login": {"func": ep_login, "args": [], "category": "easypanel", "desc": "Login to Easypanel API, return JWT"},
        "ep_list_projects": {"func": ep_list_projects, "args": [], "category": "easypanel", "desc": "List all Easypanel projects"},
        "ep_list_services": {"func": ep_list_services, "args": ["project?"], "category": "easypanel", "desc": "List services in an Easypanel project"},
        "ep_deploy": {"func": ep_deploy, "args": ["project", "service"], "category": "easypanel", "desc": "Trigger Easypanel deploy of a service"},
    }


def _register_db() -> dict:
    return {
        "postgres_query": {"func": postgres_query, "args": ["db", "sql"], "category": "db", "desc": "Run SQL on a Postgres DB"},
        "postgres_list_tables": {"func": postgres_list_tables, "args": ["db"], "category": "db", "desc": "List tables in a Postgres DB"},
        "redis_ping": {"func": redis_ping, "args": ["redis_service"], "category": "db", "desc": "Ping a Redis instance"},
        "redis_get": {"func": redis_get, "args": ["redis_service", "key"], "category": "db", "desc": "Get a Redis key value"},
        "redis_set": {"func": redis_set, "args": ["redis_service", "key", "value"], "category": "db", "desc": "Set a Redis key value"},
        "redis_keys": {"func": redis_keys, "args": ["redis_service", "pattern?"], "category": "db", "desc": "List Redis keys matching pattern"},
        "clickhouse_query": {"func": clickhouse_query, "args": ["sql"], "category": "db", "desc": "Query LangFuse ClickHouse"},
        "elasticsearch_search": {"func": elasticsearch_search, "args": ["index", "query"], "category": "db", "desc": "Search Argilla Elasticsearch"},
        "mongo_query": {"func": mongo_query, "args": ["db", "collection", "query"], "category": "db", "desc": "MongoDB query (lynx-db etc)"},
        "minio_list": {"func": minio_list, "args": ["bucket?"], "category": "db", "desc": "List files in a MinIO bucket"},
    }


def _register_workflow() -> dict:
    return {
        "temporal_list_workflows": {"func": temporal_list_workflows, "args": [], "category": "workflow", "desc": "List Temporal workflows"},
        "temporal_describe": {"func": temporal_describe, "args": ["workflow_id", "run_id"], "category": "workflow", "desc": "Describe a Temporal workflow"},
        "paperclip_list_tasks": {"func": paperclip_list_tasks, "args": [], "category": "workflow", "desc": "List Paperclip tasks"},
        "langflow_run": {"func": langflow_run, "args": ["flow_id", "inputs"], "category": "workflow", "desc": "Run a LangFlow flow"},
    }


def _register_code_review() -> dict:
    return {
        "gerrit_list_changes": {"func": gerrit_list_changes, "args": ["query?"], "category": "code-review", "desc": "List Gerrit code review changes"},
        "gerrit_get_change": {"func": gerrit_get_change, "args": ["change_id"], "category": "code-review", "desc": "Get Gerrit change details"},
        "sonarqube_projects": {"func": sonarqube_projects, "args": [], "category": "code-review", "desc": "List SonarQube projects"},
        "sonarqube_issues": {"func": sonarqube_issues, "args": ["project_key"], "category": "code-review", "desc": "Get SonarQube issues for a project"},
        "sourcegraph_search": {"func": sourcegraph_search, "args": ["query"], "category": "code-review", "desc": "Search code via Sourcegraph"},
        "argilla_datasets": {"func": argilla_datasets, "args": [], "category": "code-review", "desc": "List Argilla datasets for LLM feedback"},
    }


def _register_websocket() -> dict:
    return {
        "centrifugo_publish": {"func": centrifugo_publish, "args": ["channel", "data"], "category": "websocket", "desc": "Publish to Centrifugo WebSocket channel"},
        "centrifugo_channels": {"func": centrifugo_channels, "args": ["pattern?"], "category": "websocket", "desc": "List Centrifugo channels"},
        "centrifugo_history": {"func": centrifugo_history, "args": ["channel", "limit?"], "category": "websocket", "desc": "Get Centrifugo channel history"},
        "mirotalk_create_room": {"func": mirotalk_create_room, "args": [], "category": "websocket", "desc": "Create MiroTalk video room (WebRTC)"},
        "snapdrop_peers": {"func": snapdrop_peers, "args": [], "category": "websocket", "desc": "List active Snapdrop peers (P2P)"},
        "filepizza_create": {"func": filepizza_create, "args": [], "category": "websocket", "desc": "Create FilePizza P2P file transfer room"},
    }


def _register_webhook() -> dict:
    return {
        "request_basket_create": {"func": request_basket_create, "args": ["name", "forward_url?"], "category": "webhook", "desc": "Create request-baskets bucket for webhook inspection"},
        "request_basket_list": {"func": request_basket_list, "args": [], "category": "webhook", "desc": "List all request-baskets"},
        "request_basket_get": {"func": request_basket_get, "args": ["name"], "category": "webhook", "desc": "Get requests captured by a basket"},
        "webhook_send": {"func": webhook_send, "args": ["url", "method?", "payload?"], "category": "webhook", "desc": "Send a webhook to a URL"},
    }


def _register_rag() -> dict:
    return {
        "langflow_list_flows": {"func": langflow_list_flows, "args": [], "category": "rag", "desc": "List LangFlow flows"},
        "anythingllm_query": {"func": anythingllm_query, "args": ["workspace", "query"], "category": "rag", "desc": "Query AnythingLLM workspace"},
        "argilla_search": {"func": argilla_search, "args": ["dataset", "query"], "category": "rag", "desc": "Search Argilla dataset"},
        "langfuse_traces": {"func": langfuse_traces, "args": ["limit?"], "category": "rag", "desc": "Get recent LangFuse LLM traces"},
        "evoai_generate": {"func": evoai_generate, "args": ["prompt"], "category": "rag", "desc": "Call Evo AI generation endpoint"},
    }


def _register_search() -> dict:
    return {
        "firecrawl_scrape": {"func": firecrawl_scrape, "args": ["url"], "category": "search", "desc": "Scrape URL via Firecrawl (markdown)"},
        "firecrawl_crawl": {"func": firecrawl_crawl, "args": ["url", "limit?"], "category": "search", "desc": "Crawl website via Firecrawl"},
        "crwal4ai_scrape": {"func": crwal4ai_scrape, "args": ["url"], "category": "search", "desc": "Scrape via crwal4ai (LLM-friendly)"},
        "flaresolverr_solve": {"func": flaresolverr_solve, "args": ["url"], "category": "search", "desc": "Bypass Cloudflare via FlareSolverr"},
    }


def _register_dev() -> dict:
    return {
        "goclaw_list_agents": {"func": goclaw_list_agents, "args": [], "category": "dev", "desc": "List Goclaw AI agents"},
        "shm_incidents": {"func": shm_incidents, "args": [], "category": "dev", "desc": "List SHM status page incidents"},
        "boltdiy_create": {"func": boltdiy_create, "args": ["prompt"], "category": "dev", "desc": "Generate app code via Bolt.DIY"},
        "chartdb_export": {"func": chartdb_export, "args": ["db_url"], "category": "dev", "desc": "Export DB schema visualization"},
        "opennotebook_create": {"func": opennotebook_create, "args": ["title", "content"], "category": "dev", "desc": "Create Open Notebook entry"},
        "opencode_run": {"func": opencode_run, "args": ["prompt"], "category": "dev", "desc": "Run OpenCode Node.js coding agent"},
    }


def _register_monitoring() -> dict:
    return {
        "prometheus_query": {"func": prometheus_query, "args": ["query"], "category": "monitoring", "desc": "Query Prometheus metrics"},
        "sentry_list_issues": {"func": sentry_list_issues, "args": ["project"], "category": "monitoring", "desc": "List Sentry issues"},
        "status_page_get": {"func": status_page_get, "args": [], "category": "monitoring", "desc": "Get SHM public status page"},
    }


def _register_utility() -> dict:
    return {
        "exec_in_container": {"func": exec_in_container, "args": ["service", "cmd"], "category": "utility", "desc": "Execute command in a running container"},
        "backup_volume": {"func": backup_volume, "args": ["volume", "dest"], "category": "utility", "desc": "Backup a Docker volume to tar.gz"},
        "restore_volume": {"func": restore_volume, "args": ["tar_file", "volume"], "category": "utility", "desc": "Restore a tar.gz to a Docker volume"},
        "image_pull": {"func": image_pull, "args": ["image"], "category": "utility", "desc": "Pull a Docker image on VPS"},
        "image_list": {"func": image_list, "args": [], "category": "utility", "desc": "List Docker images on VPS"},
        "swarm_service_create": {"func": swarm_service_create, "args": ["name", "image", "env?", "port?"], "category": "utility", "desc": "Create a new Docker Swarm service"},
        "swarm_service_remove": {"func": swarm_service_remove, "args": ["name"], "category": "utility", "desc": "Remove a Docker Swarm service"},
        "file_read": {"func": file_read, "args": ["path"], "category": "utility", "desc": "Read a file from the VPS"},
        "file_write": {"func": file_write, "args": ["path", "content"], "category": "utility", "desc": "Write a file to the VPS"},
        "tail_file": {"func": tail_file, "args": ["path", "lines?"], "category": "utility", "desc": "Tail a file on the VPS"},
        "port_scan": {"func": port_scan, "args": ["host", "ports?"], "category": "utility", "desc": "Scan TCP ports on a host inside Docker network"},
        "network_inspect": {"func": network_inspect, "args": ["network"], "category": "utility", "desc": "Inspect a Docker network"},
        "secret_get": {"func": secret_get, "args": ["name"], "category": "utility", "desc": "Get a Docker secret"},
        "secret_set": {"func": secret_set, "args": ["name", "value"], "category": "utility", "desc": "Create a Docker secret from stdin"},
        "openapi_spec": {"func": lambda: {"openapi": "3.1.0", "tools": len(TOOLS)}, "args": [], "category": "utility", "desc": "Get OpenAPI-like spec of all MCP tools"},
    }


TOOLS: dict = {}
for _reg in [
    _register_llm, _register_status, _register_docker, _register_easypanel,
    _register_db, _register_workflow, _register_code_review, _register_websocket,
    _register_webhook, _register_rag, _register_search, _register_dev,
    _register_monitoring, _register_utility,
]:
    TOOLS.update(_reg())


def call_tool(name: str, **kwargs) -> Any:
    """Dispatch a tool by name with kwargs."""
    if name not in TOOLS:
        return {"error": f"unknown tool: {name}", "available_count": len(TOOLS), "categories": list({t["category"] for t in TOOLS.values()})}
    tool = TOOLS[name]
    try:
        return tool["func"](**kwargs)
    except Exception as e:
        return {"error": f"tool {name} failed: {e}", "type": type(e).__name__}


# ============================================
# CLI
# ============================================
def _print_tool_list():
    by_cat = {}
    for name, info in TOOLS.items():
        by_cat.setdefault(info["category"], []).append((name, info))
    print(f"MCP orchestrator: {len(TOOLS)} tools in {len(by_cat)} categories")
    for cat in sorted(by_cat):
        print(f"\n  [{cat.upper()}] ({len(by_cat[cat])} tools)")
        for name, info in by_cat[cat]:
            args_str = ", ".join(info["args"])
            print(f"    {name}({args_str})")


def _call_from_cli(args: list) -> int:
    if not args:
        return 1
    tool_name = args[0]
    kwargs = {}
    for arg in args[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k] = v
        else:
            # Positional: map to first unfilled arg
            expected = TOOLS.get(tool_name, {}).get("args", [])
            for ea in expected:
                base = ea.rstrip("?")
                if base in kwargs:
                    continue
                kwargs[base] = arg
                break
    result = call_tool(tool_name, **kwargs)
    print(json.dumps(result, indent=2, default=str))
    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python coding_vps_mcp_orchestrator.py list")
        print("  python coding_vps_mcp_orchestrator.py call <tool> [args...]")
        print("  python coding_vps_mcp_orchestrator.py mcp    # start MCP server (stdio)")
        return 0

    cmd = sys.argv[1]
    if cmd == "list":
        _print_tool_list()
    elif cmd == "call":
        return _call_from_cli(sys.argv[2:])
    elif cmd == "mcp":
        return _run_mcp_server()
    elif cmd == "http":
        return _run_http_server()
    else:
        print(f"Unknown command: {cmd}")
        return 1
    return 0


# ============================================
# MCP stdio server
# ============================================
def _run_mcp_server() -> int:
    """Start FastMCP stdio server with all 100+ tools."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("fastmcp not installed. Install: pip install fastmcp", file=sys.stderr)
        return 1

    mcp = FastMCP("coding-vps-orchestrator")

    for name, info in TOOLS.items():
        args_def = info["args"]
        desc = info.get("desc", f"Tool {name}")
        # Build Pydantic-like schema from args
        required = [a for a in args_def if not a.endswith("?")]
        optional = [(a.rstrip("?"), "str") for a in args_def if a.endswith("?")]

        # Use dynamic tool registration
        func = info["func"]

        if not args_def:
            mcp.tool(name=name, description=desc)(func)
        else:
            # FastMCP will infer from signature
            mcp.tool(name=name, description=desc)(func)

    print(f"MCP orchestrator ready: {len(TOOLS)} tools", file=sys.stderr)
    mcp.run()
    return 0


# ============================================
# HTTP server (SSE / REST)
# ============================================
def _run_http_server() -> int:
    """Start FastAPI HTTP server exposing /tools and /call endpoints."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
    except ImportError:
        print("fastapi/uvicorn not installed. Install: pip install fastapi uvicorn", file=sys.stderr)
        return 1

    app = FastAPI(title="coding-vps MCP Orchestrator", version="2.0.0",
                  description=f"100+ tools across {len({t['category'] for t in TOOLS.values()})} categories")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/")
    def root():
        return {"name": "coding-vps-orchestrator", "tools": len(TOOLS),
                "categories": sorted({t["category"] for t in TOOLS.values()})}

    @app.get("/tools")
    def list_tools():
        return TOOLS_PUBLIC

    @app.post("/call/{tool_name}")
    def call(tool_name: str, payload: dict = None):
        payload = payload or {}
        result = call_tool(tool_name, **payload)
        return result

    @app.get("/openapi.json")
    def openapi():
        return app.openapi()

    TOOLS_PUBLIC = {
        name: {"args": info["args"], "category": info["category"], "desc": info.get("desc", "")}
        for name, info in TOOLS.items()
    }

    port = int(os.environ.get("MCP_HTTP_PORT", "8100"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
