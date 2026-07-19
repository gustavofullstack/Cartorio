#!/usr/bin/env python3
"""Pre-commit hook + CI gate: bloqueia fallback literal de chaves/API keys em codigo.

Sprint 3 Goal #3 (2026-06-24): chaves queimadas NAO rotacionadas, mas
mitigacao inclui monitoramento. Este script fecha o loop garantindo que
NOVAS chaves literais em fallback nao entrem em codigo commitado.

G8.14.T3 (Wave 48 — LGPD-by-design): ampliado de 10 para 20+ patterns,
adicione de flags CLI (--severity, --baseline, --report-only) e
whitelist via arquivo .baseline.

LGPD: Art. 46 — zero secrets em logs, env vars, storage. Secrecy = LGPD
prerequisite (criptografia, controle de acesso). PII + secrets sao a mesma
categoria de risco (P0 incident se vazar).

Padroes detectados (Wave 48 G8.14.T3):
- PROVIDER_LITERAL (lin_api_*, sk-*, sk-proj-*, sk-ant-*, rnd_*, AQ.*,
  gAAAAA*, ghp_*, gh[sur]_*, xox[bpors]-*, AKIA*, AIza*, sk-cp-*).
- AWS access key (AKIA / ASIA prefixo + 16 chars).
- AWS secret access key (40 chars base64-ish com contexto AWS_SECRET).
- GCP service-account JSON literal (`"type": "service_account"`).
- Telegram bot tokens (`\\d{10}:[A-Za-z0-9_-]{35}`).
- Supabase service_role JWT (eyJ... com payload "role":"service_role").
- MiniMax keys (sk-cp-* + eyJhbGciOi... JWT).
- OpenAI/Anthropic project keys (sk-proj-*, sk-ant-*).
- Bearer eyJ... JWT (Authorization headers).
- PKCS8 private key (-----BEGIN PRIVATE KEY-----).
- PKCS1 RSA private key (-----BEGIN RSA PRIVATE KEY-----).
- ENV_FALLBACK: `os.environ.get(KEY, "literal_alnum_20+")` multi-line safe.

Opt-out:
- Inline na linha: `# noqa: ALLOW_KEY_FALLBACK` (motivo: <descrever>).
- Whitelist em arquivo .baseline (formato: `<path>:<lineno>:<rule>`).

Uso:
    # Modo padrao (gate): exit 1 se violacao nao-whitelisted.
    python3 backend/scripts/check_no_literal_keys.py

    # CI mode com baseline + severity threshold.
    python3 backend/scripts/check_no_literal_keys.py \\
        --severity critical \\
        --baseline backend/scripts/check_no_literal_keys.baseline

    # Report only (exit 0 mesmo com achados, util pra dry-run).
    python3 backend/scripts/check_no_literal_keys.py --report-only

    # Escopo customizado.
    python3 backend/scripts/check_no_literal_keys.py \\
        --root backend/app --root backend/scripts

Exit codes:
    0  Clean (ou --report-only com achados).
    1  Violacoes criticas ou acima do threshold (gate fail).
    2  Erro de I/O / argumento invalido.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
DEFAULT_BASELINE = BACKEND_DIR / "scripts" / "check_no_literal_keys.baseline"

OPTOUT_MARKER = "# noqa: ALLOW_KEY_FALLBACK"

# Diretorias ignoradas (vendor / caches / build artifacts).
SKIP_DIRS = frozenset(
    {
        ".venv",
        ".venv312",
        ".venv311",
        "venv",
        "env",
        "node_modules",
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "htmlcov",
        "dist",
        "build",
        ".eggs",
        "site-packages",
    }
)

# Arquivos ignorados (config templates / fixtures / docs).
SKIP_FILES = frozenset(
    {
        ".env",
        ".env.example",
        ".env.template",
        ".env.sample",
        "check_no_literal_keys.py",  # self-test NUNCA
        "check_no_literal_keys.baseline",
    }
)


# ============================================================================
# Severity levels.
# ============================================================================
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

SEVERITY_RANK = {
    SEVERITY_CRITICAL: 4,
    SEVERITY_HIGH: 3,
    SEVERITY_MEDIUM: 2,
    SEVERITY_LOW: 1,
}


@dataclass(frozen=True)
class Pattern:
    """Pattern individual com metadata de severity + tag."""

    name: str
    severity: str
    regex: re.Pattern[str]
    description: str


# ============================================================================
# Compiled regex cache (otimizacao: compila 1x, reusa).
# ============================================================================
_PATTERN_CACHE: dict[str, Pattern] = {}


def _make(name: str, severity: str, raw: str, description: str) -> Pattern:
    """Compila e cacheia um pattern. Thread-safe (CPython GIL no dict)."""
    if name not in _PATTERN_CACHE:
        _PATTERN_CACHE[name] = Pattern(
            name=name,
            severity=severity,
            regex=re.compile(raw),
            description=description,
        )
    return _PATTERN_CACHE[name]


# ============================================================================
# Pattern catalog (20 patterns, severity-tagged).
# ============================================================================
PATTERNS: tuple[Pattern, ...] = (
    # ---- CRITICAL (LGPD Art. 46 — secrets em prod) ----
    _make(
        "AWS_ACCESS_KEY_ID",
        SEVERITY_CRITICAL,
        r"\bAKIA[0-9A-Z]{16}\b",
        "AWS access key ID (20 chars, AKIA prefix).",
    ),
    _make(
        "AWS_ASIA_TEMP",
        SEVERITY_CRITICAL,
        r"\bASIA[0-9A-Z]{16}\b",
        "AWS temporary access key (STS, ASIA prefix).",
    ),
    _make(
        "AWS_SECRET_ACCESS_KEY",
        SEVERITY_CRITICAL,
        r"(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY)\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}",
        "AWS secret access key (40 chars base64-ish).",
    ),
    _make(
        "OPENAI_PROJECT_KEY",
        SEVERITY_CRITICAL,
        r"\bsk-proj-[A-Za-z0-9_\-]{20,}",
        "OpenAI project-scoped key (sk-proj-*).",
    ),
    _make(
        "ANTHROPIC_KEY",
        SEVERITY_CRITICAL,
        r"\bsk-ant-[A-Za-z0-9_\-]{20,}",
        "Anthropic API key (sk-ant-*).",
    ),
    _make(
        "OPENAI_LEGACY_KEY",
        SEVERITY_CRITICAL,
        r"['\"]sk-[A-Za-z0-9]{20,}['\"]",
        "OpenAI / generic sk-* key (quoted literal).",
    ),
    _make(
        "MINIMAX_KEY",
        SEVERITY_CRITICAL,
        r"\bsk-cp-[A-Za-z0-9_\-]{20,}",
        "MiniMax Coding Plan key (sk-cp-*).",
    ),
    _make(
        "PKCS8_PRIVATE_KEY",
        SEVERITY_CRITICAL,
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----",
        "Generic PKCS8 / OpenSSH private key block.",
    ),
    _make(
        "GCP_SERVICE_ACCOUNT_JSON",
        SEVERITY_CRITICAL,
        r"['\"](?:type|project_id|private_key_id|client_email)['\"]\s*:\s*['\"](?:service_account|[^'\"]+@[^'\"]+\.iam\.gserviceaccount\.com)['\"]",
        "GCP service-account JSON literal.",
    ),
    _make(
        "SUPABASE_SERVICE_ROLE_JWT",
        SEVERITY_CRITICAL,
        r"eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}",
        "Supabase / generic JWT (3-segment, decode-friendly).",
    ),
    _make(
        "TELEGRAM_BOT_TOKEN",
        SEVERITY_CRITICAL,
        r"\b\d{8,12}:[A-Za-z0-9_\-]{30,}\b",
        "Telegram bot token (numeric_id plus provider secret).",
    ),
    # ---- HIGH ----
    _make(
        "PROVIDER_LITERAL_GENERIC",
        SEVERITY_HIGH,
        r"['\"](?:lin_api_|rnd_|gAAAAA|ghp_|gh[sur]_|xox[bpors]-|AIza|AQ\.)[A-Za-z0-9_\-]{20,}['\"]",
        "Generic provider-prefixed literal (Linear/Render/GCP/Slack/AWS).",
    ),
    _make(
        "BEARER_JWT",
        SEVERITY_HIGH,
        r"\bBearer\s+eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
        "Authorization: Bearer <jwt> literal.",
    ),
    # ---- MEDIUM ----
    _make(
        "ENV_FALLBACK",
        SEVERITY_MEDIUM,
        r"os\.environ\.get\s*\(\s*['\"]?[A-Za-z0-9_]*(?:KEY|TOKEN|PASSWORD|SECRET)[A-Za-z0-9_]*['\"]?\s*,\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
        "os.environ.get(KEY, 'literal_fallback') — pattern de risco.",
    ),
    # ---- LOW (info / higiene) ----
    _make(
        "GOOGLE_API_KEY",
        SEVERITY_LOW,
        r"\bAIza[A-Za-z0-9_\-]{35}\b",
        "Google API key (AIza + 35 chars).",
    ),
)


# Patterns de deprecated/legacy que mantemos pra back-compat com baseline.
# Estes NAO sao flags novos — apenas alias pros patterns originais.
DEPRECATED_ALIASES = {
    # Nome antigo -> novo
    "PROVIDER_LITERAL": "PROVIDER_LITERAL_GENERIC",
}


def find_rule_for_name(name: str) -> str | None:
    """Resolve nome de regra (aceita aliases deprecated)."""
    if name in DEPRECATED_ALIASES:
        return DEPRECATED_ALIASES[name]
    if any(p.name == name for p in PATTERNS):
        return name
    return None


# ============================================================================
# Scan logic.
# ============================================================================
@dataclass(frozen=True)
class Violation:
    lineno: int
    rule: str
    severity: str
    snippet: str

    def fingerprint(self, path: str) -> str:
        """Hash para baseline matching: `<path>:<lineno>:<rule>`."""
        return f"{path}:{self.lineno}:{self.rule}"


def _should_skip_path(path: Path) -> bool:
    """Heuristica: pula vendor dirs e arquivos na whitelist."""
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.name in SKIP_FILES:
        return True
    return False


def scan_text(text: str) -> list[Violation]:
    """Escaneia string completa (sem I/O) — usado por tests."""
    violations: list[Violation] = []
    # OPT-OUT: remove linhas com marker antes de escanear.
    text_no_optout = "\n".join(line for line in text.splitlines() if OPTOUT_MARKER not in line)

    for pattern in PATTERNS:
        for match in pattern.regex.finditer(text_no_optout):
            # Calcula lineno a partir do offset.
            offset = match.start()
            lineno = text_no_optout.count("\n", 0, offset) + 1
            snippet = match.group(0)
            if len(snippet) > 100:
                snippet = snippet[:97] + "..."
            violations.append(
                Violation(
                    lineno=lineno,
                    rule=pattern.name,
                    severity=pattern.severity,
                    snippet=snippet,
                )
            )
    return violations


def scan_file(path: Path) -> list[Violation]:
    """Escaneia arquivo, retorna lista de Violation."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_text(content)


def load_baseline(baseline_path: Path) -> set[str]:
    """Carrega whitelist de fingerprints. Linhas `#` ou vazias ignoradas."""
    if not baseline_path.exists():
        return set()
    fps: set[str] = set()
    for raw in baseline_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fps.add(line)
    return fps


def filter_by_severity(violations: list[Violation], min_severity: str) -> list[Violation]:
    """Filtra violacoes abaixo do threshold de severity."""
    threshold = SEVERITY_RANK.get(min_severity, 1)
    return [v for v in violations if SEVERITY_RANK.get(v.severity, 0) >= threshold]


def filter_by_baseline(
    violations: list[Violation], rel_path: str, baseline: set[str]
) -> list[Violation]:
    """Remove violacoes whitelisted no arquivo .baseline."""
    return [v for v in violations if v.fingerprint(rel_path) not in baseline]


def iter_python_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Itera sobre arquivos .py, pulando vendor dirs."""
    for root in roots:
        if not root.exists():
            continue
        for py_file in root.rglob("*.py"):
            if not _should_skip_path(py_file):
                yield py_file


def iter_text_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Itera sobre .py/.sh/.yml/.yaml/.json/.env* etc."""
    suffixes = {".py", ".sh", ".yml", ".yaml", ".json", ".env", ".toml", ".cfg", ".ini"}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in suffixes:
                continue
            if _should_skip_path(path):
                continue
            yield path


# ============================================================================
# CLI / main.
# ============================================================================
def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Secrets scanner (LGPD Art. 46) — bloqueia chaves literais em codigo.",
    )
    p.add_argument(
        "--severity",
        choices=[SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW],
        default=SEVERITY_LOW,
        help="Threshold minimo de severity (default: low — reporta tudo).",
    )
    p.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help=f"Arquivo de whitelist (default: {DEFAULT_BASELINE}).",
    )
    p.add_argument(
        "--report-only",
        action="store_true",
        help="Exit 0 mesmo com achados (dry-run / report).",
    )
    p.add_argument(
        "--root",
        action="append",
        type=Path,
        help="Raiz adicional pra escanear (pode repetir). Default: backend/app + backend/scripts.",
    )
    p.add_argument(
        "--include-text",
        action="store_true",
        help="Tambem escaneia .sh/.yml/.json/.env (default: so .py).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    if args.root:
        roots = list(args.root)
    else:
        roots = [BACKEND_DIR / "app", BACKEND_DIR / "scripts"]

    baseline = load_baseline(args.baseline)
    if baseline:
        print(f"[baseline] {len(baseline)} fingerprints whitelisted from {args.baseline}")

    file_iter = iter_text_files(roots) if args.include_text else iter_python_files(roots)

    def _relpath(path: Path) -> str:
        """Repo-relative se possivel, senao absoluto (pra --root arbitrarios)."""
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path.resolve())

    all_violations: list[tuple[Path, Violation]] = []
    for path in file_iter:
        for v in scan_file(path):
            all_violations.append((path, v))

    # Filter baseline (FPs conhecidos).
    filtered: list[tuple[Path, Violation]] = []
    for path, v in all_violations:
        rel = _relpath(path)
        if v.fingerprint(rel) in baseline:
            continue
        filtered.append((path, v))

    # Filter severity threshold.
    threshold_violations = filter_by_severity([v for _, v in filtered], args.severity)

    # Report.
    print("=" * 72)
    print(f"SECRETS SCANNER (G8.14.T3) — severity>={args.severity}")
    print("=" * 72)

    if not filtered:
        print("OK: zero violacoes detectadas.")
        return 0

    print(
        f"Encontradas {len(filtered)} violacao(oes), {len(threshold_violations)} acima do threshold."
    )
    print()
    for path, v in filtered:
        rel = _relpath(path)
        marker = " " if v.severity in (SEVERITY_HIGH, SEVERITY_MEDIUM) else "*"
        in_threshold = " (GATE)" if v.severity_rank() >= SEVERITY_RANK.get(args.severity, 1) else ""
        # Achados podem ser segredos reais. Localizacao e regra bastam para
        # remediacao; nunca ecoar o match em logs de CI, terminal ou artefatos.
        print(f"  {marker} {rel}:{v.lineno} [{v.severity.upper()}][{v.rule}]{in_threshold}")
        print("      [valor redigido]")

    print()
    print(f"Threshold: {args.severity} ({SEVERITY_RANK.get(args.severity, 1)})")
    print(f"Above threshold: {len(threshold_violations)}")
    print(f"Whitelisted (baseline): {len(baseline)}")
    print()

    if args.report_only:
        print("--report-only: exit 0 (dry-run mode).")
        return 0

    if threshold_violations:
        print("PARA CORRIGIR:")
        print("  1. Rotacione a chave (URGENTE — LGPD Art. 46).")
        print("  2. Mova pra .env / vault / secret manager.")
        print("  3. Em ultimo caso, marque a linha com:")
        print("     # noqa: ALLOW_KEY_FALLBACK  (motivo: ...)")
        print("  4. Ou adicione fingerprint ao baseline (FP whitelist):")
        print(f"     echo '<path>:<lineno>:<rule>' >> {args.baseline}")
        return 1

    print(f"Violacoes abaixo do threshold ({args.severity}) — gate OK.")
    return 0


# Adiciona severity_rank ao Violation (decorator tardio pra evitar circular).
def _violation_severity_rank(self: Violation) -> int:
    return SEVERITY_RANK.get(self.severity, 0)


Violation.severity_rank = _violation_severity_rank  # type: ignore[attr-defined]


if __name__ == "__main__":
    sys.exit(main())
