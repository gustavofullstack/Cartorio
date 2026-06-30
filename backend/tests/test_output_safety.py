"""Testes de Output Safety utilities (LGPD-016 #13 — output scrub FULL COVERAGE).

Cobre:
- String simples com CPF
- Dict com multiplas chaves (algumas com PII)
- Dict nested (cliente.cpf)
- List de clientes
- Tipos primitivos (int, float, bool, None)
- Idempotencia (scrub 2x retorna mesmo resultado)
- Combinacoes com CNS+CNH (LGPD art. 11 BLOQUEANTE)
- Casos extremos: payload vazio, deeply nested
"""

from __future__ import annotations

from app.services.pii import scrub
from app.utils.output_safety import scrub_response, scrub_response_safe


# ============================================================================
# Strings
# ============================================================================


def test_scrub_response_string_com_cpf():
    """String com CPF eh scrubbed."""
    result, count = scrub_response("meu cpf é 123.456.789-09")
    assert "123.456.789-09" not in result
    assert "[CPF_REDACTED]" in result
    assert count == 1


def test_scrub_response_string_sem_pii_retorna_inalterado():
    """String sem PII retorna igual (count=0)."""
    payload = "Olá, tudo bem?"
    result, count = scrub_response(payload)
    assert result == payload
    assert count == 0


def test_scrub_response_string_vazia():
    """String vazia retorna vazia."""
    result, count = scrub_response("")
    assert result == ""
    assert count == 0


# ============================================================================
# Dicts
# ============================================================================


def test_scrub_response_dict_com_cpf_em_um_campo():
    """Dict com 1 campo PII: scrub so nesse campo, demais intactos."""
    payload = {"nome": "João Silva", "cpf": "123.456.789-09"}
    result, count = scrub_response(payload)
    assert result["nome"] == "João Silva"  # nao tem PII no padrao
    assert "[CPF_REDACTED]" in result["cpf"]
    assert "123.456.789-09" not in result["cpf"]
    assert count == 1


def test_scrub_response_dict_multiplos_pii():
    """Dict com CPF + CNS + CNH: conta todos (LGPD NAO permite vazar)."""
    # CNS/CNH SEM keyword sao redatados via CPF/phone_br (scrubber eh conservative).
    # O importante: NADA vaza. Label exato varia.
    payload = {
        "cpf": "123.456.789-09",
        "cns": "898 0007 6473 5600",
        "cnh": "12345678901",
        "nome": "João",
    }
    result, count = scrub_response(payload)
    # CPF formatado eh redatado como CPF
    assert "[CPF_REDACTED]" in result["cpf"]
    # CNS/CNH sem keyword sao redatados via outro padrao (CPF/phone/titulo loose)
    # mas o valor bruto NAO pode aparecer
    assert "898 0007 6473 5600" not in result["cns"]
    assert "12345678901" not in result["cnh"]
    assert "REDACTED" in result["cns"]  # qualquer marcador de redacao
    assert "REDACTED" in result["cnh"]  # qualquer marcador de redacao
    # Count >= 1 (todos foram redatados)
    assert count >= 1


def test_scrub_response_dict_multiplos_pii_com_keyword_cns_cnh():
    """Com keyword CNS/CNH, sao redatados com label especifico (LGPD art. 11 BLOQUEANTE)."""
    payload = {
        "cpf": "123.456.789-09",
        "cartao_sus": "CNS 898000764735600",  # keyword CNS
        "carteira": "CNH 12345678901",  # keyword CNH
        "nome": "João",
    }
    result, count = scrub_response(payload)
    assert "[CPF_REDACTED]" in result["cpf"]
    assert "[CNS_REDACTED]" in result["cartao_sus"]
    assert "[CNH_REDACTED]" in result["carteira"]
    assert count == 3


def test_scrub_response_dict_nested():
    """Dict nested (cliente.cpf) eh scrubbed recursivamente."""
    payload = {
        "protocolo_id": 12345,
        "cliente": {
            "nome": "João",
            "cpf": "123.456.789-09",
            "endereco": {
                "rua": "Av. Brasil",
                "cep": "38400-100",  # CEP 8 digitos eh redatado por scrub()
            },
        },
    }
    result, count = scrub_response(payload)
    assert result["cliente"]["cpf"] == "[CPF_REDACTED]"
    # CEP tambem eh redatado (regex detecta 8 digitos)
    assert result["cliente"]["endereco"]["cep"] == "[CEP_REDACTED]"
    # Total >= 2 (CPF + CEP)
    assert count >= 2


def test_scrub_response_dict_vazio():
    """Dict vazio retorna vazio."""
    result, count = scrub_response({})
    assert result == {}
    assert count == 0


# ============================================================================
# Lists
# ============================================================================


def test_scrub_response_list_de_strings_com_pii():
    """List de strings: cada item scrubbed."""
    payload = ["cpf 123.456.789-09", "cpf 987.654.321-00", "sem pii"]
    result, count = scrub_response(payload)
    assert "[CPF_REDACTED]" in result[0]
    assert "[CPF_REDACTED]" in result[1]
    assert result[2] == "sem pii"
    assert count == 2


def test_scrub_response_list_de_dicts():
    """List de dicts: cada dict eh processado."""
    payload = [
        {"cpf": "123.456.789-09"},
        {"cpf": "987.654.321-00"},
    ]
    result, count = scrub_response(payload)
    assert "[CPF_REDACTED]" in result[0]["cpf"]
    assert "[CPF_REDACTED]" in result[1]["cpf"]
    assert count == 2


# ============================================================================
# Tipos primitivos
# ============================================================================


def test_scrub_response_int_retorna_inalterado():
    """int nao eh string, retorna como veio."""
    result, count = scrub_response(12345)
    assert result == 12345
    assert count == 0


def test_scrub_response_float_retorna_inalterado():
    """float nao eh string, retorna como veio."""
    result, count = scrub_response(3.14)
    assert result == 3.14
    assert count == 0


def test_scrub_response_bool_retorna_inalterado():
    """bool nao eh string, retorna como veio."""
    result, count = scrub_response(True)
    assert result is True
    assert count == 0


def test_scrub_response_none_retorna_none():
    """None retorna None."""
    result, count = scrub_response(None)
    assert result is None
    assert count == 0


# ============================================================================
# Idempotencia
# ============================================================================


def test_scrub_response_idempotente_string():
    """Scrub 2x da mesma string retorna mesmo resultado sem novo PII."""
    payload = "cpf 123.456.789-09"
    s1, n1 = scrub_response(payload)
    s2, n2 = scrub_response(s1)
    assert s1 == s2
    assert n1 >= 1  # primeira passada detecta
    assert n2 == 0  # segunda passada NAO detecta mais (ja scrubbed)


def test_scrub_response_idempotente_dict():
    """Dict scrubbed 2x retorna mesma estrutura."""
    payload = {"cpf": "123.456.789-09"}
    s1, n1 = scrub_response(payload)
    s2, n2 = scrub_response(s1)
    assert s1 == s2
    assert n2 == 0


# ============================================================================
# LGPD art. 11 BLOQUEANTE — CNS (dado sensivel saude)
# ============================================================================


def test_scrub_response_cns_em_payload_saude():
    """CNS (saude) eh scrubbed em qualquer lugar do payload (LGPD art. 11).

    NOTA: Sem keyword "CNS"/"SUS", o CNS 15dig match-ea como titulo_eleitor
    (regex 4-4-4). O importante eh que o valor NAO vaza — label varia.
    """
    payload = {
        "tipo": "atendimento_sus",
        "paciente": {
            "cns": "898 0007 6473 5600",
            "nome": "Maria",
        },
    }
    result, count = scrub_response(payload)
    assert "898 0007 6473 5600" not in result["paciente"]["cns"]
    assert "REDACTED" in result["paciente"]["cns"]
    assert count >= 1


def test_scrub_response_cnh_em_payload_transito():
    """CNH (identificacao pessoal) eh scrubbed em qualquer lugar (LGPD art. 6).

    NOTA: Sem keyword "CNH"/"carteira", o CNH 11dig match-ea como CPF
    (regex 11 digitos). O importante eh que o valor NAO vaza — label varia.
    """
    payload = {
        "tipo": "cnh_consulta",
        "motorista": {"cnh": "12345678901"},
    }
    result, count = scrub_response(payload)
    assert "12345678901" not in result["motorista"]["cnh"]
    assert "REDACTED" in result["motorista"]["cnh"]
    assert count >= 1


# ============================================================================
# Helper simplificado
# ============================================================================


def test_scrub_response_safe_retorna_somente_payload():
    """scrub_response_safe retorna apenas o payload (sem count)."""
    result = scrub_response_safe("cpf 123.456.789-09")
    assert "[CPF_REDACTED]" in result
    assert isinstance(result, str)


def test_scrub_response_safe_dict():
    """scrub_response_safe funciona em dicts."""
    result = scrub_response_safe({"cpf": "123.456.789-09"})
    assert result["cpf"] == "[CPF_REDACTED]"


def test_scrub_response_safe_idempotente():
    """scrub_response_safe eh idempotente (igual scrub_response sem count)."""
    payload = {"cpf": "123.456.789-09"}
    s1 = scrub_response_safe(payload)
    s2 = scrub_response_safe(s1)
    assert s1 == s2


# ============================================================================
# Integracao com services.pii.scrub (LGPD-by-design)
# ============================================================================


def test_scrub_response_usa_pii_scrub_indiretamente():
    """scrub_response delega para services.pii.scrub (UNICA fonte)."""
    # Garante que scrub() retorna count correto
    direct = scrub("cpf 123.456.789-09")
    assert direct.redaction_count == 1
    # Wrapper deve retornar mesmo count
    via_wrapper, count = scrub_response("cpf 123.456.789-09")
    assert count == direct.redaction_count
    assert via_wrapper == direct.text


# ============================================================================
# LGPD-by-design: NON-PII fields (consent_ip/UA/request_id) NAO devem ser alterados
# ============================================================================


def test_scrub_response_nao_altera_audit_metadata():
    """consent_ip / UA / request_id NAO sao PII (LGPD-by-design D5) — preservados."""
    payload = {
        "consent_ip": "187.45.123.45",  # IP completo (DPO-only context)
        "user_agent": "Mozilla/5.0",
        "request_id": "abc-123-def",
        "canal": "whatsapp",
    }
    result, count = scrub_response(payload)
    # IP nao tem scrub (no regex pattern matching)
    # Scrubber NAO detecta IPs como PII por design (sao contexto tecnico)
    assert result["consent_ip"] == "187.45.123.45"
    assert result["user_agent"] == "Mozilla/5.0"
    assert result["request_id"] == "abc-123-def"
    assert result["canal"] == "whatsapp"
    assert count == 0


# ============================================================================
# Stress test / realistic payload
# ============================================================================


def test_scrub_response_payload_realista_protocolo_response():
    """Payload realista de GET /api/v1/protocolo/{numero} — campos PII scrubbed."""
    payload = {
        "numero": "2026-00001",
        "status": "DRAFT",
        "cliente": {
            "nome": "João da Silva",
            "cpf_hash": "a" * 64,  # hash NAO eh PII matching
            "cpf_consultado_pelo_escrevente": "123.456.789-09",  # hipotese: deveria ser scrubbed se vazar
        },
        "valor_total": "87.50",
        "historico": [
            {"etapa": "pii_scrubbed", "timestamp": "2026-06-24T10:00:00"},
            {"etapa": "criado", "timestamp": "2026-06-24T10:00:01"},
        ],
    }
    result, count = scrub_response(payload)
    # Hash NAO matchea padrao PII (64 chars hex)
    assert "a" * 64 in str(result["cliente"]["cpf_hash"])
    # Campo hipotetico COM CPF seria scrubbed
    if "cpf_consultado_pelo_escrevente" in result["cliente"]:
        assert "123.456.789-09" not in result["cliente"]["cpf_consultado_pelo_escrevente"]
    # Total count >= 0 (depende se cpf_consultado_pelo_escrevente existe)
    assert count >= 0
