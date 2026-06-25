"""Session Memory Template (BRAIN6).

Template estruturado para SESSION_SUMMARY_<data>.md.
Garante consistencia entre sessoes e facilita context loop engineer.

Uso:
    from brain.session_memory import SessionSummary, build_summary
    summary = SessionSummary(
        session_id="2026-06-26-zcode-1",
        date="2026-06-26",
        squad_completed="BRAIN4-6",
        tasks_done=12,
        pytest_before=952,
        pytest_after=1205,
        # ...
    )
    md_content = build_summary(summary)
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SessionSummary:
    """Sessao completa com stats + tasks + lessons."""

    session_id: str  # 2026-06-26-zcode-1
    date: str  # 2026-06-26
    start_time: str  # 15:30 BRT
    end_time: str  # 18:45 BRT

    # Stats gates
    pytest_passed_before: int
    pytest_passed_after: int
    mypy_errors: int = 0
    ruff_errors: int = 0

    # Tasks
    squad_completed: str = ""  # ex: "BRAIN4-6"
    tasks_done_today: int = 0
    tasks_pending_today: int = 0
    commits_pushed: int = 0

    # Health
    health_radar_status: str = "green"  # green / yellow / red
    services_online: int = 0
    services_total: int = 7

    # Lessons
    lessons_learned: tuple[str, ...] = field(default_factory=tuple)
    anti_patterns: tuple[str, ...] = field(default_factory=tuple)

    # Pendencias
    pendencias_externas: tuple[str, ...] = field(default_factory=tuple)

    # Proximas
    proximas_trilhas: tuple[str, ...] = field(default_factory=tuple)

    # Resumo livre
    highlights: tuple[str, ...] = field(default_factory=tuple)


# ============================================================================
# Markdown builder
# ============================================================================


TEMPLATE = """# SESSION_SUMMARY — {date}

> **Session ID**: `{session_id}`
> **Horário**: {start_time} → {end_time} BRT
> **Owner**: ZCode/Mavis (orquestrador) + Gustavo Almeida (CEO)

---

## 🚦 Gates

| Métrica | Antes | Depois | Delta |
|---|---:|---:|---:|
| **pytest passed** | {pytest_before} | {pytest_after} | {delta_pytest:+d} |
| **mypy errors** | — | {mypy_errors} | ✅ 0 |
| **ruff errors** | — | {ruff_errors} | ✅ clean |
| **Health radar** | — | {health_status} | {services_online}/{services_total} online |

---

## ✅ Trabalho entregue

**Squads completados**: {squad_completed}

**Tasks**: {tasks_done} done | {tasks_pending} pending

**Commits pushed**: {commits_pushed} to origin/master

### Highlights
{highlights_md}

---

## 📚 Lessons aprendidas (esta sessão)

{lessons_md}

---

## ⚠️ Anti-patterns identificados

{antipatterns_md}

---

## 📌 Pendências externas (precisam ação Gustavo)

{pendencias_md}

---

## 🔄 Próximas trilhas

{proximas_md}

---

**Modified by**: ZCode/Mavis (orquestrador)
**Próxima sessão**: retomar via `loop-state.json` + `index.md`
"""


def _format_list_md(items: tuple[str, ...], prefix: str = "-") -> str:
    """Formata lista como markdown bullets."""
    if not items:
        return f"{prefix} _(nenhum)_"
    return "\n".join(f"{prefix} {item}" for item in items)


def build_summary(summary: SessionSummary) -> str:
    """Constroi SESSION_SUMMARY markdown completo."""
    delta_pytest = summary.pytest_passed_after - summary.pytest_passed_before
    health_status = (
        "🟢 GREEN" if summary.health_radar_status == "green" else
        "🟡 YELLOW" if summary.health_radar_status == "yellow" else
        "🔴 RED"
    )

    return TEMPLATE.format(
        date=summary.date,
        session_id=summary.session_id,
        start_time=summary.start_time,
        end_time=summary.end_time,
        pytest_before=summary.pytest_passed_before,
        pytest_after=summary.pytest_passed_after,
        delta_pytest=delta_pytest,
        mypy_errors=summary.mypy_errors,
        ruff_errors=summary.ruff_errors,
        health_status=health_status,
        services_online=summary.services_online,
        services_total=summary.services_total,
        squad_completed=summary.squad_completed,
        tasks_done=summary.tasks_done_today,
        tasks_pending=summary.tasks_pending_today,
        commits_pushed=summary.commits_pushed,
        highlights_md=_format_list_md(summary.highlights),
        lessons_md=_format_list_md(summary.lessons_learned),
        antipatterns_md=_format_list_md(summary.anti_patterns),
        pendencias_md=_format_list_md(summary.pendencias_externas),
        proximas_md=_format_list_md(summary.proximas_trilhas),
    )


def generate_session_id(date: dt.date, agent: str = "zcode", sequence: int = 1) -> str:
    """Gera session_id canon: YYYY-MM-DD-agent-sequence."""
    return f"{date.isoformat()}-{agent}-{sequence}"


# ============================================================================
# Test helpers
# ============================================================================


def example_session() -> SessionSummary:
    """Exemplo de SessionSummary para testes/demo."""
    return SessionSummary(
        session_id="2026-06-26-zcode-1",
        date="2026-06-26",
        start_time="15:30",
        end_time="18:45",
        pytest_passed_before=1205,
        pytest_passed_after=1210,
        squad_completed="BRAIN6",
        tasks_done_today=1,
        tasks_pending_today=39,
        commits_pushed=1,
        services_online=7,
        lessons_learned=(
            "BRAIN6: Session memory template padroniza SUMMARY_*.md",
        ),
        proximas_trilhas=(
            "BRAIN7 lessons cross-rein",
            "A26 retomada",
        ),
    )