from typing import Dict, Any, List
from brain.privacy_sanitizer import PrivacySanitizer

class ENotariadoEngine:
    """
    Compliance and Verification Engine for Electronic Notary Acts (e-Notariado),
    Provimento CNJ nº 100/2020 e Provimento CNJ nº 149/2023.
    """

    @classmethod
    def verify_territorial_jurisdiction(cls, property_location: str, party_domicile: str, notary_serventia_city: str) -> Dict[str, Any]:
        """
        Verifies territorial jurisdiction compliance according to Art. 5º of Provimento CNJ 100/2020:
        - For real estate transactions: Competence belongs to the notary of the property location OR party domicile.
        - For testaments/powers of attorney: Competence belongs to the notary of the party's domicile.
        """
        prop_clean = PrivacySanitizer.sanitize(property_location).lower()
        dom_clean = PrivacySanitizer.sanitize(party_domicile).lower()
        notary_clean = notary_serventia_city.lower()

        is_valid_prop = notary_clean in prop_clean if property_location else False
        is_valid_dom = notary_clean in dom_clean if party_domicile else False

        is_competent = is_valid_prop or is_valid_dom

        return {
            "notary_city": notary_serventia_city,
            "property_location": property_location,
            "party_domicile": party_domicile,
            "is_competent": is_competent,
            "legal_basis": "Art. 5º do Provimento CNJ nº 100/2020",
            "message": "Serventia competente." if is_competent else "Alerta de incompetência territorial: Serventia notarial deve corresponder ao local do imóvel ou domicílio das partes."
        }

    @classmethod
    def get_videoconference_checklist(cls) -> List[Dict[str, Any]]:
        """
        Returns mandatory protocol checklist for e-Notariado videoconference sessions.
        """
        return [
            {"step": 1, "description": "Emissão prévia do Certificado Digital Notarial Gratuito (e-Notariado) ou uso de e-CPF ICP-Brasil.", "mandatory": True},
            {"step": 2, "description": "Gravação integral da sessão de videoconferência notarial com consentimento expresso das partes.", "mandatory": True},
            {"step": 3, "description": "Verificação de identidade e capacidade civil manifesta do outorgante perante a câmera.", "mandatory": True},
            {"step": 4, "description": "Leitura em voz alta e pausada da minuta do ato notarial eletrônico pelo Tabelião ou Substituto.", "mandatory": True},
            {"step": 5, "description": "Assinatura digital do documento PDF/A pelas partes e pelo Tabelião na plataforma e-Notariado.", "mandatory": True}
        ]
