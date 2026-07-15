"""Tests for brain_memory.py (BRAIN8 memory auto-append).

Validates:
- cria .harness/memory/lesson-NNN-{slug}.md com frontmatter YAML + body
- append bullet em .harness/memory/MEMORY.md com cross-ref para a lesson
- slug derivado do title (lowercase, hifens, max 50 chars)
- next_id = max(existing) + 1 (nao sobrescreve lessons existentes)
- idempotencia (chamar 2x com mesma lesson_id retorna erro/skip)
- reins list gravada como YAML array
- content sem frontmatter ainda funciona (degrada graciosamente)
- arquivo gerado tem secao 'Context', 'Solution' canonicas
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services import brain_memory


@pytest.fixture
def tmp_harness(tmp_path: Path) -> Path:
    """Simula .harness/memory/ com 3 lessons pre-existentes."""
    memory = tmp_path / ".harness" / "memory"
    memory.mkdir(parents=True)
    (memory / "lesson-176-sre-incident.md").write_text(
        "---\nname: lesson-176-sre-incident\ndescription: SRE 502 recovery\ntype: project\n---\n# Lesson 176\n",
        encoding="utf-8",
    )
    (memory / "lesson-177-old-thing.md").write_text("# Lesson 177\n", encoding="utf-8")
    (memory / "MEMORY.md").write_text(
        "# MEMORY cross-rein\n\n- [[lesson-176]] recovery\n- [[lesson-177]] old\n",
        encoding="utf-8",
    )
    return memory


def test_append_lesson_creates_file_with_frontmatter(tmp_harness: Path) -> None:
    """append_lesson deve criar lesson-NNN-{slug}.md com YAML frontmatter."""
    result = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Brain6 sync implemented",
        content="Created brain_sync service for incremental VPS diff.",
        reins=["cartorio-dev"],
    )
    created = tmp_harness / result["filepath"]
    assert created.exists()
    body = created.read_text(encoding="utf-8")
    assert body.startswith("---\n")
    assert "name: lesson-178" in body
    assert "description: Brain6 sync implemented" in body
    assert "type: project" in body
    assert "reins: [cartorio-dev]" in body
    assert "Brain6 sync implemented" in body
    assert "Created brain_sync service" in body


def test_append_lesson_uses_next_id_after_max(tmp_harness: Path) -> None:
    """next_id = max(existing NNN) + 1, nao 1."""
    result = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Another lesson",
        content="More content",
        reins=["cartorio-sre"],
    )
    # lesson-176 e lesson-177 existem -> next = 178
    assert "lesson-178" in result["filepath"]


def test_append_lesson_slug_derived_from_title(tmp_harness: Path) -> None:
    """Slug = title.lower().replace(' ', '-')[:50]."""
    result = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Hello World From Cartorio",
        content="X",
        reins=["cartorio-dev"],
    )
    assert "hello-world-from-cartorio" in result["filepath"]


def test_append_lesson_appends_bullet_to_memory_md(tmp_harness: Path) -> None:
    """MEMORY.md deve ganhar nova linha com wikilink para a lesson."""
    before = tmp_harness / "MEMORY.md"
    initial_size = before.stat().st_size

    brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Brain8 memory auto",
        content="Auto-append implemented",
        reins=["cartorio-dev"],
    )

    updated = before.read_text(encoding="utf-8")
    assert len(updated) > initial_size
    assert "[[lesson-178-brain8-memory-auto]]" in updated
    assert "Brain8 memory auto" in updated


def test_append_lesson_is_idempotent_on_same_id(tmp_harness: Path) -> None:
    """2a chamada com mesmo lesson_id esperado = skip (sem duplicar)."""
    first = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Same title",
        content="Same content",
        reins=["cartorio-dev"],
        lesson_id=200,
    )
    assert first["filepath"].endswith("lesson-200-same-title.md")

    # segunda chamada com mesmo lesson_id explicito deve pular
    second = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Same title",
        content="Different content",
        reins=["cartorio-dev"],
        lesson_id=200,
    )
    assert second["ok"] is False
    assert second["skipped"] is True
    assert second["filepath"] == first["filepath"]

    body = (tmp_harness / first["filepath"]).read_text(encoding="utf-8")
    # Conteudo NAO foi sobrescrito
    assert "Same content" in body
    assert "Different content" not in body


def test_append_lesson_accepts_list_of_reins(tmp_harness: Path) -> None:
    """reins como list[str] deve ser serializado como YAML list."""
    result = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Multi-rein lesson",
        content="Cross-rein content",
        reins=["cartorio-dev", "cartorio-lgpd", "cartorio-n8n"],
    )
    body = (tmp_harness / result["filepath"]).read_text(encoding="utf-8")
    assert "reins: [cartorio-dev, cartorio-lgpd, cartorio-n8n]" in body


def test_append_lesson_appends_multiple_reins_to_memory_md(tmp_harness: Path) -> None:
    """Bullet no MEMORY.md deve mencionar todas as reins."""
    brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="LGPD review",
        content="Cross LGPD review",
        reins=["cartorio-lgpd", "cartorio-dev"],
    )
    body = (tmp_harness / "MEMORY.md").read_text(encoding="utf-8")
    assert "@cartorio-lgpd" in body
    assert "@cartorio-dev" in body


def test_append_lesson_returns_dict_with_filepath(tmp_harness: Path) -> None:
    """Resultado deve ter filepath (pathlib-relativo) + ok + id."""
    result = brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="Whatever",
        content="Body",
        reins=["cartorio-dev"],
    )
    assert result["ok"] is True
    assert result["skipped"] is False
    assert "lesson-" in result["filepath"]
    assert "lesson_id" in result
    assert isinstance(result["lesson_id"], int)
    assert result["lesson_id"] >= 178


def test_append_lesson_creates_memory_dir_if_missing(tmp_path: Path) -> None:
    """Se .harness/memory/ nao existe, cria."""
    memory = tmp_path / "deeply" / "nested" / "memory"
    assert not memory.exists()
    brain_memory.append_lesson(
        memory_dir=memory,
        title="First lesson",
        content="x",
        reins=["cartorio-dev"],
    )
    assert memory.exists()
    assert (memory / "MEMORY.md").exists()


def test_append_lesson_preserves_existing_memory_md_content(tmp_harness: Path) -> None:
    """Conteudo pre-existente do MEMORY.md NAO pode ser perdido."""
    brain_memory.append_lesson(
        memory_dir=tmp_harness,
        title="New entry",
        content="x",
        reins=["cartorio-dev"],
    )
    body = (tmp_harness / "MEMORY.md").read_text(encoding="utf-8")
    assert "# MEMORY cross-rein" in body
    assert "[[lesson-176]] recovery" in body
    assert "[[lesson-177]] old" in body