import { createHash } from "node:crypto";

import type { CanonicalInboundMessage, CanonicalOutboundMessage, InboundScope } from "./contracts.js";

const CPF = /\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b/g;
const EMAIL = /\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g;
const PHONE = /\b(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}-?\d{4}\b/g;

/** Sanitiza apenas a cópia enviada a executores externos e canais. */
export function scrubPii(text: string): string {
  return text
    .replace(CPF, "$1.***.***-$4")
    .replace(EMAIL, "$1***@$2")
    .replace(PHONE, "[telefone mascarado]");
}

/** A identidade do canal não é uma identidade civil unificada. */
export function conversationId(message: CanonicalInboundMessage): string {
  const stable = `${message.platform}:${message.spaceId}:${message.senderId}`;
  return createHash("sha256").update(stable).digest("hex").slice(0, 32);
}

export function sanitizeOutbound(message: CanonicalOutboundMessage): CanonicalOutboundMessage {
  return { ...message, text: scrubPii(message.text) };
}

/** Deduplicação local defensiva; o backend permanece a fonte de idempotência. */
export class MessageDedupe {
  private readonly seen = new Map<string, number>();

  public accept(messageId: string, now = Date.now()): boolean {
    const previous = this.seen.get(messageId);
    this.seen.set(messageId, now);
    for (const [id, timestamp] of this.seen) {
      if (now - timestamp > 24 * 60 * 60 * 1000) this.seen.delete(id);
    }
    return previous === undefined;
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

export function allowOutbound(
  reason: OutboundReason,
  optedIn: boolean,
  scope: InboundScope = "allowlist"
): boolean {
  if (scope === "allowlist" && reason === "proactive") return false;
  return reason !== "proactive" || optedIn;
}

