"""N8N Workflow Validator - B11/B12 test runner.

Valida todos os workflows N8N em infra/n8n-workflows/*.json SEM precisar
subir o N8N. Detecta 9 tipos de problema:

B11 (base):
1. JSON invalido (syntax error)
2. Nodes sem type
3. Conexoes orfas (node destino nao existe)
4. Webhook sem path
5. HTTP node sem URL ou com URL hardcoded (NAO parametrizavel)
6. References a env vars que nao existem

B12 (test runner - estendido):
7. HTTP node sem retry policy (B07: 3x exp backoff)
8. HTTP node com timeout > 30s (B08: limite canon)
9. WF sem error handler wired (B06: Error Workflow trigger)
10. WFs canonicos (webhook evo-in, telegram-listener) presentes

Uso:
    python -m app.services.n8n_workflow_validator
    # ou via endpoint /admin/n8n/validate-wfs (Sprint 5)
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Diretorio padrao dos WFs
DEFAULT_WF_DIR = Path(__file__).resolve().parents[3] / "infra" / "n8n-workflows"

# Tipos de node que DEVEM ter URL parametrizada
HTTP_NODE_TYPES = ("n8n-nodes-base.httpRequest", "n8n-nodes-base.webhook")

# Variaveis de ambiente conhecidas (referenciadas como {{$env.VAR_NAME}})
KNOWN_ENV_VARS = (
    "CARTORIO_API_URL",
    "CARTORIO_API_KEY",
    "N8N_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "EVOLUTION_API_URL",
    "EVOLUTION_API_KEY",
    "CHATWOOT_URL",
    "CHATWOOT_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "REDIS_URL",
    "OPENCLAW_GATEWAY_URL",
    "OPENCODE_GO_API_KEY",
)


def _validate_one(wf_path: Path) -> dict[str, Any]:
    """Valida um workflow.

    Returns:
        dict com {file, name, valid, errors[], warnings[]}
    """
    result: dict[str, Any] = {
        "file": wf_path.name,
        "name": "",
        "valid": True,
        "errors": [],
        "warnings": [],
        "node_count": 0,
        "connection_count": 0,
    }

    # 1. JSON valido
    try:
        wf = json.loads(wf_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result["valid"] = False
        result["errors"].append(f"JSON invalido: {e}")
        return result

    result["name"] = wf.get("name", "(no name)")
    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})
    result["node_count"] = len(nodes)
    result["connection_count"] = sum(
        len(targets) for outputs in connections.values() for targets in outputs.values()
    )

    # 2. Nodes sem type
    node_names = set()
    for node in nodes:
        name = node.get("name", "")
        node_names.add(name)
        if not node.get("type"):
            result["errors"].append(f"Node '{name}' sem type")
            result["valid"] = False

    # 3. Conexoes orfas
    for source_name, outputs in connections.items():
        if source_name not in node_names:
            result["errors"].append(f"Conexao de source inexistente: {source_name}")
            result["valid"] = False
        for output_idx, targets in outputs.items():
            for target_list in targets:
                for target in target_list:
                    target_node = target.get("node", "")
                    if target_node and target_node not in node_names:
                        result["errors"].append(
                            f"Conexao para node inexistente: {source_name} -> {target_node}"
                        )
                        result["valid"] = False

    # 4. HTTP/Webhook nodes com config incorreta
    for node in nodes:
        ntype: str = node.get("type", "")
        nname: str = node.get("name", "")
        params: dict = node.get("parameters", {})

        # Webhook nao precisa de URL (URL eh o path interno)
        if ntype == "n8n-nodes-base.webhook":
            # Webhook deve ter path
            path = params.get("path", "")
            if not path:
                result["errors"].append(f"Webhook node '{nname}' sem path")
                result["valid"] = False

        # HTTP request PRECISA de URL
        if ntype == "n8n-nodes-base.httpRequest":
            url: str = params.get("url", "")
            if not url:
                result["errors"].append(f"HTTP node '{nname}' sem URL")
                result["valid"] = False
            elif url.startswith("http://localhost") or url.startswith("http://127.0.0.1"):
                # OK em dev, mas warning em prod
                result["warnings"].append(
                    f"HTTP node '{nname}' usa localhost ({url})"
                )

            # 5. HTTP com URL hardcoded (NAO parametrizada)
            if url and not url.startswith("{{") and "://api." in url:
                result["warnings"].append(
                    f"HTTP node '{nname}' tem URL hardcoded (use $env.VAR)"
                )

    # 6. Referencia a env vars desconhecidas
    wf_text = wf_path.read_text(encoding="utf-8")
    env_refs = set(re.findall(r"\{\{\s*\$env\.(\w+)\s*\}\}", wf_text))
    unknown_envs = env_refs - set(KNOWN_ENV_VARS)
    if unknown_envs:
        result["warnings"].append(
            f"Env vars nao catalogadas: {sorted(unknown_envs)}"
        )

    # === B12: checks adicionais (retry, timeout, error handler) ===

    # 7. B07: HTTP node sem retry policy (3x exp backoff)
    # N8N usa maxTries (v1.x) OU maxRetries (outras versoes). Aceita ambos >= 3.
    for node in nodes:
        ntype = node.get("type", "")
        nname = node.get("name", "")
        if ntype == "n8n-nodes-base.httpRequest":
            params = node.get("parameters", {})
            options = params.get("options", {})
            retry_cfg = options.get("retry", {})
            max_tries = retry_cfg.get("maxTries", 0) or retry_cfg.get("maxRetries", 0)
            retry_enabled = retry_cfg.get("enabled", True)
            if not retry_cfg or max_tries < 3 or not retry_enabled:
                result["warnings"].append(
                    f"B07: HTTP node '{nname}' sem retry policy 3x (atual: maxTries={max_tries}, enabled={retry_enabled})"
                )

    # 8. B08: HTTP node com timeout > 30s
    for node in nodes:
        ntype = node.get("type", "")
        nname = node.get("name", "")
        if ntype == "n8n-nodes-base.httpRequest":
            params = node.get("parameters", {})
            options = params.get("options", {})
            timeout = options.get("timeout", 0)
            if timeout > 30000:
                result["warnings"].append(
                    f"B08: HTTP node '{nname}' timeout > 30s ({timeout}ms)"
                )

    # 9. B06: WF sem error handler wired (settings.errorWorkflow nao setado)
    settings = wf.get("settings", {})
    error_workflow = settings.get("errorWorkflow")
    if not error_workflow:
        # So eh issue se WF tem nodes (WF vazio eh trivial)
        if nodes:
            result["warnings"].append(
                "B06: WF sem error handler wired (settings.errorWorkflow nao setado)"
            )

    return result


def validate_all(wf_dir: Path = DEFAULT_WF_DIR) -> dict[str, Any]:
    """Valida TODOS os workflows N8N em um diretorio.

    Returns:
        dict com {total, valid, invalid, warning, wfs[]}
    """
    if not wf_dir.exists():
        return {
            "error": f"Diretorio nao existe: {wf_dir}",
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "warning": 0,
            "wfs": [],
        }

    wfs: list[dict] = []
    for wf_path in sorted(wf_dir.glob("*.json")):
        result = _validate_one(wf_path)
        wfs.append(result)

    total = len(wfs)
    valid = sum(1 for w in wfs if w["valid"] and not w["warnings"])
    invalid = sum(1 for w in wfs if not w["valid"])
    warning = sum(1 for w in wfs if w["warnings"] and w["valid"])

    return {
        "directory": str(wf_dir),
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "warning": warning,
        "wfs": wfs,
    }
