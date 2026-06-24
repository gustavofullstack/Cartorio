"""Cache warming cron 06:00 BRT (A22).

Pre-aquece cache de emolumento antes do expediente abrir.
Tipos principais: escritura, certidao, procurao, declaracao, etc.
LGPD: log apenas count + duration, NAO expoe valores calculados.
"""
from __future__ import annotations

import dataclasses
import logging
import time
from typing import Any, Callable

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

# Folhas tipicas (cobre 90% dos casos reais). valor (R$) nao afeta emolumento
# tabelado por tipo, mas cache key inclui valor=0.0 para compatibilidade com
# a API publica de emolumento_cache.set_cached.
FOLHAS_TIPICAS: tuple[int, ...] = (1, 2, 5, 10)


def warm_emolumento_cache(
    emolumento_func: Callable[..., Any] | None = None,
) -> dict:
    """Pre-aquece cache de emolumento para tipos+folhas tipicos.

    Args:
        emolumento_func: funcao de calculo (default: app.services.emolumento.calcular).
                         Parametrizada para testabilidade.

    Returns:
        dict com stats: {cached: int, errors: int, duration_ms: int}
    """
    if emolumento_func is None:
        from app.services.emolumento import calcular

        emolumento_func = calcular

    # Import lazy para evitar circular import
    from app.services.emolumento_cache import set_cached

    start = time.perf_counter()
    cached = 0
    errors = 0
    for tipo in TIPOS_PRINCIPAIS:
        for folhas in FOLHAS_TIPICAS:
            try:
                # calcular() aceita: tipo, *, folhas, urgencia, tabela, ...
                result = emolumento_func(tipo, folhas=folhas, urgencia=False)
                # CalculoEmolumento e um @dataclass: serializar com asdict
                # Cast explicito para mypy (Callable[..., Any] -> objeto concreto)
                if dataclasses.is_dataclass(result):
                    payload: dict = dataclasses.asdict(result)  # type: ignore[arg-type]
                else:
                    payload = dict(result)
                # set_cached espera (tipo_documento, valor, payload)
                # Como o emolumento tabelado nao depende do valor monetario,
                # usamos 0.0 (fornece uma chave canonica "emolumento:{tipo}:0").
                set_cached(tipo, 0.0, payload)
                cached += 1
            except Exception as e:
                logger.warning("cache_warming falhou para %s/%dfolhas: %s", tipo, folhas, e)
                errors += 1
    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "cache_warming: cached=%d errors=%d duration_ms=%d",
        cached,
        errors,
        duration_ms,
    )
    return {"cached": cached, "errors": errors, "duration_ms": duration_ms}
