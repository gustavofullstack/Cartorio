"""Servico de Emolumento - calculo de custas cartorarias.

Tabela 2026 de emolumentos (placeholder - em producao vem de snapshot
oficial do estado). Cada calculo gera audit log imutavel.

Para producao:
- Tabela vem de carga automatica do Diario Oficial do estado
- Snapshot diario (data_vigencia) garante que calculos antigos
  nao recalculam retroativamente
- Validacao humana de qualquer excecao (isencao, gratuidade,
  urgencia justificada) - bot NAO aplica sozinho
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.services.emolumento_validacao import (
    ADICIONAL_FOLHA_PERCENTUAL,
    ADICIONAL_URGENCIA_PERCENTUAL,
    MAX_FOLHAS,
    MIN_FOLHAS,
    MOTIVOS_ISENCAO,
    TIPOS_GRATUITOS,
    isencao_aplicavel,
    validar_quantidade_folhas,
    validar_tipo,
)

# Re-exports preservam compat: callers que importavam de emolumento continuam OK.
# `isencao_aplicavel` é a regra fiscal pura (G8.11.T3 — SOLID SRP) — vem de
# ``emolumento_validacao`` para evitar duplicação que disparava mypy ``[no-redef]``.
__all__ = [
    "CalculoEmolumento",
    "EMOLUMENTOS_2026",
    "TIPOS_VALIDOS",
    "calcular",
    "isencao_aplicavel",
    "ADICIONAL_FOLHA_PERCENTUAL",
    "ADICIONAL_URGENCIA_PERCENTUAL",
    "MIN_FOLHAS",
    "MAX_FOLHAS",
    "TIPOS_GRATUITOS",
    "MOTIVOS_ISENCAO",
    "validar_tipo",
    "validar_quantidade_folhas",
]  # noqa: F401


# Tabela placeholder - MG 2026 (substituir por carga real do estado)
EMOLUMENTOS_2026: dict[str, Decimal] = {
    "certidao_negativa": Decimal("87.50"),
    "certidao_positiva": Decimal("92.30"),
    "certidao_casamento": Decimal("105.40"),
    "escritura_compra_venda": Decimal("4521.00"),
    "escritura_doacao": Decimal("3205.50"),
    "procuracao": Decimal("156.40"),
    "autenticacao": Decimal("28.90"),
    "reconhecimento_firma": Decimal("32.10"),
    "registro_nascimento": Decimal("0.00"),  # gratuito
    "registro_obito": Decimal("0.00"),  # gratuito
}

TIPOS_VALIDOS = frozenset(EMOLUMENTOS_2026.keys())


@dataclass
class CalculoEmolumento:
    tipo: str
    folhas: int
    urgencia: bool
    base: Decimal
    adicional_folhas: Decimal
    adicional_urgencia: Decimal
    total: Decimal
    tabela_referencia: str
    valido_ate: str


def calcular(
    tipo: str,
    *,
    folhas: int = 1,
    urgencia: bool = False,
    tabela: dict[str, Decimal] | None = None,
    tabela_referencia: str = "TABELA_2026_MG",
    valido_ate: str = "2026-12-31",
) -> CalculoEmolumento:
    """Calcula emolumento + adicionais. Type-safe, levanta excecao em tipo invalido."""
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo desconhecido: {tipo!r}. Validos: {sorted(TIPOS_VALIDOS)}")
    if folhas < 1 or folhas > 1000:
        raise ValueError(f"folhas deve estar entre 1 e 1000, recebeu {folhas}")

    tab = tabela or EMOLUMENTOS_2026
    base = tab[tipo]
    # 5% por folha adicional a partir da 2a
    adicional_folhas = base * Decimal("0.05") * max(0, folhas - 1)
    # 50% adicional pra urgencia
    adicional_urgencia = base * Decimal("0.50") if urgencia else Decimal("0")
    total = base + adicional_folhas + adicional_urgencia

    # Arredondamento bancario
    def quantize(d: Decimal) -> Decimal:
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return CalculoEmolumento(
        tipo=tipo,
        folhas=folhas,
        urgencia=urgencia,
        base=quantize(base),
        adicional_folhas=quantize(adicional_folhas),
        adicional_urgencia=quantize(adicional_urgencia),
        total=quantize(total),
        tabela_referencia=tabela_referencia,
        valido_ate=valido_ate,
    )
