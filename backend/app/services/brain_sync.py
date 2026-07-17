"""brain_sync.py - BRAIN6 incremental VPS sync.

Compara estado atual dos containers prod (output de `docker service ls` cached
ou `docker ps`) com o snapshot anterior em `.brain/snapshots/YYYY-MM-DD.json`,
gera diff (added/removed/changed), grava novo snapshot e atualiza a secao
"Containers prod" do `.brain/index.md`.

LGPD-safe: nao expoem PII. Apenas metadata de containers.

Funcoes publicas:
- sync_vps_incremental(): roda 1 sync e grava snapshot
- diff_against_last(): compara snapshot atual com o ultimo gravado
- _list_containers(): mocked por testes; em prod usa `docker service ls`
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_BRAIN_DIR = Path("/Users/gustavoalmeida/projetos/Cartorio/.brain")
SNAPSHOTS_DIRNAME = "snapshots"
INDEX_FILENAME = "index.md"
CONTAINERS_HEADER = "## Containers prod"


def _list_containers() -> list[dict[str, Any]]:
    """Lista containers ativos via `docker service ls` ou fallback.

    Em ambiente local (sem Docker daemon), retorna lista vazia.
    Em testes, sempre mockada via monkeypatch.
    """
    try:
        result = subprocess.run(
            ["docker", "service", "ls", "--format", "{{.Name}}\t{{.Replicas}}\t{{.Image}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        out: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                out.append({"name": parts[0], "replicas": parts[1], "image": parts[2]})
        return out
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _snapshot_path(brain_dir: Path, date_str: str) -> Path:
    return brain_dir / SNAPSHOTS_DIRNAME / f"{date_str}.json"


def _latest_snapshot(brain_dir: Path) -> dict[str, Any] | None:
    """Retorna o snapshot mais recente (por nome de arquivo YYYY-MM-DD.json)."""
    snaps_dir = brain_dir / SNAPSHOTS_DIRNAME
    if not snaps_dir.exists():
        return None
    candidates = sorted(snaps_dir.glob("*.json"), reverse=True)
    for f in candidates:
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _containers_to_state(containers: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Normaliza lista de containers para dict {name: {replicas, image}}."""
    return {
        c["name"]: {"replicas": c.get("replicas", ""), "image": c.get("image", "")}
        for c in containers
    }


def _diff_states(
    old: dict[str, dict[str, str]],
    new: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Calcula diff entre 2 estados de containers."""
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed: list[str] = []
    changed_detail: dict[str, dict[str, str]] = {}
    for name in sorted(set(new) & set(old)):
        before = old[name]
        after = new[name]
        diff_fields: dict[str, str] = {}
        for k in before:
            if before[k] != after.get(k):
                diff_fields[k] = f"{before[k]} -> {after.get(k)}"
        if diff_fields:
            changed.append(name)
            changed_detail[name] = diff_fields
    unchanged_count = len(set(old) & set(new)) - len(changed)
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "changed_detail": changed_detail,
        "unchanged_count": unchanged_count,
    }


def _update_index_containers_section(
    index_path: Path, containers: dict[str, dict[str, str]]
) -> None:
    """Atualiza (ou cria) secao '## Containers prod' em index.md."""
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"{CONTAINERS_HEADER}",
        "",
        f"Atualizado em: {today}",
        f"Total containers: {len(containers)}",
        "",
        "| Name | Replicas | Image |",
        "|---|---|---|",
    ]
    for name in sorted(containers):
        c = containers[name]
        lines.append(f"| {name} | {c.get('replicas', '')} | {c.get('image', '')} |")
    section = "\n".join(lines) + "\n"

    if not index_path.exists():
        index_path.write_text(f"# Brain Index\n\n{section}\n", encoding="utf-8")
        return

    content = index_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^{re.escape(CONTAINERS_HEADER)}.*?(?=^## |\Z)",
        re.DOTALL | re.MULTILINE,
    )
    if pattern.search(content):
        new_content = pattern.sub(section.rstrip() + "\n\n", content, count=1)
    else:
        new_content = content.rstrip() + "\n\n" + section

    index_path.write_text(new_content, encoding="utf-8")


def sync_vps_incremental(brain_dir: Path = DEFAULT_BRAIN_DIR) -> dict[str, Any]:
    """Roda 1 sync: lista containers, salva snapshot, atualiza index.md.

    Args:
        brain_dir: caminho do .brain/ local.

    Returns:
        dict com ok, snapshot_file, containers_count, diff vs anterior.
    """
    brain_dir = Path(brain_dir)
    snaps_dir = brain_dir / SNAPSHOTS_DIRNAME
    snaps_dir.mkdir(parents=True, exist_ok=True)

    containers = _list_containers()
    new_state = _containers_to_state(containers)

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    previous = _latest_snapshot(brain_dir)
    previous_state = previous.get("containers", {}) if previous else {}
    diff = _diff_states(previous_state, new_state)

    payload = {
        "snapshot_id": today,
        "date": today,
        "exported_at": now_iso,
        "containers_count": len(new_state),
        "containers": new_state,
        "diff_vs_previous": {
            "added": diff["added"],
            "removed": diff["removed"],
            "changed": diff["changed"],
            "unchanged_count": diff["unchanged_count"],
        },
    }
    snap_path = _snapshot_path(brain_dir, today)
    snap_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _update_index_containers_section(brain_dir / INDEX_FILENAME, new_state)

    return {
        "ok": True,
        "snapshot_file": str(snap_path),
        "containers_count": len(new_state),
        "added": diff["added"],
        "removed": diff["removed"],
        "changed": diff["changed"],
    }


def diff_against_last(brain_dir: Path = DEFAULT_BRAIN_DIR) -> dict[str, Any]:
    """Roda sync fresco (containers live) e retorna diff vs ultimo snapshot.

    NAO grava snapshot novo - util para healthchecks que querem
    detectar drift sem persistir.
    """
    brain_dir = Path(brain_dir)
    containers = _list_containers()
    new_state = _containers_to_state(containers)
    previous = _latest_snapshot(brain_dir)
    previous_state = previous.get("containers", {}) if previous else {}
    return _diff_states(previous_state, new_state)
