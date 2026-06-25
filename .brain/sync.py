"""Cross-session context sync (BRAIN8).

Sincroniza estado cerebral (loop + index + lessons + memory + session)
em um unico arquivo exportable, permitindo que a proxima sessao
restaure 100% do contexto.

Uso:
    python -m brain.sync export
    python -m brain.sync import <snapshot.json>
    python -m brain.sync diff  # compara estado atual vs ultimo snapshot

Quando executar:
    - FINAL de cada sessao (sempre)
    - INICIO de cada sessao (para restaurar contexto)
    - AUTOMATICAMENTE via pre-commit hook
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any

BRAIN_ROOT = Path(__file__).resolve().parent
SNAPSHOTS_DIR = BRAIN_ROOT / "snapshots"


def _read_json(path: Path) -> dict | None:
    """Le JSON com seguranca."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARN: falha ao ler {path}: {e}")
        return None


def _hash_file(path: Path) -> str:
    """SHA256 do conteudo de um arquivo."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def export_snapshot(label: str | None = None) -> dict[str, Any]:
    """Exporta estado atual do brain em snapshot JSON.

    Args:
        label: rotulo opcional (ex: 'pre-fix-openclaw-1M')

    Returns:
        dict com snapshot completo
    """
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    label_part = f"-{label}" if label else ""
    snapshot_id = f"{ts}{label_part}"

    snapshot: dict[str, Any] = {
        "snapshot_id": snapshot_id,
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "label": label,
        "files": {},
        "stats": {},
    }

    # Coletar todos os arquivos do brain
    for md_file in sorted(BRAIN_ROOT.rglob("*.md")):
        rel = md_file.relative_to(BRAIN_ROOT)
        snapshot["files"][str(rel)] = {
            "content": md_file.read_text(encoding="utf-8"),
            "hash": _hash_file(md_file),
            "size": md_file.stat().st_size,
        }

    for json_file in sorted(BRAIN_ROOT.rglob("*.json")):
        rel = json_file.relative_to(BRAIN_ROOT)
        if "snapshots" in rel.parts:
            continue
        data = _read_json(json_file)
        if data is not None:
            snapshot["files"][str(rel)] = {
                "data": data,
                "hash": _hash_file(json_file),
                "size": json_file.stat().st_size,
            }

    for py_file in sorted(BRAIN_ROOT.rglob("*.py")):
        if "snapshots" in py_file.parts or "__pycache__" in py_file.parts:
            continue
        rel = py_file.relative_to(BRAIN_ROOT)
        snapshot["files"][str(rel)] = {
            "content": py_file.read_text(encoding="utf-8"),
            "hash": _hash_file(py_file),
            "size": py_file.stat().st_size,
        }

    # Stats
    snapshot["stats"] = {
        "total_files": len(snapshot["files"]),
        "total_size_bytes": sum(f.get("size", 0) for f in snapshot["files"].values()),
        "by_type": {
            "md": sum(1 for k in snapshot["files"] if k.endswith(".md")),
            "json": sum(1 for k in snapshot["files"] if k.endswith(".json")),
            "py": sum(1 for k in snapshot["files"] if k.endswith(".py")),
        },
    }

    # Salvar
    snap_path = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    snap_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return snapshot


def list_snapshots() -> list[dict[str, str]]:
    """Lista snapshots disponiveis."""
    if not SNAPSHOTS_DIR.exists():
        return []
    snaps = []
    for f in sorted(SNAPSHOTS_DIR.glob("*.json"), reverse=True):
        data = _read_json(f)
        if data:
            snaps.append({
                "file": f.name,
                "id": data.get("snapshot_id", f.stem),
                "exported_at": data.get("exported_at", "?"),
                "label": data.get("label", ""),
                "files": data.get("stats", {}).get("total_files", 0),
            })
    return snaps


def import_snapshot(snapshot_file: str) -> dict[str, Any]:
    """Restaura brain a partir de um snapshot.

    ATENCAO: sobrescreve arquivos existentes. Use com cuidado.

    Returns:
        dict com resumo do que foi restaurado
    """
    snap_path = SNAPSHOTS_DIR / snapshot_file
    if not snap_path.exists():
        return {"error": f"Snapshot nao encontrado: {snapshot_file}"}

    data = _read_json(snap_path)
    if not data:
        return {"error": f"Snapshot invalido: {snapshot_file}"}

    restored = 0
    skipped = 0
    for rel_path, file_data in data.get("files", {}).items():
        target = BRAIN_ROOT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if "content" in file_data:
            target.write_text(file_data["content"], encoding="utf-8")
            restored += 1
        elif "data" in file_data:
            target.write_text(
                json.dumps(file_data["data"], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            restored += 1
        else:
            skipped += 1

    return {
        "snapshot_id": data.get("snapshot_id"),
        "exported_at": data.get("exported_at"),
        "restored": restored,
        "skipped": skipped,
        "label": data.get("label"),
    }


def diff_snapshots(file_a: str, file_b: str) -> dict[str, Any]:
    """Compara dois snapshots e retorna arquivos modificados."""
    a_path = SNAPSHOTS_DIR / file_a
    b_path = SNAPSHOTS_DIR / file_b
    a = _read_json(a_path)
    b = _read_json(b_path)
    if not a or not b:
        return {"error": "Snapshot invalido"}

    a_files = a.get("files", {})
    b_files = b.get("files", {})

    added = set(b_files) - set(a_files)
    removed = set(a_files) - set(b_files)
    common = set(a_files) & set(b_files)

    modified = []
    for f in common:
        if a_files[f].get("hash") != b_files[f].get("hash"):
            modified.append(f)

    return {
        "a": file_a,
        "b": file_b,
        "added": sorted(added),
        "removed": sorted(removed),
        "modified": sorted(modified),
        "unchanged_count": len(common) - len(modified),
    }


def cleanup_snapshots(keep_last: int = 10) -> dict[str, int]:
    """Remove snapshots antigos, mantendo os N mais recentes."""
    if not SNAPSHOTS_DIR.exists():
        return {"deleted": 0, "kept": 0}

    snaps = sorted(SNAPSHOTS_DIR.glob("*.json"), reverse=True)
    to_delete = snaps[keep_last:]
    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            deleted += 1
        except OSError:
            pass

    return {
        "deleted": deleted,
        "kept": min(keep_last, len(snaps)),
    }


# ============================================================================
# CLI
# ============================================================================


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m brain.sync <comando> [args]")
        print("Comandos:")
        print("  export [label]          - Exporta brain state")
        print("  list                    - Lista snapshots")
        print("  import <file>           - Restaura brain de snapshot")
        print("  diff <a> <b>            - Compara 2 snapshots")
        print("  cleanup [keep=N]        - Remove snapshots antigos (default keep=10)")
        return 1

    cmd = sys.argv[1]

    if cmd == "export":
        label = sys.argv[2] if len(sys.argv) > 2 else None
        snap = export_snapshot(label=label)
        print(f"✅ Snapshot exportado: {snap['snapshot_id']}")
        print(f"   Arquivos: {snap['stats']['total_files']}")
        print(f"   Tamanho: {snap['stats']['total_size_bytes']} bytes")
        print(f"   Por tipo: {snap['stats']['by_type']}")
        return 0

    if cmd == "list":
        snaps = list_snapshots()
        if not snaps:
            print("Nenhum snapshot encontrado")
            return 0
        print(f"{'ID':<40} {'ARQUIVOS':<10} {'LABEL':<20} {'EXPORTADO EM'}")
        print("-" * 100)
        for s in snaps[:20]:
            label = s["label"] or "-"
            print(f"{s['id']:<40} {s['files']:<10} {label:<20} {s['exported_at']}")
        return 0

    if cmd == "import":
        if len(sys.argv) < 3:
            print("Uso: import <file>")
            return 1
        result = import_snapshot(sys.argv[2])
        if "error" in result:
            print(f"❌ {result['error']}")
            return 1
        print(f"✅ Snapshot restaurado: {result['snapshot_id']}")
        print(f"   Arquivos restaurados: {result['restored']}")
        print(f"   Pulados: {result['skipped']}")
        return 0

    if cmd == "diff":
        if len(sys.argv) < 4:
            print("Uso: diff <a> <b>")
            return 1
        diff = diff_snapshots(sys.argv[2], sys.argv[3])
        if "error" in diff:
            print(f"❌ {diff['error']}")
            return 1
        print(f"Diff: {diff['a']} -> {diff['b']}")
        print(f"  Adicionados: {len(diff['added'])}")
        for f in diff["added"]:
            print(f"    + {f}")
        print(f"  Removidos: {len(diff['removed'])}")
        for f in diff["removed"]:
            print(f"    - {f}")
        print(f"  Modificados: {len(diff['modified'])}")
        for f in diff["modified"]:
            print(f"    ~ {f}")
        print(f"  Inalterados: {diff['unchanged_count']}")
        return 0

    if cmd == "cleanup":
        keep = 10
        if len(sys.argv) > 2 and sys.argv[2].startswith("keep="):
            keep = int(sys.argv[2].split("=")[1])
        result = cleanup_snapshots(keep_last=keep)
        print(f"✅ Cleanup: {result['deleted']} deletados, {result['kept']} mantidos")
        return 0

    print(f"❌ Comando desconhecido: {cmd}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
