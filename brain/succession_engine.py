from typing import Dict, Any, List

class SuccessionEngine:
    """
    Mathematical Partition & Quota Calculation Engine for Successions,
    Marital Regimes, and Testamentary Restrictions (Arts. 1.829, 1.841, 1.848 do Código Civil).
    """

    @classmethod
    def calculate_succession_shares(cls, total_estate_value: float, regime_bens: str, num_children: int = 0, spouse_alive: bool = True) -> Dict[str, Any]:
        """
        Calculates exact shares for Surviving Spouse and Children under Brazilian Civil Code:
        - Comunhão Parcial de Bens: Spouse gets 50% Meação over common property. Remaining 50% + private property form Herança.
        - Separação Convencional de Bens: Spouse does NOT get Meação, but inherits as co-heir with children over private property (equal share, min 25% if common children).
        - Comunhão Universal de Bens: Spouse gets 50% Meação over total estate, does not concur in Herança.
        """
        if total_estate_value < 0:
            raise ValueError("Valor do patrimônio não pode ser negativo.")

        regime_clean = regime_bens.lower()
        meacao_spouse = 0.0
        heranca_total = total_estate_value

        if "comunhão universal" in regime_clean:
            if spouse_alive:
                meacao_spouse = total_estate_value * 0.50
                heranca_total = total_estate_value * 0.50

        elif "comunhão parcial" in regime_clean:
            if spouse_alive:
                # Assuming 100% common property for calculation base
                meacao_spouse = total_estate_value * 0.50
                heranca_total = total_estate_value * 0.50

        elif "separação" in regime_clean or "separacao" in regime_clean:
            meacao_spouse = 0.0
            heranca_total = total_estate_value

        # Partition of Herança among Spouse and Children
        spouse_heranca_share = 0.0
        child_heranca_share = 0.0

        if num_children > 0:
            if spouse_alive and "separação" in regime_clean:
                # Spouse concur in inheritance: minimum 25% if spouse is parent of children
                num_heirs = num_children + 1
                equal_share = heranca_total / num_heirs
                if equal_share < (heranca_total * 0.25) and num_children >= 3:
                    spouse_heranca_share = heranca_total * 0.25
                    child_heranca_share = (heranca_total * 0.75) / num_children
                else:
                    spouse_heranca_share = equal_share
                    child_heranca_share = equal_share
            else:
                child_heranca_share = heranca_total / num_children
        else:
            if spouse_alive:
                spouse_heranca_share = heranca_total

        total_spouse_receive = meacao_spouse + spouse_heranca_share

        return {
            "total_estate_value": total_estate_value,
            "regime_bens": regime_bens,
            "num_children": num_children,
            "spouse_alive": spouse_alive,
            "meacao_spouse": round(meacao_spouse, 2),
            "heranca_total": round(heranca_total, 2),
            "spouse_heranca_share": round(spouse_heranca_share, 2),
            "total_spouse_receives": round(total_spouse_receive, 2),
            "child_share_each": round(child_heranca_share, 2),
            "legal_basis": "Arts. 1.829 e 1.832 do Código Civil Brasileiro"
        }

    @classmethod
    def validate_justa_causa_legitima(cls, tem_justa_causa: bool, justificativa_texto: str) -> Dict[str, Any]:
        """
        Verifies statutory compliance of testamentary restrictive clauses (inalienabilidade, impenhorabilidade, incomunicabilidade)
        over the legitimate share (Legítima) pursuant to Art. 1.848 of Civil Code.
        """
        text_clean = justificativa_texto.strip()
        is_valid = tem_justa_causa and len(text_clean) >= 20

        return {
            "is_valid": is_valid,
            "tem_justa_causa": tem_justa_causa,
            "justificativa_length": len(text_clean),
            "legal_basis": "Art. 1.848 do Código Civil Brasileiro",
            "message": "Cláusula restritiva sobre a legítima válida com justa causa expressa." if is_valid else "NULIDADE DA CLÁUSULA: Para gravar a legítima dos herdeiros necessários com inalienabilidade/impenhorabilidade, exige-se declaração expressa de JUSTA CAUSA decorrente de fatos concretos no testamento."
        }
