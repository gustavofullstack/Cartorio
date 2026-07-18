"""G8.21.T1 — OpenClaw skill registry + validator.

Descobre todas as skills em ``.agents/skills/`` (cada uma com SKILL.md e
YAML frontmatter), valida os campos obrigatorios e produz um manifesto
impressao no stdout. Usado por dead-man's-switch do agente OpenClaw
para garantir que nenhuma skill nova fica orfa e que toda skill tem
identidade rastreavel (name + description).

Uso:
    python3 scripts/openclaw_skill_registry.py
    python3 scripts/openclaw_skill_registry.py --json

Exit codes:
    0 = todas as skills sao validas
    1 = ao menos uma skill com frontmatter ausente, YAML invalido
        ou campos obrigatorios faltando (name/description).

Modified by Gustavo Almeida + cartorio-dev — G8.21.T1.
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "[ERROR] PyYAML nao instalado. uv add pyyaml e rode de novo.", file=sys.stderr
    )
    sys.exit(2)


SKILLS_DIR_DEFAULT = Path(".agents/skills")
REQUIRED_FIELDS = ("name", "description")


def parse_skill(skill_md: Path) -> dict | None:
    """Parse YAML frontmatter from SKILL.md. Returns dict or None.

    Frontmatter delim: opening ``---`` on line 1, closing ``---`` before content.
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        metadata = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(metadata, dict):
        return None
    return metadata


def validate_skill(metadata: dict, name: str) -> list[str]:
    """Return list of validation errors for the parsed metadata dict."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in metadata or metadata[field] in (None, ""):
            errors.append(f"{name}: missing required field '{field}'")
    return errors


@lru_cache(maxsize=64)
def _cached_parse(skill_md_str: str) -> dict | None:
    """Cache parsed metadata by absolute path string."""
    return parse_skill(Path(skill_md_str))


def discover_skills(skills_dir: Path) -> tuple[list[dict], list[str]]:
    """Walk skills_dir for SKILL.md; return (skills, errors)."""
    skills: list[dict] = []
    errors: list[str] = []
    if not skills_dir.exists():
        errors.append(f"skills dir not found: {skills_dir}")
        return skills, errors
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        name = skill_md.parent.name
        cached = _cached_parse(str(skill_md.resolve()))
        if cached is None:
            errors.append(f"{name}: invalid or missing YAML frontmatter")
            continue
        errs = validate_skill(cached, name)
        errors.extend(errs)
        skills.append(
            {
                "name": name,
                "path": str(skill_md.parent),
                "description": str(cached.get("description", ""))
                .strip()
                .splitlines()[0]
                if cached.get("description")
                else "",
                "version": str(cached.get("version") or "")
                if "version" in cached
                else "",
            }
        )
    return skills, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClaw skill registry + validator (G8.21.T1)."
    )
    parser.add_argument(
        "--skills-dir",
        default=str(SKILLS_DIR_DEFAULT),
        help="Diretorio raiz das skills",
    )
    parser.add_argument(
        "--json", action="store_true", help="Saida em JSON em vez de texto"
    )
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    skills, errors = discover_skills(skills_dir)

    if args.json:
        payload = {"count": len(skills), "errors": errors, "skills": skills}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Found {len(skills)} skills in {skills_dir}")
        for s in skills:
            line = f"  - {s['name']}: {s['description'][:80]}"
            if s.get("version"):
                line += f"  [v{s['version']}]"
            print(line)
        if errors:
            print("ERRORS:")
            for err in errors:
                print(f"  - {err}")

    return 0 if not errors and skills else 1


if __name__ == "__main__":
    sys.exit(main())
