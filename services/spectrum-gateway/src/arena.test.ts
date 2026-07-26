import assert from "node:assert/strict";
import test from "node:test";

import {
  ARENA_AGENT_IDS,
  ArenaTurnCoordinator,
  buildDirectedEdges,
  createArenaMessage,
  payloadHash,
} from "./arena.js";

test("arena builds the complete 6x6 directed matrix without self edges", () => {
  const edges = buildDirectedEdges();
  assert.equal(ARENA_AGENT_IDS.length, 6);
  assert.equal(edges.length, 30);
  assert.equal(edges.some((edge) => edge.from === edge.to), false);
  assert.equal(new Set(edges.map((edge) => `${edge.from}>${edge.to}`)).size, 30);
});

test("arena hashes payloads without retaining the text", () => {
  const hash = payloadHash("  ola   cartorio ");
  assert.match(hash, /^[0-9a-f]{16}$/);
  assert.equal(hash, payloadHash("ola cartorio"));
});

test("arena drops self events, duplicate events and out-of-turn speakers", () => {
  const coordinator = new ArenaTurnCoordinator({ cooldownMs: 0 });
  coordinator.start("s-1", "kimi");
  const self = createArenaMessage("s-1", "kimi", "kimi", "echo", 1);
  assert.equal(coordinator.evaluate(self).code, "SELF_MESSAGE");

  const first = createArenaMessage("s-1", "kimi", "cartorio", "ola", 2);
  assert.equal(coordinator.evaluate(first).code, "ALLOW");
  assert.equal(coordinator.evaluate(first).code, "SPEAKER_LOCK");
  const outOfTurn = createArenaMessage("s-1", "grok", "cartorio", "ola", 3);
  assert.equal(coordinator.evaluate(outOfTurn).code, "SPEAKER_LOCK");
});

test("arena enforces cooldown, hop limit and repeated-payload loop stop", () => {
  const cooldown = new ArenaTurnCoordinator({ cooldownMs: 1_500 });
  cooldown.start("s-2", "kimi");
  assert.equal(cooldown.evaluate(createArenaMessage("s-2", "kimi", "cartorio", "ola", 2_000)).code, "ALLOW");
  assert.equal(cooldown.evaluate(createArenaMessage("s-2", "cartorio", "kimi", "resposta", 2_001)).code, "COOLDOWN");

  const loop = new ArenaTurnCoordinator({ cooldownMs: 0, maxHops: 8 });
  loop.start("s-3", "kimi");
  assert.equal(loop.evaluate(createArenaMessage("s-3", "kimi", "cartorio", "igual", 1)).code, "ALLOW");
  assert.equal(loop.evaluate(createArenaMessage("s-3", "cartorio", "kimi", "igual", 2)).code, "ALLOW");
  assert.equal(loop.evaluate(createArenaMessage("s-3", "kimi", "cartorio", "igual", 3)).code, "LOOP_DETECTED");

  const hops = new ArenaTurnCoordinator({ cooldownMs: 0, maxHops: 1 });
  hops.start("s-4", "kimi");
  assert.equal(hops.evaluate(createArenaMessage("s-4", "kimi", "cartorio", "one", 1)).code, "ALLOW");
  assert.equal(hops.evaluate(createArenaMessage("s-4", "cartorio", "kimi", "two", 2)).code, "HOP_LIMIT");
});

test("arena detects seven alternating pair sends before a provider call", () => {
  const coordinator = new ArenaTurnCoordinator({ cooldownMs: 0, maxHops: 12, maxTurns: 12 });
  coordinator.start("s-5", "kimi");
  const sequence = ["kimi", "cartorio", "kimi", "cartorio", "kimi", "cartorio", "kimi"] as const;
  for (let index = 0; index < sequence.length; index += 1) {
    const sender = sequence[index]!;
    const target = sender === "kimi" ? "cartorio" : "kimi";
    const result = coordinator.evaluate(createArenaMessage("s-5", sender, target, `message-${index}`, index + 1));
    assert.equal(result.code, index === 6 ? "LOOP_DETECTED" : "ALLOW");
  }
});
