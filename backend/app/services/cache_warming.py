"""Cache warming cron 06:00 BRT (A22).

Pre-aquece cache de emolumento antes do expediente abrir.
Tipos principais: escritura, certidao, procurao, declaracao, etc.
LGPD: log apenas count + duration, NAO expoe valores calculados.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Tipos principais a pre-aquecer (TABELA_2026_MG)
TIPOS_PRINCIPAIS: tuple[str, ...] = (
    "escritura_compra_venda",
    "escritura_doacao",
    "certidao_negativa",
    "certidao_positiva",
    "procuracao",
    "declaracao",
    "reconhecimento_firma",
    "autenticacao",
)

# Valores tipicos (range) - cobre 90% dos casos reais
VALORES_TIPICOS: tuple[float, ...] = (
    10_000.0, 50_000.0, 100_000.0, 250_000.0, 500_000.0, 1_000_000.0,
)


def warm_emolumento_cache(emolumento_func: Any | None = None) -> dict:
    """Pre-aquece cache de emolumento para tipos+valores tipicos.

    Args:
        emolumento_func: funcao de calculo (default: app.services.emolumento.calcular).
                         Parametrizada para testabilidade.

    Returns:
        dict com stats: {cached: int, errors: int, duration_ms: int}
    """
    if emolumento_func is None:
        from app.services.emolumento import calcular
        emolumento_func = calcular

    start = time.perf_counter()
    cached = 0
    errors = 0
    for tipo in TIPOS_PRINCIPAIS:
        for valor in VALORES_TIPICOS:
            try:
                result = emolumento_func(tipo_documento=tipo, valor=valor)
                # Salva no cache (import lazy para evitar circular)
                from app.services.emolumento_cache import set_cached
                set_cached(tipo, valor, result)
                cached += 1
            except Exception as e:
                logger.warning("cache_warming falhou para %s/%s: %s", tipo, valor, e)
                errors += 1
    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info("cache_warming: cached=%d errors=%d duration_ms=%d", cached, errors, duration_ms)
    return {"cached": cached, "errors": errors, "duration_ms": duration_ms}
