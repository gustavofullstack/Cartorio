"""brain_memory.py - BRAIN8 memory auto-append.

Cria `.harness/memory/lesson-NNN-{slug}.md` com YAML frontmatter + body,
e faz append de 1 bullet em `.harness/memory/MEMORY.md` com cross-ref
(wikilink) e tags das reins envolvidas.

Idempotente via `lesson_id` explicito: 2a chamada com mesmo ID = skip.

LGPD-safe: caller e responsavel por nao passar PII em title/content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_MEMORY_DIR = Path("/Users/gustavoalmeida/projetos/Cartorio/.harness/memory")
MEMORY_INDEX_FILE = "MEMORY.md"
ID_PATTERN = re.compile(r"^lesson-(\d{3,})-")


def _slugify(title: str) -> str:
    """Slug = title.lower().replace(' ', '-')[:50], apenas [a-z0-9-]."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:50]


def _existing_max_id(memory_dir: Path) -> int:
    """Retorna o maior NNN encontrado em lesson-NNN-*.md ou 0 se nenhum."""
    if not memory_dir.exists():
        return 0
    max_n = 0
    for f in memory_dir.glob("lesson-*.md"):
        m = ID_PATTERN.match(f.name)
        if m:
            try:
                max_n = max(max_n, int(m.group(1)))
            except ValueError:
                continue
    return max_n


def _build_lesson_file(
    lesson_id: int,
    title: str,
    content: str,
    reins: list[str],
    slug: str,
) -> str:
    """Constroi o conteudo completo de uma lesson (frontmatter + body)."""
    reins_yaml = ", ".join(reins)
    frontmatter = (
        "---\n"
        f"name: lesson-{lesson_id}-{slug}\n"
        f"description: {title}\n"
        "type: project\n"
        f"reins: [{reins_yaml}]\n"
        "---\n"
    )
    body = (
        f"# Lesson {lesson_id} - {title}\n\n"
        f"## Context\n\n{title}\n\n"
        f"## Solution\n\n{content}\n\n"
        f"Modified by Gustavo Almeida\n"
    )
    return frontmatter + "\n" + body


def _append_to_memory_index(
    memory_dir: Path,
    lesson_id: int,
    title: str,
    slug: str,
    reins: list[str],
) -> None:
    """Append 1 bullet no MEMORY.md com wikilink + tags."""
    memory_index = memory_dir / MEMORY_INDEX_FILE
    reins_tag = " ".join(f"@{r}" for r in reins)
    bullet = f"- [[lesson-{lesson_id}-{slug}]] {title} {reins_tag}\n"

    if memory_index.exists():
        with memory_index.open("a", encoding="utf-8") as f:
            f.write(bullet)
    else:
        memory_index.write_text(
            f"# MEMORY cross-rein\n\n{bullet}",
            encoding="utf-8",
        )


def append_lesson(
    memory_dir: Path = DEFAULT_MEMORY_DIR,
    title: str = "",
    content: str = "",
    reins: list[str] | None = None,
    lesson_id: int | None = None,
) -> dict[str, Any]:
    """Cria lesson-NNN-{slug}.md + append bullet no MEMORY.md.

    Args:
        memory_dir: caminho de .harness/memory/.
        title: titulo da lesson (5-200 chars).
        content: corpo / solucao da lesson.
        reins: lista de reins (cartorio-dev, cartorio-lgpd, etc).
        lesson_id: se fornecido, usa este NNN (com skip se ja existir).

    Returns:
        dict com filepath, lesson_id, ok, skipped.
    """
    if reins is None:
        reins = ["cartorio-dev"]

    memory_dir = Path(memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)

    if lesson_id is None:
        lesson_id = _existing_max_id(memory_dir) + 1

    slug = _slugify(title)
    filename = f"lesson-{lesson_id}-{slug}.md"
    filepath = memory_dir / filename

    if filepath.exists():
        return {
            "ok": False,
            "skipped": True,
            "filepath": str(filepath),
            "lesson_id": lesson_id,
            "reason": f"lesson {lesson_id} ja existe",
        }

    body = _build_lesson_file(lesson_id, title, content, reins, slug)
    filepath.write_text(body, encoding="utf-8")

    _append_to_memory_index(memory_dir, lesson_id, title, slug, reins)

    return {
        "ok": True,
        "skipped": False,
        "filepath": str(filepath),
        "lesson_id": lesson_id,
        "slug": slug,
        "reins": reins,
    }
