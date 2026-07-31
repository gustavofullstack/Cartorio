from typing import Dict, Any, List

class EstremacaoEngine:
    """
    Validation & Verification Engine for Estremação and Partition of Condomínio Voluntário
    pro indiviso with localized possession over 5 years.
    """

    @classmethod
    def validate_estremacao_requirements(cls, posse_anos: float, tem_memorial_art: bool, tem_anuencia_confrontantes: bool, tem_outorga_uxoria: bool) -> Dict[str, Any]:
        """
        Validates Estremação requirements:
        1. Minimum 5 years of continuous localized possession.
        2. Memorial descritivo signed with ART/RRT.
        3. Express consent of all adjacent confrontantes.
        4. Spousal consent (outorga uxória/marital) when married under community property regime.
        """
        issues = []
        if posse_anos < 5.0:
            issues.append(f"Tempo de posse insuficiente: {posse_anos} anos. Exige-se no mínimo 5 (cinco) anos de posse exclusiva e localizada.")
        if not tem_memorial_art:
            issues.append("Falta de Planta e Memorial Descritivo assinados por profissional habilitado com ART/RRT.")
        if not tem_anuencia_confrontantes:
            issues.append("Falta de declaração de anuência expressa dos confrontantes das divisas.")
        if not tem_outorga_uxoria:
            issues.append("Falta de outorga uxória/marital dos cônjuges dos proprietários e confrontantes.")

        is_approved = len(issues) == 0

        return {
            "is_approved": is_approved,
            "status": "APROVADO" if is_approved else "PENDENTE",
            "posse_anos": posse_anos,
            "issues": issues,
            "legal_basis": "Provimento Conjunto CGJ-MG nº 93/2020 e Código Civil (Art. 1.314)",
            "summary": "Estremação apta para lavratura de escritura pública de divisão e individualização de gleba." if is_approved else "Estremação pendente de requisitos legais obrigatorios."
        }
