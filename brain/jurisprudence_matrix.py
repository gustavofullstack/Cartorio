from typing import Dict, Any, List

class JurisprudenceMatrix:
    """
    Jurisprudence & Binding Precedent Matrix for Notary Acts.
    Contains STJ rulings, CNJ Provimentos, and statutory legal interpretations.
    """

    PRECEDENTS = {
        "procuracao_idoso_alienacao": {
            "title": "Outorga de Poderes Especiais e Específicos para Alienação de Imóveis em Procuração Pública",
            "source": "STJ - REsp 1.836.584/MG (Rel. Min. Nancy Andrighi)",
            "summary": "Para alienar ou doar imóveis do outorgante, não basta a outorga de poderes 'amplos e gerais'. Exige-se a outorga de poderes ESPECIAIS E ESPECÍFICOS, com a identificação individualizada do bem imóvel objeto do negócio jurídico.",
            "impact_notarial": "Tabeliães devem exigir procuração pública contendo a descrição específica do imóvel objeto de alienação, sob pena de nulidade da escritura."
        },
        "adjudicacao_compulsoria_sem_registro": {
            "title": "Desnecessidade de Registro do Compromisso de Compra e Venda para Adjudicação",
            "source": "STJ - Súmula 239 / Art. 216-B da Lei 6.015/73",
            "summary": "O direito à adjudicação compulsória não se condiciona ao registro do compromisso de compra e venda no cartório de registro de imóveis.",
            "impact_notarial": "A lavratura de ata notarial de adjudicação compulsória extrajudicial prescinde do registro prévio do contrato, desde que comprovada a quitação e recusa/impossibilidade do promitente vendedor."
        },
        "usucapiao_extrajudicial_codigo_normas": {
            "title": "Regulamentação da Usucapião Extrajudicial no Código Nacional de Normas",
            "source": "CNJ - Provimento 149/2023 (Arts. 398 a 423)",
            "summary": "Consolida as regras da ata notarial e do requerimento de usucapião perante o Registro de Imóveis, prevendo notificação de confrontantes e publicação de edital.",
            "impact_notarial": "Padronização nacional da ata notarial lavrada pelo Tabelião de Notas com aposição de fé pública."
        },
        "autorizacao_viagem_eletronica": {
            "title": "Autorização Eletrônica de Viagem (AEV) para Menores",
            "source": "CNJ - Provimento 103/2020",
            "summary": "Permite a emissão da AEV via plataforma e-Notariado para menores de 16 anos viajarem desacompanhados ou com apenas um dos genitores.",
            "impact_notarial": "Validade de até 2 anos com assinatura digital notarial."
        }
    }

    @classmethod
    def search_precedents(cls, query: str) -> List[Dict[str, Any]]:
        query_clean = query.lower()
        results = []
        for key, info in cls.PRECEDENTS.items():
            combined = f"{info['title']} {info['source']} {info['summary']} {info['impact_notarial']}".lower()
            if query_clean in combined:
                results.append(info)
        return results
