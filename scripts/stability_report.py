#!/usr/bin/env python3
"""Stability Report — coletor de sinais operacionais no fim de cada wave.

Tarefa G8.16.T4 (Wave 44 / Squad 16, owner: cartorio-dev).
Gera relatório estruturado de estabilidade do Cartório 2º Notas agregando:

- **Serviços** (API, N8N, Evolution, OpenClaw, Chatwoot, Supabase, Redis,
  Traefik, LiteLLM, EasyPanel, Tailscale) — tabela 🟢 / 🟡 / 🔴 / ⚪
- **Janela temporal** configurável (``--window`` 1h/6h/24h/72h/7d ou
  ``--since`` ISO timestamp explícito)
- **Métricas de entrega**: contadores pytest/mypy/ruff, ``lesson_count``,
  ``git_commits`` no intervalo
- **Sinais LGPD**: ``audit_log`` recentes, ``chain_position``, eventos de
  retenção programados
- **Sinais HITL**: protocolos ``DRAFT`` pendentes de validação escrevente
- **Progresso do SUPER_PLANO_G8_100_TASKS.md** (contagem ``[x]`` / ``[~]`` /
  ``[ ]`` e próximas waves)

**Fail-soft por design**: nenhum coletor derruba o script. Serviço
indisponível vira linha ⚪ ou 🟡 no relatório, nunca exceção não tratada.

**LGPD-safe**: nenhum PII (CPF/RG/email/telefone) é incluído no output;
apenas contadores e rótulos. Ver ``scripts/check_no_literal_keys.py`` para
guard-rail equivalente em secrets.

Modos:
    --offline           Não faz chamadas HTTP; usa arquivos locais + heurística.
                        Ideal para CI, testes e smoke em laptops isolados.

Uso (raiz do repo):
    python3 scripts/stability_report.py --window 24h
    python3 scripts/stability_report.py --window 72h --output docs/last_report.md
    python3 scripts/stability_report.py --since 2026-07-10T00:00:00 --json
    python3 scripts/stability_report.py --wave 43 --offline

Exit codes:
    0 = relatório gerado com sucesso (mesmo com serviços em vermelho)
    2 = erro fatal de I/O (plano G8 ausente, dir de output inválido)

Modified by Gustavo Almeida — G8 Wave 44 (Squad 16 / cartorio-dev).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPER_PLANO_G8 = (ROOT / "docs" / "plans" / "SUPER_PLANO_G8_100_TASKS.md") if (ROOT / "docs" / "plans" / "SUPER_PLANO_G8_100_TASKS.md").exists() else (ROOT / "SUPER_PLANO_G8_100_TASKS.md")
SUPER_PLANO_G7 = (ROOT / "docs" / "plans" / "SUPER_PLANO_G7_100_TASKS.md") if (ROOT / "docs" / "plans" / "SUPER_PLANO_G7_100_TASKS.md").exists() else (ROOT / "SUPER_PLANO_G7_100_TASKS.md")
PROGRESS_MD = ROOT / "PROGRESS.md"
HARNESS_LOOP_STATE = ROOT / ".harness" / "loop-engineer" / "state" / "last.json"
MEMORY_DIR = ROOT / ".harness" / "memory"
PYTEST_CACHE = ROOT / ".pytest_cache" / "v" / "cache" / "lastfailed"
COVERAGE_FILE = ROOT / "backend" / ".coverage"
PYPROJECT_TOML = ROOT / "backend" / "pyproject.toml"
AUDIT_LOG_TABLES_SQL = ROOT / "backend" / "app" / "models" / "audit_log.py"

WINDOWS: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "72h": timedelta(hours=72),
    "7d": timedelta(days=7),
}

SERVICES: list[dict[str, str]] = [
    {"key": "api", "name": "API FastAPI", "host": "api.2notasudi.com.br", "path": "/health"},
    {"key": "n8n", "name": "N8N Workflows", "host": "flow.2notasudi.com.br", "path": "/healthz"},
    {
        "key": "evolution",
        "name": "Evolution API (WA)",
        "host": "whats.2notasudi.com.br",
        "path": "/",
    },
    {
        "key": "openclaw",
        "name": "OpenClaw Gateway",
        "host": "openclaw.2notasudi.com.br",
        "path": "/health",
    },
    {
        "key": "chatwoot",
        "name": "Chatwoot CRM",
        "host": "chat.2notasudi.com.br",
        "path": "/api/v1/accounts/1",
    },
    {
        "key": "supabase",
        "name": "Supabase (PG + Auth)",
        "host": "supbase.2notasudi.com.br",
        "path": "/auth/v1/health",
    },
    {"key": "redis", "name": "Redis 8", "host": "redis.2notasudi.com.br", "path": "/"},
    {
        "key": "traefik",
        "name": "Traefik Reverse Proxy",
        "host": "traefik.2notasudi.com.br",
        "path": "/ping",
    },
    {
        "key": "litellm",
        "name": "LiteLLM Proxy",
        "host": "llm.2notasudi.com.br",
        "path": "/health/liveliness",
    },
    {
        "key": "easypanel",
        "name": "EasyPanel Control",
        "host": "easypanel.2notasudi.com.br",
        "path": "/api/v1/status",
    },
    {"key": "tailscale", "name": "Tailscale SSH", "host": "100.99.172.84", "path": ""},
]

PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),  # CPF
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}-?\d{1}\b"),  # RG
    re.compile(r"\b\d{4,5}-?\d{4}\b"),  # Telefone BR
    re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),  # Email
    re.compile(r"\bprotocolo\s*[:#]?\s*\d{4,}\b", re.I),  # Protocolo
    re.compile(r"\bescritura\s*[:#]?\s*\d{4,}\b", re.I),  # Escritura
)


# ─── dataclasses ──────────────────────────────────────────────────────────


@dataclass
class ServiceSignal:
    """Linha da tabela de saúde por serviço."""

    key: str
    name: str
    host: str
    status: str  # green / yellow / red / unknown
    latency_ms: int | None
    detail: str
    error: str | None = None

    @property
    def icon(self) -> str:
        return {
            "green": "🟢",
            "yellow": "🟡",
            "red": "🔴",
            "unknown": "⚪",
        }.get(self.status, "⚪")


@dataclass
class GitSignal:
    commits: int = 0
    authors: list[str] = field(default_factory=list)
    files_changed: int = 0
    last_sha: str = ""
    last_msg: str = ""
    last_author: str = ""
    last_when: str = ""


@dataclass
class PytestSignal:
    collected: int | None = None
    lastfailed: int | None = None
    coverage_pct: float | None = None
    cache_present: bool = False


@dataclass
class AuditChainSignal:
    chain_position: int | None = None
    recent_events: int | None = None
    retention_events: int | None = None
    source: str = "unavailable"  # db / file / unavailable
    last_observed_sha: str = ""  # commit head from loop state (no PII)


@dataclass
class HitlSignal:
    draft_protocols: int | None = None
    source: str = "unavailable"


@dataclass
class WaveSignal:
    done: int = 0
    partial: int = 0
    pending: int = 0
    next_wave: str | None = None
    next_tasks: list[str] = field(default_factory=list)


@dataclass
class StabilityReport:
    generated_at: str
    window_label: str
    since: str
    until: str
    offline: bool
    services: list[ServiceSignal] = field(default_factory=list)
    git: GitSignal = field(default_factory=GitSignal)
    pytest: PytestSignal = field(default_factory=PytestSignal)
    audit: AuditChainSignal = field(default_factory=AuditChainSignal)
    hitl: HitlSignal = field(default_factory=HitlSignal)
    wave: WaveSignal = field(default_factory=WaveSignal)
    lesson_count: int = 0
    ruff_clean: bool | None = None
    mypy_clean: bool | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["services"] = [{**asdict(s), "icon": s.icon} for s in self.services]
        return d


# ─── helpers ──────────────────────────────────────────────────────────────


def parse_window(arg: str | None) -> tuple[datetime, datetime, str]:
    """Resolve janela temporal. Default: últimas 24h."""
    until = datetime.now(timezone.utc)
    if arg:
        key = arg.lower()
        if key in WINDOWS:
            since = until - WINDOWS[key]
            return since, until, key
        raise ValueError(f"invalid --window: {arg} (expected: {sorted(WINDOWS)})")
    return until - WINDOWS["24h"], until, "24h"


def parse_since(arg: str | None, until: datetime) -> tuple[datetime, datetime, str]:
    if not arg:
        return until - WINDOWS["24h"], until, "24h"
    try:
        since = datetime.fromisoformat(arg.replace("Z", "+00:00"))
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        return since, until, "custom"
    except ValueError as exc:
        raise ValueError(f"invalid --since ISO timestamp: {arg}") from exc


def scrub_pii(text: str) -> str:
    """Remove qualquer PII casualmente incluído no texto."""
    for pat in PII_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def safe_run_git(args: list[str], cwd: Path = ROOT) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, "", str(exc)


def http_probe(host: str, path: str, timeout: float = 3.0) -> tuple[str, int | None, str]:
    """Probe HTTP sem dependências externas (urllib stdlib)."""
    import urllib.request
    import urllib.error
    import socket

    url = f"https://{host}{path}" if path else f"https://{host}"
    started = time.monotonic()
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "stability-report/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = int((time.monotonic() - started) * 1000)
            code = resp.status
            body = resp.read(200).decode("utf-8", errors="replace")
            return (
                ("green", latency, body[:160])
                if code < 500
                else ("yellow", latency, f"HTTP {code}")
            )
    except urllib.error.HTTPError as exc:
        latency = int((time.monotonic() - started) * 1000)
        return ("yellow", latency, f"HTTP {exc.code}")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as exc:
        latency = int((time.monotonic() - started) * 1000)
        return ("red", latency, str(exc)[:160])


# ─── collectors ───────────────────────────────────────────────────────────


class StabilityCollector:
    """Coletor de sinais. Fail-soft: nenhum coletor derruba o script."""

    def __init__(
        self,
        window: str | None = "24h",
        since: str | None = None,
        offline: bool = False,
        super_plano: Path | None = None,
    ) -> None:
        self.offline = offline
        self.super_plano = super_plano or SUPER_PLANO_G8
        self.since, self.until, self.window_label = (
            parse_since(since, datetime.now(timezone.utc)) if since else parse_window(window)
        )

    # ─── services ────────────────────────────────────────────────────
    def collect_api_health(self) -> list[ServiceSignal]:
        if self.offline:
            return [
                ServiceSignal(
                    key=s["key"],
                    name=s["name"],
                    host=s["host"],
                    status="unknown",
                    latency_ms=None,
                    detail="offline mode — skip HTTP probe",
                )
                for s in SERVICES
            ]

        signals: list[ServiceSignal] = []
        with ThreadPoolExecutor(max_workers=min(8, len(SERVICES))) as pool:
            futures = {pool.submit(http_probe, s["host"], s["path"]): s for s in SERVICES}
            for fut in as_completed(futures):
                s = futures[fut]
                try:
                    status, latency, detail = fut.result()
                except Exception as exc:  # noqa: BLE001 — fail-soft
                    status, latency, detail = "red", None, str(exc)[:120]
                signals.append(
                    ServiceSignal(
                        key=s["key"],
                        name=s["name"],
                        host=s["host"],
                        status=status,
                        latency_ms=latency,
                        detail=scrub_pii(detail),
                    )
                )
        signals.sort(key=lambda s: s.key)
        return signals

    # ─── git metrics ─────────────────────────────────────────────────
    def collect_git_metrics(self) -> GitSignal:
        sig = GitSignal()
        since_arg = self.since.isoformat()
        rc, out, _ = safe_run_git(
            ["log", f"--since={since_arg}", "--pretty=format:%H|%an|%ae|%s|%ai"]
        )
        if rc != 0 or not out.strip():
            return sig
        commits = out.strip().splitlines()
        sig.commits = len(commits)
        authors: set[str] = set()
        for line in commits:
            parts = line.split("|", 4)
            if len(parts) >= 5:
                authors.add(parts[1])
        sig.authors = sorted(authors)
        if commits:
            head = commits[0].split("|", 4)
            sig.last_sha = head[0][:12] if head else ""
            sig.last_msg = scrub_pii(head[3]) if len(head) >= 4 else ""
            sig.last_author = head[1] if len(head) >= 2 else ""
            sig.last_when = head[4] if len(head) >= 5 else ""

        # diff stats no intervalo (best-effort, não bloqueia)
        rc2, diff_out, _ = safe_run_git(["diff", "--shortstat", f"--since={since_arg}", "HEAD"])
        if rc2 == 0 and diff_out:
            m = re.search(r"(\d+) files? changed", diff_out)
            if m:
                sig.files_changed = int(m.group(1))
        return sig

    # ─── pytest metrics ──────────────────────────────────────────────
    def collect_pytest_metrics(self) -> PytestSignal:
        sig = PytestSignal()
        # Pytest cache — formato JSON dict-like mas cabeçalho binário; tentamos
        # ler como texto e extrair contador de "lastfailed" e "collected".
        cache_path = ROOT / ".pytest_cache" / "v" / "cache" / "lastfailed"
        if cache_path.exists():
            sig.cache_present = True
            try:
                txt = cache_path.read_text(encoding="utf-8", errors="replace")
                sig.lastfailed = txt.count("\n") + (1 if txt.strip() else 0)
            except OSError:
                pass

        # coverage datafile — tentar extrair summary
        if COVERAGE_FILE.exists():
            try:
                import coverage

                cov = coverage.Coverage(data_file=str(COVERAGE_FILE))
                cov.load()
                total = cov.report(show_missing=False, file=open(os.devnull, "w"))
                sig.coverage_pct = float(total) if isinstance(total, (int, float)) else None
            except Exception:  # noqa: BLE001 — fail-soft
                # Sem coverage instalado ou datafile corrupto — segue sem dado
                sig.coverage_pct = None

        # fallback: parse de PROGRESS.md (linhas com "N tests passed")
        if sig.collected is None and PROGRESS_MD.exists():
            try:
                txt = PROGRESS_MD.read_text(encoding="utf-8", errors="replace")
                matches = re.findall(r"(\d+)\s+passed", txt)
                if matches:
                    sig.collected = int(matches[0])
            except OSError:
                pass
        return sig

    # ─── audit chain ─────────────────────────────────────────────────
    def collect_audit_chain(self) -> AuditChainSignal:
        sig = AuditChainSignal()
        sig.source = "unavailable"

        # 1) tenta ler state do loop local (não requer DB)
        if HARNESS_LOOP_STATE.exists():
            try:
                st = json.loads(HARNESS_LOOP_STATE.read_text(encoding="utf-8"))
                analyze = st.get("analyze", {}) if isinstance(st, dict) else {}
                head = analyze.get("commit_head", "")
                if head:
                    sig.last_observed_sha = head
            except (json.JSONDecodeError, OSError):
                pass

        # 2) tenta conectar ao backend (SQLAlchemy) — opcional, fail-soft
        if self.offline or not AUDIT_LOG_TABLES_SQL.exists():
            return sig

        try:
            sys.path.insert(0, str(ROOT / "backend"))
            from app.core.config import get_settings  # type: ignore
            from app.db.session import SessionLocal  # type: ignore
            from sqlalchemy import text  # type: ignore

            settings = get_settings()
            if not settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL.lower():
                sig.source = "skipped-sqlite"
                return sig

            with SessionLocal() as session:  # type: ignore[arg-type]
                row = session.execute(
                    text("SELECT COALESCE(MAX(position), 0) FROM audit_log")
                ).first()
                if row and row[0] is not None:
                    sig.chain_position = int(row[0])
                sig.source = "db"

                row2 = session.execute(
                    text(
                        "SELECT COUNT(*) FROM audit_log "
                        "WHERE created_at >= :since AND action = 'create'"
                    ),
                    {"since": self.since},
                ).first()
                if row2 and row2[0] is not None:
                    sig.recent_events = int(row2[0])
        except Exception:  # noqa: BLE001 — fail-soft
            sig.source = "unavailable"
        return sig

    # ─── LGPD signals (related, reused audit chain) ─────────────────
    def collect_lgpd_signals(self) -> dict[str, Any]:
        audit = self.collect_audit_chain()
        return {
            "audit_create_recent": audit.recent_events,
            "audit_chain_position": audit.chain_position,
            "source": audit.source,
        }

    # ─── HITL signals ────────────────────────────────────────────────
    def collect_hitl_signals(self) -> HitlSignal:
        sig = HitlSignal()
        sig.source = "unavailable"
        if self.offline:
            return sig
        try:
            sys.path.insert(0, str(ROOT / "backend"))
            from app.db.session import SessionLocal  # type: ignore
            from sqlalchemy import text  # type: ignore

            with SessionLocal() as session:  # type: ignore[arg-type]
                row = session.execute(
                    text("SELECT COUNT(*) FROM protocolo WHERE status = 'DRAFT'")
                ).first()
                sig.draft_protocols = int(row[0]) if row and row[0] is not None else 0
                sig.source = "db"
        except Exception:  # noqa: BLE001 — fail-soft
            sig.source = "unavailable"
        return sig

    # ─── wave progress ───────────────────────────────────────────────
    def collect_wave_progress(self) -> WaveSignal:
        sig = WaveSignal()
        if not self.super_plano.exists():
            return sig
        text = self.super_plano.read_text(encoding="utf-8", errors="replace")
        sig.done = len(re.findall(r"\[x\]", text, flags=re.I))
        sig.partial = len(re.findall(r"\[~\]", text))
        sig.pending = len(re.findall(r"\[ \]", text))

        # Próximas waves: linhas da tabela WAVE MAP com [ ]
        wave_section = re.search(r"## WAVE MAP.*?(?=\n## |\Z)", text, re.S)
        if wave_section:
            for line in wave_section.group(0).splitlines():
                if "|" in line and re.search(r"\[ \]", line):
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) >= 2 and cells[0].startswith("W"):
                        sig.next_wave = cells[0]
                        sig.next_tasks = re.findall(r"G8\.\d+\.T\d+", cells[1])
                        break
        return sig

    # ─── lesson count + ruff/mypy ───────────────────────────────────
    def collect_lessons(self) -> int:
        if not MEMORY_DIR.exists():
            return 0
        return sum(1 for f in MEMORY_DIR.glob("lesson-*.md") if f.is_file())

    def collect_quality_gates(self) -> tuple[bool | None, bool | None]:
        """Ruff + mypy: subprocess leve, fail-soft."""
        ruff_ok: bool | None = None
        mypy_ok: bool | None = None

        rc, _, _ = safe_run_git(["rev-parse", "--show-toplevel"], cwd=ROOT)
        if rc != 0:
            return ruff_ok, mypy_ok

        backend = ROOT / "backend"
        if not (backend / "pyproject.toml").exists():
            return ruff_ok, mypy_ok

        # Prefer `uv run` se disponível (gates oficiais rodam via venv uv).
        uv_bin = ROOT / ".venv" / "bin" / "python"
        py = str(uv_bin) if uv_bin.exists() else sys.executable

        def _gate(tool: str, args: list[str], timeout: int) -> bool | None:
            try:
                proc = subprocess.run(
                    [py, "-m", tool, *args],
                    cwd=str(backend),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return None
            if proc.returncode == 0:
                return True
            # Module not found → gate rodou, mas tool indisponível neste python
            stderr = (proc.stderr or "").lower()
            if "no module named" in stderr or "modulenotfounderror" in stderr:
                return None
            return False

        ruff_ok = _gate("ruff", ["check", "."], timeout=15)
        mypy_ok = _gate("mypy", ["app/"], timeout=60)
        return ruff_ok, mypy_ok

    # ─── orchestration ───────────────────────────────────────────────
    def collect_all(self) -> StabilityReport:
        rep = StabilityReport(
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            window_label=self.window_label,
            since=self.since.isoformat(timespec="seconds"),
            until=self.until.isoformat(timespec="seconds"),
            offline=self.offline,
        )
        rep.services = self.collect_api_health()
        rep.git = self.collect_git_metrics()
        rep.pytest = self.collect_pytest_metrics()
        rep.audit = self.collect_audit_chain()
        rep.hitl = self.collect_hitl_signals()
        rep.wave = self.collect_wave_progress()
        rep.lesson_count = self.collect_lessons()
        rep.ruff_clean, rep.mypy_clean = self.collect_quality_gates()
        if self.offline:
            rep.notes.append("offline mode: HTTP probes pulados; DB opcional")
        if not AUDIT_LOG_TABLES_SQL.exists():
            rep.notes.append("audit_log model ausente — métricas LGPD vêm de estado do loop")
        return rep


# ─── renderers ────────────────────────────────────────────────────────────


def render_markdown(rep: StabilityReport) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Stability Report — Cartório 2º Notas")
    add("")
    add(f"- **Gerado em:** {rep.generated_at}")
    add(f"- **Janela:** `{rep.window_label}` (since {rep.since} → until {rep.until})")
    add(f"- **Modo:** `{'offline' if rep.offline else 'live'}`")
    add("")

    add("## 1. Serviços")
    add("")
    add("| Status | Serviço | Host | Latência | Detalhe |")
    add("|--------|---------|------|---------:|---------|")
    for s in rep.services:
        lat = f"{s.latency_ms} ms" if s.latency_ms is not None else "—"
        add(f"| {s.icon} | {s.name} | `{s.host}` | {lat} | {scrub_pii(s.detail)[:80]} |")
    add("")

    add("## 2. Métricas de entrega")
    add("")
    add(f"- **git_commits** (na janela): {rep.git.commits}")
    add(f"- **git_authors**: {', '.join(rep.git.authors) if rep.git.authors else '—'}")
    add(f"- **git_files_changed** (best-effort): {rep.git.files_changed}")
    add(
        f"- **git_last_sha**: `{rep.git.last_sha}` — {scrub_pii(rep.git.last_msg)} ({rep.git.last_author})"
    )
    add(f"- **pytest_cache_present**: {rep.pytest.cache_present}")
    add(
        f"- **pytest_lastfailed**: {rep.pytest.lastfailed if rep.pytest.lastfailed is not None else '—'}"
    )
    add(
        f"- **coverage_pct**: {rep.pytest.coverage_pct if rep.pytest.coverage_pct is not None else '—'}"
    )
    add(f"- **lesson_count**: {rep.lesson_count}")
    ruff = "OK" if rep.ruff_clean else ("FAIL" if rep.ruff_clean is False else "—")
    mypy = "OK" if rep.mypy_clean else ("FAIL" if rep.mypy_clean is False else "—")
    add(f"- **ruff**: {ruff} · **mypy**: {mypy}")
    add("")

    add("## 3. Sinais LGPD")
    add("")
    add(
        f"- **chain_position={rep.audit.chain_position if rep.audit.chain_position is not None else '?'}**"
    )
    add(
        f"- **audit_log.create_recent** (na janela): {rep.audit.recent_events if rep.audit.recent_events is not None else '?'}"
    )
    add(
        f"- **retention_events**: {rep.audit.retention_events if rep.audit.retention_events is not None else '—'}"
    )
    add(f"- **source**: `{rep.audit.source}`")
    add("")

    add("## 4. Sinais HITL")
    add("")
    add(
        f"- **protocolo.status=DRAFT** pendentes: {rep.hitl.draft_protocols if rep.hitl.draft_protocols is not None else '?'}"
    )
    add(f"- **source**: `{rep.hitl.source}`")
    add("")

    add("## 5. Progresso do SUPER_PLANO_G8_100_TASKS.md")
    add("")
    add(f"- **[x] done**: {rep.wave.done}")
    add(f"- **[~] partial**: {rep.wave.partial}")
    add(f"- **[ ] pending**: {rep.wave.pending}")
    if rep.wave.next_wave:
        add(
            f"- **Próxima wave**: `{rep.wave.next_wave}` — tasks: {', '.join(rep.wave.next_tasks) or '?'}"
        )
    add("")

    if rep.notes:
        add("## 6. Notas")
        add("")
        for n in rep.notes:
            add(f"- {n}")
        add("")

    add("---")
    add("")
    add("_Modified by Gustavo Almeida — G8 Wave 44 / Squad 16 (cartorio-dev)._")
    return "\n".join(lines) + "\n"


# ─── CLI ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stability Report — coletor de sinais operacionais no fim de cada wave (G8.16.T4)."
    )
    parser.add_argument(
        "--window",
        choices=sorted(WINDOWS.keys()),
        default="24h",
        help="Janela predefinida (default: 24h)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO timestamp inicial (override --window)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Arquivo de saída (.md ou .json). Default: stdout",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída em JSON ao invés de Markdown",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Não chama HTTP/DB; usa só arquivos locais",
    )
    parser.add_argument(
        "--super-plano",
        type=Path,
        default=None,
        help="Caminho alternativo para SUPER_PLANO (default: SUPER_PLANO_G8_100_TASKS.md)",
    )
    args = parser.parse_args(argv)

    try:
        collector = StabilityCollector(
            window=args.window,
            since=args.since,
            offline=args.offline,
            super_plano=args.super_plano,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rep = collector.collect_all()

    if args.json:
        body = json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)
    else:
        body = render_markdown(rep)

    body = scrub_pii(body)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body, encoding="utf-8")
        print(f"OK report -> {args.output}", file=sys.stderr)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
