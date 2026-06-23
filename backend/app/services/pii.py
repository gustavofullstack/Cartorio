"""PII scrubbing service - detecta e mascara dados pessoais antes de:

1. Mandar mensagem pra LLM (Claude/GPT) - NAO vaza CPF pra API publica
2. Persistir em log de conversa - LGPD exige minimizacao
3. Exibir em UI que nao precisa do dado completo

Trocadudos: nunca eh 100%. Por isso bot usa human-in-the-loop
em qualquer acao que dependa de PII real. Este servico eh defesa
em profundidade, nao bala de prata.

LIMITACOES CONHECIDAS (LGPD cartorio-lgpd review 2026-06-23):
- NAO detecta: nome completo, endereco livre, naturalidade.
  Esses campos exigem contexto semantico que regex nao alcança.
  Mitigacao: PII scrubbing em 3 camadas + HITL obrigatorio + retencao 365d.
- Datas DD/MM/YYYY sao SEMPRE redacted (incluindo datas nao-PII).
  Trade-off assumido: falsos positivos sao aceitaveis; falsos
  negativos nao. (LGPD art. 6o VIII - prevencao).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class ScrubResult:
    text: str
    findings: dict[str, int] = field(default_factory=dict)
    redaction_count: int = 0


# Regex patterns calibrados pra formato brasileiro.
# ATENCAO LGPD: CNPJ pattern aceita QUALQUER filial (0001 a 9999),
# nao apenas matriz. Fix aplicado em 2026-06-23 (cartorio-lgpd review).
_PATTERNS: dict[str, re.Pattern[str]] = {
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "rg": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]\b"),
    "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    "cartao": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "phone_br": re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[\s-]?\d{4}"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "cep": re.compile(r"\b\d{5}-?\d{3}\b"),
    "pis": re.compile(r"\b\d{3}\.?\d{5}\.?\d{2}-?\d{2}\b"),
    "titulo_eleitor": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    # Data em formato brasileiro DD/MM/YYYY (ou DD-MM-YYYY / DD.MM.YYYY).
    # LGPD art. 6 VIII - prevencao: falso positivo aceito, falso negativo nao.
    "data_nascimento": re.compile(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b"),
    # Placa Mercosul (ABC1D23) e placa antiga (ABC-1234 / ABC1234).
    "placa_veiculo": re.compile(r"\b[A-Z]{3}-?\d[A-Z]\d{2}\b|\b[A-Z]{3}-?\d{4}\b"),
}


def scrub(text: str) -> ScrubResult:
    """Detecta e mascara PII. Retorna texto scrubbed + contagem de cada tipo."""
    findings: dict[str, int] = {}
    out = text
    total = 0
    for label, pattern in _PATTERNS.items():
        matches = pattern.findall(out)
        if matches:
            findings[label] = len(matches)
            total += len(matches)
            out = pattern.sub(f"[{label.upper()}_REDACTED]", out)
    return ScrubResult(text=out, findings=findings, redaction_count=total)


def detect_only(text: str) -> dict[str, int]:
    """So detecta, nao altera texto. Util pra gates antes de chamar LLM."""
    return {label: len(p.findall(text)) for label, p in _PATTERNS.items() if p.findall(text)}


def hash_pii(value: str, salt: str) -> str:
    """Hash deterministic com salt por cliente. Usado pra CPF/telefone no DB.

    Permite lookup (WHERE cpf_hash = ?) sem expor o valor original.
    Nao confundir com criptografia - hash nao eh reversivel.
    """
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()