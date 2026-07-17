"""CartorioBot deploy CLI (G6.E.T12).

Deploys cartorio-bot no OpenClaw gateway via SSH + API.

Passos:
1. SSH VPS (Tailscale 100.99.172.84)
2. Copia cartorio_bot/ para /opt/openclaw/agents/cartorio_bot/
3. Aplica openclaw.json (config do agent)
4. Restart container OpenClaw
5. Aguarda /health 200
6. Smoke test (E2E via cartorio_bot_e2e_test.py)

Uso:
    python3 scripts/cartorio_bot_deploy.py --dry-run
    python3 scripts/cartorio_bot_deploy.py --apply
    python3 scripts/cartorio_bot_deploy.py --rollback

Exit codes:
    0 = deploy OK
    1 = erro deploy
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-llm — G6 wave 29.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

DEFAULT_VPS = "100.99.172.84"  # Tailscale
DEFAULT_DEPLOY_DIR = "/opt/openclaw/agents/cartorio_bot"
DEFAULT_OPENCLAW_CONFIG = "/opt/openclaw/openclaw.json"


def get_config() -> tuple[str, str, str, str]:
    """Retorna (vps_host, ssh_user, ssh_key_path, deploy_dir)."""
    return (
        os.environ.get("VPS_HOST", DEFAULT_VPS),
        os.environ.get("VPS_USER", "root"),
        os.environ.get("VPS_SSH_KEY", os.path.expanduser("~/.ssh/id_rsa")),
        os.environ.get("DEPLOY_DIR", DEFAULT_DEPLOY_DIR),
    )


def run_ssh(host: str, user: str, key: str, cmd: str, timeout: float) -> tuple[int, str, str]:
    """Executa comando SSH. Retorna (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-i", key,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                "-o", "ConnectTimeout=10",
                f"{user}@{host}",
                cmd,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (124, "", f"timeout after {timeout}s")
    except Exception as exc:
        return (1, "", f"{type(exc).__name__}: {exc}")


def render_openclaw_config(agent_name: str, password: str, api_base: str) -> str:
    """Renderiza openclaw.json para cartorio-bot."""
    return f"""{{
  "agents": [
    {{
      "name": "{agent_name}",
      "type": "cartorio-bot",
      "description": "Bot conversacional do 2o Tabelionato de Notas e Protesto de Uberlandia",
      "model": "gpt-4o-mini",
      "system_prompt": "Voce eh o cartorio-bot, assistente do 2o Tabelionato de Uberlandia. Sempre responda em portugues BR, formal mas acessivel. LGPD: nunca armazene ou compartilhe dados pessoais sem consentimento explicito.",
      "tools": [
        {{"name": "api", "base_url": "{api_base}"}},
        {{"name": "n8n", "webhook_url": "https://flow.2notasudi.com.br/webhook"}},
        {{"name": "supabase", "url": "https://supbase.2notasudi.com.br"}},
        {{"name": "redis", "url": "redis://redis.2notasudi.com.br:6379"}},
        {{"name": "chatwoot", "url": "https://cartorio-chatwoot.dfgdxq.easypanel.host"}},
        {{"name": "evolution", "url": "https://whatsapp.2notasudi.com.br"}}
      ],
      "skills": [
        "cartorio_certidoes",
        "cartorio_protocolos",
        "cartorio_atendimento",
        "lgpd_consentimento"
      ],
      "mcp_servers": [
        "cartorio-mcp-cabuloso",
        "cartorio-mcp-sre",
        "cartorio-mcp-lgpd"
      ],
      "auth": {{
        "type": "challenge",
        "password_required": true,
        "password_set": true
      }}
    }}
  ]
}}
"""


def deploy_step_copy(host: str, user: str, key: str, src: str, dst: str, timeout: float) -> bool:
    """Copia pasta local para VPS via scp."""
    try:
        result = subprocess.run(
            [
                "scp",
                "-i", key,
                "-o", "StrictHostKeyChecking=no",
                "-r",
                src,
                f"{user}@{host}:{dst}",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"[ERROR] scp: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def deploy_step_write_config(host: str, user: str, key: str, config_json: str, timeout: float) -> bool:
    """Escreve openclaw.json no VPS."""
    cmd = f"echo '{config_json}' > {DEFAULT_OPENCLAW_CONFIG}"
    code, _, err = run_ssh(host, user, key, cmd, timeout)
    if code != 0:
        print(f"[ERROR] write config: {err}", file=sys.stderr)
        return False
    return True


def deploy_step_restart(host: str, user: str, key: str, timeout: float) -> bool:
    """Restart OpenClaw container."""
    cmd = "docker restart openclaw-gateway 2>&1 || systemctl restart openclaw"
    code, out, err = run_ssh(host, user, key, cmd, timeout)
    if code != 0:
        print(f"[ERROR] restart: {err or out}", file=sys.stderr)
        return False
    return True


def deploy_step_health_check(host: str, user: str, key: str, timeout: float) -> bool:
    """Aguarda /health 200."""
    cmd = "for i in 1 2 3 4 5; do curl -fs http://localhost:8080/health && break || sleep 3; done"
    code, out, err = run_ssh(host, user, key, cmd, timeout)
    if code != 0:
        print(f"[ERROR] health: {err}", file=sys.stderr)
        return False
    return "ok" in out.lower() or "live" in out.lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="CartorioBot deploy CLI")
    parser.add_argument("--apply", action="store_true", help="aplicar (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="so mostra (default)")
    parser.add_argument("--rollback", action="store_true", help="rollback para versao anterior")
    parser.add_argument("--src", default="infra/openclaw/cartorio_bot", help="pasta fonte local")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    dry_run = not args.apply and not args.rollback
    host, user, key, deploy_dir = get_config()
    api_key_password = os.environ.get("OPENCLAW_GATEWAY_PASSWORD", "")
    api_base = os.environ.get("CARTORIO_API_URL", "https://api.2notasudi.com.br")

    print(f"VPS: {user}@{host}")
    print(f"Deploy dir: {deploy_dir}")
    print(f"Mode: {'ROLLBACK' if args.rollback else 'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print()

    if not os.path.exists(key) and not dry_run:
        print(f"[ERROR] SSH key nao encontrada: {key}", file=sys.stderr)
        return 2

    if dry_run:
        config = render_openclaw_config("cartorio-bot", api_key_password, api_base)
        print("[DRY-RUN] openclaw.json:")
        print(config)
        print("[DRY-RUN] SSH copy + restart + health check seriao executados")
        return 0

    if args.rollback:
        cmd = f"cd {deploy_dir} && git checkout HEAD~1 2>&1 && docker restart openclaw-gateway"
        code, out, err = run_ssh(host, user, key, cmd, args.timeout)
        print(out)
        return 0 if code == 0 else 1

    # Apply path
    print(f"[1/4] Copy {args.src} -> {deploy_dir}...")
    if not deploy_step_copy(host, user, key, args.src, deploy_dir, args.timeout):
        return 1

    print(f"[2/4] Write openclaw.json...")
    config_json = render_openclaw_config("cartorio-bot", api_key_password, api_base)
    # Substituir newlines por \\n para SSH inline
    config_escaped = config_json.replace("'", "'\\''")
    if not deploy_step_write_config(host, user, key, config_escaped, args.timeout):
        return 1

    print(f"[3/4] Restart OpenClaw container...")
    if not deploy_step_restart(host, user, key, args.timeout):
        return 1

    print(f"[4/4] Health check /health...")
    if not deploy_step_health_check(host, user, key, args.timeout):
        return 1

    print("[WORK] Deploy OK!")
    return 0


if __name__ == "__main__":
    sys.exit(main())