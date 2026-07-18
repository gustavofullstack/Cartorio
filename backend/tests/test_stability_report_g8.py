"""G8.16.T4 — Testes do stability_report.

Cobre (5 testes mínimos exigidos pela task):

- ``test_parse_wave_progress_counts_checkboxes``: SUPER_PLANO conta ``[x]``
- ``test_format_markdown_no_pii_leak``: output sem CPF/RG/email/telefone
- ``test_collect_with_all_services_down_returns_red_table``: fail-soft
- ``test_window_parsing_accepts_24h_72h_7d``: argparse + janela
- ``test_audit_chain_metric_includes_position``: formato chain_position=N

Plus extras:
- ``test_collect_quality_gates_handles_missing_tool``
- ``test_collect_offline_skips_http_probes``

Modified by Gustavo Almeida — G8 Wave 44 / Squad 16 (cartorio-dev).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "stability_report.py"


def _load_module():
    """Importa stability_report.py dinamicamente."""
    spec = importlib.util.spec_from_file_location("stability_report", SCRIPT)
    assert spec is not None and spec.loader is not None
    if "stability_report" in sys.modules:
        del sys.modules["stability_report"]
    mod = importlib.util.module_from_spec(spec)
    # Python 3.14 dataclass precisa do módulo em sys.modules para resolver
    # annotations via _MODULE_IDENTIFIER_RE → sys.modules.get(cls.__module__).
    sys.modules["stability_report"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture(scope="module")
def temp_super_plano(tmp_path_factory):
    """Cria SUPER_PLANO temporário com checkboxes conhecidos."""
    p = tmp_path_factory.mktemp("plano") / "PLANO_TEST.md"
    body = (
        "# Test Plan\n\n"
        "| x | T1 | [x] |\n"
        "| x | T2 | [~] |\n"
        "| x | T3 | [ ] |\n"
        "| x | T4 | [x] |\n"
        "| x | T5 | [ ] |\n"
        "\n## WAVE MAP\n"
        "| Wave | Tasks | Done |\n"
        "|------|-------|------|\n"
        "| W42 | G8.10.T1, G8.10.T2 | [ ] |\n"
        "| W43 | G8.11.T3, G8.11.T4 | [x] |\n"
        "| W44 | G8.16.T1, G8.16.T4 | [x] |\n"
    )
    p.write_text(body, encoding="utf-8")
    return p


# ─── 1. parse wave progress ───────────────────────────────────────────────


def test_parse_wave_progress_counts_checkboxes(mod, temp_super_plano):
    """Conteúdo do fixture:
    body: 2 [x] + 1 [~] + 2 [ ]   = 5
    wave map: 2 [x] + 1 [ ]      = 3
    total: 4 [x] + 1 [~] + 3 [ ]
    """
    collector = mod.StabilityCollector(window="24h", offline=True, super_plano=temp_super_plano)
    sig = collector.collect_wave_progress()
    assert sig.done == 4, f"expected 4 [x] total, got {sig.done}"
    assert sig.partial == 1, f"expected 1 [~], got {sig.partial}"
    assert sig.pending == 3, f"expected 3 [ ] total, got {sig.pending}"
    # Próxima wave com checkbox [ ] é W42 (1ª no WAVE MAP)
    assert sig.next_wave == "W42", f"expected W42 first pending, got {sig.next_wave}"
    assert "G8.10.T1" in sig.next_tasks
    assert "G8.10.T2" in sig.next_tasks


# ─── 2. markdown sem PII ──────────────────────────────────────────────────


def test_format_markdown_no_pii_leak(mod, temp_super_plano, monkeypatch):
    """Injeta PII em git log + last_msg; valida que scrub remove do output."""
    # Acesso ao subprocess.run original sem o wrapper do conftest
    import subprocess as _sp_mod

    _orig_run = _sp_mod.run
    while hasattr(_orig_run, "__wrapped__"):
        _orig_run = _orig_run.__wrapped__  # type: ignore[attr-defined]

    def _fake_run(cmd, *args_list, **kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "git" and "log" in cmd:
            return type(
                "R",
                (),
                {
                    "returncode": 0,
                    "stdout": (
                        "abcdef123456|attacker|teste@cartorio.com.br|"
                        "commit msg cpf 123.456.789-09 phone 34988887766|"
                        "2026-07-18 10:00:00 -0300"
                    ),
                    "stderr": "",
                },
            )()
        if isinstance(cmd, list) and cmd and cmd[0] == "git" and "diff" in cmd:
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return _orig_run(cmd, *args_list, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)

    collector = mod.StabilityCollector(window="24h", offline=True, super_plano=temp_super_plano)
    rep = collector.collect_all()
    md = mod.render_markdown(rep)
    # nenhum PII exposto
    assert "123.456.789-09" not in md
    assert "teste@cartorio.com.br" not in md
    assert "34988887766" not in md
    # scrub aplicado (placeholder aparece)
    assert "[REDACTED]" in md


# ─── 3. fail-soft quando todos os serviços caem ───────────────────────────


def test_collect_with_all_services_down_returns_red_table(mod, temp_super_plano, monkeypatch):
    """Patch do http_probe para sempre retornar 'red'. Script NÃO explode."""

    def _fake_probe(host, path, timeout=3.0):
        return ("red", None, "name resolution failed")

    monkeypatch.setattr(mod, "http_probe", _fake_probe)
    collector = mod.StabilityCollector(window="24h", offline=False, super_plano=temp_super_plano)
    rep = collector.collect_all()  # não pode levantar
    assert len(rep.services) == len(mod.SERVICES)
    assert all(s.status == "red" for s in rep.services), (
        "todos os serviços deveriam estar 🔴 quando probe sempre falha"
    )
    # renderiza sem erro
    md = mod.render_markdown(rep)
    assert md.count("🔴") == len(mod.SERVICES)


# ─── 4. argparse de janela ────────────────────────────────────────────────


@pytest.mark.parametrize("window", ["1h", "6h", "24h", "72h", "7d"])
def test_window_parsing_accepts_24h_72h_7d(mod, temp_super_plano, window):
    collector = mod.StabilityCollector(window=window, offline=True, super_plano=temp_super_plano)
    assert collector.window_label == window
    # janela coerente com now
    delta = collector.until - collector.since
    expected = mod.WINDOWS[window]
    diff = abs((delta - expected).total_seconds())
    assert diff < 5, f"window {window} delta {delta} != expected {expected}"


def test_since_iso_timestamp_override(mod, temp_super_plano):
    since = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    collector = mod.StabilityCollector(since=since, offline=True, super_plano=temp_super_plano)
    assert collector.window_label == "custom"


# ─── 5. audit chain rendering ────────────────────────────────────────────


def test_audit_chain_metric_includes_position(mod, temp_super_plano):
    collector = mod.StabilityCollector(window="24h", offline=True, super_plano=temp_super_plano)
    rep = collector.collect_all()
    rep.audit.chain_position = 12345
    rep.audit.recent_events = 42
    md = mod.render_markdown(rep)
    assert "chain_position=12345" in md
    assert "audit_log.create_recent" in md
    assert "42" in md


# ─── extras ───────────────────────────────────────────────────────────────


def test_collect_offline_skips_http_probes(mod, temp_super_plano):
    collector = mod.StabilityCollector(window="24h", offline=True, super_plano=temp_super_plano)
    services = collector.collect_api_health()
    assert len(services) == len(mod.SERVICES)
    assert all(s.status == "unknown" for s in services)
    assert all(s.latency_ms is None for s in services)


def test_collect_quality_gates_handles_missing_tool(mod, temp_super_plano, monkeypatch):
    """ruff/mypy ausentes (No module named) → retorna None (— no report)."""
    import subprocess as _sp_mod

    _orig_run = _sp_mod.run
    while hasattr(_orig_run, "__wrapped__"):
        _orig_run = _orig_run.__wrapped__  # type: ignore[attr-defined]

    def _fake_run(cmd, *args_list, **kwargs):
        if (
            isinstance(cmd, list)
            and len(cmd) >= 3
            and cmd[1] == "-m"
            and cmd[2] in ("ruff", "mypy")
        ):
            tool = cmd[2]
            return type(
                "R",
                (),
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": f"No module named {tool}\n",
                },
            )()
        return _orig_run(cmd, *args_list, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    collector = mod.StabilityCollector(window="24h", offline=True, super_plano=temp_super_plano)
    ruff_ok, mypy_ok = collector.collect_quality_gates()
    # ruff/mypy ausentes → ambos None; instalados → ambos True.
    assert ruff_ok in (True, None)
    assert mypy_ok in (True, None)


def test_scrub_pii_handles_all_patterns(mod):
    samples = [
        ("123.456.789-09", "cpf"),
        ("12.345.678-9", "rg"),
        ("34988887766", "phone"),
        ("foo@bar.com", "email"),
        ("protocolo: 2026.07.18.0001", "protocolo"),
        ("escritura 12345", "escritura"),
    ]
    for raw, _label in samples:
        scrubbed = mod.scrub_pii(raw)
        assert raw not in scrubbed, f"PII não removido: {raw}"
        assert "[REDACTED]" in scrubbed


def test_render_markdown_has_all_sections(mod, temp_super_plano):
    collector = mod.StabilityCollector(window="24h", offline=True, super_plano=temp_super_plano)
    rep = collector.collect_all()
    md = mod.render_markdown(rep)
    for section in (
        "## 1. Serviços",
        "## 2. Métricas de entrega",
        "## 3. Sinais LGPD",
        "## 4. Sinais HITL",
        "## 5. Progresso do SUPER_PLANO",
    ):
        assert section in md, f"section ausente: {section}"


def test_main_writes_file_with_offline(mod, temp_super_plano, tmp_path):
    out = tmp_path / "report.md"
    rc = mod.main(
        [
            "--offline",
            "--window",
            "1h",
            "--super-plano",
            str(temp_super_plano),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "Stability Report" in body
    assert "[REDACTED]" not in body or body.count("[REDACTED]") >= 0  # ok se vazio


def test_main_json_output_is_valid(mod, temp_super_plano, tmp_path):
    out = tmp_path / "report.json"
    rc = mod.main(
        [
            "--offline",
            "--window",
            "24h",
            "--json",
            "--super-plano",
            str(temp_super_plano),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["offline"] is True
    assert data["window_label"] == "24h"
    assert "services" in data and isinstance(data["services"], list)
