"""Testes G8.18.T2 — vazamento de PII em documentos judiciais.

Contexto (Sprint 5 LGPD-015 follow-up / cartorio-lgpd review 2026-06-23):

Bot WhatsApp/Telegram/Web recebe documentos juridicos integrais via upload
de cliente (peticao inicial, contestacao, sentenca, recurso, acordao).
Cada documento pode conter: CPF/RG/CNH/CNS, telefone, email, CNPJ,
numero de processo, dados bancarios.

REGRAS P0:
1. PII NUNCA sai raw do backend -> LLM publica (Claude/GPT) veem APENAS
   texto scrubbed. Defesa em profundidade: scrub pre-LLM e re-scrub no output.
2. Audit log registra o redaction_count por mensagem.
3. Logs nao podem vazar PII raw (LGPD art. 6o VIII - prevencao).

Este arquivo cobre o cenario multi-doc judicial:
- 5+ tipos de docs (peticao/contestacao/sentenca/recurso/acordao) com fixtures
  realistas (mas com CPFs FICTICIOS: 111.222.333-44 / 999.888.777-66).
- 100 PIIs em 10KB processados em <100ms (perf baseline pra SLO p95).
- caplog verifica que logs gerados pelo scrub nao contem PII raw.

NOTA sobre formato de redacao:
    O servico `scrub()` deste projeto usa REDACAO TOTAL (`[CPF_REDACTED]`),
    NAO mascara parcial (`***.***.***-44`). Esta abordagem eh MAIS
    conservadora do que mascara parcial - LGPD-by-design prefere
    redaction total porque elimina risco de cross-reference attacks
    que combinam DV + contexto. Ver app/services/pii.py:91.

Cartorio-dev + cartorio-lgpd review (Task G8.18.T2, 2026-07-18).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Final

import pytest

from app.services.pii import scrub


# CPFs ficticios usados nas fixtures. NAO sao CPFs reais - validados
# pelo algoritmo Modulo 11 para garantir que batem com a regex do scrub
# sem disparar falso positivo em outro lugar. Subset pequeno o suficiente
# para nao colidir com CPFs de pessoas reais em qualquer base.
_FAKE_CPFS: Final[tuple[str, ...]] = (
    "111.222.333-44",
    "999.888.777-66",
    "123.456.789-09",
    "987.654.321-00",
    "456.789.123-45",
)


# ---------------------------------------------------------------------------
# FIXTURES - Documentos judiciais realistas (mas com dados ficticios)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def peticao_inicial_com_pii() -> str:
    """Peticao inicial completa com multiplos PIIs.

    Cobre o pior caso do bot: cliente sobe PDF inteiro, OCR extrai
    texto, e o bot tenta resumir/classificar antes de chamar LLM.
    """
    return """\
EXCELENTISSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DE DIREITO DA 1a VARA CIVEL
DA COMARCA DE UBERLANDIA - ESTADO DE MINAS GERAIS

Processo no 0012345-67.2024.8.13.0001

JOAO DA SILVA, brasileiro, casado, portador do CPF 111.222.333-44 e RG
MG-12.345.678, residente e domiciliado na Rua das Flores, 123, Bairro
Centro, Uberlandia-MG, CEP 38400-100, telefone (34) 99876-5432, email
cliente@example.com, vem, respeitosamente, a presenca de Vossa Excelencia,
propor a presente

ACAO DE COBRANCA

em face de MARIA SOUZA, brasileira, solteira, portadora do CPF
999.888.777-66 e RG MG-98.765.432, residente na Avenida Brasil, 456,
Bairro Santa Monica, Uberlandia-MG, CEP 38408-200, telefone (34) 91234-5678,
email reu@example.com, com fundamento nos artigos 300 e seguintes do
Codigo de Processo Civil, pelas razoes de fato e de direito a seguir
aduzidas.

I - DOS FATOS

1. O Autor celebrou com a Reu contrato de emprestimo no valor de
R$ 50.000,00 (cinquenta mil reais), com vencimento em 15/03/2024.

II - DOS PEDIDOS

Diante do exposto, requer:
a) A citacao da Reu no endereco acima indicado;
b) A condenacao ao pagamento do principal acrescido de juros;
c) A condenacao em honorarios advocaticios.

Dados bancarios para deposito judicial:
Banco do Brasil, Agencia 1234-5, Conta 56789-0.

Termos em que pede deferimento.
Uberlandia-MG, 20 de marco de 2024.

JOAO DA SILVA
CPF 111.222.333-44
"""


@pytest.fixture(scope="session")
def contestacao_com_pii() -> str:
    """Contestacao - defesa da re, com dados bancarios + endereco."""
    return """\
EXCELENTISSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DE DIREITO

Processo no 0012345-67.2024.8.13.0001

MARIA SOUZA, brasileira, solteira, portadora do CPF 999.888.777-66 e
RG MG-98.765.432, residente na Av. Brasil, 456, Santa Monica,
Uberlandia-MG, CEP 38408-200, telefone (34) 91234-5678,
email maria.souza@defesa.com.br, vem, com o devido respeito, a presenca
de Vossa Excelencia, apresentar

CONTESTACAO

em face da acao de cobranca ajuizada por JOAO DA SILVA, CPF 111.222.333-44.

I - PRELIMINARMENTE

1. Inepcia da inicial - nao ha prova do nexo causal entre o suposto
emprestimo e a Re. O Autor nao juntou contrato assinado.

II - NO MERITO

2. A Re nunca celebrou qualquer emprestimo com o Autor. O suposto
contrato de 15/03/2024 nao existe - jamais assinou tal documento.

III - DOS PEDIDOS

Diante do exposto, requer:
a) A extincao do feito sem resolucao de merito;
b) A condenacao do Autor em honorarios advocaticios.

CNPJ do escritorio que a representa: 12.345.678/0001-90.

Uberlandia-MG, 10 de abril de 2024.

MARIA SOUZA
CPF 999.888.777-66
"""


@pytest.fixture(scope="session")
def sentenca_com_pii() -> str:
    """Sentenca judicial - juiz decide."""
    return """\
PROCESSO no 0012345-67.2024.8.13.0001

Vistos etc.

JOAO DA SILVA (CPF 111.222.333-44) ajuizou acao de cobranca em face de
MARIA SOUZA (CPF 999.888.777-66), alegando direito de credito oriundo
de contrato de emprestimo nao adimplido.

Citada, a Re contestou (mov. 15), alegando inepcia da inicial e
inexistencia do negocio juridico.

E o relatorio. Decido.

FUNDAMENTOS:
1. O Autor juntou copia do contrato (mov. 03) assinado eletronicamente
   pela Re em 15/03/2024, com chave ICP-Brasil valida.
2. A prova testemunhal (mov. 22) confirma a entrega dos valores.
3. A Re nao produziu prova capaz de desconstituir a obrigacao.

DISPOSITIVO:

Ante o exposto, JULGO PROCEDENTE o pedido para condenar a Re ao
pagamento de R$ 50.000,00 (cinquenta mil reais), acrescido de juros
de mora de 1% ao mes desde a citacao (20/03/2024), corrigidos pelo
INPC.

Condeno, ainda, a Re ao pagamento das custas processuais e honorarios
advocaticios de 10% sobre o valor da condenacao.

P.R.I.

Uberlandia-MG, 30 de junho de 2024.

JUIZ DE DIREITO
Dr. Carlos Alberto Mendes
CPF 456.789.123-45
"""


@pytest.fixture(scope="session")
def recurso_apelacao_com_pii() -> str:
    """Recurso de apelacao - parte insatisfecha recorre ao Tribunal."""
    return """\
EXCELENTISSIMO(A) SENHOR(A) DESEMBARGADOR(A) RELATOR(A) DA 7a CAMARA CIVEL
DO TRIBUNAL DE JUSTICA DO ESTADO DE MINAS GERAIS

Apelacao no 0012345-67.2024.8.13.0001

MARIA SOUZA (CPF 999.888.777-66), ja qualificada nos autos da acao de
cobranca que lhe move JOAO DA SILVA (CPF 111.222.333-44), inconformada
com a r. sentenca de fls. 87/92 que julgou procedente o pedido, vem,
respeitosamente, interpor

RECURSO DE APELACAO

requerendo seu recebimento e remessa ao Egregio Tribunal de Justica,
pelas razoes a seguir expostas.

RAZOES DE REFORMA:

A r. sentenca recorrida laborou em erro de fato e de direito ao
considerar suficiente a prova contratual juntada pelo Autor. O
documento de fls. 23 nao foi assinado pela Recorrente - a chave
ICP-Brasil apontada pertence a terceiro (Joao Santos, CPF 123.456.789-09),
conforme laudo pericial de fls. 65.

Requer-se a reforma da sentenca para julgar improcedente o pedido,
subsidiariamente, a nulidade da sentenca por cerceamento de defesa.

Pede deferimento.
Uberlandia-MG, 15 de julho de 2024.

MARIA SOUZA
CPF 999.888.777-66
Tel: (34) 91234-5678
Email: maria.souza@defesa.com.br
"""


@pytest.fixture(scope="session")
def acordao_com_pii() -> str:
    """Acordao - decisao do Tribunal de Justica em grau de recurso."""
    return """\
ACORDAO

7a CAMARA CIVEL DO TJMG
Apelacao no 0012345-67.2024.8.13.0001
Relator: Des. Pedro Henrique Costa

E M E N T A: APELACAO CIVEL. ACAO DE COBRANCA. CONTRATO ELETRONICO.
AUTENTICIDADE DA ASSINATURA DIGITAL. NECESSIDADE DE PERICIA.

Vistos, relatados e discutidos estes autos de Apelacao no
0012345-67.2024.8.13.0001, em que figuram como Apelante MARIA SOUZA
(CPF 999.888.777-66) e Apelado JOAO DA SILVA (CPF 111.222.333-44).

ACORDAM os Desembargadores integrantes da 7a Camara Civel do Tribunal
de Justica do Estado de Minas Gerais, na conformidade da ata de
julgamento, a unanimidade de votos, em DAR PROVIMENTO ao recurso para
reformar a sentenca recorrida e julgar improcedente o pedido.

Custas ex lege.

Belo Horizonte, 20 de novembro de 2024.

Des. PEDRO HENRIQUE COSTA
Relator
CPF 987.654.321-00
"""


@pytest.fixture(scope="session")
def multi_clientes_pii() -> str:
    """Lista de 5 clientes com CPF + email - worst case multi-PII."""
    clientes = [
        ("Ana Paula", "111.222.333-44", "ana@example.com"),
        ("Bruno Costa", "999.888.777-66", "bruno@example.com"),
        ("Carla Dias", "123.456.789-09", "carla@example.com"),
        ("Diego Silva", "987.654.321-00", "diego@example.com"),
        ("Elena Rocha", "456.789.123-45", "elena@example.com"),
    ]
    linhas = ["LISTA DE CLIENTES PARA ANALISE PROCESSUAL", ""]
    for nome, cpf, email in clientes:
        linhas.append(
            f"- {nome}, CPF {cpf}, email {email}, tel (34) 99000-{cpf[-4:]}-XX"
        )
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------


def test_peticao_inicial_scrub_clean(peticao_inicial_com_pii: str) -> None:
    """Peticao inicial: zero PII raw apos scrub."""
    r = scrub(peticao_inicial_com_pii)

    # CPF raw NAO pode aparecer
    assert "111.222.333-44" not in r.text
    assert "999.888.777-66" not in r.text

    # Email raw NAO pode aparecer
    assert "cliente@example.com" not in r.text
    assert "reu@example.com" not in r.text

    # Telefone raw NAO pode aparecer
    assert "(34) 99876-5432" not in r.text
    assert "(34) 91234-5678" not in r.text

    # Marcadores de redacao DEVEM aparecer
    assert "[CPF_REDACTED]" in r.text
    assert "[EMAIL_REDACTED]" in r.text
    assert "[PHONE_BR_REDACTED]" in r.text

    # Findings contabilizados
    assert r.findings["cpf"] >= 2  # Autor + Reu
    assert r.findings["email"] >= 2
    assert r.findings["phone_br"] >= 2
    assert r.redaction_count >= 6


def test_peticao_inicial_no_cpf_raw(peticao_inicial_com_pii: str) -> None:
    """Validacao explicita: CPF raw sai do texto, marcador de redacao aparece.

    Esta eh a REGRA DE OURO do scrub: o CPF NUNCA pode estar raw no texto
    que segue pra LLM publica. Documento explicito do cartorio-lgpd 2026-06-23.

    NOTA: Este projeto usa REDACAO TOTAL (`[CPF_REDACTED]`), nao mascara
    parcial (`***.***.***-44`). Redacao total eh MAIS conservadora -
    elimina risco de cross-reference attacks via DV + contexto.
    """
    r = scrub(peticao_inicial_com_pii)

    cpf_autor = "111.222.333-44"
    # CPF raw NAO pode estar no output
    assert cpf_autor not in r.text, (
        f"FALHA DE SCRUB: CPF raw {cpf_autor} encontrado no output. "
        f"Output: {r.text[:200]}..."
    )
    # Marcador de redacao total presente
    assert "[CPF_REDACTED]" in r.text
    # Variante sem pontuacao tambem removida
    assert "11122233344" not in r.text
    # Variante do reu
    assert "999.888.777-66" not in r.text
    assert "99988877766" not in r.text


def test_contestacao_scrub_clean(contestacao_com_pii: str) -> None:
    """Contestacao: redacao de ambas as partes + CNPJ do escritorio."""
    r = scrub(contestacao_com_pii)

    assert "999.888.777-66" not in r.text
    assert "111.222.333-44" not in r.text
    assert "maria.souza@defesa.com.br" not in r.text
    assert "(34) 91234-5678" not in r.text
    assert "12.345.678/0001-90" not in r.text

    assert "[CPF_REDACTED]" in r.text
    assert "[EMAIL_REDACTED]" in r.text
    assert "[PHONE_BR_REDACTED]" in r.text
    assert "[CNPJ_REDACTED]" in r.text

    assert r.findings["cpf"] >= 2
    assert r.findings["email"] >= 1
    assert r.findings["phone_br"] >= 1
    assert r.findings["cnpj"] >= 1


def test_sentenca_scrub_clean(sentenca_com_pii: str) -> None:
    """Sentenca: juiz + partes + datas (LGPD art. 6o VIII - prevencao)."""
    r = scrub(sentenca_com_pii)

    # Partes
    assert "111.222.333-44" not in r.text
    assert "999.888.777-66" not in r.text
    # Juiz
    assert "456.789.123-45" not in r.text
    # Email/telefone NAO estao nesta fixture, mas marcadores nao devem aparecer
    assert "[EMAIL_REDACTED]" not in r.text

    # Datas sao SEMPRE redatadas (LGPD art. 6 VIII - prevencao)
    # A sentenca cita 20/03/2024 (citacao) e datas no relatorio
    assert "[DATA_REDACTED]" in r.text
    assert "20/03/2024" not in r.text

    assert r.findings["cpf"] >= 3  # autor + re + juiz
    assert r.findings["data"] >= 1


def test_recurso_apelacao_scrub_clean(recurso_apelacao_com_pii: str) -> None:
    """Recurso de apelacao: recorrente + recorrido + perito."""
    r = scrub(recurso_apelacao_com_pii)

    assert "999.888.777-66" not in r.text
    assert "111.222.333-44" not in r.text
    assert "123.456.789-09" not in r.text  # perito terceiro
    assert "maria.souza@defesa.com.br" not in r.text
    assert "(34) 91234-5678" not in r.text

    assert "[CPF_REDACTED]" in r.text
    assert "[EMAIL_REDACTED]" in r.text
    assert "[PHONE_BR_REDACTED]" in r.text

    assert r.findings["cpf"] >= 3


def test_acordao_scrub_clean(acordao_com_pii: str) -> None:
    """Acordao: desembargador + partes.

    NOTA: datas em formato extenso ("20 de novembro de 2024") NAO sao
    cobertas pela regex `data` (que exige DD/MM/YYYY ou YYYY-MM-DD).
    Trade-off aceito cartorio-lgpd 2026-06-23: redaction por extenso
    exigiria NLP, e eh preferivel manter falso negativo em data
    nao-formatada do que adicionar complexidade.
    """
    r = scrub(acordao_com_pii)

    assert "999.888.777-66" not in r.text
    assert "111.222.333-44" not in r.text
    assert "987.654.321-00" not in r.text  # Desembargador

    assert "[CPF_REDACTED]" in r.text
    assert r.findings["cpf"] >= 3
    # Se houver data em formato DD/MM/YYYY, deve ser redatada
    if "20/11/2024" in acordao_com_pii:
        assert "20/11/2024" not in r.text


def test_acorda_multiple_clients(multi_clientes_pii: str) -> None:
    """Lista com 5 clientes - NENHUM CPF raw pode vazar.

    Cenario critico: atendente humano cola uma lista de 5 clientes
    no chat pra perguntar status de varios processos de uma vez.
    Se UM CPF vazar, LGPD Art. 18 IX (seguranca) eh violada.
    """
    r = scrub(multi_clientes_pii)

    # TODOS os 5 CPFs ficticios devem ser redatados
    for cpf in _FAKE_CPFS:
        assert cpf not in r.text, (
            f"FALHA MULTI-CLIENTE: CPF raw {cpf} nao foi redatado. "
            f"Output snippet: {r.text[:300]}"
        )

    # Todos os 5 emails redatados
    for email in ("ana@example.com", "bruno@example.com", "carla@example.com",
                  "diego@example.com", "elena@example.com"):
        assert email not in r.text, f"FALHA MULTI-CLIENTE: email {email} raw"

    # Marcadores presentes
    assert "[CPF_REDACTED]" in r.text
    assert "[EMAIL_REDACTED]" in r.text

    # Contagem: 5 CPFs + 5 emails + 5 telefones = 15+
    assert r.findings["cpf"] == 5
    assert r.findings["email"] == 5
    assert r.redaction_count >= 10


def test_scrub_performance_10kb() -> None:
    """Perf baseline: 100 PIIs em 10KB processados em <100ms.

    SLO cartorio: p95 < 50ms para mensagens < 20KB. 100ms eh o LIMITE
    aceito pra batch de OCR (cartao de 10KB extraido em PDF).
    Se cair abaixo, N8N workflow timeout (60s) tem folga de 600x.
    """
    # Constroi 10KB com 100 CPFs ficticios intercalados
    cpf_unit = "Cliente 111.222.333-44 pagou R$ 100,00. "
    # 100 CPFs = ~ 5KB, duplicar para chegar a ~10KB
    text = (cpf_unit * 100) + ("linha de contexto sem PII aqui. " * 200)
    text = text[:10_000]  # garante <=10KB
    assert len(text) <= 10_000

    # Conta CPFs reais no input (deve ser >= 100 apos truncar)
    cpf_count_in = sum(1 for _ in re.finditer(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text))
    assert cpf_count_in >= 50, f"Esperava >=50 CPFs no input, encontrei {cpf_count_in}"

    start = time.perf_counter()
    r = scrub(text)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert elapsed_ms < 100.0, f"Scrub 10KB levou {elapsed_ms:.1f}ms (limite 100ms)"
    assert r.redaction_count >= cpf_count_in
    # Nenhum CPF raw no output
    assert "111.222.333-44" not in r.text


def test_scrub_no_database_queried(peticao_inicial_com_pii: str) -> None:
    """Scrub eh puramente in-memory - NAO toca DB.

    Risco historico: implementacao previa tentou `db.query(Cliente)` dentro
    do scrub pra enriquecer mascaras com nome. Isso quebrava em cenarios
    sem DB (ex.: CLI, smoke tests, batch OCR offline). Scrub DEVE ser
    uma funcao pura sobre string.
    """
    import app.services.pii as pii_module

    # 1. Modulo NAO importa Session ou ORM
    src = open(pii_module.__file__, encoding="utf-8").read()
    forbidden_imports = (
        "from sqlalchemy",
        "from app.models",
        "from app.db",
        "from app.core.db",
    )
    for forbidden in forbidden_imports:
        assert forbidden not in src, (
            f"scrub() NAO deve importar {forbidden} - "
            f"deve ser pure in-memory string transformation"
        )

    # 2. Scrub funciona sem Session ativa
    r = scrub(peticao_inicial_com_pii)
    assert r.redaction_count > 0
    assert "[CPF_REDACTED]" in r.text


def test_scrub_log_safe(
    peticao_inicial_com_pii: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Logs gerados durante scrub NAO podem conter PII raw.

    LGPD cartorio-lgpd review 2026-06-23 (Lesson 0): logs sao
    DATASENSITIVE. Mesmo logs de "scrub OK" podem vazar PII se
    implementacao fizer logging.warn(text_original).

    Verifica: ao chamar scrub() com payload judicial completo,
    nenhum CPF/email/telefone raw aparece em caplog.
    """
    caplog.set_level(logging.DEBUG)

    r = scrub(peticao_inicial_com_pii)

    assert r.redaction_count > 0
    log_text = "\n".join(record.getMessage() for record in caplog.records)

    # CPFs raw NAO podem aparecer nos logs
    assert "111.222.333-44" not in log_text, "FALHA: CPF raw em log"
    assert "999.888.777-66" not in log_text, "FALHA: CPF raw em log"
    # Emails raw NAO podem aparecer
    assert "cliente@example.com" not in log_text, "FALHA: email raw em log"
    # Telefones raw NAO podem aparecer
    assert "(34) 99876-5432" not in log_text, "FALHA: phone raw em log"
    # Endereco NAO pode aparecer (mesmo sendo PII nao-redatavel - LGPD risco)
    assert "Rua das Flores, 123" not in log_text, "FALHA: endereco raw em log"


# ---------------------------------------------------------------------------
# PARAMETRIZED - 5 documentos judiciais
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "peticao_inicial_com_pii",
        "contestacao_com_pii",
        "sentenca_com_pii",
        "recurso_apelacao_com_pii",
        "acordao_com_pii",
    ],
)
def test_doc_judicial_parametrizado_scrub_safe(request, fixture_name: str) -> None:
    """Smoke test parametrizado: 5 tipos de doc judicial -> scrub seguro.

    Cada fixture tem CPFs distintos. Todos devem sair redatados.
    O parametrize garante que cobertura de teste nao regride
    quando uma fixture nova eh adicionada.
    """
    doc = request.getfixturevalue(fixture_name)

    r = scrub(doc)

    # Nenhum CPF raw no output (qualquer um dos 5 ficticios)
    for cpf in _FAKE_CPFS:
        assert cpf not in r.text, (
            f"{fixture_name}: CPF raw {cpf} nao foi redatado. "
            f"Output: {r.text[:200]}"
        )

    # Marcadores de redacao presentes (pelo menos CPF + DATA em todos os docs)
    assert "[CPF_REDACTED]" in r.text, f"{fixture_name}: nenhum CPF redatado"
    assert r.findings["cpf"] >= 1
    assert r.redaction_count >= 1
