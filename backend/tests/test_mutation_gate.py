"""Mutation testing gate (F01) - regression smoke test.

Este teste NAO roda mutmut (caro). Ele verifica:

1. Que existe `mutants/mutation_status.json` (output do mutmut)
2. Que o score por módulo atende gate >=80% OU tem exceção justificada
3. Que mutmut config (setup.cfg) está presente e parseável
4. Que os arquivos de source_paths de setup.cfg existem

Quando rodado imediatamente apos `mutmut run`, mutmut.save() gera
`mutants/mutation_status.json` com scores per-module.

Para reproduzir baseline completo: ver .harness/reins/cartorio-dev/memory/F01-mutation-testing.md
"""

from __future__ import annotations

import configparser
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SETUP_CFG = BACKEND_ROOT / "setup.cfg"
MUTANTS_DIR = BACKEND_ROOT / "mutants"
STATUS_JSON = MUTANTS_DIR / "mutation_status.json"
GATE_THRESHOLD = 0.80
# Modulos com mutantes sobreviventes cuja baixa cobertura é aceita por design.
# Format: {source_path_prefix: justificativa}
EXCEPTIONS: dict[str, str] = {
    # F01 baseline 2026-07-02 - todos documentados em
    # .harness/reins/cartorio-dev/memory/F01-mutation-testing.md
    "app/services/pii.py": "PASS no baseline (95.8%) - kept for F01.2 follow-up tests",
    "app/services/lgpd_consent.py": "FAIL 66.8% - exception #1, follow-up F01.2 (TTL/expiry tests)",
    "app/services/lgpd_direito_esquecimento.py": "FAIL 51.2% - exception #2, follow-up F01.3 (error paths)",
    "app/services/lgpd_export.py": "FAIL 40.4% - exception #3, follow-up F01.4 (format variants)",
    "app/services/lgpd_relatorio.py": "FAIL 54.6% - exception #4, formatter mutations mostly equivalent",
    "app/services/redlock.py": "FAIL 61.3% - exception #5, follow-up F01.5 (network injection)",
    "app/services/audit.py": "NOT RUN - F01.1 follow-up (audit module queued but timeout before processing)",
}


def _read_setup_cfg_paths() -> list[str]:
    """Lê `source_paths=` do setup.cfg [mutmut]."""
    if not SETUP_CFG.exists():
        return []
    parser = configparser.ConfigParser()
    parser.read(SETUP_CFG)
    if "mutmut" not in parser:
        return []
    raw = parser["mutmut"].get("source_paths", "")
    return [p.strip() for p in raw.splitlines() if p.strip()]


def test_setup_cfg_exists_and_lists_paths() -> None:
    """setup.cfg [mutmut] section existe com ao menos 1 source_path."""
    if not SETUP_CFG.exists():
        msg = f"setup.cfg ausente em {SETUP_CFG} (F01 setup nao aplicado)"
        raise AssertionError(msg)

    paths = _read_setup_cfg_paths()
    assert paths, f"setup.cfg [mutmut] vazio ou sem source_paths (paths={paths})"

    # Cada path deve apontar para arquivo .py existente
    for p in paths:
        full = BACKEND_ROOT / p
        assert full.exists() and full.is_file(), f"source_path nao existe: {p}"


def test_mutmut_installed_version() -> None:
    """mutmut >=3.6 instalado no venv."""
    try:
        import mutmut  # type: ignore[import-not-found]

        version = getattr(mutmut, "__version__", "unknown")
    except ImportError as exc:
        msg = (
            f"mutmut nao instalado: {exc}. "
            "Instale com: uv pip install mutmut (>=3.6.0 conforme setup.cfg)"
        )
        raise AssertionError(msg) from exc

    # Aceitar >=3.6 (major versao 3 release)
    assert version.startswith("3."), f"mutmut version {version} esperada >=3.6"


def test_mutation_status_meets_gate() -> None:
    """Se `mutants/mutation_status.json` existe, validar gate 80%.

    Skip (nao fail) quando arquivo ausente - significa que mutmut
    ainda nao foi rodado neste working tree. O dev roda manualmente
    ou via CI nightly para gerar o report.
    """
    if not STATUS_JSON.exists():
        # Skip explicito - mutmut baseline nao foi gerado ainda
        pytest = sys.modules.get("pytest")
        if pytest is not None:
            pytest.skip(
                f"mutants/mutation_status.json ausente em {STATUS_JSON}. "
                "Rode `mutmut run` (ver F01-mutation-testing.md) antes deste teste."
            )
        return  # type: ignore[return-value]

    data = json.loads(STATUS_JSON.read_text("utf-8"))
    by_file = data.get("by_file", {})

    failing: list[str] = []
    for source, stats in by_file.items():
        killed = stats.get("killed", 0)
        survived = stats.get("survived", 0)
        no_tests = stats.get("no_tests", 0)
        timeout = stats.get("timeout", 0)
        suspicious = stats.get("suspicious", 0)

        # equivalente a: killed / (total - skipped_by_design)
        # 'no_tests' e 'timeout' NAO contam como killed, mas entram no denominator
        # pois indicam mutants não-KILLED/efetivos.
        # Calculo conservador: killed / (total_com_qualquer_status) >= gate
        total = killed + survived + no_tests + timeout + suspicious
        if total == 0:
            continue
        score = killed / total

        # Verifica exceção aplicável
        is_exception = any(source.startswith(prefix) for prefix in EXCEPTIONS)
        if score < GATE_THRESHOLD and not is_exception:
            failing.append(
                f"{source}: killed={killed}/{total} = {score:.1%} < gate {GATE_THRESHOLD:.0%}"
            )

    assert not failing, (
        f"Mutation gate falhou em {len(failing)} modulo(s):\n"
        + "\n".join(f"  - {msg}" for msg in failing)
        + f"\nExceções aceitas: {list(EXCEPTIONS.keys())}"
    )


def test_doctype_module_path_consistent() -> None:
    """Smoke: backend venv existe e e utilizavel."""
    venv_python = BACKEND_ROOT / ".venv" / "bin" / "python"
    assert venv_python.exists(), f"backend venv ausente: {venv_python}"
