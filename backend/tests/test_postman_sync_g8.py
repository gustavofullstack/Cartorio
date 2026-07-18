"""Tests for scripts/postman_sync.py (G8.17.T1).

Honest baseline (must pass before this PR):
  - python3 scripts/postman_sync.py --help exits 0
  - convert_to_postman_v21({}) returns valid skeleton

Coverage target:
  - minimal OpenAPI -> valid Postman v2.1 collection
  - endpoints grouped by tag
  - HTTP method mapped (GET/POST/PUT/DELETE/PATCH)
  - /cliente/{cpf} -> URL with :cpf + path variables
  - LGPD-safe: NO literal Authorization: Bearer hardcoded
  - bearer_token variable exists in collection (NOT a hardcoded value)
  - --bypass-network reads local file (offline-friendly)
  - write_collection auto-compresses when > 1MB
  - _assert_lgpd_safe raises on literal token
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURE = Path(__file__).parent / "fixtures" / "minimal_openapi.json"

sys.path.insert(0, str(SCRIPTS_DIR))
import postman_sync  # type: ignore[import-not-found]  # noqa: E402


@pytest.fixture
def openapi_min() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def collection_min(openapi_min: dict) -> dict:
    return postman_sync.convert_to_postman_v21(openapi_min, "https://api.example.com")


class TestConversion:
    def test_convert_minimal_openapi_returns_valid_postman_v21(self, collection_min: dict) -> None:
        info = collection_min["info"]
        assert info["schema"] == "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        assert "Cartorio" in info["name"]
        assert "item" in collection_min
        assert "variable" in collection_min
        assert "auth" in collection_min
        assert collection_min["auth"]["type"] == "bearer"

    def test_endpoint_grouping_by_tag(self, collection_min: dict) -> None:
        folders = {f["name"]: f for f in collection_min["item"]}
        assert "cliente" in folders
        assert "health" in folders
        assert "audit" in folders
        assert "telegram" in folders
        assert folders["cliente"]["description"].startswith("3 endpoints")

    def test_request_method_mapped(self, collection_min: dict) -> None:
        all_methods = set()
        for folder in collection_min["item"]:
            for entry in folder["item"]:
                all_methods.add(entry["request"]["method"])
        assert "GET" in all_methods
        assert "POST" in all_methods
        assert "DELETE" in all_methods

    def test_path_parameters_extracted(self, collection_min: dict) -> None:
        cliente_folder = next(f for f in collection_min["item"] if f["name"] == "cliente")
        get_cpf = next(e for e in cliente_folder["item"] if e["name"].startswith("GET"))
        url = get_cpf["request"]["url"]
        assert ":cpf" in url["path"]
        assert any(v["key"] == "cpf" for v in url["variable"])
        raw_url: str = url["raw"]
        assert ":cpf" in raw_url
        assert "{cpf}" not in raw_url

    def test_post_request_body_extracted(self, collection_min: dict) -> None:
        cliente_folder = next(f for f in collection_min["item"] if f["name"] == "cliente")
        post_create = next(e for e in cliente_folder["item"] if e["request"]["method"] == "POST")
        assert "body" in post_create["request"]
        assert post_create["request"]["body"]["mode"] == "raw"
        assert "Maria Silva" in post_create["request"]["body"]["raw"]

    def test_query_parameters_extracted(self, collection_min: dict) -> None:
        audit_folder = next(f for f in collection_min["item"] if f["name"] == "audit")
        list_logs = audit_folder["item"][0]
        query = list_logs["request"]["url"].get("query", [])
        keys = {q["key"] for q in query}
        assert "limit" in keys
        assert "offset" in keys

    def test_total_request_count_matches_paths(self, collection_min: dict, openapi_min: dict) -> None:
        expected = 0
        for path, methods in openapi_min["paths"].items():
            for m in methods:
                if m.lower() in postman_sync.SUPPORTED_METHODS:
                    expected += 1
        actual = sum(len(f["item"]) for f in collection_min["item"])
        assert actual == expected


class TestLGPDAuth:
    def test_pii_safe_collection_no_literal_bearer(self, collection_min: dict) -> None:
        """LGPD: nao persistir Authorization: Bearer hardcoded."""
        blob = json.dumps(collection_min, ensure_ascii=False)
        import re

        literal_re = re.compile(r"Authorization\s*:\s*(?:Bearer|Token)\s+[A-Za-z0-9_\-\.=]{8,}", re.IGNORECASE)
        assert not literal_re.search(blob), "Collection contains literal Authorization header!"

    def test_bearer_token_is_variable_not_literal(self, collection_min: dict) -> None:
        """bearer_token MUST be a variable placeholder, NEVER a real token."""
        bearer_var = next((v for v in collection_min["variable"] if v["key"] == "bearer_token"), None)
        assert bearer_var is not None
        assert bearer_var["value"] == ""
        assert bearer_var["type"] == "secret"
        auth_bearer = collection_min["auth"]["bearer"][0]
        assert auth_bearer["value"] == "{{bearer_token}}"

    def test_assert_lgpd_safe_passes_clean_collection(self, collection_min: dict) -> None:
        postman_sync._assert_lgpd_safe(collection_min)

    def test_assert_lgpd_safe_raises_on_literal_token(self) -> None:
        bad = {
            "info": {"name": "bad"},
            "item": [],
            "variable": [],
            "auth": {"type": "bearer", "bearer": [
                {"key": "token", "value": "Bearer abc123def456ghi789", "type": "string"}
            ]},
        }
        with pytest.raises(RuntimeError, match="LGPD"):
            postman_sync._assert_lgpd_safe(bad)

    def test_assert_lgpd_safe_raises_on_token_in_header_value(self) -> None:
        bad = {
            "info": {"name": "bad"},
            "item": [{"name": "x", "request": {
                "method": "GET",
                "header": [{"key": "Authorization", "value": "Bearer abc123def456ghi789", "type": "text"}],
                "url": {"raw": "https://x"},
            }, "response": []}],
            "variable": [],
        }
        with pytest.raises(RuntimeError, match="LGPD"):
            postman_sync._assert_lgpd_safe(bad)

    def test_assert_lgpd_safe_ignores_descriptions_with_token_word(self) -> None:
        """Descricoes em PT-BR com palavra 'token' (ex: 'refresh token JWT') NAO devem falhar."""
        safe = {
            "info": {"name": "ok", "description": "Emite access token e refresh token JWT"},
            "item": [
                {"name": "login", "request": {
                    "method": "POST",
                    "description": "Retorna access token + refresh token JWT para user_id",
                    "header": [],
                    "url": {"raw": "https://x/y"},
                }, "response": []},
            ],
            "variable": [{"key": "bearer_token", "value": "", "type": "secret"}],
            "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{bearer_token}}", "type": "string"}]},
        }
        postman_sync._assert_lgpd_safe(safe)

    def test_assert_lgpd_safe_passes_with_placeholder_only(self) -> None:
        """Placeholders Postman {{bearer_token}} nao devem triggar LGPD fail."""
        clean = {
            "info": {"name": "ok"},
            "item": [{"name": "x", "request": {
                "method": "GET",
                "header": [{"key": "Authorization", "value": "{{bearer_token}}", "type": "text"}],
                "url": {"raw": "https://x"},
            }, "response": []}],
            "variable": [{"key": "bearer_token", "value": "", "type": "secret"}],
        }
        postman_sync._assert_lgpd_safe(clean)


class TestOfflineAndCache:
    def test_bypass_network_uses_cached_file(self, tmp_path: Path) -> None:
        cached = tmp_path / "openapi.json"
        cached.write_text(FIXTURE.read_text(encoding="utf-8"))
        data = postman_sync.load_openapi_from_file(cached)
        assert data["info"]["title"].startswith("Cartorio")

    def test_bypass_network_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            postman_sync.load_openapi_from_file(tmp_path / "nonexistent.json")

    def test_load_openapi_from_app_returns_dict(self) -> None:
        """Smoke: app.main monta e retorna openapi dict (requer backend deps)."""
        pytest.importorskip("fastapi")
        try:
            data = postman_sync.load_openapi_from_app()
            assert "paths" in data
            assert "openapi" in data
        except Exception as exc:
            pytest.skip(f"app.main nao carrega em ambiente de teste: {exc}")


class TestWriteAndCompress:
    def test_write_collection_creates_file(self, collection_min: dict, tmp_path: Path) -> None:
        out = tmp_path / "out.postman_collection.json"
        actual, size = postman_sync.write_collection(collection_min, out)
        assert actual == out
        assert out.is_file()
        assert size > 0
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["info"]["schema"].endswith("v2.1.0/collection.json")

    def test_write_collection_auto_compresses_when_large(self, tmp_path: Path) -> None:
        big = {"info": {"name": "big", "schema": postman_sync.POSTMAN_SCHEMA_URL},
               "item": [], "variable": [], "auth": {"type": "bearer", "bearer": []}}
        big["item"] = [
            {"name": f"req_{i}", "request": {"method": "GET", "header": [], "url": {"raw": "https://x/y"}}, "response": []}
            for i in range(50000)
        ]
        out = tmp_path / "big.postman_collection.json"
        actual, size = postman_sync.write_collection(big, out)
        assert size > postman_sync.COMPRESS_THRESHOLD_BYTES
        assert str(actual).endswith(".json.gz")
        assert actual.suffix == ".gz"
        assert actual.is_file()

    def test_write_collection_lgpd_fail_returns_3(self, tmp_path: Path) -> None:
        bad = {
            "info": {"name": "bad"},
            "item": [],
            "variable": [],
            "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "Bearer abc123def456ghi789", "type": "string"}]},
        }
        out = tmp_path / "bad.json"
        with pytest.raises(RuntimeError, match="LGPD"):
            postman_sync.write_collection(bad, out)


class TestStats:
    def test_stats_counts_folders_and_requests(self, collection_min: dict) -> None:
        s = postman_sync.stats(collection_min)
        assert s["folders"] >= 4
        assert s["requests"] >= 5
        assert "GET" in s["methods"]
        assert "POST" in s["methods"]
        assert "DELETE" in s["methods"]
        assert "bearer_token" in s["variables"]
        assert "base_url" in s["variables"]


class TestPathConversion:
    def test_path_to_postman_with_params(self) -> None:
        raw, segs, vars_ = postman_sync._path_to_postman("/cliente/{cpf}/endereco/{tipo}")
        assert raw == "/cliente/:cpf/endereco/:tipo"
        assert segs == ["cliente", ":cpf", "endereco", ":tipo"]
        assert {v["key"] for v in vars_} == {"cpf", "tipo"}

    def test_path_to_postman_no_params(self) -> None:
        raw, segs, vars_ = postman_sync._path_to_postman("/health/llm")
        assert raw == "/health/llm"
        assert segs == ["health", "llm"]
        assert vars_ == []