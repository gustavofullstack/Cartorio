import assert from "node:assert/strict";
import test from "node:test";

import type { CanonicalInboundMessage } from "./contracts.js";
import {
  allowOutbound,
  ConsentRegistry,
  conversationId,
  getInboundScope,
  MessageDedupe,
  sanitizeOutbound,
  scrubPii,
} from "./guardrails.js";

function inbound(overrides: Partial<CanonicalInboundMessage> = {}): CanonicalInboundMessage {
  return {
    messageId: "m-1",
    platform: "imessage",
    spaceId: "space-1",
    senderId: "sender-1",
    contentType: "text",
    text: "ola",
    attachments: [],
    timestamp: new Date().toISOString(),
    metadata: {},
    ...overrides,
  };
}

test("scrubPii mascara CPF formatado e nao formatado", () => {
  assert.equal(scrubPii("CPF 123.456.789-09 informado"), "CPF 123.***.***-09 informado");
  assert.equal(scrubPii("cpf 12345678909"), "cpf 123.***.***-09");
});

test("scrubPii mascara email e telefone", () => {
  assert.equal(scrubPii("email joao.silva@exemplo.com.br"), "email j***@exemplo.com.br");
  assert.equal(scrubPii("fone (34) 99988-7766"), "fone [telefone mascarado]");
  assert.equal(scrubPii("liga +55 34 99887-6655"), "liga [telefone mascarado]");
});

test("scrubPii preserva texto sem PII", () => {
  const plain = "Qual o horario de atendimento do cartorio?";
  assert.equal(scrubPii(plain), plain);
});

test("stripInternalAgentControlLeaks remove vazamentos de controle interno e botões", () => {
  const textWithControl = "Olá! Como posso ajudar?\n↳ Redirected current run (iteration 1/150). I'll adjust using your correction.";
  assert.equal(scrubPii(textWithControl), "Olá! Como posso ajudar?");

  const textWithReview = "Atendimento prestado com sucesso.\nSelf-improvement review: User profile updated";
  assert.equal(scrubPii(textWithReview), "Atendimento prestado com sucesso.");
});

test("sanitizeOutbound aplica scrub no texto de saida", () => {
  const out = sanitizeOutbound({
    conversationId: "c-1",
    platform: "imessage",
    text: "Protocolo do CPF 123.456.789-09",
    correlationId: "corr-1",
  });
  assert.equal(out.text, "Protocolo do CPF 123.***.***-09");
  assert.equal(out.correlationId, "corr-1");
});

test("conversationId e estavel e distinto por plataforma", () => {
  const a = conversationId(inbound());
  assert.equal(a, conversationId(inbound()));
  assert.notEqual(a, conversationId(inbound({ platform: "telegram" })));
  assert.notEqual(a, conversationId(inbound({ senderId: "sender-2" })));
  assert.match(a, /^[0-9a-f]{32}$/);
});

test("MessageDedupe aceita novo, rejeita duplicado e expira apos 24h", () => {
  const dedupe = new MessageDedupe();
  const t0 = 1_000_000;
  assert.equal(dedupe.accept("m-1", t0), true);
  assert.equal(dedupe.accept("m-1", t0 + 1), false);
  const day = 24 * 60 * 60 * 1000;
  assert.equal(dedupe.accept("m-1", t0 + day + 1), true);
});

test("getInboundScope: shared/test/limited -> allowlist; public -> public; resto -> unknown", () => {
  assert.equal(getInboundScope("shared"), "allowlist");
  assert.equal(getInboundScope("test"), "allowlist");
  assert.equal(getInboundScope("limited"), "allowlist");
  assert.equal(getInboundScope("public"), "public");
  assert.equal(getInboundScope("enterprise"), "unknown");
});

test("allowOutbound: proactive bloqueado em allowlist; exige opt-in nos demais; reply sempre permitido", () => {
  assert.equal(allowOutbound("proactive", true, "allowlist"), false);
  assert.equal(allowOutbound("proactive", false, "public"), false);
  assert.equal(allowOutbound("proactive", true, "public"), true);
  assert.equal(allowOutbound("reply", false, "allowlist"), true);
  assert.equal(allowOutbound("human_approved", false, "allowlist"), true);
});

test("ConsentRegistry opt-in/opt-out", () => {
  const registry = new ConsentRegistry();
  assert.equal(registry.isOptedIn("sender-1"), false);
  registry.optIn("sender-1");
  assert.equal(registry.isOptedIn("sender-1"), true);
  registry.optOut("sender-1");
  assert.equal(registry.isOptedIn("sender-1"), false);
});
