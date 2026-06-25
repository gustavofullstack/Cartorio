"""Testes do Session Memory Template (BRAIN6)."""
from __future__ import annotations

import re

import pytest  # noqa: E402

from brain.session_memory import (  # noqa: E402
    SessionSummary,
    build_summary,
    example_session,
    generate_session_id,
)


def test_session_summary_obrigatorio_tem_campos_basicos() -> None:
    """SessionSummary requer session_id, date, start/end_time."""
    s = SessionSummary(
        session_id="test-1",
        date="2026-06-26",
        start_time="10:00",
        end_time="11:00",
        pytest_passed_before=100,
        pytest_passed_after=110,
    )
    assert s.session_id == "test-1"
    assert s.pytest_passed_after - s.pytest_passed_before == 10


def test_build_summary_renderiza_md_valido() -> None:
    """build_summary retorna markdown com secoes canonicas."""
    md = build_summary(example_session())

    # Headers canonicos
    assert "# SESSION_SUMMARY" in md
    assert "## 🚦 Gates" in md
    assert "## ✅ Trabalho entregue" in md
    assert "## 📚 Lessons aprendidas" in md
    assert "## ⚠️ Anti-patterns" in md
    assert "## 📌 Pendências externas" in md
    assert "## 🔄 Próximas trilhas" in md


def test_build_summary_delta_pytest_calculado() -> None:
    """Delta pytest eh calculado corretamente."""
    s = SessionSummary(
        session_id="t",
        date="2026-06-26",
        start_time="00:00",
        end_time="01:00",
        pytest_passed_before=100,
        pytest_passed_after=150,
    )
    md = build_summary(s)
    assert "| 100 | 150 | +50 |" in md or "100 | 150" in md


def test_build_summary_servicos_saude_corretos() -> None:
    """Servicos online/total exibidos corretamente."""
    s = SessionSummary(
        session_id="t",
        date="2026-06-26",
        start_time="00:00",
        end_time="01:00",
        pytest_passed_before=0,
        pytest_passed_after=0,
        services_online=5,
        services_total=7,
    )
    md = build_summary(s)
    assert "5/7 online" in md


def test_build_summary_health_status_cores() -> None:
    """Health status renderiza com cores (green/yellow/red)."""
    for status, cor in [("green", "🟢"), ("yellow", "🟡"), ("red", "🔴")]:
        s = SessionSummary(
            session_id="t",
            date="2026-06-26",
            start_time="00:00",
            end_time="01:00",
            pytest_passed_before=0,
            pytest_passed_after=0,
            health_radar_status=status,
        )
        md = build_summary(s)
        assert cor in md


def test_build_summary_lista_vazia_renderiza_negrito() -> None:
    """Lista vazia renderiza '(nenhum)' em italico (LGPD-friendly)."""
    s = SessionSummary(
        session_id="t",
        date="2026-06-26",
        start_time="00:00",
        end_time="01:00",
        pytest_passed_before=0,
        pytest_passed_after=0,
    )
    md = build_summary(s)
    assert "_(nenhum)_" in md


def test_generate_session_id_formato_canonico() -> None:
    """Session ID no formato YYYY-MM-DD-agent-sequence."""
    import datetime as dt

    sid = generate_session_id(dt.date(2026, 6, 26), "zcode", 3)
    assert sid == "2026-06-26-zcode-3"


def test_generate_session_id_default_sequence() -> None:
    """Sequence default = 1."""
    import datetime as dt

    sid = generate_session_id(dt.date(2026, 6, 26))
    assert sid.endswith("-1")


def test_example_session_valido() -> None:
    """example_session retorna SessionSummary valido."""
    s = example_session()
    assert s.session_id
    assert s.pytest_passed_after >= s.pytest_passed_before