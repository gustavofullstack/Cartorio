"""Testes A22 — Cache warming cron 06:00 BRT."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.cache_warming import TIPOS_PRINCIPAIS, VALORES_TIPICOS, warm_emolumento_cache


def test_tipos_principais_contem_escritura_e_certidao() -> None:
    """Lista de tipos principais inclui os 3 mais usados."""
    assert "escritura_compra_venda" in TIPOS_PRINCIPAIS
    assert "certidao_negativa" in TIPOS_PRINCIPAIS
    assert "procuracao" in TIPOS_PRINCIPAIS


def test_valores_tipicos_cobrem_faixa_real() -> None:
    """Valores tipicos cobrem 10k a 1M (90% dos casos)."""
    assert min(VALORES_TIPICOS) <= 10_000.0
    assert max(VALORES_TIPICOS) >= 1_000_000.0


def test_warm_emolumento_cache_com_mock() -> None:
    """warm roda todos tipos*valores com funcao mockada."""
    mock_func = MagicMock(return_value={"valor_base": 100.0, "valor_total": 108.0})
    with patch("app.services.emolumento_cache.set_cached") as mock_set:
        result = warm_emolumento_cache(emolumento_func=mock_func)
    # 8 tipos * 6 valores = 48
    assert result["cached"] == len(TIPOS_PRINCIPAIS) * len(VALORES_TIPICOS)
    assert result["errors"] == 0
    assert mock_func.call_count == len(TIPOS_PRINCIPAIS) * len(VALORES_TIPICOS)
    assert mock_set.call_count == len(TIPOS_PRINCIPAIS) * len(VALORES_TIPICOS)


def test_warm_emolumento_cache_com_erros() -> None:
    """warm continua mesmo se algumas chamadas falham."""
    def fake_calc(tipo_documento, valor):
        if valor == 50_000.0:
            raise RuntimeError("simulado")
        return {"valor_total": 108.0}

    with patch("app.services.emolumento_cache.set_cached"):
        result = warm_emolumento_cache(emolumento_func=fake_calc)
    # 8 tipos * 1 erro cada (valor 50k) = 8 errors
    assert result["errors"] == 8
    # 8*6 - 8 = 40 sucessos
    assert result["cached"] == (len(TIPOS_PRINCIPAIS) * len(VALORES_TIPICOS)) - 8


def test_warm_retorna_duracao_ms() -> None:
    """Result inclui duracao_ms (sempre presente)."""
    result = warm_emolumento_cache(emolumento_func=MagicMock(return_value={}))
    assert "duration_ms" in result
    assert result["duration_ms"] >= 0
