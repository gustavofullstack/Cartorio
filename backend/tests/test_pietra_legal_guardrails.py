"""Guardrails juridicos P0 — bateria sanitizada da auditoria WhatsApp.

Deterministicos: nao chamam LLM, producao, QR ou secrets.
"""

from __future__ import annotations

from app.services.pietra_legal_guardrails import apply_legal_guardrails


def test_testamento_duas_testemunhas_nunca_quatro() -> None:
    out = apply_legal_guardrails(
        user_text="Quero fazer um testamento publico",
        bot_text="Sao quatro testemunhas, creio. Voce pode excluir os demais filhos.",
    )
    low = out.lower()
    assert "duas testemunhas" in low or "2 testemunhas" in low
    assert "quatro" not in low
    assert "creio" not in low
    assert "herdeiros necessarios" in low or "legitima" in low
    assert "escrevente" in low


def test_pdf_eletronico_nao_aplica_11_21_automatico() -> None:
    out = apply_legal_guardrails(
        user_text="Recebi um PDF assinado digitalmente no celular. Posso autenticar a impressao?",
        bot_text="Basta trazer o PDF no celular. Custa R$ 11,21.",
    )
    low = out.lower()
    assert "12,99" in out or "12.99" in out
    assert "serventia" in low or "cartorio" in low
    assert "escrevente" in low


def test_semelhanca_usa_cartao_da_serventia() -> None:
    out = apply_legal_guardrails(
        user_text="Contrato ja assinado. Semelhanca ou autenticidade?",
        bot_text="Na semelhanca comparamos com outro documento de identificacao.",
    )
    low = out.lower()
    assert "cartao" in low or "ficha" in low or "livro" in low
    assert "documento de identificacao" not in low


def test_itbi_uberlandia_aliquota_2_porcento() -> None:
    out = apply_legal_guardrails(
        user_text="Vou comprar um apartamento de R$ 420 mil em Uberlandia",
        bot_text="O ITBI fica entre 2% e 3%, de R$ 8.400 a R$ 12.600.",
    )
    assert "2%" in out
    assert "3%" not in out
    assert "escrevente" in out.lower()
    assert "registro de imoveis" in out.lower() or "registro de imóveis" in out.lower()


def test_procuracao_hospital_nao_chama_escritura() -> None:
    out = apply_legal_guardrails(
        user_text="Minha mae no hospital precisa de procuracao para conta e venda de imovel",
        bot_text="O cartorio pode ir ao hospital lavrar a escritura. Laudo nao e obrigatorio.",
    )
    low = out.lower()
    assert "procuracao publica" in low or "procuração pública" in low
    assert "lavrar a escritura" not in low


def test_ata_nao_garante_autenticidade_do_conteudo() -> None:
    out = apply_legal_guardrails(
        user_text="Preciso de ata notarial de conversa do WhatsApp",
        bot_text="O tabeliao verifica a autenticidade do perfil e do conteudo.",
    )
    low = out.lower()
    assert "constata" in low or "descreve" in low
    assert "verifica a autenticidade" not in low


def test_protocolo_inexistente_nao_vira_catalogo() -> None:
    out = apply_legal_guardrails(
        user_text="Protocolo TESTE-2026-000123, segunda via e proximos horarios",
        bot_text="Catalogo do 2o Oficio: 1. Reconhecimento de Firma R$ 11,21",
    )
    low = out.lower()
    assert "catalogo" not in low
    assert "protocolo" in low
    assert "escrevente" in low or "dpo" in low or "humano" in low


def test_pedra_do_cartorio_vira_pietra() -> None:
    out = apply_legal_guardrails(
        user_text="Quem e voce",
        bot_text="Eu sou a pedra do cartorio.",
    )
    low = out.lower()
    assert "pietra" in low
    assert "pedra do cartorio" not in low


def test_lgpd_preserva_email_institucional_e_nao_repete_cpf() -> None:
    out = apply_legal_guardrails(
        user_text="Quero exclusao dos dados. CPF 000.000.000-00",
        bot_text="Pode pedir exclusao imediata. Email: dpo@2notasudi.com.br. CPF 000.000.000-00.",
    )
    assert "dpo@2notasudi.com.br" in out
    assert "000.000.000-00" not in out
    assert "draft" in out.lower() or "escrevente" in out.lower() or "dpo" in out.lower()


def test_orcamento_firma_menciona_cartao_autografo() -> None:
    out = apply_legal_guardrails(
        user_text="Tres firmas e quatro paginas autenticadas. Calcule o total.",
        bot_text="3 x 11,21 + 4 x 11,21 = R$ 78,47.",
    )
    low = out.lower()
    assert "78,47" in out
    assert "cartao" in low or "ficha" in low


def test_horario_oficial_nao_promete_sabado_nem_oito_horas() -> None:
    out = apply_legal_guardrails(
        user_text="Qual o horario de funcionamento? Abre sabado?",
        bot_text="Segunda a Sexta: 08h00 as 17h00. Sabado: 08h00 as 12h00.",
    )
    low = out.lower()
    assert "09h" in low
    assert "17h" in low
    assert "nao ha expediente regular aos sabados" in low or "sem expediente regular" in low
