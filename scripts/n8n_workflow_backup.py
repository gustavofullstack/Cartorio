"""N8N Workflow versioned backup (G6.B.T7).

Cria snapshots versionados de TODOS os WFs em infra/n8n-workflows/ + INDEX.md,
SHA256 + timestamp, mantendo ultimas 30 versoes.

Armazena em backups/n8n-workflows/{YYYY-MM-DD}/snapshot.tar.gz + manifest.json
+ .sha256 sidecar.

Uso:
    python3 scripts/n8n_workflow_backup.py                 # backup agora
    python3 scripts/n8n_workflow_backup.py --restore LATEST  # restaura
    python3 scripts/n8n_workflow_backup.py --list             # lista snapshots
    python3 scripts/n8n_workflow_backup.py --prune 30         # manter 30
    python3 scripts/n8n_workflow_backup.py --report BACKUPS.md

Exit codes:
    0 = OK (backup ou restore com sucesso)
    1 = erro pre-requisito
    2 = erro durante backup

Modified by Gustavo Almeida + cartorio-n8n — G6 wave 16.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

WF_DIR = Path("infra/n8n-workflows")
BACKUP_ROOT = Path("backups/n8n-workflows")
TIMESTAMP_FMT = "%Y-%m-%d-%H%M%S"
MAX_SNAPSHOTS = 30


def create_snapshot() -> Path:
    """Cria 1 snapshot versionado. Retorna path do tar.gz."""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    snap_dir = BACKUP_ROOT / now.strftime("%Y-%m-%d")
    snap_dir.mkdir(exist_ok=True)

    archive_name = f"snapshot-{now.strftime(TIMESTAMP_FMT)}.tar.gz"
    archive_path = snap_dir / archive_name

    files_to_backup = sorted(WF_DIR.glob("*.json")) + [WF_DIR / "INDEX.md"]
    files_to_backup = [f for f in files_to_backup if f.exists()]

    with tarfile.open(archive_path, "w:gz") as tar:
        for f in files_to_backup:
            tar.add(f, arcname=f.relative_to(WF_DIR.parent))

    # Calcular SHA256
    import hashlib
    sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (archive_path.parent / f"{archive_name}.sha256").write_text(f"{sha256}  {archive_name}\n")

    # Manifest
    manifest = {
        "created_at": now.isoformat(),
        "workflow_count": len([f for f in files_to_backup if f.suffix == ".json"]),
        "archive": archive_name,
        "size_bytes": archive_path.stat().st_size,
        "sha256": sha256,
        "files": [f.name for f in files_to_backup],
    }
    manifest_path = snap_dir / f"manifest-{now.strftime(TIMESTAMP_FMT)}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return archive_path


def list_snapshots() -> list[dict]:
    """Lista todos snapshots disponiveis, mais recentes primeiro."""
    if not BACKUP_ROOT.exists():
        return []
    snapshots: list[dict] = []
    for snap_dir in sorted(BACKUP_ROOT.iterdir(), reverse=True):
        if not snap_dir.is_dir():
            continue
        for archive in sorted(snap_dir.glob("snapshot-*.tar.gz"), reverse=True):
            manifest_files = list(snap_dir.glob(f"manifest-{archive.name.replace('snapshot-', '').replace('.tar.gz', '')}.json"))
            manifest: dict = {}
            if manifest_files:
                try:
                    manifest = json.loads(manifest_files[0].read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            snapshots.append({
                "date": snap_dir.name,
                "archive": archive.name,
                "path": str(archive),
                "size_bytes": archive.stat().st_size,
                "sha256": manifest.get("sha256"),
                "workflow_count": manifest.get("workflow_count"),
            })
    return snapshots


def restore_snapshot(snapshot: dict) -> bool:
    """Restaura 1 snapshot, sobrescrevendo WFs atuais."""
    archive_path = Path(snapshot["path"])
    if not archive_path.exists():
        return False

    # Backup de seguranca do estado atual
    safety_backup = create_snapshot()
    print(f"[safety] backup de seguranca criado: {safety_backup}", file=sys.stderr)

    # Extrair sobre WF_DIR (relative path eh WF_DIR.parent)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=WF_DIR.parent)
    return True


def prune_old_snapshots(max_keep: int = MAX_SNAPSHOTS) -> int:
    """Mantem apenas os N snapshots mais recentes. Retorna quantos deletados."""
    snapshots = list_snapshots()
    if len(snapshots) <= max_keep:
        return 0
    to_delete = snapshots[max_keep:]
    deleted = 0
    for snap in to_delete:
        archive_path = Path(snap["path"])
        if archive_path.exists():
            archive_path.unlink()
            deleted += 1
        sha_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
        if sha_path.exists():
            sha_path.unlink()
    # Limpar diretorios vazios
    for d in BACKUP_ROOT.iterdir() if BACKUP_ROOT.exists() else []:
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    return deleted


def render_markdown(snapshots: list[dict]) -> str:
    md: list[str] = []
    md.append("# N8N Workflow Backups")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Total snapshots**: {len(snapshots)}")
    md.append("")
    if not snapshots:
        md.append("## [WORK] Nenhum snapshot criado ainda")
        md.append("")
        md.append("```bash")
        md.append("python3 scripts/n8n_workflow_backup.py")
        md.append("```")
    else:
        md.append("## Lista de snapshots")
        md.append("")
        md.append("| Data | Archive | WFs | Size | SHA256 |")
        md.append("|---|---|---|---|---|")
        for s in snapshots:
            sha = s["sha256"][:16] + "..." if s["sha256"] else "?"
            size_mb = s["size_bytes"] / 1024 / 1024
            md.append(f"| {s['date']} | `{s['archive']}` | {s['workflow_count']} | {size_mb:.2f} MB | `{sha}` |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + cartorio-n8n — G6 wave 16 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="N8N workflow versioned backup")
    parser.add_argument("--restore", metavar="DATE_OR_LATEST", help="restaurar snapshot")
    parser.add_argument("--list", action="store_true", help="listar snapshots")
    parser.add_argument("--prune", type=int, metavar="N", help="manter N snapshots mais recentes")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    if args.list:
        snaps = list_snapshots()
        print(f"Total snapshots: {len(snaps)}")
        for s in snaps[:10]:
            print(f"  {s['date']} {s['archive']} ({s['workflow_count']} WFs, {s['size_bytes']/1024/1024:.2f} MB)")
        if args.report:
            args.report.write_text(render_markdown(snaps))
            print(f"  Report: {args.report}", file=sys.stderr)
        return 0

    if args.prune is not None:
        deleted = prune_old_snapshots(args.prune)
        print(f"[WORK] {deleted} snapshots antigos removidos (mantendo {args.prune})")
        return 0

    if args.restore:
        snaps = list_snapshots()
        if args.restore == "LATEST":
            if not snaps:
                print("[ERROR] nenhum snapshot para restaurar", file=sys.stderr)
                return 2
            target = snaps[0]
        else:
            matches = [s for s in snaps if args.restore in s["date"] or args.restore in s["archive"]]
            if not matches:
                print(f"[ERROR] snapshot '{args.restore}' nao encontrado", file=sys.stderr)
                return 2
            target = matches[0]
        ok = restore_snapshot(target)
        if ok:
            print(f"[WORK] Snapshot restaurado: {target['archive']}")
        else:
            print(f"[ERROR] Falha ao restaurar {target['archive']}", file=sys.stderr)
            return 2
        return 0 if ok else 2

    # Default: criar novo snapshot
    if not WF_DIR.exists():
        print(f"[ERROR] {WF_DIR} nao existe", file=sys.stderr)
        return 2

    archive = create_snapshot()
    print(f"[WORK] Snapshot criado: {archive}")
    print(f"  Size: {archive.stat().st_size / 1024 / 1024:.2f} MB")

    # Prune automatico
    deleted = prune_old_snapshots(MAX_SNAPSHOTS)
    if deleted:
        print(f"[prune] {deleted} snapshots antigos removidos (mantendo {MAX_SNAPSHOTS})")

    if args.report:
        snaps = list_snapshots()
        args.report.write_text(render_markdown(snaps))
        print(f"  Report: {args.report}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())