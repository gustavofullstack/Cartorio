"""Cálculo seguro e determinístico para regras de ConhecimentoInstitucional.

As expressões são dados declarativos: não há ``eval``, import dinâmico, I/O ou
coerção de ``float``. A única superfície aceita é uma gramática pequena:
``fixed``, ``percentage`` e ``sum``.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from re import fullmatch
from typing import Any

from app.models.conhecimento_institucional import EstadoConhecimento


class RegraDeclarativaInvalidaError(ValueError):
    """Regra fora da gramática fechada permitida."""


class ContextoCalculoInvalidoError(ValueError):
    """Valor de contexto ausente ou não seguro para cálculo monetário."""


class EstadoConhecimentoInvalidoError(ValueError):
    """Regra não publicada, portanto indisponível para cálculo automático."""


_MONEY = Decimal("0.01")
_MAX_RULE_DEPTH = 10
_MAX_SUM_ITEMS = 100
_MAX_VALUE = Decimal("1000000000000")
_MAX_DECIMAL_PLACES = 10


def gerar_chave_idempotencia(content_sha256: str, version_number: int) -> str:
    """Gera chave estável da identidade imutável da versão de conhecimento."""
    if fullmatch(r"[0-9a-fA-F]{64}", content_sha256) is None or version_number <= 0:
        raise ValueError("identidade de versão inválida")
    return sha256(f"{content_sha256.lower()}:{version_number}".encode()).hexdigest()


def calcular_regra_declarativa(
    regra: Mapping[str, Any],
    contexto: Mapping[str, Any],
    *,
    estado: str,
) -> Decimal:
    """Calcula uma regra ``PUBLISHED`` usando apenas ``Decimal``.

    A publicação é a barreira fail-closed: uma regra capturada, classificada
    ou somente aprovada ainda exige a publicação explícita antes de ser usada.
    """
    if estado != EstadoConhecimento.PUBLISHED:
        raise EstadoConhecimentoInvalidoError("regra de cálculo não está publicada")
    resultado = _calcular_expressao(regra, contexto, depth=0)
    if resultado > _MAX_VALUE:
        raise RegraDeclarativaInvalidaError("resultado excede o limite monetário")
    return resultado.quantize(_MONEY, rounding=ROUND_HALF_UP)


def _calcular_expressao(
    expressao: Mapping[str, Any], contexto: Mapping[str, Any], *, depth: int
) -> Decimal:
    if depth >= _MAX_RULE_DEPTH:
        raise RegraDeclarativaInvalidaError("profundidade máxima da regra excedida")
    operator = expressao.get("operator")
    if operator == "fixed":
        _validar_campos(expressao, {"operator", "amount"})
        return _coagir_decimal(expressao.get("amount"), "amount")
    if operator == "percentage":
        _validar_campos(expressao, {"operator", "base", "rate"})
        base_name = expressao.get("base")
        if not isinstance(base_name, str) or not base_name:
            raise RegraDeclarativaInvalidaError("base percentual inválida")
        base = _coagir_contexto(contexto, base_name)
        rate = _coagir_decimal(expressao.get("rate"), "rate")
        if rate > Decimal("1"):
            raise RegraDeclarativaInvalidaError("rate deve estar entre zero e um")
        resultado = base * rate
        if resultado > _MAX_VALUE:
            raise RegraDeclarativaInvalidaError("resultado excede o limite monetário")
        return resultado
    if operator == "sum":
        _validar_campos(expressao, {"operator", "items"})
        items = expressao.get("items")
        if not isinstance(items, list) or not items:
            raise RegraDeclarativaInvalidaError("sum exige uma lista não vazia de items")
        if len(items) > _MAX_SUM_ITEMS:
            raise RegraDeclarativaInvalidaError("sum excede o limite de items")
        total = Decimal("0")
        for item in items:
            if not isinstance(item, Mapping):
                raise RegraDeclarativaInvalidaError("item de sum deve ser um objeto declarativo")
            total += _calcular_expressao(item, contexto, depth=depth + 1)
            if total > _MAX_VALUE:
                raise RegraDeclarativaInvalidaError("resultado excede o limite monetário")
        return total
    raise RegraDeclarativaInvalidaError("operator não permitido")


def _validar_campos(expressao: Mapping[str, Any], permitidos: set[str]) -> None:
    if set(expressao) != permitidos:
        raise RegraDeclarativaInvalidaError("campos declarativos inválidos")


def _coagir_contexto(contexto: Mapping[str, Any], name: str) -> Decimal:
    if name not in contexto:
        raise ContextoCalculoInvalidoError(f"contexto ausente: {name}")
    return _coagir_decimal(contexto[name], name, context_value=True)


def _coagir_decimal(value: Any, name: str, *, context_value: bool = False) -> Decimal:
    error = ContextoCalculoInvalidoError if context_value else RegraDeclarativaInvalidaError
    if isinstance(value, bool) or isinstance(value, float):
        raise error(f"{name} deve ser Decimal, int ou string decimal")
    if not isinstance(value, (Decimal, int, str)):
        raise error(f"{name} deve ser Decimal, int ou string decimal")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError):
        raise error(f"{name} não é decimal válido") from None
    if not result.is_finite():
        raise error(f"{name} deve ser finito")
    if result < Decimal("0"):
        raise error(f"{name} não pode ser negativo")
    if result > _MAX_VALUE:
        raise error(f"{name} excede o limite permitido")
    exponent = result.as_tuple().exponent
    if not isinstance(exponent, int):
        raise error(f"{name} deve ser decimal finito")
    if exponent < -_MAX_DECIMAL_PLACES:
        raise error(f"{name} excede a precisão decimal permitida")
    return result


__all__ = [
    "ContextoCalculoInvalidoError",
    "EstadoConhecimentoInvalidoError",
    "RegraDeclarativaInvalidaError",
    "calcular_regra_declarativa",
    "gerar_chave_idempotencia",
]
