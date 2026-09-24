"""OpenClaw <-> N8N asynchronous bus simulator (G8.21.T2).

Offline, stdlib-only simulator for the OpenClaw Gateway <-> N8N messaging
bus used for long-running workflow jobs. In production this would be backed
by:

    * Redis Stream ``cartorio:openclaw:jobs`` (durable job log)
    * WebSocket ``wss://agent.2notasudi.com.br/v1/stream`` (real-time push)
    * Consumer group ``cartorio-n8n`` (N8N side, XREADGROUP + XACK)

See ``docs/OPENCLAW_N8N_BUS_G8.md`` for the full architecture decision.

This module exposes a small in-memory implementation used by tests
(``backend/tests/test_openclaw_n8n_bus_g8.py``) and by an interactive
``--mode={demo,stress,chaos}`` smoke run.

LGPD: ``scrub_payload`` is a placeholder for the real 3-layer PII scrub
(``app.services.pii.scrub``). The simulator never logs raw payload.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

Subscriber = Callable[[dict[str, Any]], Awaitable[None]]
SubscriberFn = Subscriber  # alias for clarity in type hints


@dataclass
class Job:
    """A long-running job submitted by OpenClaw for N8N to consume."""

    job_id: str
    payload: dict[str, Any]
    status: str = "pending"  # pending | processing | done | failed | cancelled
    result: dict[str, Any] | None = None
    error: str | None = None
    idempotency_key: str | None = None
    submitted_by: str = "openclaw-agent"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """PII scrub hook. Production: delegates to ``app.services.pii.scrub``.

    The simulator keeps the payload untouched but tags it with a marker
    so tests can prove scrub ran. Real implementation replaces CPF/RG/
    protocolo with ``sha256:...`` tokens per LGPD Art. 18.
    """
    if not isinstance(payload, dict):
        return {"_scrub_error": "non_dict_payload"}
    out = dict(payload)
    out["_scrubbed"] = True
    return out


class BusError(Exception):
    """Raised for bus-level invariant violations."""


class OpenClawN8NBus:
    """In-memory OpenClaw <-> N8N bus.

    Replaces Redis Stream + WebSocket for offline simulation. Safe for
    concurrent ``submit`` / ``poll`` / ``subscribe`` from a single event
    loop (asyncio.Lock guards the job dict; subscribers each get their
    own asyncio.Queue).
    """

    def __init__(self, *, max_len: int = 10_000) -> None:
        self._jobs: dict[str, Job] = {}
        self._by_idem: dict[str, str] = {}  # idempotency_key -> job_id
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._max_len = max_len
        self._lock = asyncio.Lock()
        self._closed = False

    async def submit(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        submitted_by: str = "openclaw-agent",
    ) -> Job:
        """Submit a job. Returns existing job if ``idempotency_key`` already used."""
        if self._closed:
            raise BusError("bus_closed")
        scrubbed = scrub_payload(payload)
        async with self._lock:
            if idempotency_key is not None:
                existing_id = self._by_idem.get(idempotency_key)
                if existing_id is not None:
                    existing = self._jobs.get(existing_id)
                    if existing is not None:
                        return existing
            job = Job(
                job_id=str(uuid.uuid4()),
                payload=scrubbed,
                idempotency_key=idempotency_key,
                submitted_by=submitted_by,
            )
            self._jobs[job.job_id] = job
            if idempotency_key is not None:
                self._by_idem[idempotency_key] = job.job_id
            self._enforce_max_len_locked()

        await self._publish(
            {"event": "job.submitted", "job_id": job.job_id, "workflow": scrubbed.get("workflow")}
        )
        return job

    async def poll(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    async def mark_processing(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "pending":
                return
            job.status = "processing"
            job.updated_at = time.time()
        await self._publish({"event": "job.processing", "job_id": job_id})

    async def mark_done(self, job_id: str, result: dict[str, Any]) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "done"
            job.result = result
            job.updated_at = time.time()
        await self._publish({"event": "job.done", "job_id": job_id, "result": result})

    async def mark_failed(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.error = error
            job.updated_at = time.time()
        await self._publish({"event": "job.failed", "job_id": job_id, "error": error})

    async def cancel(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != "pending":
                return False
            job.status = "cancelled"
            job.updated_at = time.time()
        await self._publish({"event": "job.cancelled", "job_id": job_id})
        return True

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        """Async generator yielding bus events. Each subscriber gets its own queue.

        Unresponsive subscribers (slow to drain) get a fresh event dropped
        silently so the bus never blocks on a stuck consumer.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1024)
        self._subscribers.append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            try:
                self._subscribers.remove(queue)
            except ValueError:
                pass

    @property
    def queue_depth(self) -> int:
        return len(self._jobs)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def close(self) -> None:
        self._closed = True
        for q in list(self._subscribers):
            await q.put({"event": "bus.closed"})

    def _enforce_max_len_locked(self) -> None:
        if len(self._jobs) <= self._max_len:
            return
        ordered = sorted(self._jobs.values(), key=lambda j: j.created_at)
        to_drop = len(self._jobs) - self._max_len
        for old in ordered[:to_drop]:
            self._jobs.pop(old.job_id, None)
            if old.idempotency_key is not None:
                self._by_idem.pop(old.idempotency_key, None)

    async def _publish(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# CLI demo modes
# ---------------------------------------------------------------------------


async def _run_demo() -> int:
    bus = OpenClawN8NBus()

    received: list[dict[str, Any]] = []

    async def consumer() -> None:
        async for event in bus.subscribe():
            received.append(event)
            if event.get("event") == "bus.closed":
                return

    consumer_task = asyncio.create_task(consumer())
    await asyncio.sleep(0)  # let consumer register

    for i in range(3):
        job = await bus.submit(
            {"workflow": "cartorio.protocolo.emitir", "context": {"trace": i}}
        )
        await bus.mark_processing(job.job_id)
        await bus.mark_done(job.job_id, {"protocolo": f"P-{i:03d}"})

    await asyncio.sleep(0)
    await bus.close()
    await asyncio.wait_for(consumer_task, timeout=2.0)

    print(json.dumps({"received_events": received}, indent=2))
    return 0


async def _run_stress(n: int = 1000) -> int:
    bus = OpenClawN8NBus(max_len=10_000)
    started = time.time()

    async def producer(i: int) -> None:
        await bus.submit({"workflow": "stress", "context": {"i": i}})

    await asyncio.gather(*(producer(i) for i in range(n)))
    elapsed = time.time() - started
    print(
        json.dumps(
            {
                "submitted": n,
                "queue_depth": bus.queue_depth,
                "elapsed_s": round(elapsed, 3),
                "throughput_per_s": round(n / elapsed, 1),
            },
            indent=2,
        )
    )
    return 0


async def _run_chaos() -> int:
    bus = OpenClawN8NBus()
    healthy_events: list[dict[str, Any]] = []
    stuck_done = asyncio.Event()

    async def stuck_consumer() -> None:
        async for _event in bus.subscribe():
            return  # immediately stops consuming

    async def healthy_consumer() -> None:
        async for event in bus.subscribe():
            healthy_events.append(event)
            if len(healthy_events) >= 3:
                stuck_done.set()
                return

    stuck = asyncio.create_task(stuck_consumer())
    healthy = asyncio.create_task(healthy_consumer())
    await asyncio.sleep(0)

    for i in range(3):
        await bus.submit({"workflow": "chaos", "context": {"i": i}})

    await asyncio.wait_for(healthy, timeout=2.0)
    stuck.cancel()
    try:
        await stuck
    except (asyncio.CancelledError, Exception):
        pass

    print(json.dumps({"healthy_received": len(healthy_events)}, indent=2))
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("demo", "stress", "chaos"),
        default="demo",
        help="Demo mode (default: demo).",
    )
    parser.add_argument("--n", type=int, default=1000, help="Jobs for --mode=stress.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.mode == "demo":
        return asyncio.run(_run_demo())
    if args.mode == "stress":
        return asyncio.run(_run_stress(args.n))
    if args.mode == "chaos":
        return asyncio.run(_run_chaos())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())