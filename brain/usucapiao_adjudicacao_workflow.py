from typing import Dict, Any, List

class ExtrajudicialWorkflowEngine:
    """
    Step-by-Step State Machine Workflow Manager for:
    1. Usucapião Extrajudicial (Lei 6.015/73 Art. 216-A / Prov. CNJ 149/2023)
    2. Adjudicação Compulsória Extrajudicial (Lei 6.015/73 Art. 216-B / Prov. CNJ 149/2023)
    """

    USUCAPIAO_STAGES = [
        {"stage": 1, "name": "Qualificação & Protocolo Inicial", "desc": "Coleta de documentos de identidade, histórico de posse e indicação dos confrontantes."},
        {"stage": 2, "name": "Diligência Notarial & Vistoria", "desc": "Realização de diligência notarial no local pelo Tabelião/Substituto com emissão de relatório."},
        {"stage": 3, "name": "Lavratura da Ata Notarial", "desc": "Lavratura de Ata Notarial de Usucapião atestando o tempo e a natureza da posse mansa e pacífica."},
        {"stage": 4, "name": "Prenotação no Registro de Imóveis (RI)", "desc": "Protocolo do requerimento formal assinado por Advogado instruído com a Ata Notarial."},
        {"stage": 5, "name": "Notificação dos Confrontantes & Entes Públicos", "desc": "Notificação pessoal dos confrontantes e cientificação da União, Estado e Município."},
        {"stage": 6, "name": "Publicação de Edital", "desc": "Publicação de edital em jornal de grande circulação para ciência de terceiros interessados (prazo 15 dias)."},
        {"stage": 7, "name": "Registro & Abertura de Matrícula", "desc": "Deferimento pelo Oficial de Registro de Imóveis com abertura de nova matrícula originária."}
    ]

    ADJUDICACAO_STAGES = [
        {"stage": 1, "name": "Análise do Contrato de Promessa", "desc": "Verificação do contrato de promessa de compra e venda sem cláusula de arrependimento."},
        {"stage": 2, "name": "Comprovação de Quitação Integral", "desc": "Verificação de recibos, comprovantes bancários ou declaração de quitação do preço."},
        {"stage": 3, "name": "Comprovação da Inadimplência/Recusa", "desc": "Notificação extrajudicial prévia do promitente vendedor frustrada ou recusa formal."},
        {"stage": 4, "name": "Lavratura da Ata Notarial de Adjudicação", "desc": "Lavratura da Ata Notarial pelo Tabelião certificando a quitação e recusa do vendedor."},
        {"stage": 5, "name": "Registro da Carta de Adjudicação", "desc": "Registro direto da propriedade perante o Oficial de Registro de Imóveis (Art. 216-B Lei 6.015/73)."}
    ]

    @classmethod
    def get_usucapiao_stage_info(cls, current_stage: int) -> Dict[str, Any]:
        if 1 <= current_stage <= len(cls.USUCAPIAO_STAGES):
            info = cls.USUCAPIAO_STAGES[current_stage - 1]
            return {
                "process": "Usucapião Extrajudicial",
                "current_stage": current_stage,
                "total_stages": len(cls.USUCAPIAO_STAGES),
                "stage_info": info,
                "next_stage": current_stage + 1 if current_stage < len(cls.USUCAPIAO_STAGES) else None
            }
        return {"error": f"Estágio inválido: {current_stage}. Escolha entre 1 e {len(cls.USUCAPIAO_STAGES)}."}

    @classmethod
    def get_adjudicacao_stage_info(cls, current_stage: int) -> Dict[str, Any]:
        if 1 <= current_stage <= len(cls.ADJUDICACAO_STAGES):
            info = cls.ADJUDICACAO_STAGES[current_stage - 1]
            return {
                "process": "Adjudicação Compulsória Extrajudicial",
                "current_stage": current_stage,
                "total_stages": len(cls.ADJUDICACAO_STAGES),
                "stage_info": info,
                "next_stage": current_stage + 1 if current_stage < len(cls.ADJUDICACAO_STAGES) else None
            }
        return {"error": f"Estágio inválido: {current_stage}. Escolha entre 1 e {len(cls.ADJUDICACAO_STAGES)}."}
