"""Testes de performance do PII scrubber.

LGPD: PII scrubber roda em toda request. Se for lento, vira gargalo.

SLA: p99 < 5ms (meta do mega-plano P2.BE.13).
"""
from __future__ import annotations

import time

from app.services.pii import scrub


def test_pii_scrub_baseline_latency() -> None:
    """Texto sem PII tem latencia minima."""
    text = "Ola, qual o horario de funcionamento do cartorio?"
    start = time.perf_counter()
    for _ in range(100):
        scrub(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_call_ms = elapsed_ms / 100
    # 100 chamadas em <500ms (5ms cada)
    assert per_call_ms < 5, f"PII scrub lento: {per_call_ms:.2f}ms/call (esperado <5ms)"


def test_pii_scrub_with_cpf() -> None:
    """Texto COM CPF ainda < 5ms (regex CPF nao deve ser gargalo)."""
    text = "Meu CPF e 123.456.789-09 e quero uma certidao de nascimento"
    start = time.perf_counter()
    for _ in range(100):
        scrub(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_call_ms = elapsed_ms / 100
    assert per_call_ms < 5, f"PII scrub com CPF lento: {per_call_ms:.2f}ms/call"


def test_pii_scrub_with_many_pii() -> None:
    """Texto com MUITAS PII (50+) ainda < 10ms (stress)."""
    pii_blocks = []
    for i in range(50):
        pii_blocks.append(f"CPF {10000000000 + i:011d} email{i}@x.com tel (34)9{i:04d}-0000")
    text = " ".join(pii_blocks)
    start = time.perf_counter()
    for _ in range(100):
        scrub(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_call_ms = elapsed_ms / 100
    # Stress: 50+ PII em < 10ms (linear scaling)
    assert per_call_ms < 10, f"PII scrub stress lento: {per_call_ms:.2f}ms/call (esperado <10ms)"


def test_pii_scrub_p99_latency() -> None:
    """Calcula p99 (percentil 99) de 1000 chamadas.

    SLA: p99 < 5ms.
    """
    text = "Meu CNS e 123456789012345 e CNH 98765432100 e CPF 123.456.789-09"
    latencies_ms = []
    for _ in range(1000):
        start = time.perf_counter()
        scrub(text)
        elapsed = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed)
    latencies_ms.sort()
    p99 = latencies_ms[int(0.99 * len(latencies_ms))]  # p99
    p50 = latencies_ms[int(0.50 * len(latencies_ms))]  # p50
    p95 = latencies_ms[int(0.95 * len(latencies_ms))]  # p95
    max_ms = latencies_ms[-1]

    print(
        f"\n[PII bench] p50={p50:.3f}ms p95={p95:.3f}ms p99={p99:.3f}ms max={max_ms:.3f}ms"
    )

    # p99 < 5ms (meta do mega-plano)
    assert p99 < 5, f"p99 latency {p99:.3f}ms >= 5ms SLA"


def test_pii_scrub_throughput() -> None:
    """Mede throughput (chamadas/segundo)."""
    text = "Ola, quero uma certidao"
    start = time.perf_counter()
    count = 0
    while time.perf_counter() - start < 1.0:  # 1 segundo
        scrub(text)
        count += 1
    elapsed = time.perf_counter() - start
    throughput = count / elapsed
    print(f"\n[PII bench] throughput: {throughput:.0f} calls/sec")
    # Throughput minimo: 1000 calls/sec
    assert throughput > 1000, f"Throughput baixo: {throughput:.0f} calls/sec (esperado >1000)"


def test_pii_scrub_check_digit_cns_latency() -> None:
    """Check-digit CNS (16 digitos) tem custo extra - ainda < 5ms?"""
    text = "CNS 8980007647356000"  # CNS valido de teste
    start = time.perf_counter()
    for _ in range(100):
        scrub(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_call_ms = elapsed_ms / 100
    assert per_call_ms < 5, f"PII scrub com CNS check-digit lento: {per_call_ms:.2f}ms"


def test_pii_scrub_check_digit_cnh_latency() -> None:
    """Check-digit CNH (11 digitos) tem custo extra - ainda < 5ms?"""
    text = "CNH 12345678978"  # CNH valido matematicamente
    start = time.perf_counter()
    for _ in range(100):
        scrub(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    per_call_ms = elapsed_ms / 100
    assert per_call_ms < 5, f"PII scrub com CNH check-digit lento: {per_call_ms:.2f}ms"
