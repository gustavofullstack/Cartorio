#!/usr/bin/env python3
"""G8.19.T4 — auditoria interna das modificações em workflows N8N críticos."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

WORKFLOW_DIR = Path("infra/n8n-workflows")
CRITICAL_WFS = {
    "template-orcamento-escritura.json": "critical",
    "00-error-handler.json": "critical",
    "01-consulta-emolumento.json": "critical",
    "02-criar-protocolo.json": "critical",
    "04-boas-vindas-lgpd.json": "critical",
    "08-audit-verify-diario.json": "critical",
    "12-chatbot-llm-end-to-end.json": "critical",
    "22-audit-verify-6h.json": "critical",
    "23-lgpd-esqueci-v2.json": "critical",
    "24-retencao-diaria.json": "critical",
    "25-protocolo-concluido-pdf.json": "critical",
    "28-audit-snapshot.json": "high",
    "30-health-deep-check.json": "high",
    "38-emolumento-calculator.json": "critical",
    "evo-in.json": "critical",
}
NON_STRUCTURAL_FIELDS = {
    "createdAt",
    "pinData",
    "shared",
    "staticData",
    "triggerCount",
    "updatedAt",
    "versionCounter",
    "versionId",
}


def repository_root() -> Path:
    """Retorna a raiz do repositório sem depender do diretório atual."""
    return Path(__file__).resolve().parents[1]


def _structural_payload(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: _structural_payload(value)
            for key, value in data.items()
            if key not in NON_STRUCTURAL_FIELDS
        }
    if isinstance(data, list):
        return [_structural_payload(value) for value in data]
    return data


def compute_hash(wf_path: Path) -> str:
    """Calcula SHA256 do JSON estrutural canônico, com chaves ordenadas."""
    with wf_path.open(encoding="utf-8") as workflow_file:
        data = json.load(workflow_file)
    canonical = json.dumps(
        _structural_payload(data),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        check=False,
        cwd=root,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git rev-parse HEAD failed")
    return result.stdout.strip()


@lru_cache(maxsize=256)
def _git_log_cached(root: str, workflow: str, head: str) -> tuple[str, ...]:
    workflow_path = (WORKFLOW_DIR / workflow).as_posix()
    result = subprocess.run(
        [
            "git",
            "log",
            head,
            "--pretty=format:%H|%an|%ae|%at|%s",
            "--follow",
            "--",
            workflow_path,
        ],
        capture_output=True,
        check=False,
        cwd=root,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git log failed for {workflow}")
    return tuple(result.stdout.splitlines())


def _workflow_snapshot(root: Path, workflow: str) -> dict[str, str]:
    workflow_path = root / WORKFLOW_DIR / workflow
    with workflow_path.open(encoding="utf-8") as workflow_file:
        payload = json.load(workflow_file)
    workflow_id = str(payload.get("id") or f"local:{workflow_path.stem}")
    return {
        "path": workflow,
        "id": workflow_id,
        "hash": compute_hash(workflow_path),
        "threshold": CRITICAL_WFS[workflow],
    }


def _parse_git_entry(line: str, snapshot: dict[str, str]) -> dict[str, str]:
    parts = line.split("|", 4)
    if len(parts) != 5:
        raise ValueError(f"invalid git log entry for {snapshot['path']}")
    commit, author, email, raw_timestamp, subject = parts
    timestamp = datetime.fromtimestamp(int(raw_timestamp), timezone.utc).isoformat()
    return {
        "workflow": snapshot["path"],
        "workflow_id": snapshot["id"],
        "workflow_hash": snapshot["hash"],
        "threshold": snapshot["threshold"],
        "commit": commit,
        "author": author,
        "email": email,
        "timestamp": timestamp,
        "subject": subject,
    }


def collect_modifications(
    root: Path, workflows: tuple[str, ...]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Coleta snapshots atuais e histórico Git dos workflows selecionados."""
    head = _git_head(root)
    snapshots = [_workflow_snapshot(root, workflow) for workflow in workflows]
    entries = [
        _parse_git_entry(line, snapshot)
        for snapshot in snapshots
        for line in _git_log_cached(str(root), snapshot["path"], head)
    ]
    entries.sort(
        key=lambda entry: (entry["timestamp"], entry["workflow"]), reverse=True
    )
    return snapshots, entries


def _parse_since(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Processa argumentos da CLI."""
    parser = argparse.ArgumentParser(
        description="Audita modificações Git em workflows N8N críticos, sem acessar o N8N live."
    )
    parser.add_argument("--since", help="ISO timestamp; only report changes after")
    parser.add_argument("--critical-only", action="store_true")
    parser.add_argument("--output", type=Path, help="JSON output file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    """Executa a auditoria e imprime ou grava relatório JSON."""
    args = parse_args(argv)
    repo_root = (root or repository_root()).resolve()
    selected = tuple(
        workflow
        for workflow, threshold in CRITICAL_WFS.items()
        if not args.critical_only or threshold == "critical"
    )

    try:
        snapshots, entries = collect_modifications(repo_root, selected)
        if args.since:
            since = _parse_since(args.since)
            entries = [
                entry
                for entry in entries
                if datetime.fromisoformat(entry["timestamp"]) >= since
            ]
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"N8N workflow audit failed: {exc}", file=sys.stderr)
        return 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "critical_wfs": list(CRITICAL_WFS),
        "selected_wfs": list(selected),
        "modifications_count": len(entries),
        "workflows": snapshots,
        "entries": entries,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
        print(f"Report written to {args.output} ({len(entries)} entries)")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
