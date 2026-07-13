"""postman_export.py — Converte /openapi.json em Postman collection v2.1."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx


def openapi_to_postman(openapi: dict, base_url: str) -> dict:
    """Build a Postman v2.1 collection from an OpenAPI 3.x spec."""
    items: list[dict] = []
    paths = openapi.get("paths", {})
    for path, methods in paths.items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            op_id = op.get("operationId") or f"{method}_{path}"
            summary = op.get("summary") or op.get("description") or path
            url_path = path.replace("{", ":").replace("}", "")
            req: dict = {
                "method": method.upper(),
                "header": [],
                "url": {
                    "raw": f"{{{{base_url}}}}{url_path}",
                    "host": ["{{base_url}}"],
                    "path": url_path.strip("/").split("/"),
                },
                "description": summary,
            }
            # Body for POST/PUT/PATCH
            if method.lower() in {"post", "put", "patch"} and "requestBody" in op:
                content = op["requestBody"].get("content", {})
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    example = schema.get("example") or {}
                    if not example and "$ref" in schema:
                        ref_name = schema["$ref"].rsplit("/", 1)[-1]
                        example = openapi.get("components", {}).get("schemas", {}).get(ref_name, {}).get("example", {})
                    req["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(example, indent=2, ensure_ascii=False) if example else "",
                        "options": {"raw": {"language": "json"}},
                    }
            items.append({
                "name": op_id,
                "request": req,
                "response": [],
            })
    return {
        "info": {
            "name": "Cartório 2º Notas API",
            "description": "Backend API for 2º Serviço Notarial de Uberlândia. Generated from /openapi.json",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": openapi.get("info", {}).get("version", "1.0.0"),
        },
        "item": items,
        "variable": [
            {"key": "base_url", "value": base_url, "type": "string"},
        ],
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{api_token}}", "type": "string"}],
        },
    }


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else "https://api.2notasudi.com.br/openapi.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/POSTMAN_COLLECTION.json")
    base_url = sys.argv[3] if len(sys.argv) > 3 else "api.2notasudi.com.br"

    print(f"Fetching OpenAPI from {src}...")
    r = httpx.get(src, timeout=15)
    r.raise_for_status()
    openapi = r.json()
    paths_count = len(openapi.get("paths", {}))
    print(f"  paths: {paths_count}")

    collection = openapi_to_postman(openapi, base_url)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  items: {len(collection['item'])}")
    print(f"SAVED -> {out}")


if __name__ == "__main__":
    main()