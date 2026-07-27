"""Motor de Extração de Dados Jurídicos via IA com PII Scrubbing e Auditoria Imutável.

Analisa requisições de clientes do 2º Ofício Notarial de Uberlândia (Tabelionato Djalma),
extrai parâmetros notariais de forma segura e calcula o orçamento com discriminativo fiscal real.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.services.emolumento_real_djalma import EmolumentoDetalhados, calcular_emolumento_real_djalma
from app.services.pii import scrub


@dataclass
class ExtraçaoResultado:
    texto_sanitizado: str
    tipo_ato_identificado: str
    valor_declarado_identificado: Decimal | None
    folhas_identificadas: int
    urgencia_identificada: bool
    calculo: EmolumentoDetalhados
    hitl_obrigatorio: bool
    status_auditoria: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "texto_sanitizado": self.texto_sanitizado,
            "tipo_ato_identificado": self.tipo_ato_identificado,
            "valor_declarado_identificado": float(self.valor_declarado_identificado) if self.valor_declarado_identificado is not None else None,
            "folhas_identificadas": self.folhas_identificadas,
            "urgencia_identificada": self.urgencia_identificada,
            "calculo": self.calculo.to_dict(),
            "hitl_obrigatorio": self.hitl_obrigatorio,
            "status_auditoria": self.status_auditoria,
        }


def extrair_valor_monetario(texto: str) -> Decimal | None:
    """Extrai valores monetários em formato R$ X.XXX,XX ou X,XX do texto."""
    # Exemplo: R$ 350.000,00 ou 350000 ou R$350.000
    padrao = r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)"
    matches = re.findall(padrao, texto, re.IGNORECASE)
    for m in matches:
        limpo = m.replace(".", "").replace(",", ".")
        try:
            val = Decimal(limpo)
            if val > Decimal("100"):  # Ignora números de folhas ou artigos
                return val
        except Exception:
            continue
    return None


def extrair_folhas(texto: str) -> int:
    """Extrai quantidade de folhas mencionada no texto."""
    match = re.search(r"(\d+)\s*(?:folhas?|pág|páginas?)", texto, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return 1


def extrair_tipo_ato(texto: str) -> str:
    """Classifica o tipo de ato notarial no texto com base nas palavras-chave do Tabelionato Djalma."""
    t = texto.lower()
    if "compra e venda" in t or "imóvel" in t or "escritura de compra" in t:
        return "escritura_compra_venda"
    elif "escritura" in t and ("divórcio" in t or "emancipação" in t or "pacto" in t or "sem valor" in t):
        return "escritura_sem_valor"
    elif "ata notarial" in t or "constatação" in t or "whatsapp" in t:
        return "ata_notarial_primeira_folha"
    elif "procuração previdenciária" in t or "inss" in t:
        return "procuracao_previdenciaria"
    elif "procuração" in t and ("veículo" in t or "carro" in t or "imóvel" in t):
        return "procuracao_imovel_veiculo"
    elif "procuração" in t:
        return "procuracao_geral"
    elif "autenticação" in t or "autenticar" in t or "cópia" in t:
        return "autenticacao_pagina"
    elif "reconhecimento" in t or "firma" in t:
        if "autenticidade" in t or "presencial" in t:
            return "reconhecimento_firma_autenticidade"
        return "reconhecimento_firma_semelhanca"
    elif "testamento" in t:
        return "testamento_publico"
    elif "certidão" in t and "inteiro teor" in t:
        return "certidao_inteiro_teor"
    elif "certidão" in t:
        return "certidao_breve_relato"
    return "procuracao_geral"


def extrair_e_calcular_solicitacao(
    texto_usuario: str,
    *,
    forcar_urgencia: bool = False,
) -> ExtraçaoResultado:
    """Sanitiza, extrai sinais e consulta somente itens oficiais publicados.

    A função não persiste uma entrada de auditoria; a rota chamadora deve fazê-lo
    quando houver uma operação de negócio. Esse contrato evita declarar uma
    cadeia de auditoria validada sem ter gravado evento algum.
    """
    # 1. PII Scrubbing (Garantia LGPD Art. 18 / 3-Camadas)
    texto_sanitizado = scrub(texto_usuario).text

    # 2. Extração de Entidades via NLP / Regex
    tipo_ato = extrair_tipo_ato(texto_sanitizado)
    valor_declarado = extrair_valor_monetario(texto_sanitizado)
    folhas = extrair_folhas(texto_sanitizado)
    urgencia = forcar_urgencia or bool(re.search(r"\b(urgente|urgência|hoje|rápido)\b", texto_sanitizado, re.IGNORECASE))

    # 3. Consulta de item publicado; atos compostos retornam HITL_REQUIRED.
    calculo = calcular_emolumento_real_djalma(
        tipo_ato=tipo_ato,
        valor_declarado=valor_declarado,
        folhas=folhas,
        urgencia=urgencia,
    )

    # 4. Human-in-the-Loop Obrigatório para atos que exijam conferência de documentos
    hitl_obrigatorio = calculo.status == "HITL_REQUIRED"

    return ExtraçaoResultado(
        texto_sanitizado=texto_sanitizado,
        tipo_ato_identificado=tipo_ato,
        valor_declarado_identificado=valor_declarado,
        folhas_identificadas=folhas,
        urgencia_identificada=urgencia,
        calculo=calculo,
        hitl_obrigatorio=hitl_obrigatorio,
        status_auditoria="NOT_PERSISTED",
    )
