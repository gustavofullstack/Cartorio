import assert from "node:assert/strict";
import test from "node:test";

import {
  ARENA_SCENARIO_CATEGORIES,
  ARENA_TESTERS,
  buildCartorioScenarioCatalog,
} from "./arena-scenarios.js";

test("arena catalog provides 20 human-like scenarios to each of the five testers", () => {
  const catalog = buildCartorioScenarioCatalog();
  assert.equal(catalog.length, 100);
  assert.equal(new Set(catalog.map((scenario) => scenario.id)).size, 100);
  for (const tester of ARENA_TESTERS) {
    assert.equal(catalog.filter((scenario) => scenario.tester === tester).length, 20);
  }
  assert.equal(new Set(catalog.map((scenario) => scenario.category)).size, ARENA_SCENARIO_CATEGORIES.length);
});

test("arena catalog keeps Cartorio as the only SUT target and marks critical policies", () => {
  const catalog = buildCartorioScenarioCatalog();
  assert.equal(catalog.every((scenario) => scenario.target === "cartorio"), true);
  assert.equal(catalog.filter((scenario) => scenario.requiresHitl).length, 25);
  assert.equal(catalog.filter((scenario) => scenario.requiresMcp).length, 15);
  assert.equal(catalog.filter((scenario) => scenario.adversarial).length, 10);
  assert.equal(catalog.some((scenario) => /api|credenciais/i.test(scenario.text)), true);
});
