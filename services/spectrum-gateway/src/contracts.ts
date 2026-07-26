export type Platform = "imessage" | "telegram" | "whatsapp" | "web";

export interface CanonicalInboundMessage {
  messageId: string;
  platform: Platform;
  spaceId: string;
  senderId: string;
  senderHandle?: string;
  contentType: "text" | "attachment" | "unsupported";
  text?: string;
  attachments: ReadonlyArray<{ readonly name?: string; readonly mimeType?: string }>;
  replyTo?: string;
  timestamp: string;
  metadata: Readonly<Record<string, string>>;
}

export interface CanonicalOutboundMessage {
  conversationId: string;
  platform: Platform;
  text: string;
  replyTo?: string;
  correlationId: string;
}

export type ConversationState =
  | "NEW"
  | "ACTIVE"
  | "WAITING_USER"
  | "WAITING_TOOL"
  | "WAITING_HUMAN"
  | "HITL_REQUIRED"
  | "HANDOFF"
  | "CLOSED";

export interface TaskEnvelope {
  taskId: string;
  correlationId: string;
  conversationId: string;
  objective: string;
  allowedTools: readonly string[];
  forbiddenTools: readonly string[];
  timeoutMs: number;
  maxSteps: number;
  riskLevel: "low" | "medium" | "high";
  requiresHitl: boolean;
  contextRefs: readonly string[];
}

export interface TaskResult {
  status: "completed" | "handoff" | "degraded" | "rejected";
  answer: string;
  toolCalls: readonly string[];
  evidence: readonly string[];
  errors: readonly string[];
  riskFlags: readonly string[];
}
