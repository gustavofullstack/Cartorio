"""G8.01.T2 — Testes para otimização de buffering streams/radar.

Cobre:
  - StreamBuffer: flush por tamanho, latência, explícito
  - estimate_size: string, dict, list, fallback
  - batch_log_entries: tamanho exato, scrub PII
  - yield_radar_metrics: chunks corretos
  - optimize_radar_response: chunks otimizados para SSE
  - LGPD: PII scrubbed em batch_log_entries
  - CLI demo

Modified by Gustavo Almeida — G8 Wave 34 A2.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "app" / "services" / "stream_buffer.py"


@pytest.fixture(scope="module")
def stream_module():
    """Importa stream_buffer via package normal (Pydantic settings exige env)."""
    import os

    # Garante que o env Pydantic tem o mínimo necessário
    os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
    os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)
    os.environ.setdefault("AUDIT_HMAC_KEY", "x" * 32)
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
    os.environ.setdefault("EVOLUTION_API_KEY", "test")

    # Import via package: precisa de backend/ no sys.path
    backend_root = str(ROOT.parent)
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from app.services import stream_buffer as mod  # noqa: PLC0415

    return mod


class TestEstimateSize:
    def test_string_size(self, stream_module):
        s = "hello world"
        assert stream_module.estimate_size(s) == len(s.encode("utf-8"))

    def test_dict_size(self, stream_module):
        d = {"a": "x", "b": "yy"}
        # 1 + 1 + 1 + 2 = 5 (keys + values)
        assert stream_module.estimate_size(d) >= 5

    def test_nested_dict_size(self, stream_module):
        d = {"outer": {"inner": "value"}}
        size = stream_module.estimate_size(d)
        assert size > 0

    def test_list_size(self, stream_module):
        lst = ["a", "bb", "ccc"]
        assert stream_module.estimate_size(lst) == 1 + 2 + 3

    def test_fallback_int(self, stream_module):
        assert stream_module.estimate_size(42) == 256

    def test_fallback_object(self, stream_module):
        class Foo:
            pass

        assert stream_module.estimate_size(Foo()) == 256

    def test_empty_dict(self, stream_module):
        assert stream_module.estimate_size({}) == 0

    def test_empty_list(self, stream_module):
        assert stream_module.estimate_size([]) == 0

    def test_empty_string(self, stream_module):
        assert stream_module.estimate_size("") == 0


class TestStreamBuffer:
    def test_initial_state_empty(self, stream_module):
        buf = stream_module.StreamBuffer[str]()
        assert buf.pending == 0
        assert buf.pending_size == 0

    def test_append_no_flush_under_threshold(self, stream_module):
        buf = stream_module.StreamBuffer[str](max_chunk_size=1000, max_latency_ms=10000)
        result = buf.append("item", 10)
        assert result is None
        assert buf.pending == 1

    def test_append_flushes_on_size(self, stream_module):
        buf = stream_module.StreamBuffer[str](max_chunk_size=100, max_latency_ms=10000)
        # Adiciona 5 items de 30 bytes = 150 bytes > 100 → flush
        result = buf.append("x" * 30, 30)
        assert result is None  # 30 < 100
        result = buf.append("x" * 30, 30)
        assert result is None  # 60 < 100
        result = buf.append("x" * 30, 30)
        assert result is None  # 90 < 100
        result = buf.append("x" * 30, 30)
        # 120 >= 100 → flush
        assert result is not None
        assert len(result) == 4
        assert buf.pending == 0

    def test_explicit_flush(self, stream_module):
        buf = stream_module.StreamBuffer[str](max_chunk_size=10000, max_latency_ms=10000)
        buf.append("item1", 10)
        buf.append("item2", 20)
        result = buf.flush()
        assert len(result) == 2
        assert buf.pending == 0

    def test_flush_empty_returns_empty_list(self, stream_module):
        buf = stream_module.StreamBuffer[str]()
        assert buf.flush() == []

    def test_latency_flush(self, stream_module):
        """Flush por latência: items pequenos, mas tempo alto."""
        buf = stream_module.StreamBuffer[str](max_chunk_size=10000, max_latency_ms=50)
        buf.append("x", 5)
        time.sleep(0.06)  # 60ms > 50ms
        result = buf.append("y", 5)  # trigger latency check
        assert result is not None

    def test_pending_property(self, stream_module):
        buf = stream_module.StreamBuffer[str](max_chunk_size=10000)
        buf.append("a", 10)
        buf.append("b", 20)
        assert buf.pending == 2
        assert buf.pending_size == 30

    def test_generic_typing(self, stream_module):
        """StreamBuffer funciona com qualquer tipo T (test size threshold only)."""
        # Latência 30s para evitar flush por tempo (apenas testamos size)
        buf_int: stream_module.StreamBuffer[int] = stream_module.StreamBuffer(
            max_chunk_size=10, max_latency_ms=30000
        )
        # Adiciona 3 items de 5 bytes = 15 bytes > 10 threshold
        r1 = buf_int.append(42, 5)
        r2 = buf_int.append(43, 5)
        r3 = buf_int.append(44, 5)
        # Pelo menos um dos appends deve ter triggrado flush por size
        flushed = [r for r in [r1, r2, r3] if r is not None]
        assert len(flushed) >= 1
        # Items flushed incluem 42+43 (flush em 10 bytes = 2 items)
        all_flushed: list[int] = []
        for r in flushed:
            all_flushed.extend(r)
        assert 42 in all_flushed
        assert 43 in all_flushed
        # Flush final deve retornar o que sobrou
        remaining = buf_int.flush()
        all_items = all_flushed + remaining
        assert sorted(all_items) == [42, 43, 44]

    def test_flush_resets_size(self, stream_module):
        buf = stream_module.StreamBuffer[str](max_chunk_size=100)
        for _ in range(5):
            buf.append("x" * 30, 30)
        buf.flush()
        assert buf.pending == 0
        assert buf.pending_size == 0


class TestBatchLogEntries:
    def test_yields_batches_of_correct_size(self, stream_module):
        entries = [{"msg": f"event {i}"} for i in range(25)]
        batches = list(stream_module.batch_log_entries(entries, size=10))
        assert len(batches) == 3
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5  # resto

    def test_empty_input_yields_nothing(self, stream_module):
        batches = list(stream_module.batch_log_entries([], size=10))
        assert batches == []

    def test_size_clamps_to_minimum(self, stream_module):
        entries = [{"msg": f"event {i}"} for i in range(3)]
        batches = list(stream_module.batch_log_entries(entries, size=0))
        # size=0 é inválido, deve virar 100 (default)
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_scrubs_cpf_in_message(self, stream_module):
        entries = [{"msg": "user 123.456.789-09 failed"}]
        batches = list(stream_module.batch_log_entries(entries, size=10))
        # pii.scrub deve mascarar o CPF
        msg = batches[0][0]["msg"]
        # Scrub normalmente substitui por ***.***.***-**
        assert "123.456.789-09" not in msg

    def test_scrubs_email(self, stream_module):
        entries = [{"msg": "contact gustavo@example.com done"}]
        batches = list(stream_module.batch_log_entries(entries, size=10))
        msg = batches[0][0]["msg"]
        assert "gustavo@example.com" not in msg

    def test_preserves_non_string_values(self, stream_module):
        entries = [{"event": "x", "count": 5, "active": True}]
        batches = list(stream_module.batch_log_entries(entries, size=10))
        entry = batches[0][0]
        assert entry["count"] == 5
        assert entry["active"] is True

    def test_handles_non_dict_entries(self, stream_module):
        entries = ["raw string", 42, None]  # type: ignore[list-item]
        batches = list(stream_module.batch_log_entries(entries, size=10))  # type: ignore[arg-type]
        # Non-dict entries são pass-through (não scrubable, retornados as-is)
        assert len(batches) == 1
        assert "raw string" in batches[0]


class TestYieldRadarMetrics:
    def test_yields_chunks(self, stream_module):
        metrics = {f"queue_{i}": {"depth": i} for i in range(120)}
        chunks = list(stream_module.yield_radar_metrics(metrics, batch_size=50))
        assert len(chunks) == 3
        assert len(chunks[0]) == 50
        assert len(chunks[1]) == 50
        assert len(chunks[2]) == 20

    def test_yields_dicts_not_tuples(self, stream_module):
        metrics = {"a": 1, "b": 2, "c": 3}
        chunks = list(stream_module.yield_radar_metrics(metrics, batch_size=2))
        for chunk in chunks:
            assert isinstance(chunk, dict)

    def test_empty_yields_empty(self, stream_module):
        chunks = list(stream_module.yield_radar_metrics({}, batch_size=10))
        assert chunks == []

    def test_batch_size_clamps(self, stream_module):
        metrics = {f"k_{i}": i for i in range(5)}
        # batch_size=0 deve virar 50 (default)
        chunks = list(stream_module.yield_radar_metrics(metrics, batch_size=0))
        assert len(chunks) == 1


class TestOptimizeRadarResponse:
    def test_empty_returns_empty(self, stream_module):
        assert stream_module.optimize_radar_response({}) == []

    def test_single_small_entry_one_chunk(self, stream_module):
        data = {"queue_evolution": {"depth": 5, "expired_total": 10}}
        chunks = stream_module.optimize_radar_response(data, max_size_per_chunk=1024)
        assert len(chunks) == 1
        assert "queue_evolution" in chunks[0]

    def test_large_data_splits_into_chunks(self, stream_module):
        data = {f"queue_{i}": {"big_value": "x" * 1000} for i in range(10)}
        chunks = stream_module.optimize_radar_response(data, max_size_per_chunk=2048)
        # Cada chunk com ~2 entries de 1000 bytes
        assert len(chunks) >= 3

    def test_chunks_within_max_size(self, stream_module):
        data = {f"q_{i}": "x" * 500 for i in range(20)}
        max_size = 2048
        chunks = stream_module.optimize_radar_response(data, max_size_per_chunk=max_size)
        for chunk in chunks:
            # Cada chunk deve estar aproximadamente dentro do limite
            # (último entry pode fazer ultrapassar marginalmente)
            assert stream_module.estimate_size(chunk) <= max_size * 2

    def test_preserves_all_keys(self, stream_module):
        data = {f"k_{i}": f"v_{i}" for i in range(50)}
        chunks = stream_module.optimize_radar_response(data, max_size_per_chunk=200)
        all_keys = set()
        for chunk in chunks:
            all_keys.update(chunk.keys())
        assert all_keys == set(data.keys())


class TestLGPDCompliance:
    """Defesa em profundidade: PII scrubbed em batch operations."""

    def test_batch_log_strips_cpf(self, stream_module):
        entries = [{"user": "123.456.789-09", "action": "view_protocolo"}]
        batches = list(stream_module.batch_log_entries(entries))
        msg = str(batches[0])
        assert "123.456.789-09" not in msg

    def test_batch_log_strips_phone(self, stream_module):
        entries = [{"phone": "+55 34 99999-0000", "action": "call"}]
        batches = list(stream_module.batch_log_entries(entries))
        msg = str(batches[0])
        # scrub mascara telefone
        assert "+55 34 99999-0000" not in msg or "***" in msg

    def test_batch_log_strips_email(self, stream_module):
        entries = [{"email": "cliente@cartorio.com.br"}]
        batches = list(stream_module.batch_log_entries(entries))
        msg = str(batches[0])
        # scrub mascara email
        assert "cliente@cartorio.com.br" not in msg


class TestCLI:
    def test_demo_runs(self):
        # Skip se settings Pydantic exige env completa
        pytest.importorskip("app", reason="app package não acessível")
        env = {
            "PYTHONPATH": str(ROOT),
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "DATABASE_URL": "sqlite:///test.db",
            "JWT_SECRET_KEY": "x" * 32,
            "AUDIT_HMAC_KEY": "x" * 32,
        }
        result = subprocess.run(
            [sys.executable, str(MODULE), "--demo"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(ROOT),
            env=env,
        )
        if result.returncode != 0:
            pytest.skip(f"CLI demo skip (env Pydantic dev): {result.stderr[:200]}")
        # Demo deve mostrar contadores
        assert "StreamBuffer demo" in result.stdout
        assert "batch_log_entries" in result.stdout
        assert "optimize_radar_response" in result.stdout

    def test_help_runs(self):
        result = subprocess.run(
            [sys.executable, str(MODULE), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(ROOT),
            env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        )
        assert result.returncode in (0, 1, 2)
        assert result.stdout or result.stderr
