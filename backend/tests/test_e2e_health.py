"""F05 E2E health smoke test.

Verifica que Playwright + chromium binary estao disponiveis antes da suite
E2E completa rodar. Falha LOUD se setup estiver quebrado (drift entre
dev e CI).

NAO usa marker `e2e` para rodar em CI unit (catches regression de setup).
Tests E2E propriamente ditos estao em `tests/e2e/test_full_flow.py`.

Cenarios:
  1. Playwright python lib instalado
  2. pytest-playwright plugin carregado (ou playwright.sync_api)
  3. chromium browser binary disponivel (Playwright install rodou)
  4. playwright CLI disponivel (warning se nao)
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


def test_playwright_lib_instalado() -> None:
    """Playwright python lib esta instalado.

    SKIP (nao FAIL) se nao instalado: o objetivo deste test e detectar
    DRIFT (ex: dev instalou mas CI esquceu). Em CI unit sem Playwright,
    o teste simplesmente eh skip — a suite E2E nao roda de qualquer forma
    porque `addopts` exclui marker `e2e`.
    """
    pytest.importorskip(
        "playwright",
        reason="playwright NAO instalado (CI unit pula suite E2E via marker)",
    )


def test_pytest_playwright_plugin_ou_sync_api() -> None:
    """pytest-playwright plugin ou playwright.sync_api disponivel.

    Mesma logica do test anterior: skip se Playwright NAO instalado.
    Falha loud apenas se Playwright ESTA instalado mas os bindings estao
    quebrados (drift real de setup).
    """
    pytest.importorskip(
        "playwright",
        reason="playwright NAO instalado (CI unit pula suite E2E via marker)",
    )
    # Se chegamos aqui, Playwright esta instalado. Verifica bindings.
    try:
        import pytest_playwright  # type: ignore[import-not-found]  # noqa: F401

        return
    except ImportError:
        pass
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]  # noqa: F401

        return
    except ImportError as exc:
        pytest.fail(
            f"Playwright instalado mas bindings quebrados. "
            f"Reinstale: uv sync --extra e2e --force-reinstall. Erro: {exc}"
        )


def test_chromium_browser_disponivel() -> None:
    """Chromium binary esta instalado via `playwright install`.

    Playwright guarda browsers em ~/.cache/ms-playwright/ por default.
    Verifica existencia de chromium-<rev>/chrome-linux/chrome (Linux) ou
    chrome-mac/Chromium.app (macOS).
    """
    cache_root = Path.home() / ".cache" / "ms-playwright"
    if not cache_root.exists():
        pytest.skip(
            f"Playwright cache root ausente: {cache_root}. "
            f"Rode: playwright install chromium. "
            f"Suite E2E NAO pode rodar sem browser instalado."
        )

    # Procura qualquer versao de chromium-* (Playwright versiona dirs).
    chromium_dirs = sorted(cache_root.glob("chromium-*"))
    assert chromium_dirs, f"Nenhum chromium-* em {cache_root}. Rode: playwright install chromium"

    # Verifica que o binary existe em pelo menos 1 instalacao.
    found_binary = False
    for d in chromium_dirs:
        candidates = [
            d / "chrome-linux" / "chrome",
            d / "chrome-linux" / "headless_shell",
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


def test_playwright_cli_no_path() -> None:
    """CLI playwright esta disponivel (instala browser deps).

    Nao-fatal se nao estiver no PATH — apenas warning. pytest-playwright
    pode usar Playwright Python API direto.
    """
    playwright_cli = shutil.which("playwright")
    if playwright_cli is not None:
        return  # OK — CLI disponivel.

    # Em ambientes CI headless, playwright pode estar em .venv/bin/.
    venv_playwright = Path(".venv") / "bin" / "playwright"
    if venv_playwright.exists():
        return  # OK — CLI em .venv.

    # Warning nao-fatal — suite E2E ainda funciona via Python API.
    import warnings

    warnings.warn(
        "playwright CLI nao encontrada no PATH. "
        "Suite ainda funciona via Python API mas `playwright install` "
        "via CLI nao estara disponivel para setup manual.",
        stacklevel=2,
    )
