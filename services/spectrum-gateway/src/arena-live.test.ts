import assert from "node:assert/strict";
import test from "node:test";

import { SpectrumCloudError, UnsupportedError } from "spectrum-ts";

import type { ArenaMessage } from "./arena.js";
import {
  BlockedProviderPlanError,
  SpectrumArenaTransport,
  classifyProbeError,
  maskPhoneNumber,
  parseEnvContent,
  probeAgent,
  probeRegistry,
  REGISTRY_SCHEMA,
  type AgentRegistryFile,
  type CredentialLoader,
  type IMessageInstanceLike,
  type SpectrumProbeClient,
} from "./arena-live.js";

const FAKE_SECRET = "photon-secret-that-must-never-leak-000";
const FAKE_PHONE = "+15551239335";

function fixtureRegistry(): AgentRegistryFile {
  return {
    schema: REGISTRY_SCHEMA,
    observed_at: "2026-07-26T18:53:00Z",
    source: "fixture",
    agents: [
      {
        agent_id: "cartorio",
        display_name: "CARTORIO BOT TEST",
        project_id: "438527e1-2399-49dc-967c-22e33986035a",
        phone_masked: "UNQUERIED",
        runtime_state: "running",
        configured_profile: true,
        role: "SYSTEM_UNDER_TEST",
        provider_plan: "free",
        registered_user_count: 2,
      },
      {
        agent_id: "grok",
        display_name: "Grok Agent",
        project_id: "bcdcc0f7-e758-4678-bb23-936343f969cd",
        phone_masked: "UNQUERIED",
        runtime_state: "unknown",
        configured_profile: false,
        role: "CHAOTIC_HUMAN_USER",
        provider_plan: "free",
        registered_user_count: 1,
      },
    ],
    conclusion: "fixture conclusion",
  };
}

test("parseEnvContent handles comments, export prefixes and quoted values", () => {
  const parsed = parseEnvContent(
    [
      "# comment",
      "",
      "PHOTON_PROJECT_ID=abc-123",
      'export PHOTON_PROJECT_SECRET="quoted value"',
      "OTHER_KEY='single quoted'",
    ].join("\n")
  );
  assert.equal(parsed.PHOTON_PROJECT_ID, "abc-123");
  assert.equal(parsed.PHOTON_PROJECT_SECRET, "quoted value");
  assert.equal(parsed.OTHER_KEY, "single quoted");
});

test("parseEnvContent rejects malformed lines without leaking the value", () => {
  assert.throws(
    () => parseEnvContent(`BROKEN LINE WITH SECRET ${FAKE_SECRET}`),
    (err: unknown) => {
      assert.ok(err instanceof Error);
      assert.match(err.message, /line 1/);
      assert.equal(err.message.includes(FAKE_SECRET), false);
      return true;
    }
  );
});

test("maskPhoneNumber keeps only country code and last 4 digits", () => {
  assert.equal(maskPhoneNumber(FAKE_PHONE), "+1 (***) ***-9335");
  assert.equal(maskPhoneNumber("+1 (555) 123-9335"), "+1 (***) ***-9335");
  assert.equal(maskPhoneNumber("+5511999887766"), "+551 (***) ***-7766");
  assert.equal(maskPhoneNumber("5551239335"), "+(***) ***-9335");
  assert.equal(maskPhoneNumber(""), "UNAVAILABLE");
  const masked = maskPhoneNumber(FAKE_PHONE);
  assert.equal(masked.includes("5123"), false);
});

test("classifyProbeError maps 401/403 to INVALID_CREDENTIALS and never exposes messages", () => {
  const unauthorized = new SpectrumCloudError(401, "unauthorized", `bad secret ${FAKE_SECRET}`);
  assert.equal(classifyProbeError(unauthorized), "INVALID_CREDENTIALS");
  const forbidden = new SpectrumCloudError(403, "forbidden", "nope");
  assert.equal(classifyProbeError(forbidden), "INVALID_CREDENTIALS");
  const serverError = new SpectrumCloudError(500, "internal", "boom");
  assert.equal(classifyProbeError(serverError), "PROVIDER_ERROR");
  assert.equal(classifyProbeError(new TypeError("fetch failed")), "NETWORK_ERROR");
});

test("probeAgent classifies missing credentials without calling the provider", async () => {
  let calls = 0;
  const client: SpectrumProbeClient = {
    async probe() {
      calls += 1;
      return { lineType: "shared", phonesMasked: [] };
    },
  };
  const outcome = await probeAgent({ agent_id: "grok", project_id: "p-grok" }, undefined, client);
  assert.equal(outcome.runtimeState, "missing_credentials");
  assert.equal(outcome.phoneMasked, "UNAVAILABLE");
  assert.equal(calls, 0);
});

test("probeAgent reports auth_ok with masked phone for dedicated lines", async () => {
  const client: SpectrumProbeClient = {
    async probe() {
      return { lineType: "dedicated", phonesMasked: [maskPhoneNumber(FAKE_PHONE)] };
    },
  };
  const outcome = await probeAgent(
    { agent_id: "cartorio", project_id: "p-cartorio" },
    { projectId: "p-cartorio", projectSecret: FAKE_SECRET },
    client
  );
  assert.equal(outcome.runtimeState, "auth_ok");
  assert.equal(outcome.phoneMasked, "+1 (***) ***-9335");
  assert.equal(outcome.lineType, "dedicated");
  assert.equal(JSON.stringify(outcome).includes(FAKE_PHONE), false);
  assert.equal(JSON.stringify(outcome).includes(FAKE_SECRET), false);
});

test("probeAgent reports auth_ok with UNAVAILABLE phone on shared lines", async () => {
  const client: SpectrumProbeClient = {
    async probe() {
      return { lineType: "shared", phonesMasked: [] };
    },
  };
  const outcome = await probeAgent(
    { agent_id: "kimi", project_id: "p-kimi" },
    { projectId: "p-kimi", projectSecret: FAKE_SECRET },
    client
  );
  assert.equal(outcome.runtimeState, "auth_ok");
  assert.equal(outcome.phoneMasked, "UNAVAILABLE");
  assert.equal(outcome.lineType, "shared");
});

test("probeAgent classifies provider failures as auth_failed with a safe error code", async () => {
  const client: SpectrumProbeClient = {
    async probe() {
      throw new SpectrumCloudError(401, "unauthorized", `rejected ${FAKE_SECRET}`);
    },
  };
  const outcome = await probeAgent(
    { agent_id: "agy", project_id: "p-agy" },
    { projectId: "p-agy", projectSecret: FAKE_SECRET },
    client
  );
  assert.equal(outcome.runtimeState, "auth_failed");
  assert.equal(outcome.probeError, "INVALID_CREDENTIALS");
  assert.equal(outcome.phoneMasked, "UNAVAILABLE");
  assert.equal(JSON.stringify(outcome).includes(FAKE_SECRET), false);
});

test("probeRegistry preserves the schema and refreshes probe fields", async () => {
  const loader: CredentialLoader = {
    async load(profile) {
      if (profile === "cartorio") return { projectId: "p-cartorio", projectSecret: FAKE_SECRET };
      return undefined;
    },
  };
  const client: SpectrumProbeClient = {
    async probe() {
      return { lineType: "dedicated", phonesMasked: [maskPhoneNumber(FAKE_PHONE)] };
    },
  };
  const observedAt = new Date("2026-07-26T20:00:00Z");
  const updated = await probeRegistry(fixtureRegistry(), loader, client, observedAt);

  assert.equal(updated.schema, REGISTRY_SCHEMA);
  assert.equal(updated.observed_at, "2026-07-26T20:00:00.000Z");
  assert.equal(updated.agents.length, 2);

  const cartorio = updated.agents[0];
  assert.ok(cartorio);
  assert.equal(cartorio.agent_id, "cartorio");
  assert.equal(cartorio.runtime_state, "auth_ok");
  assert.equal(cartorio.phone_masked, "+1 (***) ***-9335");
  assert.equal(cartorio.configured_profile, true);
  assert.equal(cartorio.role, "SYSTEM_UNDER_TEST");
  assert.equal(cartorio.registered_user_count, 2);

  const grok = updated.agents[1];
  assert.ok(grok);
  assert.equal(grok.runtime_state, "missing_credentials");
  assert.equal(grok.phone_masked, "UNAVAILABLE");
  assert.equal(grok.configured_profile, false);

  const serialized = JSON.stringify(updated);
  assert.equal(serialized.includes(FAKE_SECRET), false);
  assert.equal(serialized.includes(FAKE_PHONE), false);
});

test("probeRegistry clears a stale probe_error from a previous failed run on success", async () => {
  const stale: AgentRegistryFile = {
    ...fixtureRegistry(),
    agents: [{ ...fixtureRegistry().agents[0]!, probe_error: "INVALID_CREDENTIALS" }],
  };
  const loader: CredentialLoader = {
    async load() {
      return { projectId: "p-cartorio", projectSecret: FAKE_SECRET };
    },
  };
  const client: SpectrumProbeClient = {
    async probe() {
      return { lineType: "shared", phonesMasked: [] };
    },
  };
  const updated = await probeRegistry(stale, loader, client, new Date("2026-07-26T20:05:00Z"));
  const cartorio = updated.agents[0];
  assert.ok(cartorio);
  assert.equal(cartorio.runtime_state, "auth_ok");
  assert.equal("probe_error" in cartorio, false);
  assert.equal(cartorio.line_type, "shared");
});

test("SpectrumArenaTransport sends through a resolved space and returns the provider id", async () => {
  const createdFor: string[] = [];
  const instance: IMessageInstanceLike = {
    space: {
      async create(users: string) {
        createdFor.push(users);
        return {
          async send() {
            return { id: "provider-guid-1" };
          },
        };
      },
    },
  };
  const transport = new SpectrumArenaTransport(instance, () => "+15551239335");
  const message: ArenaMessage = {
    scenarioId: "live-1",
    sender: "kimi",
    target: "cartorio",
    text: "ola arena",
    messageId: "m-1",
    nowMs: 1,
  };
  const result = await transport.send(message);
  assert.deepEqual(createdFor, ["+15551239335"]);
  assert.equal(result.providerMessageId, "provider-guid-1");
  assert.match(result.deliveredAt, /^\d{4}-\d{2}-\d{2}T/);
});

test("SpectrumArenaTransport classifies provider plan refusals as BLOCKED_PROVIDER_PLAN", async () => {
  const instance: IMessageInstanceLike = {
    space: {
      async create() {
        throw UnsupportedError.action("space.create", "iMessage (shared mode)", "shared mode cannot create group chats");
      },
    },
  };
  const transport = new SpectrumArenaTransport(instance, () => "+15551239335");
  const message: ArenaMessage = {
    scenarioId: "live-2",
    sender: "kimi",
    target: "cartorio",
    text: "texto bruto que nao pode vazar",
    messageId: "m-2",
    nowMs: 1,
  };
  await assert.rejects(
    () => transport.send(message),
    (err: unknown) => {
      assert.ok(err instanceof BlockedProviderPlanError);
      assert.equal(err.code, "BLOCKED_PROVIDER_PLAN");
      assert.equal(err.message.includes("texto bruto"), false);
      return true;
    }
  );
});

test("SpectrumArenaTransport throws when the target has no registered handle", async () => {
  const instance: IMessageInstanceLike = {
    space: {
      async create() {
        throw new Error("must not be reached");
      },
    },
  };
  const transport = new SpectrumArenaTransport(instance, () => undefined);
  const message: ArenaMessage = {
    scenarioId: "live-3",
    sender: "kimi",
    target: "grok",
    text: "ola",
    messageId: "m-3",
    nowMs: 1,
  };
  await assert.rejects(() => transport.send(message), /no registered line handle/);
});
