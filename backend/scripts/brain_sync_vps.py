"""brain_sync_vps.py - sincronizacao bidirecional cerebro local <-> VPS (BRAIN3).

Uso:
  cd backend
  uv run python scripts/brain_sync_vps.py --push  # local -> VPS
  uv run python scripts/brain_sync_vps.py --pull  # VPS -> local
  uv run python scripts/brain_sync_vps.py --full  # push + pull

Pre-requisitos:
- SSH Tailscale para VPS: ssh cartorio@vps-cartorio.tail2fe279.ts.net
- rsync instalado
- Diretorio VPS: /var/lib/docker/volumes/cartorio_brain/_data/ (criado pelo admin)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LOCAL_BRAIN = Path("/Users/gustavoalmeida/projetos/Cartorio/.brain")
VPS_HOST = "cartorio@vps-cartorio.tail2fe279.ts.net"
VPS_BRAIN = "/var/lib/docker/volumes/cartorio_brain/_data/"


def _check_rsync() -> bool:
    return shutil.which("rsync") is not None


def _check_ssh() -> bool:
    return shutil.which("ssh") is not None


def push_to_vps() -> int:
    """local -> VPS via rsync over ssh."""
    if not _check_rsync() or not _check_ssh():
        print("ERRO: rsync/ssh nao instalados. brew install rsync openssh", file=sys.stderr)
        return 1

    if not LOCAL_BRAIN.exists():
        print(f"ERRO: {LOCAL_BRAIN} nao existe", file=sys.stderr)
        return 1

    print(f"[push] {LOCAL_BRAIN} -> {VPS_HOST}:{VPS_BRAIN}")
    cmd = [
        "rsync",
        "-avz",
        "--delete",
        str(LOCAL_BRAIN) + "/",
        f"{VPS_HOST}:{VPS_BRAIN}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.returncode != 0:
        print(f"ERRO rsync: {result.stderr}", file=sys.stderr)
        return result.returncode
    return 0


def pull_from_vps() -> int:
    """VPS -> local via rsync over ssh."""
    if not _check_rsync() or not _check_ssh():
        print("ERRO: rsync/ssh nao instalados", file=sys.stderr)
        return 1

    print(f"[pull] {VPS_HOST}:{VPS_BRAIN} -> {LOCAL_BRAIN}")
    cmd = [
        "rsync",
        "-avz",
        "--delete",
        f"{VPS_HOST}:{VPS_BRAIN}",
        str(LOCAL_BRAIN) + "/",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.returncode != 0:
        print(f"ERRO rsync: {result.stderr}", file=sys.stderr)
        return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--push", action="store_true", help="local -> VPS")
    parser.add_argument("--pull", action="store_true", help="VPS -> local")
    parser.add_argument("--full", action="store_true", help="push + pull")
    args = parser.parse_args()

    if not (args.push or args.pull or args.full):
        print("Use --push, --pull ou --full")
        return 1

    rc = 0
    if args.full or args.push:
        rc |= push_to_vps()
    if args.full or args.pull:
        rc |= pull_from_vps()
    return rc


if __name__ == "__main__":
    sys.exit(main())
