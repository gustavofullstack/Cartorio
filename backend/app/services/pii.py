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
    """Detecta e mascara PII. Retorna texto scrubbed + contagem de cada tipo.

    A2: instrumenta counter `pii_blocked_total{tipo_scrub,channel}` e
    histogram `scrub_latency_ms{tipo_scrub,result}` quando PII detectado.
    Channel default 'api'.

    Lookup do store eh DINAMICO (via modulo) para permitir reset em tests
    via `app.services.metrics.store = new_store`.
    """
    import time

    from app.services import metrics as metrics_mod

    metrics_store = metrics_mod.store

    findings: dict[str, int] = {}
    out = text
    total = 0
    start = time.perf_counter()
    for label, pattern in _PATTERNS.items():
        matches = pattern.findall(out)
        if matches:
            findings[label] = len(matches)
            total += len(matches)
            out = pattern.sub(f"[{label.upper()}_REDACTED]", out)
    duration_ms = (time.perf_counter() - start) * 1000.0

    # A2 metricas: instrumentar counter + histogram
    if total > 0:
        for tipo_scrub in findings.keys():
            metrics_store.inc_pii_blocked(tipo_scrub=tipo_scrub, channel="api")
        metrics_store.track_scrub_latency(
            tipo_scrub=",".join(sorted(findings.keys())),
            result="blocked",
            duration_ms=duration_ms,
        )
    else:
        metrics_store.track_scrub_latency(
            tipo_scrub="none",
            result="allowed",
            duration_ms=duration_ms,
        )

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


# ============================================================================
# CNS - validacao de check-digit (DV) via Modulo 11
# Manual tecnico DATASUS / Ministerio da Saude (CADSUS).
# Camada EXTRA de validacao alem do regex CNS. NAO substitui o regex;
# so eh chamada quando o regex ja matcheou.
#
# Algoritmo (confirmado por implementacao de referencia):
# - CNS = 15 digitos + 1 DV = 16 digitos totais
# - Pesos FIXOS decrescentes: 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
#   aplicados da posicao 1 (peso 15) ate posicao 15 (peso 1)
# - Soma = soma(digito[i] * peso[i])
# - DV = 11 - (soma mod 11)
# - Se DV >= 10, DV = 0 (regra de overflow)
#
# Classificacao do CNS:
# - Provisorio: 1o digito = 8 ou 9
# - Definitivo: 1o digito = 1, 2, 3, 4, 5 ou 6
# ============================================================================


_CNS_PESOS: tuple[int, ...] = (15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)


def _cns_mod11(first15: str) -> int:
    """Aplica Modulo 11 sobre os 15 primeiros digitos do CNS.

    Retorna DV calculado: 11 - (soma mod 11), ou 0 se resultado >= 10.
    """
    soma = sum(int(d) * p for d, p in zip(first15, _CNS_PESOS, strict=True))
    resto = soma % 11
    dv = 11 - resto
    return 0 if dv >= 10 else dv


def _cns_dv(first15: str) -> int:
    """Calcula DV (digito verificador unico) do CNS a partir dos 15 primeiros digitos.

    Levanta ValueError se entrada nao tiver 15 digitos decimais.
    """
    if len(first15) != 15 or not first15.isdigit():
        raise ValueError("CNS primeiros 15 digitos invalidos")
    return _cns_mod11(first15)


def validate_cns(cns_digits: str) -> bool:
    """Valida check-digit (DV) de um CNS ja normalizado (so digitos).

    Regras de aceite:
    - 16 digitos: valida DV (pos 16) via Modulo 11 com pesos fixos 15..1.
    - 15 digitos: retorna False (CNS sem DV NAO eh confiavel - pode ser
      ISBN/processo/OAB; caller deve re-promptar usuario).
    - Outros tamanhos ou nao-digitos: retorna False.

    Caller deve pre-normalizar a entrada removendo espacos/pontos
    (ex.: re.sub(r'\\D', '', cns)) antes de chamar esta funcao.

    Referencia: Manual tecnico DATASUS / Ministerio da Saude (CADSUS).
    """
    if not cns_digits or not cns_digits.isdigit():
        return False
    if len(cns_digits) == 15:
        return False
    if len(cns_digits) != 16:
        return False
    first15 = cns_digits[:15]
    dv_declarado = int(cns_digits[15])
    dv_calculado = _cns_dv(first15)
    return dv_calculado == dv_declarado


# ============================================================================
# CNH (Carteira Nacional de Habilitacao) - validacao de check-digit (DV1 + DV2)
# Formato: 9 digitos base + 2 DV = 11 digitos totais.
# Algoritmo publico: Modulo 11 com pesos ciclicos 2..9 (direita para esquerda).
# Fonte: implementacoes open source validadas (tiimgreen/validar-cnh,
# jcassio0/validarCNPJ-CPF-CNH). Nao ha publicacao oficial DENATRAN.
#
# Camada EXTRA ao regex CNH. NAO substitui o regex cnh em _PATTERNS.
# ============================================================================


def _cnh_mod11(digitos: str) -> int:
    """Aplica Modulo 11 sobre uma string de digitos decimais.

    Pesos ciclicos 2..9, do mais a direita (peso 2) ate o mais a
    esquerda. Retorna DV calculado: se (soma mod 11) < 2, DV = 0;
    senao DV = 11 - (soma mod 11).
    """
    soma = 0
    n = len(digitos)
    for i, ch in enumerate(digitos):
        dist = n - 1 - i
        peso = (dist % 8) + 2  # ciclo 2..9 (8 valores)
        soma += int(ch) * peso
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def _cnh_dv1(first9: str) -> int:
    """Calcula DV1 (posicao 10) da CNH a partir dos 9 primeiros digitos.

    Levanta ValueError se entrada nao tiver 9 digitos decimais.
    """
    if len(first9) != 9 or not first9.isdigit():
        raise ValueError("CNH primeiros 9 digitos invalidos")
    return _cnh_mod11(first9)


def _cnh_dv2(first10: str) -> int:
    """Calcula DV2 (posicao 11) da CNH a partir dos 10 primeiros digitos (9 + DV1).

    Levanta ValueError se entrada nao tiver 10 digitos decimais.
    """
    if len(first10) != 10 or not first10.isdigit():
        raise ValueError("CNH primeiros 10 digitos (9 + DV1) invalidos")
    return _cnh_mod11(first10)


def validate_cnh(cnh_digits: str) -> bool:
    """Valida check-digit (DV1 + DV2) de uma CNH ja normalizada (so digitos).

    Regras de aceite:
    - 11 digitos: valida DV1 (pos 10) e DV2 (pos 11) via Modulo 11.
    - 9 digitos: retorna False (CNH sem DV NAO eh confiavel).
    - Outros tamanhos ou nao-digitos: retorna False.

    Caller deve pre-normalizar a entrada removendo espacos/pontos
    (ex.: re.sub(r'\\D', '', cnh)) antes de chamar esta funcao.

    Referencia: algoritmo publico, validado por implementacoes open source.
    """
    if not cnh_digits or not cnh_digits.isdigit():
        return False
    if len(cnh_digits) == 9:
        return False
    if len(cnh_digits) != 11:
        return False
    first9 = cnh_digits[:9]
    dv1_declarado = int(cnh_digits[9])
    dv2_declarado = int(cnh_digits[10])
    dv1_calculado = _cnh_dv1(first9)
    if dv1_calculado != dv1_declarado:
        return False
    dv2_calculado = _cnh_dv2(first9 + str(dv1_calculado))
    return dv2_calculado == dv2_declarado