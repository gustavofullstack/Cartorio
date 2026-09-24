"""Prometheus SLO rules deploy (G6.D.T8).

Faz reload do Prometheus apos adicionar SLO rules em infra/prometheus/slo_rules.yml.

Endpoints comuns:
- POST /-/reload (Prometheus 2.0+)
- POST /api/v1/admin/tsdb/clean (TSDB admin)
- WebSocket /api/v1/sd/config (service discovery)

Uso:
    python3 scripts/prometheus_slo_deploy.py                  # reload
    python3 scripts/prometheus_slo_deploy.py --validate      # so valida
    python3 scripts/prometheus_slo_deploy.py --url URL       # custom Prometheus

Exit codes:
    0 = reload OK
    1 = erro API
    2 = erro pre-requisito

Modified by Gustavo Almeida + cartorio-sre — G6 wave 24.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

DEFAULT_URL = "http://localhost:9090"
SLO_RULES_PATH = Path("infra/prometheus/slo_rules.yml")


def get_prometheus_config() -> tuple[str, str]:
    """Retorna (url, basic_auth_password) via env."""
    url = os.environ.get("PROMETHEUS_URL", DEFAULT_URL)
    password = os.environ.get("PROMETHEUS_PASSWORD", "")
    return url, password


def validate_rules(path: Path) -> bool:
    """Valida YAML do SLO rules."""
    try:
        import yaml
    except ImportError:
        print("[ERROR] pyyaml nao instalado", file=sys.stderr)
        return False
    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as exc:
        print(f"[ERROR] YAML invalido: {exc}", file=sys.stderr)
        return False
    if "groups" not in data:
        print("[ERROR] YAML sem 'groups'", file=sys.stderr)
        return False
    total_rules = sum(len(g.get("rules", [])) for g in data["groups"])
    print(f"[WORK] YAML valido: {len(data['groups'])} groups, {total_rules} rules")
    return True


def reload_prometheus(url: str, password: str, timeout: float) -> bool:
    """Faz POST /-/reload."""
    auth: tuple[str, str] | None = None
    if password:
        auth = ("admin", password)
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{url}/-/reload", auth=auth)
            if r.status_code in (200, 204):
                print(f"[WORK] Reload OK (status {r.status_code})")
                return True
            print(f"[ERROR] Reload falhou: HTTP {r.status_code} - {r.text[:200]}", file=sys.stderr)
            return False
    except httpx.RequestError as exc:
        print(f"[ERROR] Conexao: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def check_prometheus_health(url: str, password: str, timeout: float) -> bool:
    """GET /-/ready para verificar health."""
    auth: tuple[str, str] | None = ("admin", password) if password else None
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{url}/-/ready", auth=auth)
            if r.status_code == 200:
                print(f"[WORK] Prometheus ready: {r.text.strip()}")
                return True
            print(f"[ERROR] Prometheus not ready: {r.status_code}", file=sys.stderr)
            return False
    except httpx.RequestError as exc:
        print(f"[ERROR] Conexao: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Prometheus SLO rules deploy")
    parser.add_argument("--url", help="Prometheus URL (default: PROMETHEUS_URL env ou localhost:9090)")
    parser.add_argument("--password", help="basic auth password (default: PROMETHEUS_PASSWORD env)")
    parser.add_argument("--validate", action="store_true", help="apenas validar YAML")
    parser.add_argument("--no-reload", action="store_true", help="pular reload")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    url = args.url or get_prometheus_config()[0]
    password = args.password or get_prometheus_config()[1]

    print(f"Prometheus URL: {url}")
    print(f"SLO rules: {SLO_RULES_PATH}")
    print(f"Mode: {'validate-only' if args.validate else 'full'}")
    print()

    if not SLO_RULES_PATH.exists():
        print(f"[ERROR] {SLO_RULES_PATH} nao existe", file=sys.stderr)
        return 2

    if not validate_rules(SLO_RULES_PATH):
        return 2

    if args.validate:
        return 0

    if not check_prometheus_health(url, password, args.timeout):
        return 1

    if not args.no_reload:
        if not reload_prometheus(url, password, args.timeout):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())