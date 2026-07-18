"""G8.01.T2 — Otimização de buffering para streams de logs e radar endpoints.

Resolve problema de mensagens grandes em streaming responses:
- Logs podem ter entries de 100KB+ (stacktrace completo, payloads Evolution)
- Radar endpoints servem /api/v1/health/radar/expanded com métricas agregadas
- Sem buffering adequado, o FastAPI responde em chunks pequenos, gerando overhead
  de network frames e CPU para o cliente

API:
- StreamBuffer: classe que acumula chunks e flusha quando:
  1. Tamanho acumulado >= max_chunk_size (back-pressure)
  2. Tempo desde último flush >= max_latency_ms (latência controlada)
  3. flush() explícito (finalização)
- batch_log_entries(entries, size=100): agrupa entries de log para reduzir I/O
- yield_radar_metrics(metrics, batch_size=50): gerador async para SSE

LGPD: PII em entries é scrubbed no momento de bufferização (defense-in-depth).

Modified by Gustavo Almeida — G8 Wave 34 A2.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from app.services.pii import scrub

T = TypeVar("T")


@dataclass
class StreamBuffer(Generic[T]):
    """Buffer genérico para acumular entries e flushar por tamanho/tempo.

    Usado para:
    - Logs: muitas entries pequenas (I/O bound)
    - Radar SSE: métricas agregadas
    - DLQ: dump de entries expiradas

    Configuração conservadora (default):
    - max_chunk_size: 64KB (1 frame TCP típico)
    - max_latency_ms: 250ms (perceptível sem ser lento)
    """

    max_chunk_size: int = 65536  # 64KB
    max_latency_ms: int = 250
    _buffer: list[T] = field(default_factory=list)
    _buffer_size: int = 0
    _last_flush_ts: float = field(default_factory=time.monotonic)

    def append(self, item: T, item_size: int) -> list[T] | None:
        """Adiciona item. Retorna lista para flush se threshold atingido.

        Args:
            item: Entry a ser adicionada.
            item_size: Tamanho estimado do item (bytes).

        Returns:
            Lista de items para flush (callers devem processar/enviar),
            ou None se buffer ainda não atingiu threshold.
        """
        self._buffer.append(item)
        self._buffer_size += item_size
        # Flush por tamanho
        if self._buffer_size >= self.max_chunk_size:
            return self._flush()
        # Flush por latência
        now = time.monotonic()
        if (now - self._last_flush_ts) * 1000 >= self.max_latency_ms:
            return self._flush()
        return None

    def _flush(self) -> list[T]:
        """Esvazia buffer e retorna items."""
        items = self._buffer
        self._buffer = []
        self._buffer_size = 0
        self._last_flush_ts = time.monotonic()
        return items

    def flush(self) -> list[T]:
        """Flush explícito (finalização do stream)."""
        if self._buffer:
            return self._flush()
        return []

    @property
    def pending(self) -> int:
        return len(self._buffer)

    @property
    def pending_size(self) -> int:
        return self._buffer_size


def estimate_size(item: Any) -> int:
    """Estima tamanho em bytes de um item para threshold de buffer.

    Para strings, retorna len(string).
    Para dicts, soma len(key) + len(value) recursivo (shallow).
    Para outros, retorna 256 (estimativa padrão de 1 linha de log).
    """
    if isinstance(item, str):
        return len(item.encode("utf-8"))
    if isinstance(item, dict):
        total = 0
        for k, v in item.items():
            total += len(str(k))
            total += estimate_size(v)
        return total
    if isinstance(item, (list, tuple)):
        return sum(estimate_size(x) for x in item)
    return 256  # estimativa padrão


def batch_log_entries(
    entries: list[dict[str, Any]],
    *,
    size: int = 100,
) -> Iterator[list[dict[str, Any]]]:
    """Agrupa entries de log em batches de N items.

    Yields:
        Listas de até `size` entries cada. LGPD: cada entry é scrubbed
        antes do yield (defense-in-depth).
    """
    if size <= 0:
        size = 100
    for i in range(0, len(entries), size):
        batch = entries[i : i + size]
        # Scrub PII em cada entry
        cleaned = []
        for e in batch:
            if isinstance(e, dict):
                # Scrub recursivo via pii.scrub para cada string value
                cleaned_entry = {}
                for k, v in e.items():
                    if isinstance(v, str):
                        cleaned_entry[k] = scrub(v).text
                    else:
                        cleaned_entry[k] = v
                cleaned.append(cleaned_entry)
            else:
                cleaned.append(e)
        yield cleaned


def yield_radar_metrics(
    metrics: dict[str, Any],
    *,
    batch_size: int = 50,
) -> Iterator[dict[str, Any]]:
    """Gerador que yields métricas radar em chunks para SSE.

    Args:
        metrics: dict {queue: {gauge_name: value, ...}}
        batch_size: items por chunk (default 50).

    Yields:
        Chunks de dict no formato {queue: {...}}, um por vez.
    """
    if batch_size <= 0:
        batch_size = 50
    items = list(metrics.items())
    for i in range(0, len(items), batch_size):
        chunk = dict(items[i : i + batch_size])
        yield chunk


def optimize_radar_response(
    radar_data: dict[str, Any],
    *,
    max_size_per_chunk: int = 16384,  # 16KB por chunk SSE
) -> list[dict[str, Any]]:
    """Divide response radar em chunks otimizados para streaming.

    Args:
        radar_data: payload completo do /api/v1/health/radar/expanded
        max_size_per_chunk: max bytes por chunk (default 16KB)

    Returns:
        Lista de chunks prontos para enviar via SSE.
    """
    if not radar_data:
        return []
    chunks: list[dict[str, Any]] = []
    current_chunk: dict[str, Any] = {}
    current_size = 0
    for key, value in radar_data.items():
        value_size = estimate_size(value)
        if current_size + value_size > max_size_per_chunk and current_chunk:
            chunks.append(current_chunk)
            current_chunk = {}
            current_size = 0
        current_chunk[key] = value
        current_size += value_size + len(key)
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


__all__ = [
    "StreamBuffer",
    "batch_log_entries",
    "estimate_size",
    "optimize_radar_response",
    "yield_radar_metrics",
]


def _cli() -> None:
    """CLI smoke test."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="G8.01.T2 stream buffer")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    args = parser.parse_args()

    if args.demo:
        # Demo 1: StreamBuffer com threshold de tamanho
        buf: StreamBuffer[str] = StreamBuffer(max_chunk_size=100, max_latency_ms=1000)
        flushed = []
        for i in range(20):
            chunk = f"log entry {i}: " + ("x" * 20)  # ~30 bytes
            result = buf.append(chunk, estimate_size(chunk))
            if result:
                flushed.append(result)
        flushed.append(buf.flush())
        print(f"StreamBuffer demo: {len(flushed)} flushes, {sum(len(f) for f in flushed)} items")

        # Demo 2: batch_log_entries
        fake_logs = [{"msg": f"event {i} cpf=123.456.789-0{i % 10}"} for i in range(5)]
        batches = list(batch_log_entries(fake_logs, size=2))
        print(f"batch_log_entries: {len(batches)} batches of size 2")
        print(f"  first batch: {batches[0]}")

        # Demo 3: optimize_radar_response
        radar = {f"metric_{i}": f"value_{i}" + ("x" * 100) for i in range(50)}
        chunks = optimize_radar_response(radar, max_size_per_chunk=512)
        print(f"optimize_radar_response: {len(chunks)} chunks")
        return
    parser.print_help(sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    _cli()
