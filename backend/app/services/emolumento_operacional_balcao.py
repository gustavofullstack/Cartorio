"""Camada operacional de balcão 2026, separada da tabela regulatória TJMG.

Os valores desta camada incluem componentes internos de balcão e não alteram
``emolumento_real_djalma.ATOS_PUBLICADOS_2026``. Atos financeiros continuam
HITL: as faixas servem para consulta do escrevente, não para decisão autônoma.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final


OPERATIONAL_LAYER: Final[str] = "OPERATIONAL_POS_2NOTAS_2026"


@dataclass(frozen=True)
class OperationalItem:
    code: str
    nature: str
    total: Decimal


@dataclass(frozen=True)
class OperationalBand:
    codes: tuple[str, ...]
    ceiling: Decimal | None
    total: Decimal
    per_excess_block: bool = False


GENERAL_ITEMS: Final[dict[str, OperationalItem]] = {
    "abertura_firma": OperationalItem("1502-4", "Abertura de firma", Decimal("11.61")),
    "aditamento": OperationalItem("1418-3", "Aditamento/rerratificacao", Decimal("44.88")),
    "aprovacao_testamento_cerrado": OperationalItem(
        "1101-5", "Aprovacao de testamento cerrado", Decimal("678.90")
    ),
    "apostilamento": OperationalItem("8310-5", "Apostilamento por documento", Decimal("189.38")),
    "arquivamento": OperationalItem("8101-8", "Arquivamento", Decimal("13.91")),
    "ata_notarial": OperationalItem("1202-1", "Ata notarial ate duas folhas", Decimal("226.15")),
    "ata_notarial_folha": OperationalItem("1203-9", "Ata notarial por folha", Decimal("11.61")),
    "autenticacao_documento_eletronico": OperationalItem(
        "1302-9", "Autenticacao de documento eletronico", Decimal("13.91")
    ),
    "autenticacao": OperationalItem("1301-1", "Autenticacao", Decimal("11.61")),
    "busca_livros_5_anos": OperationalItem(
        "8301-4", "Busca de livros por cinco anos", Decimal("9.79")
    ),
    "certidao_inteiro_teor": OperationalItem(
        "8401-2", "Certidao de inteiro teor", Decimal("42.49")
    ),
    "certidao_quesitos": OperationalItem("8402-0", "Certidao conforme quesitos", Decimal("66.30")),
    "diligencia_outros_limites": OperationalItem(
        "8503-5", "Diligencia outros limites", Decimal("56.53")
    ),
    "diligencia_rural": OperationalItem("8502-7", "Diligencia perimetro rural", Decimal("42.18")),
    "diligencia_urbana": OperationalItem("8501-9", "Diligencia perimetro urbano", Decimal("24.34")),
    "escritura_sem_valor": OperationalItem(
        "1401-9", "Escritura sem conteudo financeiro", Decimal("75.48")
    ),
    "inventario_sem_valor": OperationalItem(
        "1460-5", "Inventario sem conteudo financeiro", Decimal("226.14")
    ),
    "pacto_divorcio_dissolucao_uniao": OperationalItem(
        "1477-9", "Pacto, divorcio, dissolucao ou uniao estavel", Decimal("678.88")
    ),
    "procuracao_financeira": OperationalItem(
        "1458-9", "Procuracao com conteudo financeiro", Decimal("226.14")
    ),
    "procuracao": OperationalItem("1437-3", "Procuracao generica", Decimal("71.38")),
    "procuracao_inss": OperationalItem("1438-1", "Procuracao INSS", Decimal("37.91")),
    "reconhecimento_firma": OperationalItem("1501-6", "Reconhecimento de firma", Decimal("11.61")),
    "reconhecimento_dut_atpv": OperationalItem(
        "1501-6+CNTV", "Reconhecimento de firma em DUT/ATPV (com CNTV/MG)", Decimal("16.61")
    ),
    "xerox_1_face": OperationalItem("XEROX-1", "Xerox - uma face", Decimal("1.80")),
    "xerox_2_faces": OperationalItem("XEROX-2", "Xerox - frente e verso", Decimal("3.60")),
    "revogacao_testamento": OperationalItem("1457-1", "Revogacao de testamento", Decimal("226.36")),
    "substabelecimento": OperationalItem("1455-5", "Substabelecimento", Decimal("47.59")),
    "testamento": OperationalItem("1456-3", "Testamento generico", Decimal("452.71")),
    "testamento_cerrado_rogo": OperationalItem(
        "1459-7", "Testamento cerrado a rogo", Decimal("905.43")
    ),
    "autenticacao_digital_cenad": OperationalItem(
        "1697-2", "Autenticacao digital CENAD", Decimal("13.46")
    ),
    "autorizacao_eletronica_viagem": OperationalItem(
        "1698-0", "Autorizacao eletronica de viagem", Decimal("11.61")
    ),
    "reconhecimento_enot_assina": OperationalItem(
        "1699-8", "Reconhecimento e-Not Assina", Decimal("11.61")
    ),
}


_CEILINGS: Final[tuple[str, ...]] = (
    "1400",
    "2720",
    "5440",
    "7000",
    "14000",
    "28000",
    "42000",
    "56000",
    "70000",
    "105000",
    "140000",
    "175000",
    "210000",
    "280000",
    "350000",
    "420000",
    "560000",
    "700000",
    "840000",
    "1120000",
    "1400000",
    "1680000",
    "3200000",
    "3700000",
)

_ESCRITURA_CODES: Final[tuple[str, ...]] = (
    "1402-7",
    "1403-5",
    "1404-3",
    "1405-0",
    "1406-8",
    "1407-6",
    "1408-4",
    "1409-2",
    "1410-0",
    "1411-8",
    "1600-6",
    "1601-4",
    "1602-2",
    "1603-0",
    "1604-8",
    "1605-5",
    "1606-3",
    "1607-1",
    "1608-9",
    "1609-7",
    "1610-5",
    "1611-3",
    "1416-7",
    "1417-5",
)

_ESCRITURA_TOTALS: Final[tuple[str, ...]] = (
    "227.95",
    "371.84",
    "538.85",
    "745.98",
    "994.78",
    "1285.21",
    "1616.57",
    "1989.94",
    "2404.60",
    "3026.34",
    "3839.67",
    "4106.03",
    "4372.88",
    "4914.86",
    "5050.25",
    "5186.26",
    "5677.78",
    "5989.84",
    "6302.53",
    "7046.73",
    "7632.83",
    "8219.92",
    "8808.22",
    "13034.69",
)

ESCRITURA_FINANCEIRA_BANDS: Final[tuple[OperationalBand, ...]] = tuple(
    OperationalBand((code,), Decimal(ceiling), Decimal(total))
    for code, ceiling, total in zip(_ESCRITURA_CODES, _CEILINGS, _ESCRITURA_TOTALS, strict=True)
) + (OperationalBand(("1612-1",), None, Decimal("2254.46"), per_excess_block=True),)

_TESTAMENTO_CODES: Final[tuple[tuple[str, str], ...]] = (
    ("1419-1", "1645-1"),
    ("1420-9", "1646-9"),
    ("1421-7", "1647-7"),
    ("1422-5", "1648-5"),
    ("1423-3", "1649-3"),
    ("1424-1", "1650-1"),
    ("1425-8", "1651-9"),
    ("1426-6", "1652-7"),
    ("1427-4", "1653-5"),
    ("1428-2", "1654-3"),
    ("1615-4", "1655-0"),
    ("1616-2", "1656-8"),
    ("1617-0", "1657-6"),
    ("1618-8", "1658-4"),
    ("1619-6", "1659-2"),
    ("1620-4", "1660-0"),
    ("1621-2", "1661-8"),
    ("1622-0", "1662-6"),
    ("1623-8", "1663-4"),
    ("1624-6", "1664-2"),
    ("1625-3", "1665-9"),
    ("1626-1", "1666-7"),
    ("1433-2", "1667-5"),
    ("1434-0", "1668-3"),
)

_TESTAMENTO_TOTALS: Final[tuple[str, ...]] = (
    "113.98",
    "185.92",
    "269.42",
    "372.99",
    "497.38",
    "642.60",
    "808.28",
    "994.96",
    "1202.31",
    "1513.17",
    "1919.84",
    "2053.01",
    "2186.44",
    "2457.43",
    "2525.13",
    "2593.13",
    "2838.89",
    "2994.92",
    "3151.27",
    "3523.37",
    "3816.41",
    "4109.96",
    "4404.11",
    "6517.35",
)

TESTAMENTO_ALTERACAO_BANDS: Final[tuple[OperationalBand, ...]] = tuple(
    OperationalBand(codes, Decimal(ceiling), Decimal(total))
    for codes, ceiling, total in zip(_TESTAMENTO_CODES, _CEILINGS, _TESTAMENTO_TOTALS, strict=True)
) + (OperationalBand(("1627-9", "1669-1"), None, Decimal("1127.24"), per_excess_block=True),)


def format_brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


OPERATIONAL_ALIASES: Final[dict[str, str]] = {
    "procuracao_geral": "procuracao",
    "procuracao_generica": "procuracao",
    "procuracao_patrimonial": "procuracao_financeira",
    "procuracao_banco": "procuracao_financeira",
    "procuracao_veiculo": "procuracao_financeira",
    "procuracao_imovel": "procuracao_financeira",
    "procuracao_previdenciaria": "procuracao_inss",
    "procuracao_previdencia": "procuracao_inss",
    "autenticacao_copia_folha": "autenticacao",
    "autenticacao_fisica": "autenticacao",
    "autenticacao_eletronica": "autenticacao_documento_eletronico",
    "reconhecimento_firma_assinatura": "reconhecimento_firma",
    "dut_atpv": "reconhecimento_dut_atpv",
    "reconhecimento_dut": "reconhecimento_dut_atpv",
    "xerox": "xerox_1_face",
    "xerox_uma_face": "xerox_1_face",
    "xerox_frente_verso": "xerox_2_faces",
}


def calcular_emolumento_operacional(
    tipo_ato: str,
    *,
    valor_declarado: Decimal | float | int | None = None,
    folhas: int = 1,
    urgencia: bool = False,
) -> dict[str, object]:
    """Calcula o total operacional praticado no balcão da serventia (MG 2026).

    Retorna status PUBLISHED para atos simples diretos de balcão e HITL_REQUIRED
    para urgência, valores declarados ou situações que exijam validação do escrevente.
    """
    folhas = max(1, folhas)
    slug = OPERATIONAL_ALIASES.get(tipo_ato, tipo_ato)

    if urgencia:
        return {
            "cartorio": "2º Tabelionato de Notas de Uberlândia",
            "tipo_ato": slug,
            "valor_declarado": str(valor_declarado) if valor_declarado is not None else None,
            "folhas": folhas,
            "status": "HITL_REQUIRED",
            "total": None,
            "pricing_layer": "operational_pos_2notas",
            "tabela_referencia": "TABELA_OPERACIONAL_BALCAO_2NOTAS_2026",
            "motivo_hitl": "Atendimento com urgência exige conferência do escrevente.",
            "vigencia": "2026",
        }

    if valor_declarado is not None:
        return {
            "cartorio": "2º Tabelionato de Notas de Uberlândia",
            "tipo_ato": slug,
            "valor_declarado": str(valor_declarado),
            "folhas": folhas,
            "status": "HITL_REQUIRED",
            "total": None,
            "pricing_layer": "operational_pos_2notas",
            "tabela_referencia": "TABELA_OPERACIONAL_BALCAO_2NOTAS_2026",
            "motivo_hitl": "Ato com conteúdo financeiro depende de faixa e composição pelo escrevente.",
            "vigencia": "2026",
        }

    item = GENERAL_ITEMS.get(slug)
    if item is None:
        return {
            "cartorio": "2º Tabelionato de Notas de Uberlândia",
            "tipo_ato": slug,
            "valor_declarado": None,
            "folhas": folhas,
            "status": "HITL_REQUIRED",
            "total": None,
            "pricing_layer": "operational_pos_2notas",
            "tabela_referencia": "TABELA_OPERACIONAL_BALCAO_2NOTAS_2026",
            "motivo_hitl": "Ato não localizado na tabela operacional de balcão; encaminhado ao escrevente.",
            "vigencia": "2026",
        }

    total_val = item.total
    if slug == "autenticacao" and folhas > 1:
        total_val = item.total * Decimal(folhas)
    elif folhas > 1 and slug not in ("ata_notarial", "ata_notarial_folha"):
        return {
            "cartorio": "2º Tabelionato de Notas de Uberlândia",
            "tipo_ato": slug,
            "valor_declarado": None,
            "folhas": folhas,
            "status": "HITL_REQUIRED",
            "total": None,
            "pricing_layer": "operational_pos_2notas",
            "tabela_referencia": "TABELA_OPERACIONAL_BALCAO_2NOTAS_2026",
            "motivo_hitl": "Quantidade de folhas adicional para este ato exige composição pelo escrevente.",
            "vigencia": "2026",
        }

    return {
        "cartorio": "2º Tabelionato de Notas de Uberlândia",
        "tipo_ato": slug,
        "valor_declarado": None,
        "folhas": folhas,
        "status": "PUBLISHED",
        "total": f"{total_val:.2f}",
        "item_codigo": item.code,
        "descricao": item.nature,
        "pricing_layer": "operational_pos_2notas",
        "tabela_referencia": "TABELA_OPERACIONAL_BALCAO_2NOTAS_2026",
        "motivo_hitl": None,
        "vigencia": "2026",
    }
