import re
from typing import Dict, Any, List, Tuple
from brain.privacy_sanitizer import PrivacySanitizer

class DocumentIdentifier:
    """
    Automatic document classifier and category predictor for notary documents.
    Uses multi-feature keyword density, title analysis, and statutory term matching.
    """

    CATEGORIES_PATTERNS = {
        "Testamento": [
            r"testamento", r"testador", r"testamenteiro", r"legado", r"herdeiro necessário",
            r"disposição de última vontade", r"cédula testamentária", r"cláusula restritiva",
            r"legítima", r"incomunicabilidade", r"impenhorabilidade", r"inalienabilidade"
        ],
        "Usucapião": [
            r"usucapião", r"usucapiao", r"ata notarial de usucapião", r"posse mansa e pacífica",
            r"animus domini", r"confrontantes", r"planta e memorial descritivo", r"tempo de posse",
            r"justo título", r"certidão de feitos ajuizados"
        ],
        "Inventário e Partilha": [
            r"inventário", r"inventario", r"partilha", r"de cujos", r"inventariante",
            r"herdeiro", r"renúncia de herança", r"adjudicação de bens", r"itcmd",
            r"meação", r"monte mor"
        ],
        "Divórcio e Separação": [
            r"divórcio", r"divorcio", r"separação", r"separacao", r"dissolução conjugal",
            r"partilha de bens do casal", r"alimentos", r"alteração de nome", r"certidão de casamento"
        ],
        "União Estável e Casamento": [
            r"união estável", r"uniao estavel", r"conviventes", r"pacto antenupcial",
            r"regime de bens", r"separação total", r"comunhão parcial", r"comunhão universal"
        ],
        "Adjudicação Compulsória": [
            r"adjudicação compulsória", r"adjudicacao compulsoria", r"promessa de compra e venda",
            r"quitaçaõ integral", r"recusa do promitente vendedor", r"carta de adjudicação"
        ],
        "Estremação": [
            r"estremação", r"estremacao", r"gleba", r"condomínio pro indiviso", r"confrontante",
            r"anuência dos confrontantes", r"certidão de imóvel"
        ],
        "Tabelas e Emolumentos": [
            r"tabela", r"emolumentos", r"custas", r"faixa de valor", r"taxa fiscal",
            r"vfer", r"provimento de custas"
        ],
        "Normas e Provimentos CNJ": [
            r"provimento", r"cnj", r"conselho nacional de justiça", r"jurisprudência",
            r"stj", r"superior tribunal de justiça", r"provimento conjunto"
        ],
        "Atos Notariais Diversos": [
            r"reconhecimento de firma", r"autenticação", r"apostilamento", r"procuração",
            r"procuracao", r"ata notarial", r"abrir firma", r"diligência"
        ]
    }

    @classmethod
    def identify(cls, text: str, filename: str = "") -> Dict[str, Any]:
        """
        Classifies input text and filename, returning predicted category, confidence score, and top matches.
        """
        text_clean = PrivacySanitizer.sanitize(text).lower()
        fn_clean = filename.lower()
        
        scores: Dict[str, float] = {cat: 0.0 for cat in cls.CATEGORIES_PATTERNS}
        matches_found: Dict[str, List[str]] = {cat: [] for cat in cls.CATEGORIES_PATTERNS}

        for cat, patterns in cls.CATEGORIES_PATTERNS.items():
            for pat in patterns:
                # Filename match gives high weight
                if re.search(pat, fn_clean):
                    scores[cat] += 3.0
                    matches_found[cat].append(f"filename: '{pat}'")

                # Text content match
                matches = re.findall(pat, text_clean)
                if matches:
                    weight = 1.0 + min(len(matches) * 0.2, 2.0)
                    scores[cat] += weight
                    matches_found[cat].append(f"text ({len(matches)}x): '{pat}'")

        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_cats[0]

        # Calculate confidence score between 0.0 and 1.0
        total_score = sum(scores.values())
        if total_score == 0 or top_score == 0:
            confidence = 0.1
            predicted_category = "Geral / Outros"
        else:
            confidence = min(0.99, round(top_score / (top_score + 2.0), 2))
            predicted_category = top_cat

        return {
            "predicted_category": predicted_category,
            "confidence": confidence,
            "raw_score": round(top_score, 2),
            "matched_indicators": matches_found.get(predicted_category, [])[:5],
            "all_scores": {cat: round(sc, 2) for cat, sc in sorted_cats if sc > 0}
        }
