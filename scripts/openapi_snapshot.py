"""OpenAPI Snapshot generator + diff (G6.A.T3).

Gera snapshot da OpenAPI spec em JSON, compara com baseline, e falha CI
se houver diff (endpoint removido/alterado sem bump de versao).

Uso:
    python3 scripts/openapi_snapshot.py                    # gera snapshot
    python3 scripts/openapi_snapshot.py --check            # compara com baseline
    python3 scripts/openapi_snapshot.py --update           # atualiza baseline
    python3 scripts/openapi_snapshot.py --report snap.md  # gera report markdown

Exit codes:
    0 = snapshot gerado ou sem diff
    1 = diff detectado (--check) ou endpoint quebrado
    2 = erro pre-requisito (FastAPI nao disponivel, baseline ausente)

Storage:
    snapshots/openapi.baseline.json (committed)
    snapshots/openapi.current.json (gitignored, regenerated)

Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 6.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SNAPSHOT_DIR = Path("snapshots")
BASELINE = SNAPSHOT_DIR / "openapi.baseline.json"
CURRENT = SNAPSHOT_DIR / "openapi.current.json"
HTTP_METHODS = frozenset({"delete", "get", "head", "options", "patch", "post", "put", "trace"})


@dataclass
class SemanticDiff:
    """Mudancas OpenAPI classificadas pelo impacto para consumidores."""

    added_paths: list[str] = field(default_factory=list)
    removed_paths: list[str] = field(default_factory=list)
    removed_operations: list[str] = field(default_factory=list)
    changed_parameters: list[str] = field(default_factory=list)
    changed_request_bodies: list[str] = field(default_factory=list)
    removed_success_responses: list[str] = field(default_factory=list)
    changed_security: list[str] = field(default_factory=list)

    @property
    def breaking(self) -> list[str]:
        return (
            self.removed_paths
            + self.removed_operations
            + self.changed_parameters
            + self.changed_request_bodies
            + self.removed_success_responses
            + self.changed_security
        )


def get_openapi_spec() -> dict:
    """Importa app.main e extrai OpenAPI schema."""
    import os
    print("Generating OpenAPI spec from app.main:app ...", file=sys.stderr)
    env = os.environ.copy()
    env.setdefault("APP_ENV", "development")
    cwd = "backend" if os.path.exists("backend") else "."
    result = subprocess.run(
        [
            "uv", "run", "python", "-c",
            "from app.main import app; import json; "
            "print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print(f"[ERROR] Failed to import app.main: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return json.loads(result.stdout)


def save_snapshot(spec: dict, path: Path) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True))


def _resolve_local_ref(document: dict[str, Any], ref: str) -> bool:
    """Confirma que um JSON Pointer local existe no documento OpenAPI."""
    if not ref.startswith("#/"):
        return False
    value: Any = document
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or token not in value:
            return False
        value = value[token]
    return True


def validate_internal_refs(document: dict[str, Any], *, label: str) -> list[str]:
    """Lista refs OpenAPI invalidos sem buscar documentos externos."""
    problems: list[str] = []

    def walk(value: Any, location: str) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and not _resolve_local_ref(document, ref):
                problems.append(f"{label}:{location} -> {ref}")
            for key, child in value.items():
                walk(child, f"{location}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{location}/{index}")

    walk(document, "$")
    return problems


def _operation_parameters(operation: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(parameter.get("in", "")), str(parameter.get("name", ""))): parameter
        for parameter in operation.get("parameters", [])
        if isinstance(parameter, dict)
    }


def _effective_security(document: dict[str, Any], operation: dict[str, Any]) -> Any:
    if "security" in operation:
        return operation["security"]
    return document.get("security", [])


def semantic_diff(baseline: dict[str, Any], current: dict[str, Any]) -> SemanticDiff:
    """Detecta somente regressao de contrato, ignorando documentacao cosmetica."""
    base_paths = set(baseline.get("paths", {}).keys())
    curr_paths = set(current.get("paths", {}).keys())
    result = SemanticDiff(
        added_paths=sorted(curr_paths - base_paths),
        removed_paths=[f"path removed: {path}" for path in sorted(base_paths - curr_paths)],
    )
    base_schemes = baseline.get("components", {}).get("securitySchemes", {})
    curr_schemes = current.get("components", {}).get("securitySchemes", {})
    for name, base_scheme in base_schemes.items():
        current_scheme = curr_schemes.get(name)
        critical = ("type", "scheme", "in", "name", "bearerFormat", "flows")
        if not isinstance(current_scheme, dict) or any(
            base_scheme.get(key) != current_scheme.get(key) for key in critical
        ):
            result.changed_security.append(f"security scheme changed: {name}")

    for path in sorted(base_paths & curr_paths):
        base_operations = baseline["paths"][path]
        current_operations = current["paths"][path]
        for method, base_operation in base_operations.items():
            if method not in HTTP_METHODS or not isinstance(base_operation, dict):
                continue
            current_operation = current_operations.get(method)
            operation_id = f"{method.upper()} {path}"
            if not isinstance(current_operation, dict):
                result.removed_operations.append(f"operation removed: {operation_id}")
                continue
            if _effective_security(baseline, base_operation) != _effective_security(
                current, current_operation
            ):
                result.changed_security.append(f"operation security changed: {operation_id}")
            base_parameters = _operation_parameters(base_operation)
            current_parameters = _operation_parameters(current_operation)
            for parameter_key, base_parameter in base_parameters.items():
                current_parameter = current_parameters.get(parameter_key)
                if current_parameter is None:
                    result.changed_parameters.append(
                        f"parameter removed: {operation_id} {parameter_key[0]} {parameter_key[1]}"
                    )
                elif not base_parameter.get("required", False) and current_parameter.get("required", False):
                    result.changed_parameters.append(
                        f"parameter became required: {operation_id} {parameter_key[0]} {parameter_key[1]}"
                    )
            base_body = base_operation.get("requestBody")
            current_body = current_operation.get("requestBody")
            if isinstance(base_body, dict) and current_body is None:
                result.changed_request_bodies.append(f"request body removed: {operation_id}")
            elif (
                isinstance(base_body, dict)
                and isinstance(current_body, dict)
                and not base_body.get("required", False)
                and current_body.get("required", False)
            ):
                result.changed_request_bodies.append(f"request body became required: {operation_id}")
            base_success = {code for code in base_operation.get("responses", {}) if str(code).startswith("2")}
            current_success = {
                code for code in current_operation.get("responses", {}) if str(code).startswith("2")
            }
            for code in sorted(base_success - current_success):
                result.removed_success_responses.append(
                    f"success response removed: {operation_id} {code}"
                )
    return result


def render_markdown(diff: SemanticDiff, current: dict[str, Any]) -> str:
    md: list[str] = []
    md.append("# OpenAPI Snapshot Report")
    md.append("")
    md.append(f"**Data**: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"**Total paths no current**: {len(current.get('paths', {}))}")
    md.append("")
    md.append("## Diff vs baseline")
    md.append("")
    md.append(f"- **Paths adicionados**: {len(diff.added_paths)}")
    md.append(f"- **Quebras detectadas**: {len(diff.breaking)}")
    md.append("")
    if diff.added_paths:
        md.append("### Adicionados (novos endpoints)")
        md.append("")
        for p in diff.added_paths:
            methods = ", ".join(current["paths"][p].keys())
            md.append(f"- `{p}` ({methods})")
        md.append("")
    if diff.breaking:
        md.append("### Quebras de contrato")
        md.append("")
        for item in diff.breaking:
            md.append(f"- `{item}`")
        md.append("")
    md.append("---")
    md.append("")
    md.append("**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 6 (auto-gerado)**")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAPI snapshot generator")
    parser.add_argument("--check", action="store_true", help="comparar com baseline e exit 1 se diff")
    parser.add_argument("--update", action="store_true", help="atualizar baseline com current")
    parser.add_argument("--report", type=Path, help="gerar report markdown")
    args = parser.parse_args()

    spec = get_openapi_spec()
    save_snapshot(spec, CURRENT)
    print(f"Snapshot salvo: {CURRENT} ({len(spec.get('paths', {}))} paths)", file=sys.stderr)

    if args.update:
        save_snapshot(spec, BASELINE)
        print(f"Baseline atualizado: {BASELINE}")
        return 0

    if args.check:
        if not BASELINE.exists():
            print(f"[ERROR] Baseline nao existe: {BASELINE}", file=sys.stderr)
            print(f"  Rode: python3 scripts/openapi_snapshot.py --update", file=sys.stderr)
            return 2
        baseline = json.loads(BASELINE.read_text())
        invalid_refs = validate_internal_refs(baseline, label="baseline") + validate_internal_refs(
            spec, label="current"
        )
        if invalid_refs:
            print(f"[ERROR] {len(invalid_refs)} refs OpenAPI invalidos")
            for problem in invalid_refs[:10]:
                print(f"  - {problem}")
            return 2
        diff = semantic_diff(baseline, spec)
        if diff.added_paths:
            print(f"[WORK] {len(diff.added_paths)} paths adicionados (non-breaking)")
        if args.report:
            args.report.write_text(render_markdown(diff, spec))
        if diff.breaking:
            print(f"[HOLD] {len(diff.breaking)} quebras de contrato")
            for item in diff.breaking[:10]:
                print(f"  - {item}")
            return 1
        print("[WORK] Sem quebra de contrato vs baseline")
        return 0

    print(f"Gerado: {CURRENT}")
    print(f"Para comparar: --check")
    print(f"Para atualizar baseline: --update")
    return 0


if __name__ == "__main__":
    sys.exit(main())
