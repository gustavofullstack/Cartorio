from typing import Dict, Any, List, Optional
from brain.db import BrainDatabase
from brain.privacy_sanitizer import PrivacySanitizer

class KnowledgeBaseEngine:
    """
    Search and Retrieval Engine for Notary Knowledge, STJ Jurisprudence,
    CNJ Provimentos, and Legal Rules.
    """

    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.db = BrainDatabase(db_path)

    def query_knowledge(self, query_text: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """
        Executes semantic search over indexed documents and legal norms.
        Returns matched documents, extracted snippets, and legal citations.
        """
        clean_query = PrivacySanitizer.sanitize(query_text)
        results = self.db.search_documents(query=clean_query, category=category, limit=limit)

        matches = []
        for r in results:
            text = r.get("sanitized_text", "")
            # Find relevant snippet window around query terms
            snippet = text[:300] + "..." if len(text) > 300 else text
            
            matches.append({
                "document_id": r["id"],
                "filename": r["filename"],
                "category": r["category"],
                "word_count": r["word_count"],
                "snippet": snippet
            })

        return {
            "query": clean_query,
            "category_filter": category,
            "total_matches": len(matches),
            "results": matches
        }

    def get_provimento_summary(self, provimento_num: str) -> Dict[str, Any]:
        """
        Retrieves summary of key CNJ Provimentos (e.g. 103/2020, 149/2023).
        """
        known_provimentos = {
            "103": {
                "num": "103/2020 CNJ",
                "title": "Autorização Eletrônica de Viagem (AEV) para Crianças e Adolescentes",
                "summary": "Dispõe sobre a autorização eletrônica de viagem nacional e internacional de crianças e adolescentes até 16 anos desacompanhados ou com apenas um dos pais, lavrada por meio da plataforma e-Notariado.",
                "key_points": [
                    "Validade de até 2 anos",
                    "Assinatura digital via e-Notariado",
                    "Reconhecimento presencial ou por videoconferência"
                ]
            },
            "149": {
                "num": "149/2023 CNJ",
                "title": "Código Nacional de Normas da Corregedoria Nacional de Justiça - Foro Extrajudicial",
                "summary": "Consolida o Código Nacional de Normas da Corregedoria Nacional de Justiça do foro extrajudicial, unificando procedimentos de Notas e Registro de Imóveis.",
                "key_points": [
                    "Padronização dos atos notariais em âmbito nacional",
                    "Integração de centrais de serviços eletrônicos",
                    "Directrizes para adjudicação compulsória extrajudicial"
                ]
            }
        }

        num_clean = provimento_num.replace("provimento", "").replace("cnj", "").strip()
        for k, v in known_provimentos.items():
            if k in num_clean:
                return v

        return {
            "num": provimento_num,
            "title": "Provimento Extrajudicial CNJ",
            "summary": "Norma regulamentar do Conselho Nacional de Justiça sobre atos notariais e registrais.",
            "key_points": ["Consulte a base completa do BRAIN para mais detalhes."]
        }
