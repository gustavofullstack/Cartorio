import { readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { imessage } from "@spectrum-ts/imessage";
import { Spectrum, SpectrumCloudError, UnsupportedError, cloud } from "spectrum-ts";

import type { ArenaAgentId, ArenaMessage } from "./arena.js";
import { payloadHash } from "./arena.js";
import type { ArenaTransport } from "./arena-runner.js";

/**
 * Live Spectrum adapter for the iMessage Agent Arena.
 *
 * Fase 0 (this delivery) is read-only against the provider: the `probe` CLI mode
 * authenticates each registered agent against Spectrum Cloud and records what the
 * provider exposes about the agent's own line. The `edges` and `scenarios` modes
 * are parsed but intentionally not executed here — no outbound message is sent.
 *
 * Hard rules enforced by this module:
 * - PHOTON_PROJECT_SECRET values are held in memory only and never logged.
 * - Phone numbers are only ever emitted masked (`+1 (***) ***-9335`).
 * - Provider tokens returned by `cloud.issueImessageTokens` are discarded after
 *   extracting the (masked) number list.
 */

export const REGISTRY_SCHEMA = "cartorio-os/imessage-agent-registry-v1";

// ---------------------------------------------------------------------------
// .env parsing (no dependency; errors never include line values)
// ---------------------------------------------------------------------------

export function parseEnvContent(content: string): Record<string, string> {
  const parsed: Record<string, string> = {};
  const lines = content.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = (lines[index] ?? "").trim();
    if (!line || line.startsWith("#")) continue;
    const normalized = line.startsWith("export ") ? line.slice("export ".length).trimStart() : line;
    const separator = normalized.indexOf("=");
    if (separator <= 0) throw new Error(`invalid .env syntax at line ${index + 1}`);
    const key = normalized.slice(0, separator).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) throw new Error(`invalid .env key at line ${index + 1}`);
    let value = normalized.slice(separator + 1).trim();
    const quote = value[0];
    if ((quote === '"' || quote === "'") && value.endsWith(quote) && value.length >= 2) {
      value = value.slice(1, -1);
    }
    parsed[key] = value;
  }
  return parsed;
}

// ---------------------------------------------------------------------------
// Phone masking
// ---------------------------------------------------------------------------

/** Masks an E.164-ish number, keeping only the country code and the last 4 digits. */
export function maskPhoneNumber(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length < 4) return "UNAVAILABLE";
  const last4 = digits.slice(-4);
  if (digits.length > 10) return `+${digits.slice(0, digits.length - 10)} (***) ***-${last4}`;
  if (digits.length === 10) return `+(***) ***-${last4}`;
  return `+** ***-${last4}`;
}

// ---------------------------------------------------------------------------
// Credential loading (presence-only semantics; secrets never logged)
// ---------------------------------------------------------------------------

export interface AgentCredentials {
  readonly projectId: string;
  readonly projectSecret: string;
}

export interface CredentialLoader {
  load(profile: string): Promise<AgentCredentials | undefined>;
}

/**
 * Reads `<profilesDir>/<profile>/.env` and extracts PHOTON_PROJECT_ID /
 * PHOTON_PROJECT_SECRET. Returns undefined when the file is missing, unreadable,
 * malformed, or lacks either key — callers classify that as MISSING_CREDENTIALS.
 */
export async function loadProfileCredentials(
  profilesDir: string,
  profile: string
): Promise<AgentCredentials | undefined> {
  let content: string;
  try {
    content = await readFile(path.join(profilesDir, profile, ".env"), "utf8");
  } catch {
    return undefined;
  }
  let env: Record<string, string>;
  try {
    env = parseEnvContent(content);
  } catch {
    return undefined;
  }
  const projectId = env.PHOTON_PROJECT_ID;
  const projectSecret = env.PHOTON_PROJECT_SECRET;
  if (!projectId || !projectSecret) return undefined;
  return { projectId, projectSecret };
}

// ---------------------------------------------------------------------------
// Probe (Fase 0, read-only)
// ---------------------------------------------------------------------------

export type ProbeRuntimeState = "auth_ok" | "auth_failed" | "missing_credentials";
export type ProbeErrorCode = "INVALID_CREDENTIALS" | "NETWORK_ERROR" | "PROVIDER_ERROR";

export interface LineProbeResult {
  readonly lineType: "shared" | "dedicated";
  readonly phonesMasked: readonly string[];
}

export interface SpectrumProbeClient {
  probe(credentials: AgentCredentials): Promise<LineProbeResult>;
}

class ProbeTimeoutError extends Error {
  public constructor(timeoutMs: number) {
    super(`spectrum probe timed out after ${timeoutMs}ms`);
    this.name = "ProbeTimeoutError";
  }
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new ProbeTimeoutError(timeoutMs)), timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (err: unknown) => {
        clearTimeout(timer);
        reject(err instanceof Error ? err : new Error(String(err)));
      }
    );
  });
}

/** Maps any thrown error to a log-safe probe code; raw messages are never surfaced. */
export function classifyProbeError(err: unknown): ProbeErrorCode {
  if (err instanceof SpectrumCloudError) {
    return err.status === 401 || err.status === 403 ? "INVALID_CREDENTIALS" : "PROVIDER_ERROR";
  }
  return "NETWORK_ERROR";
}

/**
 * Probe client backed by the spectrum-ts cloud API. Authentication is proven by
 * `cloud.getProject` (requires the project secret); the line type comes from
 * `cloud.issueImessageTokens` (`cloud.getImessageInfo` 401s on this plan). Dedicated lines expose their numbers via
 * `cloud.issueImessageTokens` — shared lines expose no own number at all (the SDK
 * routes them through a "shared" sentinel), which is reported as UNAVAILABLE.
 */
export class CloudSpectrumProbeClient implements SpectrumProbeClient {
  public constructor(private readonly timeoutMs = 30_000) {}

  public async probe(credentials: AgentCredentials): Promise<LineProbeResult> {
    return withTimeout(this.probeInternal(credentials), this.timeoutMs);
  }

  private async probeInternal({ projectId, projectSecret }: AgentCredentials): Promise<LineProbeResult> {
    await cloud.getProject(projectId, projectSecret);
    // NOTE: `cloud.getImessageInfo` is unauthenticated and 401s on this plan —
    // line type comes from `issueImessageTokens` instead (verified live 2026-07-26).
    const tokens = await cloud.issueImessageTokens(projectId, projectSecret);
    if (tokens.type !== "dedicated") return { lineType: "shared", phonesMasked: [] };
    const phonesMasked = Object.values(tokens.numbers)
      .filter((phone): phone is string => typeof phone === "string" && phone.length > 0)
      .map(maskPhoneNumber);
    return { lineType: "dedicated", phonesMasked };
  }
}

export interface AgentProbeOutcome {
  readonly agentId: string;
  readonly projectId: string;
  readonly runtimeState: ProbeRuntimeState;
  readonly phoneMasked: string;
  readonly lineType?: "shared" | "dedicated";
  readonly probeError?: ProbeErrorCode;
}

/** Probes a single agent; never throws and never emits raw secrets or numbers. */
export async function probeAgent(
  agent: { readonly agent_id: string; readonly project_id: string },
  credentials: AgentCredentials | undefined,
  client: SpectrumProbeClient
): Promise<AgentProbeOutcome> {
  if (!credentials) {
    return {
      agentId: agent.agent_id,
      projectId: agent.project_id,
      runtimeState: "missing_credentials",
      phoneMasked: "UNAVAILABLE",
    };
  }
  try {
    const probe = await client.probe(credentials);
    return {
      agentId: agent.agent_id,
      projectId: agent.project_id,
      runtimeState: "auth_ok",
      phoneMasked: probe.phonesMasked[0] ?? "UNAVAILABLE",
      lineType: probe.lineType,
    };
  } catch (err: unknown) {
    return {
      agentId: agent.agent_id,
      projectId: agent.project_id,
      runtimeState: "auth_failed",
      phoneMasked: "UNAVAILABLE",
      probeError: classifyProbeError(err),
    };
  }
}

// ---------------------------------------------------------------------------
// Registry (schema cartorio-os/imessage-agent-registry-v1)
// ---------------------------------------------------------------------------

export interface RegistryAgentEntry {
  readonly agent_id: string;
  readonly display_name: string;
  readonly project_id: string;
  readonly phone_masked: string;
  readonly runtime_state: string;
  readonly configured_profile: boolean;
  readonly role: string;
  readonly provider_plan: string;
  readonly registered_user_count: number;
  readonly line_type?: "shared" | "dedicated";
  readonly probe_error?: ProbeErrorCode;
}

export interface AgentRegistryFile {
  readonly schema: string;
  readonly observed_at: string;
  readonly source: string;
  readonly agents: readonly RegistryAgentEntry[];
  readonly conclusion: string;
}

/**
 * Runs the Fase 0 probe over every registry agent and returns an updated registry
 * that preserves the v1 schema. Edges are NOT marked PASS — that is a later phase
 * that requires real outbound sends.
 */
export async function probeRegistry(
  registry: AgentRegistryFile,
  loader: CredentialLoader,
  client: SpectrumProbeClient,
  observedAt: Date = new Date()
): Promise<AgentRegistryFile> {
  const agents: RegistryAgentEntry[] = [];
  for (const agent of registry.agents) {
    const credentials = await loader.load(agent.agent_id);
    const outcome = await probeAgent(agent, credentials, client);
    // Drop stale probe_error/line_type from previous runs; success must not
    // inherit an old failure classification.
    const { probe_error: _staleError, line_type: _staleLineType, ...rest } = agent;
    agents.push({
      ...rest,
      configured_profile: credentials !== undefined,
      phone_masked: outcome.phoneMasked,
      runtime_state: outcome.runtimeState,
      ...(outcome.lineType ? { line_type: outcome.lineType } : {}),
      ...(outcome.probeError ? { probe_error: outcome.probeError } : {}),
    });
  }
  const iso = observedAt.toISOString();
  return {
    ...registry,
    observed_at: iso,
    agents,
    conclusion:
      `Fase 0 probe executed at ${iso} via spectrum-ts cloud API (read-only; ` +
      "no outbound message was sent). runtime_state reflects the per-agent probe " +
      "outcome (auth_ok/auth_failed/missing_credentials). The 6x6 allowlist matrix " +
      "and all 30 directed routes remain UNVERIFIED pending live edge runs.",
  };
}

// ---------------------------------------------------------------------------
// Live transport (structured for future edges/scenarios modes; unused by probe)
// ---------------------------------------------------------------------------

export interface IMessageSpaceLike {
  send(content: string): Promise<{ readonly id: string } | undefined>;
}

export interface IMessageInstanceLike {
  readonly space: {
    create(users: string): Promise<IMessageSpaceLike>;
  };
}

/** Classified error for provider-plan limitations (e.g. shared mode group sends). */
export class BlockedProviderPlanError extends Error {
  public readonly code = "BLOCKED_PROVIDER_PLAN" as const;

  public constructor(detail: string) {
    super(detail);
    this.name = "BlockedProviderPlanError";
  }
}

/**
 * ArenaTransport that delivers through a live spectrum-ts iMessage instance.
 * The handle resolver maps arena agents to their line handle (E.164 or email);
 * handles live in memory only — telemetry keeps payloadHash/provider id hashes.
 *
 * Provider-plan refusals surface as `UnsupportedError` from the SDK and are
 * re-classified as `BlockedProviderPlanError` instead of being circumvented.
 */
export class SpectrumArenaTransport implements ArenaTransport {
  public constructor(
    private readonly instance: IMessageInstanceLike,
    private readonly resolveHandle: (agent: ArenaAgentId) => string | undefined
  ) {}

  public async send(
    message: ArenaMessage
  ): Promise<{ readonly providerMessageId: string; readonly deliveredAt: string }> {
    const handle = this.resolveHandle(message.target);
    if (!handle) throw new Error(`arena-live: no registered line handle for target "${message.target}"`);
    try {
      const space = await this.instance.space.create(handle);
      const sent = await space.send(message.text);
      if (!sent) throw new Error("arena-live: provider returned no message id for an accepted send");
      return { providerMessageId: sent.id, deliveredAt: new Date().toISOString() };
    } catch (err: unknown) {
      if (err instanceof UnsupportedError) {
        throw new BlockedProviderPlanError(
          `arena-live: provider refused the send for payload ${payloadHash(message.text)}`
        );
      }
      throw err;
    }
  }
}

/** Opens a live iMessage platform instance; caller owns `stop()` on the Spectrum app. */
export async function createLiveIMessageInstance(credentials: AgentCredentials): Promise<{
  readonly instance: IMessageInstanceLike;
  readonly stop: () => Promise<void>;
}> {
  const app = await Spectrum({
    projectId: credentials.projectId,
    projectSecret: credentials.projectSecret,
    providers: [imessage.config()],
  });
  return { instance: imessage(app), stop: () => app.stop() };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const DEFAULT_REGISTRY_PATH = path.join(REPO_ROOT, "docs", "testing", "IMESSAGE_AGENT_REGISTRY.json");
const DEFAULT_PROFILES_DIR = path.join(os.homedir(), ".hermes", "profiles");

async function runProbe(registryPath: string, profilesDir: string): Promise<number> {
  const registry = JSON.parse(await readFile(registryPath, "utf8")) as AgentRegistryFile;
  if (registry.schema !== REGISTRY_SCHEMA) {
    console.error(`[arena-live] unexpected registry schema "${registry.schema}"; refusing to update`);
    return 2;
  }
  const loader: CredentialLoader = {
    load: (profile) => loadProfileCredentials(profilesDir, profile),
  };
  const updated = await probeRegistry(registry, loader, new CloudSpectrumProbeClient());
  await writeFile(registryPath, `${JSON.stringify(updated, null, 2)}\n`, "utf8");
  for (const agent of updated.agents) {
    const suffix = agent.probe_error ? ` error=${agent.probe_error}` : "";
    console.log(
      `[arena:probe] ${agent.agent_id} project=${agent.project_id} ` +
        `state=${agent.runtime_state} phone=${agent.phone_masked}${suffix}`
    );
  }
  console.log(`[arena:probe] registry updated at ${registryPath}`);
  return 0;
}

async function main(argv: readonly string[]): Promise<number> {
  const mode = argv[2] ?? "probe";
  if (mode === "probe") {
    return runProbe(DEFAULT_REGISTRY_PATH, DEFAULT_PROFILES_DIR);
  }
  if (mode === "edges" || mode === "scenarios") {
    console.error(
      `[arena-live] mode "${mode}" is not part of the Fase 0 delivery; no outbound sends were performed`
    );
    return 2;
  }
  console.error(`[arena-live] unknown mode "${mode}" (expected probe|edges|scenarios)`);
  return 2;
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : undefined;
if (invokedPath && invokedPath === fileURLToPath(import.meta.url)) {
  main(process.argv)
    .then((code) => {
      process.exitCode = code;
    })
    .catch((err: unknown) => {
      // Error names are safe; messages may embed provider URLs and are not printed.
      console.error(`[arena-live] fatal: ${err instanceof Error ? err.name : "unknown"}`);
      process.exitCode = 1;
    });
}
