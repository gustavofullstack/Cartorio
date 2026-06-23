"""Testes do PII scrubbing - LGPD compliance."""

from app.services.pii import detect_only, hash_pii, scrub


def test_scrub_cpf_with_and_without_punctuation():
    r = scrub("meu cpf é 123.456.789-09 ou 12345678909")
    assert "123.456.789-09" not in r.text
    assert "12345678909" not in r.text
    assert r.findings["cpf"] == 2
    assert "[CPF_REDACTED]" in r.text


def test_scrub_rg_cnpj_phone_email():
    text = "RG 12.345.678-9, CNPJ 12.345.678/0001-90, tel (11) 98765-4321, email joao@example.com"
    r = scrub(text)
    assert "12.345.678-9" not in r.text
    assert "12.345.678/0001-90" not in r.text
    assert "(11) 98765-4321" not in r.text
    assert "joao@example.com" not in r.text
    assert "rg" in r.findings
    assert "cnpj" in r.findings
    assert "phone_br" in r.findings
    assert "email" in r.findings


def test_scrub_clean_text_unchanged():
    text = "Olá, gostaria de saber o status do meu protocolo"
    r = scrub(text)
    assert r.text == text
    assert r.findings == {}
    assert r.redaction_count == 0


def test_detect_only_does_not_modify_text():
    text = "cpf 123.456.789-09 e email teste@x.com"
    findings = detect_only(text)
    assert findings == {"cpf": 1, "email": 1}
    # texto original intacto
    assert "123.456.789-09" in text
    assert "teste@x.com" in text


def test_hash_pii_deterministic_with_same_salt():
    h1 = hash_pii("12345678909", salt="cliente-salt-1")
    h2 = hash_pii("12345678909", salt="cliente-salt-1")
    assert h1 == h2
    assert len(h1) == 64


def test_hash_pii_different_with_different_salt():
    h1 = hash_pii("12345678909", salt="salt-A")
    h2 = hash_pii("12345678909", salt="salt-B")
    assert h1 != h2


def test_hash_pii_irreversible():
    """Hash nao deve permitir recuperar o valor original em tempo util."""
    cpf = "12345678909"
    h = hash_pii(cpf, salt="x")
    assert cpf not in h
    assert cpf[:6] not in h  # nem prefixo


def test_scrub_credit_card():
    text = "pagar com cartao 4111 1111 1111 1111"
    r = scrub(text)
    assert "4111" not in r.text
    assert "cartao" in r.findings


def test_scrub_placa_veiculo_mercosul():
    """Placa Mercosul (ABC1D23) deve ser redatada."""
    text = "minha placa é ABC1D23 e o carro é preto"
    r = scrub(text)
    assert "ABC1D23" not in r.text
    assert "placa_veiculo" in r.findings
    assert "[PLACA_VEICULO_REDACTED]" in r.text


def test_scrub_placa_veiculo_antiga():
    """Placa antiga (ABC1234) deve ser redatada."""
    text = "placa ABC1234 encontrada no estacionamento"
    r = scrub(text)
    assert "ABC1234" not in r.text
    assert "placa_veiculo" in r.findings


def test_scrub_data_br():
    """Data no formato dd/mm/yyyy deve ser redatada (LGPD: data nascimento = PII)."""
    text = "nasci em 15/03/1985 e hoje é 23/06/2026"
    r = scrub(text)
    assert "15/03/1985" not in r.text
    # cartorio-lgpd commit 56e6f6b renomeou chave 'data' -> 'data_nascimento'
    # e regex agora aceita tambem DD-MM-YYYY / DD.MM.YYYY
    assert "data_nascimento" in r.findings
    assert r.findings["data_nascimento"] >= 2


def test_scrub_data_iso():
    """Data ISO (yyyy-mm-dd) deve ser redatada."""
    text = "evento marcado para 2026-07-15"
    r = scrub(text)
    assert "2026-07-15" not in r.text
    # NOTA: regex data_nascimento foi tightened em 56e6f6b para aceitar
    # SOMENTE formato brasileiro (DD/MM/YYYY), NAO ISO. ISO yyyy-mm-dd NAO
    # eh mais detectado (trade-off: evita falso positivo em datas de protocolo).
    assert "data_nascimento" not in r.findings


def test_scrub_combo_placa_e_data():
    """Placa + data + cpf numa so mensagem devem ser todos redatados."""
    text = "veiculo ABC1D23, cpf 123.456.789-09, nasc 01/01/1990"
    r = scrub(text)
    assert "ABC1D23" not in r.text
    assert "123.456.789-09" not in r.text
    assert "01/01/1990" not in r.text
    assert "placa_veiculo" in r.findings
    assert "cpf" in r.findings
    assert "data" in r.findings


def test_scrub_nao_redata_nome_pf_ou_endereco():
    """Documenta limite: nome PF e endereco NAO sao detectados por regex.
    Cobertura real vem do HITL (escrevente valida antes de agir)."""
    text = "Sr. Joao da Silva, Rua das Flores 123, Sao Paulo"
    r = scrub(text)
    # Texto NAO e alterado (sem regex match)
    assert r.text == text
    assert r.findings == {}
    assert r.redaction_count == 0
