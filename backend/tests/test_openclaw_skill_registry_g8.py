"""G8.21.T1 — Tests for OpenClaw skill registry + validator.

Cobre:
  1. ``parse_skill`` retorna metadata dict quando frontmatter e valido.
  2. ``parse_skill`` retorna None em YAML invalido ou ausente.
  3. ``validate_skill`` denuncia campo ``name`` faltando.
  4. ``validate_skill`` denuncia campo ``description`` faltando.
  5. ``validate_skill`` aceita metadata completa.
  6. ``discover_skills`` caminha SKILL.md e agrega resultados corretamente.
  7. ``main`` retorna 0 quando todas as skills sao validas.
  8. ``main`` retorna 1 quando ha erros de validacao.

Modified by Gustavo Almeida + cartorio-dev — G8.21.T1.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "openclaw_skill_registry.py"


@pytest.fixture(scope="module")
def reg_module() -> Any:
    """Importa scripts/openclaw_skill_registry.py dinamicamente (scripts/ nao e pacote)."""
    spec = importlib.util.spec_from_file_location("openclaw_skill_registry", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("openclaw_skill_registry", module)
    spec.loader.exec_module(module)
    return module


def _write_skill(tmp_path: Path, name: str, body: str) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    return skill_dir / "SKILL.md"


def _valid_body() -> str:
    return "---\nname: foo\ndescription: Uma skill de teste\nversion: 1.2.3\n---\n\n# Foo\n"


def test_parse_skill_returns_metadata(reg_module: Any, tmp_path: Path) -> None:
    skill_md = _write_skill(tmp_path, "foo", _valid_body())
    metadata = reg_module.parse_skill(skill_md)
    assert isinstance(metadata, dict)
    assert metadata["name"] == "foo"
    assert "skill de teste" in str(metadata["description"])


def test_parse_skill_invalid_yaml_returns_none(reg_module: Any, tmp_path: Path) -> None:
    skill_md = _write_skill(
        tmp_path,
        "broken",
        "---\nfoo: [unclosed bracket\n---\n",
    )
    assert reg_module.parse_skill(skill_md) is None
    skill_md_no_front = _write_skill(tmp_path, "nofm", "# sem frontmatter\n")
    assert reg_module.parse_skill(skill_md_no_front) is None


def test_validate_skill_missing_name(reg_module: Any) -> None:
    errs = reg_module.validate_skill({"description": "x"}, "stub")
    assert any("'name'" in e for e in errs)


def test_validate_skill_missing_description(reg_module: Any) -> None:
    errs = reg_module.validate_skill({"name": "x"}, "stub")
    assert any("'description'" in e for e in errs)


def test_validate_skill_complete_passes(reg_module: Any) -> None:
    errs = reg_module.validate_skill({"name": "x", "description": "y"}, "stub")
    assert errs == []


def test_main_walks_skills_dir_correctly(
    reg_module: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    valid = _write_skill(tmp_path, "alpha", _valid_body())
    extra = tmp_path / "alpha" / "notes.md"
    extra.write_text("ignored\n", encoding="utf-8")
    _write_skill(tmp_path, "nofm", "no frontmatter here\n")

    skills, errors = reg_module.discover_skills(tmp_path)
    assert len(skills) == 1
    assert skills[0]["name"] == "alpha"
    assert valid.exists()
    assert any("nofm" in e for e in errors)


def test_main_returns_0_on_valid(
    reg_module: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_skill(tmp_path, "alpha", _valid_body())
    monkeypatch.setattr(sys, "argv", ["openclaw_skill_registry", "--skills-dir", str(tmp_path)])
    rc = reg_module.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "Found 1 skills" in captured.out
    assert "alpha" in captured.out


def test_main_returns_1_on_errors(
    reg_module: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_skill(
        tmp_path,
        "broken",
        "---\ndescription: only desc, no name\n---\n",
    )
    monkeypatch.setattr(sys, "argv", ["openclaw_skill_registry", "--skills-dir", str(tmp_path)])
    rc = reg_module.main()
    assert rc == 1
    captured = capsys.readouterr()
    assert "ERRORS" in captured.out
    assert "name" in captured.out
