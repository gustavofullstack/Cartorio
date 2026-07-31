from typing import Dict, Any, List, Optional

class EmolumentCalculations:
    """
    Emoluments & Tax Calculations Engine for Notary Acts.
    Provides fee lookups based on asset value ranges, tax comparisons (ITCMD vs ITBI),
    and additional notary charges (ISS, FERJ, FUNPERJ, Distribution, etc.).
    """

    # Representative Notary Fee Scale (Tabela 5 - Escrituras / Atos Notariais)
    FEE_SCALE = [
        {"max_val": 10000.0, "fee": 150.00},
        {"max_val": 50000.0, "fee": 380.00},
        {"max_val": 100000.0, "fee": 750.00},
        {"max_val": 250000.0, "fee": 1450.00},
        {"max_val": 500000.0, "fee": 2600.00},
        {"max_val": 1000000.0, "fee": 4200.00},
        {"max_val": float("inf"), "fee": 6500.00}
    ]

    @classmethod
    def calculate_emoluments(cls, asset_value: float, act_type: str = "Escritura") -> Dict[str, Any]:
        """
        Calculates notary emoluments, state fund surcharge (approx 20%), and total fee based on property asset value.
        """
        if asset_value < 0:
            raise ValueError("Asset value cannot be negative.")

        base_fee = 0.0
        for tier in cls.FEE_SCALE:
            if asset_value <= tier["max_val"]:
                base_fee = tier["fee"]
                break
        
        # Additional statutory funds/fees (~20% state funds/distribution)
        statutory_funds = round(base_fee * 0.20, 2)
        total_fee = round(base_fee + statutory_funds, 2)

        return {
            "act_type": act_type,
            "asset_value": asset_value,
            "base_emolument": base_fee,
            "statutory_funds": statutory_funds,
            "total_emolument_fee": total_fee
        }

    @classmethod
    def compare_doacao_vs_compra_venda(cls, property_value: float, itcmd_rate: float = 0.04, itbi_rate: float = 0.02) -> Dict[str, Any]:
        """
        Calculates and compares the total tax payload between:
        1. Doação (Donation) - ITCMD (Imposto sobre Transmissão Causa Mortis e Doação)
        2. Compra e Venda (Sale & Purchase) - ITBI (Imposto de Transmissão de Bens Imóveis)
        """
        itcmd_amount = round(property_value * itcmd_rate, 2)
        itbi_amount = round(property_value * itbi_rate, 2)
        
        emoluments = cls.calculate_emoluments(property_value)["total_emolument_fee"]

        total_doacao = round(itcmd_amount + emoluments, 2)
        total_compra_venda = round(itbi_amount + emoluments, 2)
        difference = round(abs(total_doacao - total_compra_venda), 2)

        cheaper_option = "Compra e Venda (ITBI)" if total_compra_venda < total_doacao else "Doação (ITCMD)"

        return {
            "property_value": property_value,
            "emoluments_fee": emoluments,
            "doacao": {
                "tax_name": "ITCMD (Estadual)",
                "rate": f"{itcmd_rate * 100:.1f}%",
                "tax_amount": itcmd_amount,
                "total_cost": total_doacao
            },
            "compra_e_venda": {
                "tax_name": "ITBI (Municipal)",
                "rate": f"{itbi_rate * 100:.1f}%",
                "tax_amount": itbi_amount,
                "total_cost": total_compra_venda
            },
            "difference": difference,
            "cheaper_option": cheaper_option,
            "summary_note": f"Em geral, ITBI (municipal, ~2%) é menor que ITCMD (estadual, 4% a 8%), tornando Compra e Venda mais econômica em impostos do que Doação pura."
        }
