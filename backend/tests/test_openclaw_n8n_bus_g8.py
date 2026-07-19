"""G8.21.T2 — testes do barramento OpenClaw <-> N8N (simulador offline).

Cobre:
- submit/poll basico (id, status, payload)
- subscribe com fan-out para N subscribers
- idempotencia via ``idempotency_key`` (N submits = 1 job)
- concurrencia: 50 submits simultaneos preservam unicidade de IDs
- failure mode: subscriber nao-responsivo nao bloqueia os demais
- lifecycle: pending -> processing -> done / failed
- cancel de job pending; idempotencia do cancel
- LGPD: payload passa pelo scrub hook antes de armazenar

LGPD-safe: payloads sinteticos, IDs UUID, nao ha CPF/RG real.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))  # noqa: E402

from openclaw_n8n_bus_sim import (  # noqa: E402
    BusError,
    Job,
    OpenClawN8NBus,
    scrub_payload,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> OpenClawN8NBus:
    return OpenClawN8NBus(max_len=1000)


# ---------------------------------------------------------------------------
# Lifecycle basico
# ---------------------------------------------------------------------------


async def test_submit_returns_job_with_id(bus: OpenClawN8NBus) -> None:
    job = await bus.submit({"workflow": "cartorio.protocolo.emitir"})
    assert isinstance(job, Job)
    assert job.job_id
    assert len(job.job_id) >= 32  # UUID4
    assert job.status == "pending"
    assert job.payload["workflow"] == "cartorio.protocolo.emitir"


async def test_poll_returns_submitted_job(bus: OpenClawN8NBus) -> None:
    submitted = await bus.submit({"workflow": "wf-a", "context": {"i": 1}})
    polled = await bus.poll(submitted.job_id)
    assert polled is not None
    assert polled.job_id == submitted.job_id
    assert polled.status == "pending"


async def test_poll_unknown_returns_none(bus: OpenClawN8NBus) -> None:
    assert await bus.poll("does-not-exist") is None


# ---------------------------------------------------------------------------
# Subscribe / fan-out
# ---------------------------------------------------------------------------


async def test_subscribe_receives_event(bus: OpenClawN8NBus) -> None:
    received: list[dict] = []

    async def consumer() -> None:
        async for event in bus.subscribe():
            received.append(event)
            if event["event"] == "job.submitted":
                return

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0)  # register subscriber before submit

    await bus.submit({"workflow": "wf-b"})

    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 1
    assert received[0]["event"] == "job.submitted"
    assert "job_id" in received[0]
    assert received[0]["workflow"] == "wf-b"


async def test_multiple_subscribers_all_receive_event(bus: OpenClawN8NBus) -> None:
    n = 5
    queues: list[asyncio.Queue] = [asyncio.Queue() for _ in range(n)]

    async def consumer(idx: int) -> list[dict]:
        out: list[dict] = []
        async for event in bus.subscribe():
            out.append(event)
            await queues[idx].put(event)
            if len(out) >= 1:
                return out
        return out

    tasks = [asyncio.create_task(consumer(i)) for i in range(n)]
    await asyncio.sleep(0)

    await bus.submit({"workflow": "fanout"})

    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)
    for i in range(n):
        evt = await asyncio.wait_for(queues[i].get(), timeout=1.0)
        assert evt["event"] == "job.submitted"


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


async def test_sim_handles_concurrent_jobs(bus: OpenClawN8NBus) -> None:
    n = 50

    async def submit_one(i: int) -> Job:
        return await bus.submit({"workflow": "stress", "context": {"i": i}})

    jobs = await asyncio.gather(*(submit_one(i) for i in range(n)))
    ids = {j.job_id for j in jobs}
    assert len(ids) == n, "duplicate job_ids under concurrency"
    assert bus.queue_depth == n


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


async def test_idempotency_dedup_job_ids(bus: OpenClawN8NBus) -> None:
    idem = "client-retry-2026-07-18"
    j1 = await bus.submit({"workflow": "wf-c"}, idempotency_key=idem)
    j2 = await bus.submit({"workflow": "wf-c"}, idempotency_key=idem)
    j3 = await bus.submit({"workflow": "wf-c"}, idempotency_key=idem)
    assert j1.job_id == j2.job_id == j3.job_id
    assert bus.queue_depth == 1


async def test_different_idempotency_keys_produce_different_jobs(bus: OpenClawN8NBus) -> None:
    j1 = await bus.submit({"workflow": "wf-d"}, idempotency_key="k-1")
    j2 = await bus.submit({"workflow": "wf-d"}, idempotency_key="k-2")
    assert j1.job_id != j2.job_id
    assert bus.queue_depth == 2


# ---------------------------------------------------------------------------
# Failure mode
# ---------------------------------------------------------------------------


async def test_failure_mode_unresponsive_subscriber(bus: OpenClawN8NBus) -> None:
    """Subscriber que nao drena nao deve bloquear os demais."""
    healthy: list[dict] = []
    started = asyncio.Event()
    finished = asyncio.Event()

    async def stuck_consumer() -> None:
        # never drains; just hold the subscription open
        async for _event in bus.subscribe():
            started.set()
            await finished.wait()
            return

    async def healthy_consumer() -> None:
        async for event in bus.subscribe():
            healthy.append(event)
            return

    stuck_task = asyncio.create_task(stuck_consumer())
    healthy_task = asyncio.create_task(healthy_consumer())
    await asyncio.sleep(0)

    await bus.submit({"workflow": "chaos-1"})
    await asyncio.sleep(0)

    await asyncio.wait_for(healthy_task, timeout=2.0)
    assert len(healthy) == 1
    assert healthy[0]["event"] == "job.submitted"

    # cleanup the stuck subscriber
    finished.set()
    await stuck_task


async def test_submit_after_close_raises(bus: OpenClawN8NBus) -> None:
    await bus.close()
    with pytest.raises(BusError):
        await bus.submit({"workflow": "after-close"})


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


async def test_mark_done_updates_status_and_result(bus: OpenClawN8NBus) -> None:
    job = await bus.submit({"workflow": "wf-e"})
    await bus.mark_processing(job.job_id)
    mid = await bus.poll(job.job_id)
    assert mid is not None
    assert mid.status == "processing"

    await bus.mark_done(job.job_id, {"protocolo_id": 999})
    end = await bus.poll(job.job_id)
    assert end is not None
    assert end.status == "done"
    assert end.result == {"protocolo_id": 999}


async def test_mark_failed_records_error(bus: OpenClawN8NBus) -> None:
    job = await bus.submit({"workflow": "wf-f"})
    await bus.mark_failed(job.job_id, "escrevente_offline")
    polled = await bus.poll(job.job_id)
    assert polled is not None
    assert polled.status == "failed"
    assert polled.error == "escrevente_offline"


async def test_cancel_pending_job_succeeds(bus: OpenClawN8NBus) -> None:
    job = await bus.submit({"workflow": "wf-g"})
    ok = await bus.cancel(job.job_id)
    assert ok is True
    polled = await bus.poll(job.job_id)
    assert polled is not None
    assert polled.status == "cancelled"


async def test_cancel_processing_job_returns_false(bus: OpenClawN8NBus) -> None:
    job = await bus.submit({"workflow": "wf-h"})
    await bus.mark_processing(job.job_id)
    assert await bus.cancel(job.job_id) is False


# ---------------------------------------------------------------------------
# LGPD / scrub hook
# ---------------------------------------------------------------------------


def test_scrub_payload_marks_payload() -> None:
    out = scrub_payload({"workflow": "wf", "cpf": "123"})
    assert out["_scrubbed"] is True


def test_scrub_payload_non_dict_returns_marker() -> None:
    out = scrub_payload("not a dict")  # type: ignore[arg-type]
    assert out["_scrub_error"] == "non_dict_payload"


async def test_submit_runs_scrub_hook(bus: OpenClawN8NBus) -> None:
    job = await bus.submit({"workflow": "wf-lgpd", "cpf_fake": "111"})
    assert job.payload["_scrubbed"] is True


# ---------------------------------------------------------------------------
# Max-len trim
# ---------------------------------------------------------------------------


async def test_max_len_trims_oldest() -> None:
    bus = OpenClawN8NBus(max_len=3)
    jobs = [await bus.submit({"workflow": "wf-trim", "context": {"i": i}}) for i in range(5)]
    assert bus.queue_depth == 3
    kept_ids = {j.job_id for j in jobs[-3:]}
    for j in jobs[-3:]:
        assert await bus.poll(j.job_id) is not None
    for j in jobs[:2]:
        assert await bus.poll(j.job_id) is None
    assert kept_ids  # sanity
