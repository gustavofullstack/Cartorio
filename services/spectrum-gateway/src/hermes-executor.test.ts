import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import test from "node:test";

import type { TaskEnvelope, TaskResult } from "./contracts.js";
import { HermesExecutor } from "./hermes-executor.js";

function task(): TaskEnvelope {
  return {
    taskId: "t-1",
    correlationId: "corr-1",
    conversationId: "conv-1",
    objective: "ola",
    allowedTools: [],
    forbiddenTools: [],
    timeoutMs: 5_000,
    maxSteps: 1,
    riskLevel: "low",
    requiresHitl: true,
    contextRefs: [],
  };
}

test("executor sem endpoint/token retorna degraded sem chamar rede", async () => {
  const executor = new HermesExecutor(undefined, undefined);
  const result = await executor.execute(task());
  assert.equal(result.status, "degraded");
  assert.deepEqual(result.evidence, ["executor_not_configured"]);
});

test("executor sanitiza PII da resposta do Hermes", async () => {
  const payload: TaskResult = {
    status: "completed",
    answer: "Seu CPF 123.456.789-09 foi recebido",
    toolCalls: [],
    evidence: [],
    errors: [],
    riskFlags: [],
  };
  const server: Server = createServer((_req, res) => {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(payload));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  try {
    const executor = new HermesExecutor(`http://127.0.0.1:${port}/execute`, "token-fake");
    const result = await executor.execute(task());
    assert.equal(result.status, "completed");
    assert.equal(result.answer, "Seu CPF 123.***.***-09 foi recebido");
  } finally {
    server.close();
  }
});

test("executor lanca erro quando Hermes rejeita (status nao-2xx)", async () => {
  const server: Server = createServer((_req, res) => {
    res.writeHead(500).end();
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  try {
    const executor = new HermesExecutor(`http://127.0.0.1:${port}/execute`, "token-fake");
    await assert.rejects(() => executor.execute(task()), /rejected request: 500/);
  } finally {
    server.close();
  }
});
