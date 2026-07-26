import assert from "node:assert/strict";
import test from "node:test";

import { ArenaTurnCoordinator, createArenaMessage } from "./arena.js";
import { ArenaRunner, type ArenaTransport } from "./arena-runner.js";

test("runner never calls transport when TurnCoordinator blocks an event", async () => {
  let calls = 0;
  const transport: ArenaTransport = {
    async send() {
      calls += 1;
      return { providerMessageId: "provider-id", deliveredAt: "2026-07-26T00:00:00Z" };
    },
  };
  const coordinator = new ArenaTurnCoordinator({ cooldownMs: 0 });
  coordinator.start("runner-1", "kimi");
  const runner = new ArenaRunner(coordinator, transport);
  const record = await runner.attempt(createArenaMessage("runner-1", "kimi", "kimi", "echo", 1));
  assert.equal(record.decision, "SELF_MESSAGE");
  assert.equal(calls, 0);
  assert.equal("text" in record, false);
});

test("runner sends only approved turn and retains hashes instead of raw transport data", async () => {
  const transport: ArenaTransport = {
    async send() {
      return { providerMessageId: "provider-message-private", deliveredAt: "2026-07-26T00:00:00Z" };
    },
  };
  const coordinator = new ArenaTurnCoordinator({ cooldownMs: 0 });
  coordinator.start("runner-2", "kimi");
  const runner = new ArenaRunner(coordinator, transport);
  const record = await runner.attempt(createArenaMessage("runner-2", "kimi", "cartorio", "ola", 1));
  assert.equal(record.decision, "ALLOW");
  assert.match(record.payloadHash, /^[0-9a-f]{16}$/);
  assert.match(record.providerMessageIdHash ?? "", /^[0-9a-f]{16}$/);
  assert.equal(JSON.stringify(record).includes("provider-message-private"), false);
});

test("runner records a generic transport error without leaking exception details", async () => {
  const transport: ArenaTransport = {
    async send() {
      throw new Error("provider credential must never reach telemetry");
    },
  };
  const coordinator = new ArenaTurnCoordinator({ cooldownMs: 0 });
  coordinator.start("runner-3", "kimi");
  const runner = new ArenaRunner(coordinator, transport);
  const record = await runner.attempt(createArenaMessage("runner-3", "kimi", "cartorio", "ola", 1));
  assert.equal(record.errorCode, "TRANSPORT_ERROR");
  assert.equal(JSON.stringify(record).includes("credential"), false);
});
