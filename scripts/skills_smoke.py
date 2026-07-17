#!/usr/bin/env python3
"""Skills smoke check (G7.15.T2).

Valida presença e sanidade mínima das skills core em `.agents/skills/`:
  - diretório existe
  - SKILL.md não-vazio (≥ MIN_BYTES)
  - extrai first-line purpose (description YAML ou H1)
  - detecta descriptions placeholder óbvias (TODO / placeholder / …)

Uso (raiz do repo):
  python3 scripts/skills_smoke.py
  python3 scripts/skills_smoke.py --json
  python3 scripts/skills_smoke.py --all

Exit 0 se todas as CORE skills passam; exit 1 caso contrário.

Modified by Gustavo Almeida — G7.15 Wave 25.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".agents" / "skills"

# Core skills exigidas pelo smoke G7.15.T2 (+ easypanel/hostinger do deliverable)
CORE_SKILLS = (
    "api",
    "chatwoot",
    "n8n",
    "supabase",
    "easypanel",
    "hostinger",
)

MIN_BYTES = 200

# Placeholders óbvios em description (não reescreve skills — só reporta)
PLACEHOLDER_RE = re.compile(
    r"(?i)\b("
    r"TODO|FIXME|placeholder|coming\s+soon|lorem\s+ipsum|"
    r"dummy\s+skill|not\s+implemented|\bTBD\b"
    r")\b"
)

# Falso-positivo PT: "TODOS" não é "TODO"
_TODOS_GUARD = re.compile(r"(?i)TODOS")


def _is_placeholder_hit(text: str, match: re.Match[str]) -> bool:
    """Ignore Portuguese 'TODOS' matching the TODO alternative."""
    if match.group(1).upper() != "TODO":
        return True
    window = text[max(0, match.start() - 1) : match.end() + 2]
    return _TODOS_GUARD.search(window) is None


def find_placeholders(text: str) -> list[str]:
    hits: list[str] = []
    for m in PLACEHOLDER_RE.finditer(text):
        if _is_placeholder_hit(text, m):
            hits.append(m.group(0))
    return hits


def parse_skill_md(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    bytes_n = len(raw.encode("utf-8"))
    lines_n = raw.count("\n") + (0 if raw.endswith("\n") or not raw else 1)

    frontmatter = ""
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]

    desc_first = ""
    # description: | multiline
    m = re.search(
        r"(?ms)^description:\s*\|\s*\n((?:[ \t]+.+\n)+)",
        frontmatter,
    )
    if m:
        block = m.group(1)
        for line in block.splitlines():
            stripped = line.strip()
            if stripped:
                desc_first = stripped
                break
    else:
        m2 = re.search(r"(?m)^description:\s*(.+)$", frontmatter)
        if m2:
            desc_first = m2.group(1).strip().strip("\"'")

    h1 = ""
    m3 = re.search(r"(?m)^#\s+(.+)$", body)
    if m3:
        h1 = m3.group(1).strip()

    purpose = desc_first or h1 or "(missing purpose)"
    # Only flag placeholders in description / frontmatter name+description area
    ph_hits = find_placeholders(frontmatter)

    return {
        "bytes": bytes_n,
        "lines": lines_n,
        "description_first": desc_first,
        "h1": h1,
        "purpose": purpose,
        "placeholder_hits": ph_hits,
        "has_placeholder": bool(ph_hits),
    }


def check_skill(name: str) -> dict:
    skill_dir = SKILLS_DIR / name
    skill_md = skill_dir / "SKILL.md"
    result: dict = {
        "name": name,
        "path": str(skill_dir.relative_to(ROOT)),
        "dir_exists": skill_dir.is_dir(),
        "skill_md_exists": skill_md.is_file(),
        "ok": False,
        "errors": [],
    }

    if not skill_dir.is_dir():
        result["errors"].append("directory missing")
        return result
    if not skill_md.is_file():
        result["errors"].append("SKILL.md missing")
        return result

    meta = parse_skill_md(skill_md)
    result.update(meta)

    if meta["bytes"] < MIN_BYTES:
        result["errors"].append(f"SKILL.md too small ({meta['bytes']} < {MIN_BYTES})")
    if not (meta["description_first"] or meta["h1"]):
        result["errors"].append("no description/H1 purpose")
    if meta["has_placeholder"]:
        result["errors"].append(
            "placeholder in frontmatter: " + ", ".join(meta["placeholder_hits"])
        )

    result["ok"] = len(result["errors"]) == 0
    return result


def list_all_skill_dirs() -> list[str]:
    if not SKILLS_DIR.is_dir():
        return []
    names: list[str] = []
    for p in sorted(SKILLS_DIR.iterdir()):
        if p.is_dir() and (p / "SKILL.md").is_file():
            names.append(p.name)
    return names


def run(include_all: bool = False) -> dict:
    core_results = [check_skill(n) for n in CORE_SKILLS]
    core_pass = sum(1 for r in core_results if r["ok"])
    core_total = len(CORE_SKILLS)

    extended: list[dict] = []
    if include_all:
        extra_names = [n for n in list_all_skill_dirs() if n not in CORE_SKILLS]
        extended = [check_skill(n) for n in extra_names]

    verdict = "PASS" if core_pass == core_total else "FAIL"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills_dir": str(SKILLS_DIR.relative_to(ROOT)),
        "core_required": list(CORE_SKILLS),
        "core": core_results,
        "core_pass": core_pass,
        "core_total": core_total,
        "extended": extended,
        "inventory": list_all_skill_dirs(),
        "inventory_count": len(list_all_skill_dirs()),
        "verdict": verdict,
        "doc": "docs/SKILLS_SMOKE_G7.md",
        "map": ".harness/loop-engineer/SKILLS-MAP.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="G7.15 skills smoke")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument(
        "--all",
        action="store_true",
        help="also check non-core skills present under .agents/skills/",
    )
    args = parser.parse_args()

    report = run(include_all=args.all)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"Skills smoke G7.15 — {report['verdict']} · "
            f"core {report['core_pass']}/{report['core_total']}"
        )
        for r in report["core"]:
            flag = "OK" if r["ok"] else "FAIL"
            purpose = (r.get("purpose") or "")[:72]
            print(f"  [{flag}] {r['name']}: {purpose}")
            for err in r.get("errors") or []:
                print(f"         · {err}")
        if args.all and report["extended"]:
            print(f"  extended ({len(report['extended'])}):")
            for r in report["extended"]:
                flag = "OK" if r["ok"] else "FAIL"
                print(f"  [{flag}] {r['name']}")
        print(f"  inventory: {report['inventory_count']} skills with SKILL.md")
        print(f"  doc: {report['doc']}")

    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
