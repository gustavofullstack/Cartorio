import { randomUUID } from "node:crypto";
import { createServer } from "node:http";

import { imessage } from "@spectrum-ts/imessage";
import { Spectrum } from "spectrum-ts";

import type {
  CanonicalInboundMessage,
  ChannelCapabilities,
  GatewayHealthContract,
  Platform,
  TaskEnvelope,
} from "./contracts.js";
import { PhantomPanelAdapter } from "./control-plane.js";
import { conversationId, getInboundScope, MessageDedupe, sanitizeOutbound, scrubPii } from "./guardrails.js";
import { HermesExecutor } from "./hermes-executor.js";

const projectId = process.env.SPECTRUM_PROJECT_ID;
const projectSecret = process.env.SPECTRUM_PROJECT_SECRET;
const lineMode = process.env.SPECTRUM_LINE_MODE ?? "shared";

export function getChannelCapabilities(platform: Platform = "imessage"): ChannelCapabilities {
  const scope = getInboundScope(lineMode);
  return {
    platform,
    canSendText: true,
    canSendMedia: platform !== "imessage",
    canSendPoll: platform === "whatsapp" || platform === "telegram",
    inboundScope: scope,
    requiresPairing: platform === "whatsapp",
  };
}

let lastInboundAt: string | null = null;
let lastOutboundAt: string | null = null;
let lastError: string | null = null;

export function getGatewayHealth(): GatewayHealthContract {
  return {
    processUp: true,
    providerConnected: Boolean(projectId && projectSecret),
    channelCapabilityKnown: true,
    lastInboundAt,
    lastOutboundAt,
    lastError: lastError ? scrubPii(lastError) : null,
  };
}

if (lineMode === "public") {
  throw new Error("Public inbound requires a provider-supported dedicated line; shared lines remain allowlisted");
}

if (!projectId || !projectSecret) {
  console.warn("[cartorio-spectrum] Spectrum credentials missing; gateway running in scaffold/verification mode");
} else {
  const dedupe = new MessageDedupe();
  const executor = new HermesExecutor(process.env.HERMES_EXECUTOR_URL, process.env.HERMES_EXECUTOR_TOKEN);
  const phantom = new PhantomPanelAdapter(); // Explicitly disabled placeholder; no invented API calls.
  void phantom.getHealth();

  function toInbound(space: unknown, message: unknown): CanonicalInboundMessage {
    const raw = message as { id?: unknown; content?: { type?: unknown; text?: unknown }; sender?: { id?: unknown; handle?: unknown } };
    const rawSpace = space as { id?: unknown };
    const text = typeof raw.content?.text === "string" ? raw.content.text : undefined;
    return {
      messageId: String(raw.id ?? randomUUID()),
      platform: "imessage" satisfies Platform,
      spaceId: String(rawSpace.id ?? "unknown"),
      senderId: String(raw.sender?.id ?? "unknown"),
      senderHandle: typeof raw.sender?.handle === "string" ? raw.sender.handle : undefined,
      contentType: text ? "text" : "unsupported",
      text,
      attachments: [],
      timestamp: new Date().toISOString(),
      metadata: {},
    };
  }

  try {
    const app = await Spectrum({ projectId, projectSecret, providers: [imessage.config()] });
    console.error("[cartorio-spectrum] ready: iMessage inbound is provider-governed; no proactive outbound");

    for await (const [space, message] of app.messages) {
      lastInboundAt = new Date().toISOString();
      const inbound = toInbound(space, message);
      if (!dedupe.accept(inbound.messageId) || inbound.contentType !== "text" || !inbound.text) continue;
      const cid = conversationId(inbound);
      const task: TaskEnvelope = {
        taskId: randomUUID(),
        correlationId: randomUUID(),
        conversationId: cid,
        objective: inbound.text,
        allowedTools: ["cartorio_calcular_emolumento", "cartorio_consultar_protocolo"],
        forbiddenTools: ["cartorio_audit_verify"],
        timeoutMs: 45_000,
        maxSteps: 4,
        riskLevel: "medium",
        requiresHitl: true,
        contextRefs: [],
      };
      const result = await executor.execute(task).catch(() => {
        lastError = "executor_error";
        return {
          status: "degraded" as const,
          answer: "Não foi possível concluir agora. Um escrevente continuará o atendimento.",
          toolCalls: [],
          evidence: [],
          errors: ["executor_error"],
          riskFlags: ["degraded"],
        };
      });
      const outbound = sanitizeOutbound({ conversationId: cid, platform: "imessage", text: result.answer, correlationId: task.correlationId });
      await (space as { send: (text: string) => Promise<void> }).send(outbound.text);
      lastOutboundAt = new Date().toISOString();
    }
  } catch (err: unknown) {
    lastError = err instanceof Error ? err.message : String(err);
    console.error("[cartorio-spectrum] initialization error:", lastError);
  }
}

// Health/readiness mínimo: sempre exposto (inclusive em scaffold mode), apenas loopback.
const healthPort = Number(process.env.SPECTRUM_HEALTH_PORT ?? 8790);
const healthServer = createServer((req, res) => {
  if (req.url !== "/health" && req.url !== "/ready") {
    res.writeHead(404).end();
    return;
  }
  const health = getGatewayHealth();
  const ready = health.providerConnected && health.channelCapabilityKnown;
  res.writeHead(req.url === "/ready" && !ready ? 503 : 200, { "content-type": "application/json" });
  res.end(JSON.stringify(health));
});
healthServer.listen(healthPort, "127.0.0.1", () => {
  console.error(`[cartorio-spectrum] health endpoint on 127.0.0.1:${healthPort}`);
});

