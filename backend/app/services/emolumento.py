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
    quantize = lambda d: d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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


def isencao_aplicavel(tipo: str, *, motivo: str) -> bool:
    """Verifica se tipo eh candidato a isencao pelo motivo.

    APENAS indica elegibilidade - aplicacao real exige validacao humana
    do tabeliao. Bot NAO concede isencao sozinho.
    """
    gratuítos = {"registro_nascimento", "registro_obito"}
    if tipo in gratuítos:
        return True
    motivos_validos = {
        "justica_gratuita",
        "entidade_filantropica",
        "programa_social",
    }
    return motivo in motivos_validos
