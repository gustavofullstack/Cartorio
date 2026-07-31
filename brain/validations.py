import re
from typing import Dict, Any, List
from brain.privacy_sanitizer import PrivacySanitizer

class ActValidations:
    """
    Validations & Requirements Engine for Notary Acts.
    Verifies completeness of required document packages and mandatory legal clauses.
    """

    REQUIRED_DOCUMENTS_CHECKLIST = {
        "Inventário e Partilha": [
            {"doc": "Certidão de Óbito", "mandatory": True},
            {"doc": "RG e CPF das Partes", "mandatory": True},
            {"doc": "Certidão de Casamento", "mandatory": True},
            {"doc": "Certidão Receita Federal", "mandatory": True},
            {"doc": "Certidão ITCMD", "mandatory": True},
            {"doc": "Certidão Municipal IPTU", "mandatory": True},
            {"doc": "Matrícula do Imóvel", "mandatory": True},
            {"doc": "Certidão CENSEC Testamento", "mandatory": True}
        ],
        "Usucapião": [
            {"doc": "Ata Notarial", "mandatory": True},
            {"doc": "Planta e Memorial Descritivo", "mandatory": True},
            {"doc": "Certidões Feitos Ajuizados", "mandatory": True},
            {"doc": "Comprovante de Posse", "mandatory": True},
            {"doc": "Anuência Confrontantes", "mandatory": True},
            {"doc": "Matrícula do Imóvel", "mandatory": True}
        ],
        "Testamento": [
            {"doc": "RG e CPF do Testador", "mandatory": True},
            {"doc": "Certidão de Nascimento ou Casamento", "mandatory": True},
            {"doc": "Comprovante de Residência", "mandatory": True},
            {"doc": "Testemunhas", "mandatory": True},
            {"doc": "Atestado Médico Capacidade", "mandatory": False}
        ],
        "Divórcio e Separação": [
            {"doc": "Certidão de Casamento", "mandatory": True},
            {"doc": "RG e CPF dos Cônjuges", "mandatory": True},
            {"doc": "Pacto Antenupcial", "mandatory": False},
            {"doc": "Documentos dos Bens", "mandatory": True},
            {"doc": "Certidão Filhos", "mandatory": True},
            {"doc": "Assinatura Advogado", "mandatory": True}
        ]
    }

    MANDATORY_CLAUSES = {
        "Usucapião": [
            "sob as penas da lei",
            "posse mansa"
        ],
        "Testamento": [
            "plena capacidade física e mental",
            "legítima dos herdeiros"
        ],
        "Divórcio e Separação": [
            "não se encontra em estado gravídico",
            "inexistência de filhos menores"
        ]
    }

    @classmethod
    def validate_document_checklist(cls, act_type: str, provided_docs: List[str]) -> Dict[str, Any]:
        """
        Validates provided document names against required checklist for a given notary act.
        """
        if act_type not in cls.REQUIRED_DOCUMENTS_CHECKLIST:
            return {
                "act_type": act_type,
                "status": "UNKNOWN_ACT",
                "message": f"No registered checklist for act '{act_type}'."
            }

        checklist = cls.REQUIRED_DOCUMENTS_CHECKLIST[act_type]
        provided_clean = " ".join([PrivacySanitizer.sanitize(d).lower() for d in provided_docs])

        present = []
        missing_mandatory = []
        missing_optional = []

        for item in checklist:
            doc_name = item["doc"]
            is_mand = item["mandatory"]
            
            # Check key tokens of doc_name
            req_tokens = [t.lower() for t in doc_name.split() if len(t) > 2 and t.lower() not in ['das', 'dos', 'uma', 'com']]
            # Must match at least 50% of significant tokens
            matched_count = sum(1 for tok in req_tokens if tok in provided_clean)
            is_present = matched_count >= max(1, len(req_tokens) // 2)

            if is_present:
                present.append(doc_name)
            else:
                if is_mand:
                    missing_mandatory.append(doc_name)
                else:
                    missing_optional.append(doc_name)

        if not missing_mandatory:
            status = "APPROVED"
        elif len(present) > 0:
            status = "PENDING_DOCS"
        else:
            status = "REJECTED"

        return {
            "act_type": act_type,
            "status": status,
            "total_required": len(checklist),
            "total_present": len(present),
            "present_documents": present,
            "missing_mandatory_documents": missing_mandatory,
            "missing_optional_documents": missing_optional
        }

    @classmethod
    def validate_mandatory_clauses(cls, act_type: str, draft_text: str) -> Dict[str, Any]:
        """
        Verifies whether mandatory statutory clauses are included in a draft act text.
        """
        if act_type not in cls.MANDATORY_CLAUSES:
            return {"act_type": act_type, "status": "UNKNOWN_ACT", "missing_clauses": []}

        clauses = cls.MANDATORY_CLAUSES[act_type]
        text_clean = PrivacySanitizer.sanitize(draft_text).lower()

        missing = []
        found = []

        for phrase in clauses:
            if phrase.lower() in text_clean:
                found.append(phrase)
            else:
                missing.append(phrase)

        is_valid = len(missing) == 0

        return {
            "act_type": act_type,
            "is_valid": is_valid,
            "found_clauses": found,
            "missing_clauses": missing
        }
