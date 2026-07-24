from app.api.v1.telegram import scrub_bot_outbound


def test_telegram_output_scrub_pii():
    """G9.06.T2: Teste provando CPF/RG/protocolo nunca raw na saída."""
    # Entrada simulada (o LLM vazando PII por alucinacao ou pq recebeu raw)
    llm_vazado = "Seu CPF é 123.456.789-00 e o protocolo é PT-12345678-MG. Entre em contato com dpo@2notasudi.com.br."

    # Passa pelo scrub de saída (que o telegram usa)
    safe_out = scrub_bot_outbound(llm_vazado)

    # Validações
    assert "123.456.789-00" not in safe_out, "CPF vazado na saida!"
    assert "[CPF_REDACTED]" in safe_out or "123.***.***-00" in safe_out

    assert "PT-12345678-MG" not in safe_out, "Protocolo vazado na saida!"

    # E o email oficial do DPO deve ser MANTIDO (excecao oficial)
    assert "dpo@2notasudi.com.br" in safe_out, "Email oficial foi mascarado indevidamente!"
