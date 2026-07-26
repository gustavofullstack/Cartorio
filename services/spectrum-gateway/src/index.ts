import { randomUUID } from "node:crypto";

import { imessage } from "@spectrum-ts/imessage";
import { Spectrum } from "spectrum-ts";

import type { CanonicalInboundMessage, Platform, TaskEnvelope } from "./contracts.js";
import { PhantomPanelAdapter } from "./control-plane.js";
import { conversationId, MessageDedupe, sanitizeOutbound } from "./guardrails.js";
import { HermesExecutor } from "./hermes-executor.js";

const projectId = process.env.SPECTRUM_PROJECT_ID;
const projectSecret = process.env.SPECTRUM_PROJECT_SECRET;
const lineMode = process.env.SPECTRUM_LINE_MODE ?? "shared";
if (lineMode === "public") {
  throw new Error("Public inbound requires a provider-supported dedicated line; shared lines remain allowlisted");
}
if (!projectId || !projectSecret) throw new Error("Spectrum credentials must be injected through the environment");

const dedupe = new MessageDedupe();
const executor = new HermesExecutor(process.env.HERMES_EXECUTOR_URL, process.env.HERMES_EXECUTOR_TOKEN);
const phantom = new PhantomPanelAdapter(); // Explicitly disabled placeholder; no invented API calls.
void phantom.getHealth();

function toInbound(space: unknown, message: unknown): CanonicalInboundMessage {
  const raw = message as { id?: unknown; content?: { type?: unknown; text?: unknown }; sender?: { id?: unknown; handle?: unknown } };
  const rawSpace = space as { id?: unknown };
  const text = typeof raw.content?.text === "string" ? raw.content.text : undefined;
  return {
    messageId: String(raw.id ?? randomUUID()), platform: "imessage" satisfies Platform,
    spaceId: String(rawSpace.id ?? "unknown"), senderId: String(raw.sender?.id ?? "unknown"),
    senderHandle: typeof raw.sender?.handle === "string" ? raw.sender.handle : undefined,
    contentType: text ? "text" : "unsupported", text, attachments: [], timestamp: new Date().toISOString(), metadata: {},
  };
}

const app = await Spectrum({ projectId, projectSecret, providers: [imessage.config()] });
console.error("[cartorio-spectrum] ready: iMessage inbound is provider-governed; no proactive outbound");

for await (const [space, message] of app.messages) {
  const inbound = toInbound(space, message);
  if (!dedupe.accept(inbound.messageId) || inbound.contentType !== "text" || !inbound.text) continue;
  const cid = conversationId(inbound);
  const task: TaskEnvelope = {
    taskId: randomUUID(), correlationId: randomUUID(), conversationId: cid,
    objective: inbound.text, allowedTools: ["cartorio_calcular_emolumento", "cartorio_consultar_protocolo"],
    forbiddenTools: ["cartorio_audit_verify"], timeoutMs: 45_000, maxSteps: 4,
    riskLevel: "medium", requiresHitl: true, contextRefs: [],
  };
  const result = await executor.execute(task).catch(() => ({
    status: "degraded" as const, answer: "Não foi possível concluir agora. Um escrevente continuará o atendimento.",
    toolCalls: [], evidence: [], errors: ["executor_error"], riskFlags: ["degraded"],
  }));
  const outbound = sanitizeOutbound({ conversationId: cid, platform: "imessage", text: result.answer, correlationId: task.correlationId });
  await (space as { send: (text: string) => Promise<void> }).send(outbound.text);
}
