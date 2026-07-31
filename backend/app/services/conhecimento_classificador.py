"""Classificação documental local e determinística (sem LLM, sem rede).

Opera exclusivamente sobre texto já sanitizado. Nunca aprova publicação:
o resultado sempre permanece em ``PENDING_HUMAN_VALIDATION``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Final

# Catálogo fechado de tipos institucionais do 2º Tabelionato.
# code → (display_name, padrões regex em texto sanitizado)
_CATALOGO: Final[dict[str, tuple[str, tuple[str, ...]]]] = {
    "TESTAMENTO": (
        "Testamento público / cláusulas",
        (
            r"testamento",
            r"testamenteiro",
            r"herdeiro\s+testament",
            r"revoga[cç][aã]o\s+de\s+testamento",
            r"cl[aá]usulas?\s+restritivas",
            r"nascituro",
        ),
    ),
    "USUCAPIAO": (
        "Usucapião extrajudicial / ata",
        (
            r"usucapi[aã]o",
            r"justo\s+t[ií]tulo",
            r"posse\s+mansa",
            r"confrontantes?",
        ),
    ),
    "INVENTARIO_PARTILHA": (
        "Inventário, partilha e renúncia",
        (
            r"invent[aá]rio",
            r"partilha",
            r"ren[uú]ncia",
            r"inventariante",
            r"monte\s+mor",
            r"sobrepartilha",
        ),
    ),
    "DIVORCIO_UNIAO_ESTAVEL": (
        "Divórcio / união estável / pacto",
        (
            r"div[oó]rcio",
            r"uni[aã]o\s+est[aá]vel",
            r"pacto\s+antenupcial",
            r"dissolu[cç][aã]o\s+de\s+uni[aã]o",
            r"regime\s+de\s+bens",
        ),
    ),
    "ESCRITURA_COMPRA_VENDA": (
        "Escritura de compra e venda / doação / cessão",
        (
            r"compra\s+e\s+venda",
            r"escritura\s+p[uú]blica",
            r"doa[cç][aã]o",
            r"cess[aã]o\s+de\s+direitos",
            r"transmitente",
            r"adquirente",
        ),
    ),
    "ESTREMACAO": (
        "Estremação",
        (r"estrema[cç][aã]o", r"confrontante", r"divis[aã]o\s+amig"),
    ),
    "PROCURACAO": (
        "Procuração e diligência",
        (
            r"procura[cç][aã]o",
            r"outorgante",
            r"outorgad[oa]",
            r"poderes\s+espec",
            r"dilig[eê]ncia",
        ),
    ),
    "RECONHECIMENTO_FIRMA": (
        "Reconhecimento de firma / autenticação / apostilamento",
        (
            r"reconhecimento\s+de\s+firma",
            r"autentica[cç][aã]o",
            r"apostilamento",
            r"e-?notariado",
            r"firma\s+por\s+semelhan[cç]a",
            r"firma\s+verdadeira",
        ),
    ),
    "ATA_NOTARIAL": (
        "Ata notarial",
        (
            r"ata\s+notarial",
            r"adjudica[cç][aã]o\s+compuls[oó]ria",
            r"constata[cç][aã]o",
        ),
    ),
    "EMOLUMENTOS": (
        "Tabela de emolumentos / valores",
        (
            r"emolumento",
            r"tabela\s+de\s+custas",
            r"taxa\s+de\s+fiscaliza",
            r"selo\s+de\s+fiscaliza",
            r"issqn",
        ),
    ),
    "NORMATIVO_CNJ": (
        "Normativo CNJ / provimento / jurisprudência",
        (
            r"provimento",
            r"\bcnj\b",
            r"corregedoria",
            r"jurisprud[eê]ncia",
            r"s[uú]mula",
            r"c[oó]digo\s+de\s+normas",
        ),
    ),
    "LISTA_DOCUMENTOS": (
        "Relação / checklist de documentos",
        (
            r"rela[cç][aã]o\s+de\s+documentos",
            r"documentos?\s+necess[aá]rios",
            r"checklist",
            r"lista\s+de\s+doctos",
            r"documenta[cç][aã]o\s+para",
        ),
    ),
    "SUCESSOES_HERANCA": (
        "Sucessões e herança",
        (
            r"heran[cç]a",
            r"sucess[aã]o",
            r"herdeiro\s+necess",
            r"mea[cç][aã]o",
            r"colaterais?",
            r"c[oô]njuge\s+sobrevivente",
        ),
    ),
    "OUTROS_ATOS": (
        "Outros atos notariais",
        (
            r"penhora",
            r"hipoteca",
            r"fian[cç]a",
            r"condom[ií]nio",
            r"holding",
            r"direito\s+de\s+superf[ií]cie",
            r"paternidade",
            r"dav\b",
        ),
    ),
}

_MIN_CONFIDENCE: Final[Decimal] = Decimal("0.3500")
_MAX_CONFIDENCE: Final[Decimal] = Decimal("0.9500")


@dataclass(frozen=True)
class ClassificacaoDocumento:
    """Resultado determinístico; nunca implica aprovação humana."""

    document_type_code: str
    display_name: str
    confidence: Decimal
    matched_signals: int
    classifier_name: str
    requires_human_validation: bool
    idempotency_key: str

    def as_dict(self) -> dict[str, object]:
        return {
            "document_type_code": self.document_type_code,
            "display_name": self.display_name,
            "confidence": str(self.confidence),
            "matched_signals": self.matched_signals,
            "classifier_name": self.classifier_name,
            "requires_human_validation": self.requires_human_validation,
            "idempotency_key": self.idempotency_key,
        }


def catalogo_tipos_documento() -> dict[str, str]:
    """Mapa code → display_name do catálogo fechado."""
    return {code: meta[0] for code, meta in _CATALOGO.items()}


def classificar_texto_sanitizado(
    texto_sanitizado: str,
    *,
    unit_id: str,
    classifier_name: str = "local_keyword_v1",
) -> ClassificacaoDocumento:
    """Classifica texto já sanitizado; fail-closed se entrada inválida.

    Não envia dados a rede/LLM. O resultado sempre exige validação humana.
    """
    if not isinstance(texto_sanitizado, str) or not texto_sanitizado.strip():
        raise ValueError("texto_sanitizado obrigatório")
    if not unit_id or len(unit_id) < 8:
        raise ValueError("unit_id opaco obrigatório")
    if _contem_marcador_pii_bruta(texto_sanitizado):
        # Texto sanitizado legítimo usa [REDACTED:...]; rejeita se parecer bruto.
        raise ValueError("texto aparenta conter PII bruta; recusar classificação")

    lowered = texto_sanitizado.casefold()
    melhor_code = "OUTROS_ATOS"
    melhor_nome = _CATALOGO["OUTROS_ATOS"][0]
    melhor_hits = 0

    for code, (display_name, patterns) in _CATALOGO.items():
        hits = sum(1 for pattern in patterns if re.search(pattern, lowered, re.IGNORECASE))
        if hits > melhor_hits:
            melhor_hits = hits
            melhor_code = code
            melhor_nome = display_name

    confidence = _score_confidence(melhor_hits, len(texto_sanitizado))
    idem = sha256(f"{classifier_name}:{unit_id}:{melhor_code}:{confidence}".encode()).hexdigest()

    return ClassificacaoDocumento(
        document_type_code=melhor_code,
        display_name=melhor_nome,
        confidence=confidence,
        matched_signals=melhor_hits,
        classifier_name=classifier_name,
        requires_human_validation=True,
        idempotency_key=idem,
    )


def _score_confidence(hits: int, text_len: int) -> Decimal:
    """Confiança monotônica limitada; nunca chega a 1.0 (HITL obrigatório)."""
    if hits <= 0:
        return _MIN_CONFIDENCE
    base = Decimal("0.40") + (Decimal(hits) * Decimal("0.12"))
    # Textos muito curtos reduzem confiança.
    if text_len < 80:
        base -= Decimal("0.10")
    if base < _MIN_CONFIDENCE:
        return _MIN_CONFIDENCE
    if base > _MAX_CONFIDENCE:
        return _MAX_CONFIDENCE
    return base.quantize(Decimal("0.0001"))


def _contem_marcador_pii_bruta(texto: str) -> bool:
    """Heurística conservadora: CPF formatado cru (não o placeholder REDACTED)."""
    if re.search(r"(?<!\[REDACTED:CPF\])\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto):
        # Se o match não é parte de placeholder, bloquear.
        for match in re.finditer(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto):
            start = max(0, match.start() - 20)
            window = texto[start : match.end() + 5]
            if "REDACTED" not in window:
                return True
    return False


__all__ = [
    "ClassificacaoDocumento",
    "catalogo_tipos_documento",
    "classificar_texto_sanitizado",
]
