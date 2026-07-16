"""OpenAPI Snapshot generator + diff (G6.A.T3).

Gera snapshot da OpenAPI spec em JSON, compara com baseline, e falha CI
se houver diff (endpoint removido/alterado sem bump de versao).

Uso:
    python3 scripts/openapi_snapshot.py                    # gera snapshot
    python3 scripts/openapi_snapshot.py --check            # compara com baseline
    python3 scripts/openapi_snapshot.py --update           # atualiza baseline
    python3 scripts/openapi_snapshot.py --report snap.md  # gera report markdown

Exit codes:
    0 = snapshot gerado ou sem diff
    1 = diff detectado (--check) ou endpoint quebrado
    2 = erro pre-requisito (FastAPI nao disponivel, baseline ausente)

Storage:
    snapshots/openapi.baseline.json (committed)
    snapshots/openapi.current.json (gitignored, regenerated)

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 6.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_DIR = Path("snapshots")
BASELINE = SNAPSHOT_DIR / "openapi.baseline.json"
CURRENT = SNAPSHOT_DIR / "openapi.current.json"


def get_openapi_spec() -> dict:
    """Importa app.main e extrai OpenAPI schema."""
    import os
    print("Generating OpenAPI spec from app.main:app ...", file=sys.stderr)
    env = os.environ.copy()
    env.setdefault("APP_ENV", "development")
    result = subprocess.run(
        [
            "uv", "run", "python", "-c",
            "from app.main import app; import json; "
            "print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))",
        ],
        cwd="backend",
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print(f"[ERROR] Failed to import app.main: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return json.loads(result.stdout)


def save_snapshot(spec: dict, path: Path) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True))


def diff_specs(baseline: dict, current: dict) -> tuple[list[str], list[str], list[str]]:
    """Compara baseline vs current. Retorna (added, removed, changed) endpoints."""
    base_paths = set(baseline.get("paths", {}).keys())
    curr_paths = set(current.get("paths", {}).keys())

    added = sorted(curr_paths - base_paths)
    removed = sorted(base_paths - curr_paths)

    # Endpoints alterados (mesmo path mas assinatura diferente)
    changed: list[str] = []
    for path in sorted(base_paths & curr_paths):
        base_ops = baseline["paths"][path]
        curr_ops = current["paths"][path]
        if json.dumps(base_ops, sort_keys=True) != json.dumps(curr_ops, sort_keys=True):
            changed.append(path)

    return added, removed, changed


def render_markdown(added: list[str], removed: list[str], changed: list[str], current: dict) -> str:
    md: list[str] = []
    md.append("# OpenAPI Snapshot Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Total paths no current**: {len(current.get('paths', {}))}")
    md.append("")
    md.append("## Diff vs baseline")
    md.append("")
    md.append(f"- **Adicionados**: {len(added)}")
    md.append(f"- **Removidos**: {len(removed)}")
    md.append(f"- **Alterados**: {len(changed)}")
    md.append("")
    if added:
        md.append("### Adicionados (novos endpoints)")
        md.append("")
        for p in added:
            methods = ", ".join(current["paths"][p].keys())
            md.append(f"- `{p}` ({methods})")
        md.append("")
    if removed:
        md.append("### Removidos (breaking change!)")
        md.append("")
        for p in removed:
            md.append(f"- `{p}`")
        md.append("")
    if changed:
        md.append("### Alterados (signature diff)")
        md.append("")
        for p in changed:
            md.append(f"- `{p}`")
        md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 6 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAPI snapshot generator")
    parser.add_argument("--check", action="store_true", help="comparar com baseline e exit 1 se diff")
    parser.add_argument("--update", action="store_true", help="atualizar baseline com current")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    spec = get_openapi_spec()
    save_snapshot(spec, CURRENT)
    print(f"Snapshot salvo: {CURRENT} ({len(spec.get('paths', {}))} paths)", file=sys.stderr)

    if args.update:
        save_snapshot(spec, BASELINE)
        print(f"Baseline atualizado: {BASELINE}")
        return 0

    if args.check:
        if not BASELINE.exists():
            print(f"[ERROR] Baseline nao existe: {BASELINE}", file=sys.stderr)
            print(f"  Rode: python3 scripts/openapi_snapshot.py --update", file=sys.stderr)
            return 2
        baseline = json.loads(BASELINE.read_text())
        added, removed, changed = diff_specs(baseline, spec)

        if removed:
            print(f"[HOLD] {len(removed)} endpoints REMOVIDOS (breaking change!)")
            for p in removed:
                print(f"  - {p}")
            return 1

        if changed:
            print(f"[HOLD] {len(changed)} endpoints ALTERADOS (signature diff)")
            for p in changed[:10]:
                print(f"  - {p}")

        if added:
            print(f"[WORK] {len(added)} endpoints ADICIONADOS (non-breaking)")

        if not removed and not changed:
            print(f"[WORK] Sem diff vs baseline")
            return 0

        # Tem mudancas, mas nenhuma breaking. Report.
        if args.report:
            args.report.write_text(render_markdown(added, removed, changed, spec))
        return 1  # changed sem removed ainda e diff

    print(f"Gerado: {CURRENT}")
    print(f"Para comparar: --check")
    print(f"Para atualizar baseline: --update")
    return 0


if __name__ == "__main__":
    sys.exit(main())
