#!/usr/bin/env python3
"""G8.04.T2 — CLI: empacota/exporta system prompt do LobeChat (CartórioBot).

Uso:
  # Exporta para ./export/lobechat-prompt (default)
  python3 scripts/export_lobechat_prompt.py

  # Diretório customizado
  python3 scripts/export_lobechat_prompt.py --out /tmp/lobechat-prompt-pkg

  # Fonte explícita
  python3 scripts/export_lobechat_prompt.py --source infra/openclaw-agent/workspace/SOUL.md

  # Forçar prompt embedded (ignora arquivos)
  python3 scripts/export_lobechat_prompt.py --embedded-only

  # JSON no stdout (paths + sha256)
  python3 scripts/export_lobechat_prompt.py --json

Saída:
  <out>/prompt.md
  <out>/metadata.json   # version, sha256, source — sem secrets

Modified by Gustavo Almeida — G8.04.T2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.lobechat_prompt_export import (  # noqa: E402
    CARTORIO_DEFAULT_SYSTEM_PROMPT,
    PACKAGE_VERSION,
    export_package,
    find_repo_root,
    list_candidate_sources,
    load_system_prompt,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Exporta system prompt LobeChat CartórioBot (prompt.md + metadata.json).",
    )
    p.add_argument(
        "--out",
        "-o",
        type=Path,
        default=PROJECT_ROOT / "export" / "lobechat-prompt",
        help="Diretório de saída (default: export/lobechat-prompt)",
    )
    p.add_argument(
        "--source",
        "-s",
        type=Path,
        default=None,
        help="Arquivo fonte explícito (md ou agent_cartorio_import.json)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Raiz do monorepo (auto-detect se omitido)",
    )
    p.add_argument(
        "--embedded-only",
        action="store_true",
        help="Usa apenas CARTORIO_DEFAULT_SYSTEM_PROMPT (ignora arquivos)",
    )
    p.add_argument(
        "--list-sources",
        action="store_true",
        help="Lista fontes candidatas existentes e sai",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Imprime resultado em JSON no stdout",
    )
    p.add_argument(
        "--version",
        action="store_true",
        help="Imprime package_version e sai",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.version:
        print(PACKAGE_VERSION)
        return 0

    root = args.repo_root or find_repo_root(PROJECT_ROOT)

    if args.list_sources:
        sources = list_candidate_sources(root)
        payload = {
            "repo_root": str(root),
            "candidates": [str(s) for s in sources],
            "embedded_chars": len(CARTORIO_DEFAULT_SYSTEM_PROMPT),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"repo_root: {root}")
            if sources:
                for s in sources:
                    print(f"  - {s}")
            else:
                print("  (nenhuma fonte em disco; usaria embedded)")
            print(f"embedded_chars: {len(CARTORIO_DEFAULT_SYSTEM_PROMPT)}")
        return 0

    if args.embedded_only:
        # Exporta forçando preferred inexistente + allow_embedded via temp path trick:
        # write temp load from constant by preferred that fails → use allow_embedded
        # Simpler: call load with preferred=None after monkey? Use preferred_source
        # pointing nowhere is error. Instead export with preferred_source None after
        # temporarily isolating — cleanest API: preferred_source of a temp file.
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            # Direct: write embedded via preferred empty? Better call export with
            # allow_embedded and no candidates — not possible if SOUL.md exists.
            # So write preferred file with embedded content.
            emb = Path(td) / "embedded_prompt.md"
            emb.write_text(
                CARTORIO_DEFAULT_SYSTEM_PROMPT
                if CARTORIO_DEFAULT_SYSTEM_PROMPT.endswith("\n")
                else CARTORIO_DEFAULT_SYSTEM_PROMPT + "\n",
                encoding="utf-8",
            )
            result = export_package(
                args.out,
                repo_root=root,
                preferred_source=emb,
                allow_embedded=True,
                extra_metadata={"forced_embedded": True},
            )
            # Normalize source label for consumers
            result["source"] = "embedded:CARTORIO_DEFAULT_SYSTEM_PROMPT"
            result["source_kind"] = "embedded"
            result["metadata"]["source"] = "embedded:CARTORIO_DEFAULT_SYSTEM_PROMPT"
            result["metadata"]["source_kind"] = "embedded"
            meta_path = Path(result["metadata_path"])
            meta_path.write_text(
                json.dumps(result["metadata"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    else:
        result = export_package(
            args.out,
            repo_root=root,
            preferred_source=args.source,
            allow_embedded=True,
        )

    if args.json:
        # metadata already nested; drop huge prompt body
        print(
            json.dumps(
                {k: v for k, v in result.items() if k != "metadata"}
                | {"metadata": result.get("metadata")},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"ok: {result['ok']}")
        print(f"out_dir: {result['out_dir']}")
        print(f"prompt: {result['prompt_path']}")
        print(f"metadata: {result['metadata_path']}")
        print(f"source: {result['source']} ({result['source_kind']})")
        print(f"sha256: {result['prompt_sha256']}")
        print(f"package_version: {result['package_version']}")

    # Smoke: ensure load also works
    _ = load_system_prompt(repo_root=root, allow_embedded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
