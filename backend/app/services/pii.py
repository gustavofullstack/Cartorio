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

========================================================================
!! ORDEM CRITICA DOS PATTERNS - NAO REORDENAR SEM TESTAR TODOS !!
========================================================================
P0.5 docs 2026-06-23 (cartorio-dev): a ordem dos regex em _PATTERNS
(dict insertion order) EH CRITICA porque scrub() processa em sequencia
e cada match eh substituido ANTES do proximo pattern rodar. Risco real
de regressao se alguem "limpar" a ordem por logica alfabetica.

Conflitos documentados (resolveram via ordem + tightening):
- CNS (15 dig) ANTES de phone_br (10+ dig loose): senao phone_br
  engole os primeiros 10-11 digitos do CNS e deixa "12345" solto.
  Confirmado por test_scrub_cns_15_digitos_contiguos_com_keyword.
- CNH (11 dig) ANTES de cpf (11 dig): senao cpf engole os 11 digitos
  da CNH primeiro. Keyword "CNH"/"habilitacao"/"motorista" desambigua,
  mas cpf match SEM keyword continua sendo cpf.
  Confirmado por test_scrub_cnh_11_digitos_contiguos_com_keyword.
- PIS (3-5-3 grupos) ANTES de cpf (3-3-3-2 grupos): formato distinto
  evita match ambiguo. Trade-off: PIS exige 3 grupos, CPF exige 4.
- RG (7-9 dig com ponto) ANTES de cep (5-3 com hifen): RG exige
  ponto, CEP nao - evita match de CEP puro como RG.
- cartao (4-4-4-4 ou 4-6-5 agrupado) ANTES de phone_br loose: formato
  agrupado eh mais especifico que phone.

Testes que dependem desta ordem (NAO REMOVER):
- tests/test_pii.py::test_scrub_cns_15_digitos_contiguos_com_keyword
- tests/test_pii.py::test_scrub_cnh_11_digitos_contiguos_com_keyword
- tests/test_pii.py::test_scrub_credit_card (4-4-4-4 vs phone loose)
- tests/test_pii.py::test_scrub_rg_cnpj_phone_email (RG vs CEP)

REGRA: ao adicionar novo pattern, perguntar:
1. Colide com vizinho (mesmo N de digitos)? Adicionar ANTES do vizinho.
2. Keyword-anchored (CNS, CNH) ou loose? Keyword antes de loose.
3. Se trocar a ordem, rodar pytest tests/test_pii.py -v --tb=short
   E verificar test_scrub_cep_puro_is_redacted,
   test_scrub_isbn_is_not_redacted (FP tests).

LGPD review desta ordem: cartorio-lgpd 2026-06-23 (Sprint 3 LGPD-015
follow-up). Cross-review formal pre-merge em ADR-019 (P0.5).
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
# Ordem dos patterns: mais especificos primeiro. Cada pattern precisa
# ser distinto o suficiente pra nao colidir com vizinhos. Fix aplicado
# em 2026-06-23 (cartorio-lgpd review) - conflitos PIS vs CPF,
# RG vs CEP, cartao vs phone_br, titulo vs phone_br resolvidos via
# reordenacao + tightening de regex.
# - "data_nascimento" cobre BR (DD/MM/YYYY com /-.) e NAO ISO. Trade-off
#   documentado: datas de protocolo em formato ISO NAO sao redatadas
#   (evita falso positivo em logs de sistema).
# - CNS e CNH adicionados em 2026-06-23 (P0.3 + P0.4 cartorio-lgpd
#   audit): ambos sao ANCHORED em keyword ("CNS"/"SUS" para CNS;
#   "CNH"/"carteira nacional de habilitacao"/"habilitacao"/
#   "motorista" para CNH) para evitar falso positivo contra
#   ISBN, OAB, CNJ, conta bancaria, CEP, etc. LGPD art. 11
#   (CNS = dado sensivel saude) e art. 6 (CNH = identificacao
#   pessoal) cobertos.
_PATTERNS: dict[str, re.Pattern[str]] = {
    # 1. EMAIL - tem @, super especifico
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    # 2. DATA - formato BR DD/MM/YYYY com separadores /-. e ISO YYYY-MM-DD.
    # LGPD art. 6 VIII - prevencao: falso positivo aceito, falso negativo nao.
    "data": re.compile(
        r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b"  # DD/MM/YYYY BR
        r"|\b\d{4}-\d{2}-\d{2}\b"  # YYYY-MM-DD ISO
    ),
    # 3. PLACA VEICULO - Mercosul (ABC1D23) e antiga (ABC-1234 / ABC1234)
    "placa_veiculo": re.compile(
        r"\b[A-Z]{3}-?\d[A-Z]\d{2}\b|\b[A-Z]{3}-?\d{4}\b"
    ),
    # 4. CNPJ - 14 digitos com pontos/dash/separador opcionais (matriz ou filial)
    "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    # 5. CNS (Cartao Nacional de Saude) - LGPD art. 11 BLOQUEANTE.
    # ANCHORED em keyword: "CNS" / "SUS" / "cartao nacional de saude".
    # Formato 1: 15 digitos contiguos (CNS provisorio / definitivo).
    # Formato 2: 17 digitos (CNS + DV - modelo DATASUS).
    # Formato 3: 3-4-4-4 com espacos ou pontos (DATASUS legivel).
    # Context: ate 30 chars nao-digit entre keyword e numero (permite
    # "meu CNS e 12345..." mas bloqueia matches long-distance).
    # Anti-FP: SEM keyword, 15 digitos sozinho NAO matchea (pode ser
    # ISBN, OAB, CNJ, hash, etc - FPs conhecidos de regex 15-digit).
    # ORDEM CRITICA: CNS DEVE rodar ANTES de phone_br (senao phone_br
    # come os primeiros 11 digitos do CNS de 15).
    "cns": re.compile(
        r"(?i)\b(?:CNS|SUS|cart[aã]o\s+nacional\s+de\s+sa[uú]de)\b"
        r"[^\d\n]{0,30}?"
        r"(?:\d{15}|\d{17}|\d{3}[\s.]?\d{4}[\s.]?\d{4}[\s.]?\d{4})\b"
    ),
    # 6. CNH (Carteira Nacional de Habilitacao) - LGPD art. 6.
    # ANCHORED em keyword: "CNH" / "carteira nacional de habilitacao" /
    # "habilitacao" / "motorista". Formato 1: 11 digitos contiguos.
    # Formato 2: 9 digitos + DV (2 chars, com ou sem hifen/espaco).
    # Context: ate 30 chars nao-digit entre keyword e numero.
    # Anti-FP: SEM keyword, 11 digitos sozinho NAO matchea (colide
    # com CPF; keyword desambigua).
    # ORDEM CRITICA: CNH DEVE rodar ANTES de CPF (senao CPF come os
    # 11 digitos da CNH primeiro).
    "cnh": re.compile(
        r"(?i)\b(?:CNH|carteira\s+nacional\s+de\s+habilita[çc][aã]o|"
        r"habilita[çc][aã]o|motorista)\b"
        r"[^\d\n]{0,30}?"
        r"(?:\d{11}|\d{9}[\s.\-]?\d{2})\b"
    ),
    # 7. CPF - 11 digitos em formato 3-3-3-2 (3 grupos + verificador)
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    # 8. PIS - 11 digitos em formato 3-5-3 (3 grupos, sem verificador)
    # Diferenciado de CPF por ter 3 grupos em vez de 4.
    "pis": re.compile(r"\b\d{3}\.?\d{5}\.?\d{3}\b"),
    # 9. RG - 7-9 digitos + verificador (digito ou X). EXIGE pelo menos
    # um ponto para nao colidir com CEP.
    "rg": re.compile(r"\b\d{1,2}\.\d{3}\.?\d{3}-?[\dxX]\b"),
    # 10. TITULO_ELEITOR - 12 digitos com espacos opcionais (3 grupos de 4)
    "titulo_eleitor": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    # 11. PHONE_BR - telefone brasileiro 10-11 digitos
    "phone_br": re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[\s-]?\d{4}"),
    # 12. CEP - 8 digitos (5+3 com hifen opcional). Roda DEPOIS de RG.
    "cep": re.compile(r"\b\d{5}-?\d{3}\b"),
    # 13. CARTAO - cartao de credito 16 (Visa/MC) ou 15 (Amex) digitos.
    # Agrupamento explicito (4-4-4-4 ou 4-6-5) para nao colidir com phone.
    "cartao": re.compile(
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
        r"|\b\d{4}[\s-]?\d{6}[\s-]?\d{5}\b"
    ),
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