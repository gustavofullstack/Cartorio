import { createHash } from "node:crypto";

import type { CanonicalInboundMessage, CanonicalOutboundMessage, InboundScope } from "./contracts.js";

const CPF = /\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b/g;
const EMAIL = /\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g;
const PHONE = /(?:\+?55[\s.-]*)?\(?\d{2}\)?[\s.-]*9\d{4}[\s.-]?\d{4}|\b9?\d{4}[\s-]?\d{4}\b/g;

const AGENT_CONTROL_PATTERNS = [
  /↳?\s*Redirected current run.*$/gim,
  /Self-improvement review:.*$/gim,
  /Approve Once\s*\/\s*Always Approve\s*\/\s*Cancel/gim,
  /\[This response was interrupted.*\]/gim,
  /I'll adjust using your correction\./gim,
  /^\/new\b.*$/gim,
  /^\/approve\b.*$/gim,
  /^\/always\b.*$/gim,
  /^\/cancel\b.*$/gim,
];

export function stripInternalAgentControlLeaks(text: string): string {
  let cleaned = text;
  for (const pat of AGENT_CONTROL_PATTERNS) {
    cleaned = cleaned.replace(pat, "");
  }
  return cleaned.trim();
}

/** Sanitiza apenas a cópia enviada a executores externos e canais. */
export function scrubPii(text: string): string {
  const scrubbed = text
    .replace(CPF, "$1.***.***-$4")
    .replace(EMAIL, "$1***@$2")
    .replace(PHONE, "[telefone mascarado]");
  return stripInternalAgentControlLeaks(scrubbed);
}

/** A identidade do canal não é uma identidade civil unificada. */
export function conversationId(message: CanonicalInboundMessage): string {
  const stable = `${message.platform}:${message.spaceId}:${message.senderId}`;
  return createHash("sha256").update(stable).digest("hex").slice(0, 32);
}

export function sanitizeOutbound(message: CanonicalOutboundMessage): CanonicalOutboundMessage {
  return { ...message, text: scrubPii(message.text) };
}

/** Deduplicação local defensiva (janela 24h); o backend permanece a fonte de idempotência. */
export class MessageDedupe {
  private static readonly TTL_MS = 24 * 60 * 60 * 1000;

  private readonly seen = new Map<string, number>();

  public accept(messageId: string, now = Date.now()): boolean {
    for (const [id, timestamp] of this.seen) {
      if (now - timestamp > MessageDedupe.TTL_MS) this.seen.delete(id);
    }
    if (this.seen.has(messageId)) return false;
    this.seen.set(messageId, now);
    return true;
  }
}

export type OutboundReason = "reply" | "transactional" | "human_approved" | "proactive";

export class ConsentRegistry {
  private readonly optedInSenders = new Set<string>();

  public optIn(senderId: string): void {
    this.optedInSenders.add(senderId);
  }

  public optOut(senderId: string): void {
    this.optedInSenders.delete(senderId);
  }

  public isOptedIn(senderId: string): boolean {
    return this.optedInSenders.has(senderId);
  }
}

/** Escopo de inbound da linha: shared/test nunca vira public por flag local (R3). */
export function getInboundScope(mode: string): InboundScope {
  if (mode === "public") return "public";
  if (mode === "shared" || mode === "test" || mode === "limited") return "allowlist";
  return "unknown";
}

export function allowOutbound(
  reason: OutboundReason,
  optedIn: boolean,
  scope: InboundScope = "allowlist"
): boolean {
  if (scope === "allowlist" && reason === "proactive") return false;
  return reason !== "proactive" || optedIn;
}

