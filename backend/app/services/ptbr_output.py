"""Pequena normalização determinística da ortografia PT-BR de saída.

O modelo pode devolver texto sem acentos mesmo quando o prompt pede português.
Esta camada corrige apenas palavras inequívocas e preserva texto do cliente,
nomes próprios e números. Não é um corretor gramatical nem substitui revisão
humana para atos jurídicos.
"""

from __future__ import annotations

import re

_WORD_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("cartorio", "cartório"),
    ("Cartorio", "Cartório"),
    ("oficio", "ofício"),
    ("Oficio", "Ofício"),
    ("Uberlandia", "Uberlândia"),
    ("uberlandia", "uberlândia"),
    ("servico", "serviço"),
    ("Servico", "Serviço"),
    ("autenticacao", "autenticação"),
    ("Autenticacao", "Autenticação"),
    ("procuracao", "procuração"),
    ("Procuracao", "Procuração"),
    ("reconhecimento de firma", "reconhecimento de firma"),
    ("situacoes", "situações"),
    ("Situacoes", "Situações"),
    ("comprovacao", "comprovação"),
    ("Comprovacao", "Comprovação"),
    ("informacao", "informação"),
    ("Informacao", "Informação"),
    ("informacoes", "informações"),
    ("Informacoes", "Informações"),
    ("validacao", "validação"),
    ("Validacao", "Validação"),
    ("nao", "não"),
    ("Nao", "Não"),
    ("voce", "você"),
    ("Voce", "Você"),
    ("Ola", "Olá"),
    ("ola", "olá"),
    ("endereco", "endereço"),
    ("Endereco", "Endereço"),
    ("horario", "horário"),
    ("Horario", "Horário"),
    ("documento eletronico", "documento eletrônico"),
    ("Documento eletronico", "Documento eletrônico"),
)


def normalize_ptbr_output(text: str) -> str:
    """Corrige um conjunto fechado de erros ortográficos recorrentes."""
    if not text:
        return text
    result = text
    for source, target in _WORD_REPLACEMENTS:
        result = re.sub(rf"(?<![\wÀ-ÿ]){re.escape(source)}(?![\wÀ-ÿ])", target, result)
    # ``E muito utilizada`` no começo de um período é verbo, não conjunção.
    result = re.sub(r"(?m)(^|[.!?]\s+)(E)\s+(?=[a-záéíóúãõâêô])", r"\1É ", result)
    result = re.sub(r"\be\s+(?=(?:um|uma|um dos|uma das)\b)", "é ", result)
    return result


__all__ = ["normalize_ptbr_output"]
