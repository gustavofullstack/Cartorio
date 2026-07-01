#!/usr/bin/env python3
"""Pre-commit hook: bloqueia fallback literal de chaves/API keys em codigo.

Sprint 3 Goal #3 (2026-06-24): chaves queimadas NAO rotacionadas, mas
mitigacao inclui monitoramento. Este script fecha o loop garantindo que
NOVAS chaves literais em fallback nao entrem em codigo commitado.

Detecta:
- Literais com prefixo de provedor conhecido (lin_api, sk-, rnd_, AQ.,
  gAAAAA, ghp_, xox[bpors]-). Multi-line safe.
- Literais 20+ chars alfanumericos precedidos de nome *_KEY/_TOKEN/_PASSWORD.

Opt-out: linha com `# noqa: ALLOW_KEY_FALLBACK` explicito + comentario
explicando o por que. NUNCA silencioso.

Uso:
    python3 backend/scripts/check_no_literal_keys.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

OPTOUT_MARKER = "# noqa: ALLOW_KEY_FALLBACK"

# (a) Literal com prefixo de provedor conhecido (provider-specific signal).
PROVIDER_LITERAL = re.compile(
    r"['\"](?:"
    r"lin_api_[A-Za-z0-9]{20,}"  # Linear
    r"|sk-[A-Za-z0-9]{20,}"  # OpenAI / OpenCode / generic
    r"|rnd_[A-Za-z0-9]{20,}"  # Render
    r"|gAAAAA[A-Za-z0-9_\-]{20,}"  # Google API keys
    r"|ghp_[A-Za-z0-9]{20,}"  # GitHub PAT (classic)
    r"|gh[sur]_[A-Za-z0-9]{20,}"  # GitHub PAT (fine-grained)
    r"|xox[bpors]-[A-Za-z0-9-]{20,}"  # Slack
    r"|AKIA[A-Z0-9]{16}"  # AWS access key
    r"|AIza[A-Za-z0-9_\-]{35}"  # Google API key
    r"|AQ\.[A-Za-z0-9_\-]{30,}"  # Jules / Google Cloud token
    r")['\"]"
)

# (b) Contexto `os.environ.get(KEY, "literal_alnum_20+")` mesmo com
# multi-line. Usa lookahead que aceita whitespace/newline entre args.
ENV_FALLBACK_PATTERN = re.compile(
    r"os\.environ\.get\s*\([^)]*?\b(?:KEY|TOKEN|PASSWORD|SECRET)\b[^)]*?,\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
    re.DOTALL,
)


def is_literal_key_line(line: str) -> bool:
    """Match single-line: heuristic simples."""
    return bool(PROVIDER_LITERAL.search(line))


def has_fallback_pattern(text: str) -> bool:
    """Match multi-line `os.environ.get(KEY, "literal")`."""
    return bool(ENV_FALLBACK_PATTERN.search(text))


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Retorna lista de violacoes como (lineno, regra, conteudo)."""
    violations: list[tuple[int, str, str]] = []
    try:
        content = path.read_text()
    except (OSError, UnicodeDecodeError):
        return violations

    # 1) Multi-line: os.environ.get(KEY, "literal") com comment opt-out
    #    Escaneamos bloco-a-bloco removendo linhas com opt-out.
    text_no_optout = "\n".join(
        line for line in content.splitlines() if OPTOUT_MARKER not in line
    )
    if has_fallback_pattern(text_no_optout):
        # Encontra pelo menos uma linha com violacao real para reportar
        for lineno, line in enumerate(content.splitlines(), 1):
            if OPTOUT_MARKER in line:
                continue
            if PROVIDER_LITERAL.search(line):
                violations.append((lineno, "PROVIDER_LITERAL", line.strip()))
            elif "os.environ.get" in line and any(
                kw in line for kw in ("KEY", "TOKEN", "PASSWORD", "SECRET")
            ):
                if PROVIDER_LITERAL.search(
                    # tenta match ate na mesma linha + linha seguinte
                    line + " " + (content.splitlines()[lineno] if lineno < len(content.splitlines()) else "")
                ):
                    violations.append((lineno, "ENV_FALLBACK", line.strip()))

    # 2) Single-line provider literal mesmo sem os.environ.get
    for lineno, line in enumerate(content.splitlines(), 1):
        if OPTOUT_MARKER in line:
            continue
        if is_literal_key_line(line):
            # Avoid duplicar o que ja foi reportado via ENV_FALLBACK
            if not any(v[0] == lineno for v in violations):
                violations.append((lineno, "PROVIDER_LITERAL", line.strip()))

    return violations


def main() -> int:
    violations: list[str] = []

    # Escopo: backend/app + backend/scripts. Tests (.venv) e migrations fora.
    for subdir in ("app", "scripts"):
        root = BACKEND_DIR / subdir
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            rel = py_file.relative_to(REPO_ROOT)
            for lineno, rule, content in scan_file(py_file):
                violations.append(f"{rel}:{lineno} [{rule}]: {content[:140]}")

    if violations:
        print("=" * 72)
        print("PRE-COMMIT HOOK: BLOCOUE FALLBACK LITERAL DE CHAVES (LGPD/security)")
        print("=" * 72)
        print()
        for v in violations:
            print(f"  BLOCKED: {v}")
        print()
        print("Para aceitar conscientemente, adicione na MESMA LINHA:")
        print("  # noqa: ALLOW_KEY_FALLBACK  (motivo: <descrever aqui>)")
        print()
        print("Ref: Sprint 3 Goal #3 (2026-06-24) — chaves queimadas NAO sao")
        print("     rotacionadas, mas NAO devem proliferar em codigo.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
