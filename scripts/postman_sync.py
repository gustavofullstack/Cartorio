"""postman_sync.py — Regenera e sincroniza Postman Collection v2.1 a partir do OpenAPI.

Diferencas vs scripts/postman_export.py (G7.17.T1):
  - Agrupamento por tag em folders (G7 export era flat)
  - LGPD-safe: bearer token via {{bearer_token}} variable, NUNCA hardcoded
  - Path params convertidos :param (Postman convention) com path variables
  - Cache local de OpenAPI (TTL 5min) para evitar refetch em CI
  - Compressao gzip automatica quando output > 1MB
  - --from-app (carrega de app.main sem network) para CI/dev
  - --bypass-network (le cached openapi.json) para offline run
  - Stats: folders / requests / methods breakdown

Uso:
  # Dev (com app rodando na 8000):
  python3 scripts/postman_sync.py --output infra/postman/cartorio-api.postman_collection.json

  # CI (sem network, do codigo):
  cd backend && uv run python ../scripts/postman_sync.py --from-app \\
      --output ../infra/postman/cartorio-api.postman_collection.json

  # Offline (cached):
  python3 scripts/postman_sync.py --bypass-network \\
      --cached-openapi backend/docs/openapi.json \\
      --output infra/postman/cartorio-api.postman_collection.json

LGPD: Authorization SEMPRE via {{bearer_token}} variable. NUNCA persistir token real.
HITL: Collection sincronizada auto; DEV escolhe environment/workspace ao executar.

Modified by Gustavo Almeida — G8.17.T1 (Wave 47).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENAPI_URL = "http://localhost:8000/openapi.json"
DEFAULT_BASE_URL = "https://api.2notasudi.com.br"
DEFAULT_OUTPUT = ROOT / "infra" / "postman" / "cartorio-api.postman_collection.json"
CACHE_DIR = Path(
    os.environ.get("POSTMAN_SYNC_CACHE", str(ROOT / ".cache" / "postman-sync"))
)
CACHE_TTL_SECONDS = 300
COMPRESS_THRESHOLD_BYTES = 1024 * 1024
SUPPORTED_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
POSTMAN_SCHEMA_URL = (
    "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
)

# LGPD: patterns que indicam token bearer LITERAL (NUNCA deve aparecer).
# 1) "Authorization: Bearer abc..." em header ou config
# 2) "Bearer <token>" cru dentro de um value de header/variavel
_BEARER_LITERAL_RE = re.compile(
    r"(?:Authorization\s*:\s*)?(?:Bearer|Token)\s+[A-Za-z0-9_\-\.=]{8,}",
    re.IGNORECASE,
)
# Excluir matches legitimos (placeholders Postman "{{bearer_token}}").
_PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")


def _now_ts() -> int:
    return int(time.time())


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def fetch_openapi(
    url: str, *, timeout: float = 10.0, use_cache: bool = True
) -> dict[str, Any]:
    """Fetch OpenAPI JSON. Honors CACHE_TTL_SECONDS via .cache/postman-sync/."""
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{_cache_key(url)}.json"
        if (
            cache_file.is_file()
            and (_now_ts() - int(cache_file.stat().st_mtime)) < CACHE_TTL_SECONDS
        ):
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cache_file.unlink(missing_ok=True)
    req = urllib.request.Request(
        url, headers={"User-Agent": "cartorio-postman-sync/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    payload = json.loads(data)
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{_cache_key(url)}.json"
        cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def load_openapi_from_app() -> dict[str, Any]:
    """Load OpenAPI schema from the live FastAPI app (no network)."""
    backend = ROOT / "backend"
    if not (backend / "app" / "main.py").is_file():
        raise RuntimeError(f"backend/app/main.py nao encontrado em {backend}")
    sys.path.insert(0, str(backend))
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
    os.environ.setdefault("APP_ENV", "development")
    from app.main import app  # type: ignore[import-not-found]

    return app.openapi()


def load_openapi_from_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"openapi cache nao encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _openapi_to_paths(paths: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Yield (path, method, op) for every HTTP operation."""
    out: list[tuple[str, str, dict[str, Any]]] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            if method.lower() not in SUPPORTED_METHODS:
                continue
            out.append((path, method.lower(), op))
    return out


def _path_to_postman(path: str) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Convert /cliente/{cpf} -> ('/cliente/:cpf', ['cliente', ':cpf'], [{key:'cpf',value:''}]).

    Returns raw_url_suffix, path_segments, path_variables.
    """
    segments: list[str] = []
    variables: list[dict[str, Any]] = []
    for seg in path.strip("/").split("/"):
        if not seg:
            continue
        if seg.startswith("{") and seg.endswith("}"):
            name = seg[1:-1]
            segments.append(f":{name}")
            variables.append({"key": name, "value": "", "type": "string"})
        else:
            segments.append(seg)
    return "/" + "/".join(segments), segments, variables


def _build_request_body(
    op: dict[str, Any], openapi: dict[str, Any]
) -> dict[str, Any] | None:
    """Extract request body from OpenAPI operation, returning Postman body or None."""
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return None
    content = rb.get("content", {})
    json_content = content.get("application/json")
    if not isinstance(json_content, dict):
        return None
    schema = json_content.get("schema", {})
    if not isinstance(schema, dict):
        return None
    example: Any = schema.get("example")
    if example is None and "$ref" in schema:
        ref_name = str(schema["$ref"]).rsplit("/", 1)[-1]
        example = (
            openapi.get("components", {})
            .get("schemas", {})
            .get(ref_name, {})
            .get("example")
        )
    if example is None:
        example = {}
    return {
        "mode": "raw",
        "raw": json.dumps(example, indent=2, ensure_ascii=False),
        "options": {"raw": {"language": "json"}},
    }


def _build_query_params(op: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract query parameters (non-path) from OpenAPI operation."""
    params = op.get("parameters") or []
    out: list[dict[str, Any]] = []
    for p in params:
        if not isinstance(p, dict):
            continue
        if p.get("in") != "query":
            continue
        name = p.get("name", "param")
        schema = p.get("schema") or {}
        out.append(
            {
                "key": name,
                "value": str(schema.get("example", schema.get("default", ""))),
                "type": "string",
                "description": p.get("description", "")[:200]
                if p.get("description")
                else "",
            }
        )
    return out


def build_request(
    path: str, method: str, op: dict[str, Any], openapi: dict[str, Any], base_url: str
) -> dict[str, Any]:
    """Build a single Postman v2.1 item (folder entry) from an OpenAPI operation."""
    raw_suffix, segments, path_vars = _path_to_postman(path)
    raw_url = f"{base_url.rstrip('/')}{raw_suffix}"
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0]
    op_id = op.get("operationId") or f"{method.upper()}_{path}"
    name = f"{method.upper()} {path}"[:120]
    description_parts: list[str] = []
    if op.get("summary"):
        description_parts.append(str(op["summary"]))
    if op.get("description"):
        description_parts.append(str(op["description"]))
    description_parts.append(f"operationId: {op_id}")

    headers: list[dict[str, str]] = [
        {"key": "Accept", "value": "application/json", "type": "text"},
        {"key": "X-API-Key", "value": "{{cartorio_api_key}}", "type": "text"},
    ]
    request: dict[str, Any] = {
        "method": method.upper(),
        "header": headers,
        "url": {
            "raw": raw_url,
            "protocol": "https",
            "host": [host],
            "path": segments,
            "variable": path_vars,
        },
        "description": "\n\n".join(description_parts)[:2000],
    }
    query_params = _build_query_params(op)
    if query_params:
        request["url"]["query"] = query_params
    body = _build_request_body(op, openapi)
    if body is not None:
        request["body"] = body
    return {"name": name, "request": request, "response": []}


def convert_to_postman_v21(openapi: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Convert OpenAPI dict to Postman Collection v2.1 dict, grouped by tag."""
    info = openapi.get("info", {})
    paths = openapi.get("paths", {})

    by_tag: dict[str, list[dict[str, Any]]] = {}
    method_counter: Counter[str] = Counter()
    seen_operations: set[tuple[str, str]] = set()
    for path, method, op in _openapi_to_paths(paths):
        # FastAPI can expose both a route and its trailing-slash compatibility
        # alias. Postman must execute each HTTP operation once; retain the
        # canonical no-trailing-slash form and omit the compatibility duplicate.
        canonical_path = path.rstrip("/") or "/"
        operation_key = (method, canonical_path)
        if operation_key in seen_operations:
            continue
        seen_operations.add(operation_key)
        method_counter[method.upper()] += 1
        tags = op.get("tags") or ["default"]
        tag = str(tags[0]) if tags else "default"
        by_tag.setdefault(tag, []).append(
            build_request(canonical_path, method, op, openapi, base_url)
        )

    folders: list[dict[str, Any]] = []
    for tag_name in sorted(by_tag.keys()):
        folders.append(
            {
                "name": tag_name,
                "description": f"{len(by_tag[tag_name])} endpoints (tag: {tag_name})",
                "item": by_tag[tag_name],
            }
        )

    collection: dict[str, Any] = {
        "info": {
            "name": f"{info.get('title', 'Cartorio API')} (sync)",
            "description": (
                f"{info.get('description', '')}\n\n"
                "Gerado por scripts/postman_sync.py (G8.17.T1). "
                "Authorization SEMPRE via {{bearer_token}} variable. "
                "NUNCA persistir tokens reais."
            ),
            "schema": POSTMAN_SCHEMA_URL,
            "version": info.get("version", "0.6.0"),
            "_postman_id": f"cartorio-sync-{int(time.time())}",
        },
        "item": folders,
        "variable": [
            {"key": "base_url", "value": base_url, "type": "string"},
            {"key": "bearer_token", "value": "", "type": "secret"},
            {"key": "cartorio_api_key", "value": "", "type": "secret"},
        ],
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{bearer_token}}", "type": "string"}],
        },
    }
    return collection


def _walk_request_headers(items: list[Any]) -> list[tuple[str, str]]:
    """Recursively walk items/folders and yield (path, header_value) for sensitive headers."""
    out: list[tuple[str, str]] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        if "item" in entry and isinstance(entry["item"], list):
            out.extend(_walk_request_headers(entry["item"]))
            continue
        req = entry.get("request", {})
        if not isinstance(req, dict):
            continue
        for i, h in enumerate(req.get("header", []) or []):
            if not isinstance(h, dict):
                continue
            key = str(h.get("key", "")).lower()
            if key == "authorization" or "token" in key:
                val = h.get("value", "")
                if isinstance(val, str):
                    out.append((f"request.header[{h.get('key', '?')}]", val))
    return out


def _assert_lgpd_safe(collection: dict[str, Any]) -> None:
    """Raise RuntimeError if collection contains literal Authorization bearer tokens.

    Audita apenas campos sensiveis (auth, variables, headers Authorization/*token*).
    Descricoes em portugues com palavra 'token' (ex: 'refresh token JWT') sao ignoradas.
    """
    sensitive_values: list[tuple[str, str]] = []

    auth = collection.get("auth") or {}
    if isinstance(auth, dict):
        bearer_list = auth.get("bearer")
        if isinstance(bearer_list, list):
            for i, v in enumerate(bearer_list):
                if isinstance(v, dict) and isinstance(v.get("value"), str):
                    sensitive_values.append((f"auth.bearer[{i}].value", v["value"]))
        apikey_list = auth.get("apikey")
        if isinstance(apikey_list, list):
            for i, v in enumerate(apikey_list):
                if isinstance(v, dict) and isinstance(v.get("value"), str):
                    sensitive_values.append((f"auth.apikey[{i}].value", v["value"]))
    for var in collection.get("variable", []) or []:
        if isinstance(var, dict) and isinstance(var.get("value"), str):
            sensitive_values.append(
                (f"variable[{var.get('key', '?')}].value", var["value"])
            )
    for path, val in _walk_request_headers(collection.get("item", []) or []):
        sensitive_values.append((path, val))

    for path, value in sensitive_values:
        sanitized = _PLACEHOLDER_RE.sub("", value)
        if _BEARER_LITERAL_RE.search(sanitized):
            raise RuntimeError(
                f"LGPD VIOLATION: literal Bearer/Token value at {path}: "
                f"{value[:50]}... Use {{{{bearer_token}}}} variable instead."
            )
        if (
            "bearer_token" in path
            and value
            and not value.startswith("{{")
            and len(value) > 8
        ):
            raise RuntimeError(
                f"LGPD VIOLATION: bearer_token variable has non-template value at {path}"
            )


def _maybe_compress(output: Path, collection_bytes: bytes) -> Path:
    """Compress with gzip if output > COMPRESS_THRESHOLD_BYTES."""
    if len(collection_bytes) <= COMPRESS_THRESHOLD_BYTES:
        return output
    gz_path = output.with_name(output.name + ".gz")
    gz_path.write_bytes(gzip.compress(collection_bytes))
    return gz_path


def write_collection(
    collection: dict[str, Any],
    output: Path,
    *,
    pretty: bool = True,
) -> tuple[Path, int]:
    """Write collection to disk; returns (actual_output_path, size_bytes)."""
    _assert_lgpd_safe(collection)
    output.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(
        collection, indent=2 if pretty else None, ensure_ascii=False
    ).encode("utf-8")
    output.write_bytes(blob)
    actual = _maybe_compress(output, blob)
    return actual, len(blob)


def stats(collection: dict[str, Any]) -> dict[str, Any]:
    """Return summary stats: folder count, request count, methods breakdown."""
    folders = collection.get("item", [])
    method_counter: Counter[str] = Counter()
    total = 0
    for folder in folders:
        for entry in folder.get("item", []):
            req = entry.get("request", {})
            method_counter[req.get("method", "?")] += 1
            total += 1
    return {
        "folders": len(folders),
        "requests": total,
        "methods": dict(method_counter),
        "variables": [v["key"] for v in collection.get("variable", [])],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Postman Collection v2.1 a partir de OpenAPI (G8.17.T1)",
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument(
        "--openapi-url",
        default=DEFAULT_OPENAPI_URL,
        help="URL do /openapi.json (default: localhost:8000)",
    )
    src.add_argument(
        "--from-app", action="store_true", help="Carrega de app.main (sem network)"
    )
    src.add_argument(
        "--bypass-network",
        action="store_true",
        help="Le arquivo cached (--cached-openapi)",
    )
    parser.add_argument(
        "--cached-openapi",
        type=Path,
        default=ROOT / "backend" / "docs" / "openapi.json",
        help="Path do openapi.json cached (usado com --bypass-network)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path do Postman collection JSON",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="Origin only (sem /api/v1)"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Desabilita cache de fetch"
    )
    parser.add_argument(
        "--no-compress", action="store_true", help="Nao comprimir mesmo se >1MB"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suprime output nao-essencial"
    )
    args = parser.parse_args()

    try:
        if args.from_app:
            if not args.quiet:
                print("[1/4] Carregando OpenAPI de app.main (no-network)...")
            openapi = load_openapi_from_app()
        elif args.bypass_network:
            if not args.quiet:
                print(f"[1/4] Lendo OpenAPI cached de {args.cached_openapi}...")
            openapi = load_openapi_from_file(args.cached_openapi)
        else:
            if not args.quiet:
                print(f"[1/4] Fetching OpenAPI de {args.openapi_url}...")
            openapi = fetch_openapi(args.openapi_url, use_cache=not args.no_cache)
    except Exception as exc:
        print(f"[ERROR] load openapi: {exc}", file=sys.stderr)
        return 2

    paths_count = len(openapi.get("paths", {}))
    if not args.quiet:
        print(f"[2/4] Convertendo {paths_count} paths para Postman v2.1...")
    collection = convert_to_postman_v21(openapi, args.base_url)
    s = stats(collection)

    try:
        if not args.quiet:
            print(f"[3/4] Escrevendo collection em {args.output}...")
        actual_path, size = write_collection(collection, args.output)
    except RuntimeError as exc:
        print(f"[LGPD FAIL] {exc}", file=sys.stderr)
        return 3

    if not args.quiet:
        print("[4/4] OK")
        print(f"  paths:      {paths_count}")
        print(f"  folders:    {s['folders']}")
        print(f"  requests:   {s['requests']}")
        print(f"  methods:    {s['methods']}")
        print(f"  variables:  {s['variables']}")
        print(f"  output:     {actual_path} ({size} bytes)")
        print(f"SAVED -> {actual_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
