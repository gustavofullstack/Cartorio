import { createHash, randomUUID } from "node:crypto";

export const ARENA_AGENT_IDS = ["cartorio", "kimi", "agy", "antigravity", "codex", "grok"] as const;

export type ArenaAgentId = (typeof ARENA_AGENT_IDS)[number];
export type ArenaDecisionCode =
  | "ALLOW"
  | "SELF_MESSAGE"
  | "DUPLICATE"
  | "COOLDOWN"
  | "SPEAKER_LOCK"
  | "TURN_LIMIT"
  | "HOP_LIMIT"
  | "LOOP_DETECTED";

export interface ArenaRegistryEntry {
  readonly agentId: ArenaAgentId;
  readonly displayName: string;
  readonly projectId: string;
  readonly phoneMasked: string;
  readonly runtimeState: "running" | "unknown" | "offline";
  readonly role: string;
}

export interface DirectedEdge {
  readonly from: ArenaAgentId;
  readonly to: ArenaAgentId;
}

export interface ArenaMessage {
  readonly scenarioId: string;
  readonly sender: ArenaAgentId;
  readonly target: ArenaAgentId;
  readonly text: string;
  readonly messageId: string;
  readonly nowMs: number;
}

export interface ArenaDecision {
  readonly allowed: boolean;
  readonly code: ArenaDecisionCode;
  readonly detail: string;
}

export interface ArenaState {
  readonly scenarioId: string;
  readonly currentSpeaker: ArenaAgentId;
  readonly turns: number;
  readonly hops: number;
  readonly completed: boolean;
}

export interface ArenaLimits {
  readonly maxTurns: number;
  readonly maxHops: number;
  readonly cooldownMs: number;
  readonly duplicateWindowMs: number;
}

const DEFAULT_LIMITS: ArenaLimits = {
  maxTurns: 12,
  maxHops: 8,
  cooldownMs: 1_500,
  duplicateWindowMs: 60_000,
};

export function buildDirectedEdges(
  agents: readonly ArenaAgentId[] = ARENA_AGENT_IDS
): readonly DirectedEdge[] {
  return agents.flatMap((from) => agents.filter((to) => to !== from).map((to) => ({ from, to })));
}

/** Hashes payloads so arena telemetry never needs to retain message text. */
export function payloadHash(text: string): string {
  return createHash("sha256").update(text.trim().replaceAll(/\s+/g, " ")).digest("hex").slice(0, 16);
}

/**
 * In-memory coordinator for a single controlled scenario. It makes no provider calls;
 * the live sender must invoke it before any outbound Spectrum operation.
 */
export class ArenaTurnCoordinator {
  private readonly limits: ArenaLimits;
  private readonly seen = new Map<string, number>();
  private readonly payloadOccurrences = new Map<string, number>();
  private readonly pairHistory: string[] = [];
  private lastSentAt = -Infinity;
  private state: ArenaState | undefined;

  public constructor(limits: Partial<ArenaLimits> = {}) {
    this.limits = { ...DEFAULT_LIMITS, ...limits };
  }

  public start(scenarioId: string, firstSpeaker: ArenaAgentId): ArenaState {
    this.seen.clear();
    this.payloadOccurrences.clear();
    this.pairHistory.length = 0;
    this.lastSentAt = -Infinity;
    this.state = { scenarioId, currentSpeaker: firstSpeaker, turns: 0, hops: 0, completed: false };
    return this.getState();
  }

  public getState(): ArenaState {
    if (!this.state) throw new Error("Arena scenario has not started");
    return { ...this.state };
  }

  public stop(): void {
    if (!this.state) return;
    this.state = { ...this.state, completed: true };
  }

  public evaluate(message: ArenaMessage): ArenaDecision {
    const state = this.getState();
    if (state.completed || state.turns >= this.limits.maxTurns) {
      return this.block("TURN_LIMIT", "scenario turn limit reached");
    }
    if (message.sender === message.target) return this.block("SELF_MESSAGE", "self-originated events are dropped");
    if (message.sender !== state.currentSpeaker) {
      return this.block("SPEAKER_LOCK", "only the current speaker may send the next arena message");
    }
    if (state.hops + 1 > this.limits.maxHops) return this.block("HOP_LIMIT", "scenario hop limit reached");
    if (message.nowMs - this.lastSentAt < this.limits.cooldownMs) {
      return this.block("COOLDOWN", "cooldown between arena messages has not elapsed");
    }
    if (!this.acceptDeduplication(message)) return this.block("DUPLICATE", "duplicate message event within window");

    const hash = payloadHash(message.text);
    const occurrences = (this.payloadOccurrences.get(hash) ?? 0) + 1;
    this.payloadOccurrences.set(hash, occurrences);
    if (occurrences >= 3 || this.wouldAlternateTooLong(message)) {
      return this.block("LOOP_DETECTED", "repeated payload or alternating pair loop detected");
    }

    this.pairHistory.push(`${message.sender}>${message.target}`);
    this.lastSentAt = message.nowMs;
    this.state = {
      ...state,
      currentSpeaker: message.target,
      turns: state.turns + 1,
      hops: state.hops + 1,
    };
    return { allowed: true, code: "ALLOW", detail: "controlled arena turn accepted" };
  }

  private acceptDeduplication(message: ArenaMessage): boolean {
    for (const [messageId, timestamp] of this.seen) {
      if (message.nowMs - timestamp > this.limits.duplicateWindowMs) this.seen.delete(messageId);
    }
    if (this.seen.has(message.messageId)) return false;
    this.seen.set(message.messageId, message.nowMs);
    return true;
  }

  private wouldAlternateTooLong(message: ArenaMessage): boolean {
    const candidate = [...this.pairHistory, `${message.sender}>${message.target}`];
    const recent = candidate.slice(-7);
    if (recent.length < 7) return false;
    for (let index = 1; index < recent.length; index += 1) {
      const previous = recent[index - 1];
      const current = recent[index];
      if (!previous || !current) return false;
      const [previousFrom, previousTo] = previous.split(">");
      const [from, to] = current.split(">");
      if (from !== previousTo || to !== previousFrom) return false;
    }
    return true;
  }

  private block(code: Exclude<ArenaDecisionCode, "ALLOW">, detail: string): ArenaDecision {
    return { allowed: false, code, detail };
  }
}

export function createArenaMessage(
  scenarioId: string,
  sender: ArenaAgentId,
  target: ArenaAgentId,
  text: string,
  nowMs: number
): ArenaMessage {
  return { scenarioId, sender, target, text, nowMs, messageId: randomUUID() };
}
