"""G8.04.T2 — Testes do export/package do system prompt LobeChat.

Cobre:
  - CARTORIO_DEFAULT_SYSTEM_PROMPT: HITL + LGPD, sem secrets
  - load_system_prompt: fallbacks (arquivo md, json systemRole, embedded)
  - export_package: escreve prompt.md + metadata.json com sha256
  - metadata sem chaves de secret
  - sha256 estável / consistente com conteúdo
  - CLI scripts/export_lobechat_prompt.py --list-sources / --embedded-only

Modified by Gustavo Almeida — G8.04.T2.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.lobechat_prompt_export import (
    CARTORIO_DEFAULT_SYSTEM_PROMPT,
    DEFAULT_SOURCE_CANDIDATES,
    EXPORTER_VERSION,
    METADATA_FILENAME,
    PACKAGE_VERSION,
    PROMPT_FILENAME,
    build_metadata,
    export_package,
    find_repo_root,
    list_candidate_sources,
    load_system_prompt,
    redact_secrets,
    sha256_text,
)

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SCRIPT = REPO / "scripts" / "export_lobechat_prompt.py"
VENV_PY = BACKEND / ".venv312" / "bin" / "python"


def _python() -> str:
    if VENV_PY.is_file():
        return str(VENV_PY)
    return sys.executable


class TestConstants:
    def test_default_prompt_mentions_hitl_and_lgpd(self) -> None:
        text = CARTORIO_DEFAULT_SYSTEM_PROMPT.upper()
        assert "HITL" in text
        assert "LGPD" in text
        assert (
            "CARTÓRIO" in CARTORIO_DEFAULT_SYSTEM_PROMPT
            or "Cartório" in CARTORIO_DEFAULT_SYSTEM_PROMPT
        )

    def test_default_prompt_has_no_literal_secrets(self) -> None:
        low = CARTORIO_DEFAULT_SYSTEM_PROMPT.lower()
        for bad in ("sk-", "api_key=", "password=", "bearer "):
            assert bad not in low

    def test_package_version_semver(self) -> None:
        parts = PACKAGE_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_candidates_include_openclaw_and_lobechat(self) -> None:
        joined = " ".join(DEFAULT_SOURCE_CANDIDATES)
        assert "SOUL.md" in joined
        assert "lobechat" in joined
        assert "docs/" in joined or any(c.startswith("docs/") for c in DEFAULT_SOURCE_CANDIDATES)
        assert any(c.startswith(".agents") for c in DEFAULT_SOURCE_CANDIDATES)


class TestShaAndRedact:
    def test_sha256_text_matches_hashlib(self) -> None:
        sample = "olá cartório\n"
        assert sha256_text(sample) == hashlib.sha256(sample.encode("utf-8")).hexdigest()

    def test_redact_secrets_masks_api_key(self) -> None:
        raw = "api_key=sk-abcdefghijklmnopqrstuvwxyz123456"
        out = redact_secrets(raw)
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in out
        assert "REDACTED" in out


class TestFindRepoRoot:
    def test_finds_cartorio_root(self) -> None:
        root = find_repo_root(BACKEND)
        assert (root / "backend").is_dir()
        assert (root / "infra").is_dir() or (root / "SUPER_PLANO_G8_100_TASKS.md").is_file()


class TestLoadSystemPrompt:
    def test_loads_soul_or_import_when_present(self) -> None:
        load = load_system_prompt(repo_root=REPO, allow_embedded=True)
        assert load.text.strip()
        assert load.sha256 == sha256_text(load.text)
        assert load.char_count > 50
        assert load.source_kind in {"file", "json_systemRole", "embedded"}

    def test_preferred_md_source(self, tmp_path: Path) -> None:
        src = tmp_path / "custom_prompt.md"
        body = "# Custom\nHITL obrigatório.\nLGPD: sem CPF no LLM.\n"
        src.write_text(body, encoding="utf-8")
        load = load_system_prompt(repo_root=REPO, preferred_source=src)
        assert "HITL" in load.text
        assert load.source_kind == "file"
        assert load.sha256 == sha256_text(load.text)

    def test_preferred_json_system_role(self, tmp_path: Path) -> None:
        src = tmp_path / "agent.json"
        payload = {
            "schemaVersion": 1,
            "agents": [
                {
                    "identifier": "test",
                    "systemRole": "Você é bot de teste.\nHITL e LGPD.\n",
                }
            ],
        }
        src.write_text(json.dumps(payload), encoding="utf-8")
        load = load_system_prompt(repo_root=REPO, preferred_source=src)
        assert "bot de teste" in load.text
        assert load.source_kind == "json_systemRole"

    def test_embedded_when_no_sources(self, tmp_path: Path) -> None:
        # repo vazio isolado
        load = load_system_prompt(repo_root=tmp_path, allow_embedded=True)
        assert load.source_kind == "embedded"
        assert load.source == "embedded:CARTORIO_DEFAULT_SYSTEM_PROMPT"
        assert "HITL" in load.text
        assert "LGPD" in load.text

    def test_raises_when_no_source_and_no_embedded(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_system_prompt(repo_root=tmp_path, allow_embedded=False)

    def test_preferred_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_system_prompt(
                repo_root=REPO,
                preferred_source=tmp_path / "does-not-exist.md",
            )


class TestExportPackage:
    def test_writes_prompt_and_metadata(self, tmp_path: Path) -> None:
        out = tmp_path / "pkg"
        result = export_package(out, repo_root=REPO, allow_embedded=True)
        assert result["ok"] is True
        prompt_path = Path(result["prompt_path"])
        meta_path = Path(result["metadata_path"])
        assert prompt_path.name == PROMPT_FILENAME
        assert meta_path.name == METADATA_FILENAME
        assert prompt_path.is_file()
        assert meta_path.is_file()

        body = prompt_path.read_text(encoding="utf-8")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["prompt_sha256"] == sha256_text(body)
        assert meta["package_version"] == PACKAGE_VERSION
        assert meta["exporter_version"] == EXPORTER_VERSION
        assert meta["contains_secrets"] is False
        assert meta["hitl_required"] is True
        assert meta["lgpd_safe_export"] is True
        assert "source" in meta
        # no secret *values* / banned key names (contains_secrets flag is OK)
        banned_exact = {"api_key", "apikey", "token", "password", "secret", "authorization"}
        for k in meta:
            assert k.lower() not in banned_exact
        assert "sk-" not in json.dumps(meta).lower()

    def test_export_from_preferred_source(self, tmp_path: Path) -> None:
        src = tmp_path / "p.md"
        src.write_text("Prompt X\nHITL\nLGPD\n", encoding="utf-8")
        out = tmp_path / "out"
        result = export_package(out, preferred_source=src, repo_root=REPO)
        assert result["source_kind"] == "file"
        assert "Prompt X" in Path(result["prompt_path"]).read_text(encoding="utf-8")


class TestBuildMetadata:
    def test_strips_banned_extra_keys(self, tmp_path: Path) -> None:
        load = load_system_prompt(repo_root=tmp_path, allow_embedded=True)
        meta = build_metadata(
            load,
            extra={
                "api_key": "should-not-appear",
                "note": "ok",
                "OPENAI_TOKEN": "nope",
            },
        )
        assert "api_key" not in meta
        assert "OPENAI_TOKEN" not in meta
        assert meta["note"] == "ok"


class TestListCandidates:
    def test_list_on_real_repo(self) -> None:
        paths = list_candidate_sources(REPO)
        # Real repo should have at least SOUL.md or agent import
        assert isinstance(paths, list)
        if paths:
            assert all(p.is_file() for p in paths)


class TestCLI:
    def test_script_exists(self) -> None:
        assert SCRIPT.is_file()

    def test_cli_list_sources_json(self) -> None:
        proc = subprocess.run(
            [_python(), str(SCRIPT), "--list-sources", "--json"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"},
            check=False,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)
        assert "repo_root" in data
        assert "candidates" in data

    def test_cli_embedded_only_export(self, tmp_path: Path) -> None:
        out = tmp_path / "cli-out"
        proc = subprocess.run(
            [_python(), str(SCRIPT), "--embedded-only", "--out", str(out), "--json"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"},
            check=False,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        data = json.loads(proc.stdout)
        assert data["ok"] is True
        assert (out / PROMPT_FILENAME).is_file()
        assert (out / METADATA_FILENAME).is_file()
        body = (out / PROMPT_FILENAME).read_text(encoding="utf-8")
        assert "HITL" in body
        assert "LGPD" in body
        meta = json.loads((out / METADATA_FILENAME).read_text(encoding="utf-8"))
        assert meta["prompt_sha256"] == sha256_text(body)

    def test_cli_version(self) -> None:
        proc = subprocess.run(
            [_python(), str(SCRIPT), "--version"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            env={k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"},
            check=False,
            timeout=15,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == PACKAGE_VERSION
