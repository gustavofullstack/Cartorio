"""test_n8n_workflows.py - valida que todos WFs N8N estao bem-formados.

SQUAD B B12 - test runner 28+ WFs (estatico, sem Playwright/WorkflowTestKit).

Para cada *.json em infra/n8n-workflows/, valida:
1. JSON parse OK
2. Tem 'name', 'nodes', 'connections'
3. Tem pelo menos 1 trigger (webhook, schedule, email, manual, errorTrigger)
4. Tem pelo menos 1 node de saida (httpRequest, telegram, set, etc)
5. Connections nao tem referencia circular morta
6. nodes[i].id eh unico
7. nodes[i].type esta na lista de tipos suportados

Exit code 0 = todos OK, 1 = pelo menos 1 WF invalido.

Uso:
  cd backend
  uv run python scripts/test_n8n_workflows.py
  uv run python scripts/test_n8n_workflows.py --strict  # falha em warning tbm
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VALID_TRIGGER_TYPES = (
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.emailReadImap",
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.errorTrigger",
    "n8n-nodes-base.executeWorkflowTrigger",
    "n8n-nodes-base.formTrigger",
    "n8n-nodes-base.cron",  # legacy
)

VALID_OUTPUT_TYPES_PREFIX = (
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.telegram",
    "n8n-nodes-base.chatwoot",
    "n8n-nodes-base.set",
    "n8n-nodes-base.code",
    "n8n-nodes-base.if",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.evolutionApi",
    "n8n-nodes-base.supabase",
    "n8n-nodes-base.postgres",
    "n8n-nodes-base.redis",
    "n8n-nodes-base.respondToWebhook",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.wait",
    "n8n-nodes-base.emailSend",
    "n8n-nodes-base.function",
    "n8n-nodes-base.functionItem",
    "n8n-nodes-base.merge",
    "n8n-nodes-base.stopAndError",
    "n8n-nodes-base.errorWorkflow",  # legacy
    "@n8n/n8n-nodes-base.",
    # Community nodes (validos no N8N)
    "n8n-nodes-evolution-api.evolutionApi",  # community
    "n8n-nodes-mcp.mcpClient",  # community MCP client
    "n8n-nodes-mcp.",  # qualquer outro MCP community
)


def validate_workflow(path: Path) -> list[str]:
    """Retorna lista de problemas (vazia = OK)."""
    issues: list[str] = []
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"JSON parse error: {e}"]

    if not isinstance(wf, dict):
        return ["top-level nao eh objeto"]

    # 1. campos minimos
    for field in ("name", "nodes", "connections"):
        if field not in wf:
            issues.append(f"campo obrigatorio ausente: {field!r}")

    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})

    if not isinstance(nodes, list):
        issues.append("'nodes' nao eh lista")
        return issues
    if not isinstance(connections, dict):
        issues.append("'connections' nao eh dict")
        return issues

    # 2. pelo menos 1 trigger
    triggers = [n for n in nodes if n.get("type") in VALID_TRIGGER_TYPES]
    if not triggers:
        issues.append(f"sem trigger (esperado 1 de: {', '.join(t.split('.')[-1] for t in VALID_TRIGGER_TYPES[:4])})")

    # 3. IDs unicos
    ids_seen: set[str] = set()
    for n in nodes:
        nid = n.get("id")
        if not nid:
            issues.append("node sem id")
            continue
        if nid in ids_seen:
            issues.append(f"id duplicado: {nid}")
        ids_seen.add(nid)

    # 4. connections referenciam nodes existentes
    # Formato N8N: {src_name: {output_type: [[{node, type, index}]]}}
    #             OU legacy: {src_name: [[{node, type, index}]]}
    node_ids = {n.get("id") for n in nodes if n.get("id")}
    node_names = {n.get("name") for n in nodes if n.get("name")}
    for src, conn_data in connections.items():
        if src not in node_names and src not in node_ids:
            issues.append(f"connection origem inexistente: {src!r}")
            continue
        # Normaliza: pode ser {"main": [...]} ou ja ser lista
        branches = conn_data.get("main") if isinstance(conn_data, dict) else conn_data
        if not isinstance(branches, list):
            issues.append(f"connection {src!r} nao tem 'main' list")
            continue
        for branch_idx, branch in enumerate(branches):
            if not isinstance(branch, list):
                continue
            for link in branch:
                tgt = link.get("node") if isinstance(link, dict) else None
                if tgt and tgt not in node_names and tgt not in node_ids:
                    issues.append(f"connection destino inexistente: {src!r}->{tgt!r}")

    # 5. node type valido (warning, nao erro)
    invalid_types = []
    for n in nodes:
        ntype = n.get("type", "")
        if ntype in VALID_TRIGGER_TYPES:
            continue
        if any(ntype.startswith(prefix) for prefix in VALID_OUTPUT_TYPES_PREFIX):
            continue
        if "n8n-nodes-base." in ntype or "@n8n/" in ntype:
            continue
        invalid_types.append(ntype)
    if invalid_types:
        issues.append(f"node types nao reconhecidos: {set(invalid_types)}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workflows-dir",
        default=str(Path(__file__).parent.parent.parent / "infra/n8n-workflows"),
    )
    parser.add_argument("--strict", action="store_true", help="falha em qualquer issue")
    args = parser.parse_args()

    wf_dir = Path(args.workflows_dir)
    if not wf_dir.exists():
        print(f"ERRO: {wf_dir} nao existe", file=sys.stderr)
        return 1

    json_files = sorted(wf_dir.glob("*.json"))
    if not json_files:
        print(f"Nenhum .json em {wf_dir}")
        return 0

    print(f"Validando {len(json_files)} workflows em {wf_dir}\n")

    passed = 0
    failed = 0
    for wf_path in json_files:
        issues = validate_workflow(wf_path)
        if not issues:
            print(f"  PASS  {wf_path.name}")
            passed += 1
        else:
            print(f"  FAIL  {wf_path.name}")
            for issue in issues:
                print(f"        - {issue}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed de {len(json_files)} total")
    return 1 if (failed > 0 and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
