"""postman_export.py — Converte OpenAPI em Postman collection v2.1 (G7.17.T1).

Uso:
  python3 scripts/postman_export.py
  python3 scripts/postman_export.py --from-app          # gera via app.main (local)
  python3 scripts/postman_export.py --src URL|path.json
  python3 scripts/postman_export.py --out docs/postman_collection.generated.json

Auth: X-API-Key ({{cartorio_api_key}}) — alinhado à API real (não bearer genérico).
Evita double-prefix /api/v1/api/v1/ (base_url sem path; paths OpenAPI absolutos).

Modified by Gustavo Almeida — G7 Wave 17.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def openapi_to_postman(openapi: dict, base_url: str) -> dict:
    """Build a Postman v2.1 collection from an OpenAPI 3.x spec."""
    # base_url must be origin only, e.g. https://api.2notasudi.com.br
    base_url = base_url.rstrip("/")
    if base_url.startswith("http"):
        host_display = base_url
    else:
        host_display = f"https://{base_url}"
        base_url = host_display

    items: list[dict] = []
    paths = openapi.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not isinstance(op, dict):
                continue
            op_id = op.get("operationId") or f"{method}_{path}"
            summary = op.get("summary") or op.get("description") or path
            # Keep OpenAPI path as-is under base_url (no double /api/v1)
            raw = f"{base_url}{path}".replace("{", ":").replace("}", "")
            # Postman path segments without leading empty
            segs = [
                s.replace("{", ":").replace("}", "")
                for s in path.strip("/").split("/")
                if s
            ]
            req: dict = {
                "method": method.upper(),
                "header": [
                    {
                        "key": "X-API-Key",
                        "value": "{{cartorio_api_key}}",
                        "type": "text",
                    },
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text",
                    },
                ],
                "url": {
                    "raw": raw,
                    "protocol": "https",
                    "host": base_url.replace("https://", "")
                    .replace("http://", "")
                    .split("/"),
                    "path": segs,
                },
                "description": summary
                if isinstance(summary, str)
                else str(summary)[:500],
            }
            if method.lower() in {"post", "put", "patch"} and "requestBody" in op:
                content = op["requestBody"].get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    example = schema.get("example") or {}
                    if not example and "$ref" in schema:
                        ref_name = schema["$ref"].rsplit("/", 1)[-1]
                        example = (
                            openapi.get("components", {})
                            .get("schemas", {})
                            .get(ref_name, {})
                            .get("example", {})
                        )
                    req["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(example, indent=2, ensure_ascii=False)
                        if example
                        else "{}",
                        "options": {"raw": {"language": "json"}},
                    }
            items.append({"name": str(op_id)[:120], "request": req, "response": []})

    return {
        "info": {
            "name": "Cartório 2º Notas API (generated)",
            "description": (
                "Generated from OpenAPI. Use variable cartorio_api_key. "
                "Do not prefix paths with /api/v1 twice."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": openapi.get("info", {}).get("version", "0.6.0"),
        },
        "item": items,
        "variable": [
            {"key": "base_url", "value": base_url, "type": "string"},
            {"key": "cartorio_api_key", "value": "", "type": "string"},
        ],
        "auth": {
            "type": "apikey",
            "apikey": [
                {"key": "key", "value": "X-API-Key", "type": "string"},
                {"key": "value", "value": "{{cartorio_api_key}}", "type": "string"},
                {"key": "in", "value": "header", "type": "string"},
            ],
        },
    }


def load_openapi(src: str, from_app: bool) -> dict:
    if from_app:
        sys.path.insert(0, str(ROOT / "backend"))
        from app.main import app  # type: ignore

        return app.openapi()
    path = Path(src)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    import httpx

    print(f"Fetching OpenAPI from {src}...")
    r = httpx.get(src, timeout=20.0, verify=True)
    r.raise_for_status()
    return r.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAPI → Postman v2.1 (G7.17.T1)")
    parser.add_argument(
        "--src",
        default="https://api.2notasudi.com.br/openapi.json",
        help="URL or local openapi.json path",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "postman_collection.generated.json",
    )
    parser.add_argument(
        "--base-url",
        default="https://api.2notasudi.com.br",
        help="Origin only (no /api/v1 suffix)",
    )
    parser.add_argument(
        "--from-app",
        action="store_true",
        help="Build OpenAPI from local app.main (no network)",
    )
    args = parser.parse_args()

    try:
        openapi = load_openapi(args.src, args.from_app)
    except Exception as exc:
        print(f"[ERROR] load openapi: {exc}", file=sys.stderr)
        return 2

    paths_count = len(openapi.get("paths", {}))
    collection = openapi_to_postman(openapi, args.base_url)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # Sanity: no double prefix
    blob = args.out.read_text(encoding="utf-8")
    if "/api/v1/api/v1/" in blob:
        print("[FAIL] generated collection still has double /api/v1/", file=sys.stderr)
        return 1
    print(f"  paths: {paths_count}")
    print(f"  items: {len(collection['item'])}")
    print(f"SAVED -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
