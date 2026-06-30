"""Testes de performance do PII scrubbing (E1.S1.T4).

LGPD cartorio review: latencia do scrub NAO pode ser gargalo do webhook.
Meta: < 5ms para textos tipicos de WhatsApp (ate 500 chars).
Texto com 100+ PII deve ser < 50ms.
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


from app.services.pii import detect_only, scrub  # noqa: E402


# ============================================================================
# Helpers
# ============================================================================


def _time_us(fn, *args) -> float:
    """Roda fn(*args) e retorna duracao em microsegundos."""
    start = time.perf_counter()
    fn(*args)
    return (time.perf_counter() - start) * 1_000_000


# ============================================================================
# Benchmarks com mensagens tipicas
# ============================================================================


def test_scrub_texto_curto_menos_5ms() -> None:
    """Mensagem curta tipica (50-200 chars) deve ser < 5ms."""
    text = (
        "Ola, gostaria de saber o valor do emolumento para "
        "certidao de casamento. Meu CPF eh 123.456.789-09."
    )
    duration_us = _time_us(scrub, text)
    # Meta < 5ms = 5000us
    assert duration_us < 5000, f"scrub levou {duration_us:.0f}us (> 5ms) para texto curto"


def test_scrub_texto_medio_500_chars_menos_5ms() -> None:
    """Mensagem media (500 chars) com 1-2 PII deve ser < 5ms."""
    text = (
        "Bom dia, gostaria de tirar uma duvida sobre o processo de "
        "compra e venda de imoveis. O cartorio faz o reconhecimento "
        "de firma? Preciso levar documentos pessoais como RG e CPF? "
        "Tambem tenho duvida sobre o valor do emolumento. Meu CPF "
        "para registro eh 987.654.321-00 e meu email eh joao@example.com. "
        "Aguardo retorno. Obrigado!"
    )
    assert len(text) >= 300
    duration_us = _time_us(scrub, text)
    assert duration_us < 5000, f"scrub levou {duration_us:.0f}us para texto de {len(text)} chars"


def test_scrub_texto_longo_2000_chars_menos_20ms() -> None:
    """Texto longo (2000 chars, simulando historico) < 20ms.

    Caso edge: cliente mandou varios paragraphs antes do LLM processar.
    """
    base = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 30
    text = base + " Meu CPF eh 123.456.789-09 e meu email eh teste@example.com."
    assert len(text) >= 1500
    duration_us = _time_us(scrub, text)
    # Meta mais relaxada: 20ms para texto 4x maior
    assert duration_us < 20_000, f"scrub levou {duration_us:.0f}us para {len(text)} chars"


def test_scrub_texto_com_muitas_pii_menos_50ms() -> None:
    """Texto com 10+ PII (cenarios reais de historico) < 50ms."""
    pii_examples = [
        "123.456.789-09",  # CPF
        "987.654.321-00",  # CPF
        "joao@example.com",  # email
        "11 98765-4321",  # phone
        "12.345.678/0001-90",  # CNPJ
        "12.345.678-9",  # RG
        "123.456.789.000",  # PIS
        "1234 5678 9012",  # titulo
        "01/01/1990",  # data
        "01310-100",  # CEP
    ]
    text = " ".join([f"Documento: {p}" for p in pii_examples] * 5)
    duration_us = _time_us(scrub, text)
    assert duration_us < 50_000, f"scrub levou {duration_us:.0f}us para texto com muitos PII"


def test_scrub_texto_sem_pii_tem_mesma_perf() -> None:
    """Texto sem nenhum PII deve ser rapido (regex nao bate)."""
    text = (
        "Ola, gostaria de saber o horario de funcionamento do cartorio. "
        "Voce atende de segunda a sexta? Tem alguma exigencia especial?"
    )
    # Roda 10x e pega media (pode ter variacao de 1a chamada)
    durations = [_time_us(scrub, text) for _ in range(10)]
    avg_us = sum(durations) / len(durations)
    assert avg_us < 5000, f"scrub sem PII levou media {avg_us:.0f}us (> 5ms)"


# ============================================================================
# detect_only ainda mais rapido
# ============================================================================


def test_detect_only_mais_rapido_que_scrub() -> None:
    """detect_only (gate rapido) deve ser < 1ms para texto curto."""
    text = "Meu CPF eh 123.456.789-09"
    durations = [_time_us(detect_only, text) for _ in range(10)]
    avg_us = sum(durations) / len(durations)
    assert avg_us < 1000, f"detect_only levou {avg_us:.0f}us (esperado < 1ms)"


# ============================================================================
# Estabilidade: roda 100x sem degradar
# ============================================================================


def test_scrub_100_execucoes_estavel() -> None:
    """100 chamadas consecutivas sem memory leak ou degradacao."""
    text = "Meu CPF eh 123.456.789-09 e meu email eh teste@example.com"

    # Warmup
    for _ in range(5):
        scrub(text)

    # Medicao
    start = time.perf_counter()
    for _ in range(100):
        scrub(text)
    total_us = (time.perf_counter() - start) * 1_000_000

    # 100 chamadas < 500ms total = 5ms/call em media
    assert total_us < 500_000, f"100 chamadas levaram {total_us / 1000:.1f}ms (> 500ms)"


# ============================================================================
# Throughput: 200 chamadas/segundo (meta do webhook)
# ============================================================================


def test_throughput_minimo_200_msg_por_segundo() -> None:
    """Webhook precisa aguentar 200 req/s. Cada req = 1 scrub.
    Meta: 1000 chamadas em < 5s = 200/s."""
    text = "Ola cartorio, gostaria de saber o valor do emolumento."

    start = time.perf_counter()
    for _ in range(1000):
        scrub(text)
    total_s = time.perf_counter() - start

    throughput = 1000 / total_s
    assert throughput >= 200, f"throughput {throughput:.0f} msg/s (< 200 esperado)"
