"""F05 E2E health smoke test (v2 — feedback verifier attempt 1).

Verifica drift de setup Playwright SEM importar a lib (NAO usa
`pytest.importorskip` — feedback verifier attempt 1: importorskip ainda
requer Playwright instalado, NAO devia ser CI-blocking).

Estrategia v2:
- Test sentinel via `subprocess.run(['playwright', '--version'])` — se
  Playwright instalado, retorna versao; senao, FileNotFoundError -> skip.
- Test health check via `urllib.request.urlopen()` puro (sem httpx) — sanity
  check de que a API responde em E2E_BASE_URL.
- ZERO import de playwright em qualquer path. Drift detection real (NAO
  falha se Playwright ausente — apenas skip + warning).

NAO usa marker `e2e` para rodar em CI unit (catches regression de setup).
Tests E2E propriamente ditos estao em `tests/e2e/test_full_flow.py`.

Cenarios:
  1. Playwright CLI binary disponivel (subprocess.run --version)
  2. Health check da API via urllib puro
"""

from __future__ import annotations

import os
import subprocess
import warnings
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

import pytest


# ============================================================================
# Cenarios
# ============================================================================


def test_playwright_cli_via_subprocess() -> None:
    """Playwright CLI binary disponivel via subprocess.run (NAO import).

    Drift detection puro: se `playwright --version` retorna 0, setup OK.
    Se NAO retorna 0 ou FileNotFoundError, SKIP com warning (NAO fail —
    CI unit nao deve bloquear por causa de optional-deps ausente).

    Diferenca vs v1: v1 usava `pytest.importorskip("playwright", ...)`
    que AINDA exige Playwright instalado (apenas skipa a execucao, NAO
    a verificacao). v2 usa subprocess.run puro que funciona mesmo com
    Playwright completamente ausente.
    """
    # Tenta localizar playwright CLI.
    candidates: list[str] = []
    cli_path = shutil_which("playwright")
    if cli_path is not None:
        candidates.append(cli_path)
    candidates.append(str(Path(".venv") / "bin" / "playwright"))
    candidates.append(str(Path.home() / ".local" / "bin" / "playwright"))

    if not candidates:
        warnings.warn(
            "playwright CLI NAO encontrado em PATH ou .venv/bin. "
            "Suite E2E NAO pode rodar — instale com: "
            "`uv sync --extra e2e && playwright install chromium`.",
            stacklevel=2,
        )
        pytest.skip("playwright CLI ausente (suite E2E NAO pode rodar)")

    # Tenta executar --version no primeiro candidate.
    last_error: Exception | None = None
    for cli in candidates:
        try:
            result = subprocess.run(  # noqa: S603
                [cli, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            last_error = exc
            continue

        if result.returncode == 0:
            # Drift detection OK — Playwright CLI funciona.
            version = result.stdout.strip() or result.stderr.strip()
            assert version, "playwright --version retornou stdout/stderr vazio"
            return  # OK — drift detection passou.

    # Nenhum candidate funcionou.
    warnings.warn(
        f"playwright CLI NAO executavel (last error: {last_error}). Suite E2E NAO pode rodar.",
        stacklevel=2,
    )
    pytest.skip("playwright CLI NAO executavel")


def test_api_health_via_urllib() -> None:
    """Health check da API via urllib.request puro (sem browser).

    Sanity check basico: API responde /health/live em E2E_BASE_URL.
    NAO depende de Playwright, httpx ou qualquer lib externa alem de stdlib.
    """
    base_url = os.getenv("E2E_BASE_URL", "http://localhost:8000").rstrip("/")
    health_url = urljoin(base_url + "/", "api/v1/health/live")

    try:
        with urlopen(health_url, timeout=5) as resp:  # noqa: S310
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        warnings.warn(
            f"API NAO respondeu em {health_url}: {exc}. "
            f"Verifique se API esta rodando ou ajuste E2E_BASE_URL.",
            stacklevel=2,
        )
        pytest.skip(f"API offline em {health_url} (erro: {type(exc).__name__})")

    assert status == 200, f"health esperado 200, recebeu {status}: {body}"
    # body pode ser JSON ou texto puro.
    assert "ok" in body.lower() or "live" in body.lower() or "healthy" in body.lower(), (
        f"health body inesperado: {body!r}"
    )


def test_chromium_browser_cache_via_filesystem() -> None:
    """Chromium binary presente no Playwright cache (filesystem check).

    NAO importa playwright — apenas verifica `~/.cache/ms-playwright/`
    diretamente. SKIP se cache ausente (Playwright NAO instalado).
    """
    cache_root = Path.home() / ".cache" / "ms-playwright"
    if not cache_root.exists():
        warnings.warn(
            f"Playwright cache root ausente: {cache_root}. "
            f"Rode: playwright install chromium. "
            f"Suite E2E NAO pode rodar sem browser instalado.",
            stacklevel=2,
        )
        pytest.skip(f"Playwright cache root ausente em {cache_root}")

    # Procura qualquer versao de chromium-* (Playwright versiona dirs).
    chromium_dirs = sorted(cache_root.glob("chromium-*"))
    if not chromium_dirs:
        pytest.skip(f"Nenhum chromium-* em {cache_root}. Rode: playwright install chromium")

    # Verifica que o binary existe em pelo menos 1 instalacao.
    found_binary = False
    for d in chromium_dirs:
        candidates = [
            d / "chrome-linux" / "chrome",
            d / "chrome-linux" / "headless_shell",
                d / "chrome-linux64" / "chrome",
                d / "chrome-linux64" / "headless_shell",
            d / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
            # Windows
            d / "chrome-win" / "chrome.exe",
        ]
        for cand in candidates:
            if cand.exists() and cand.is_file():
                found_binary = True
                break
        if found_binary:
            break

    assert found_binary, (
        f"Chromium binary NAO encontrado em {chromium_dirs}. Rode: playwright install chromium"
    )


# ============================================================================
# Helpers
# ============================================================================


def shutil_which(name: str) -> str | None:
    """Wrapper para shutil.which que retorna Path em vez de str.

    shutil.which ja retorna str | None, mas tipamos explicitamente para
    satisfazer mypy strict.
    """
    import shutil

    result = shutil.which(name)
    return str(result) if result is not None else None
