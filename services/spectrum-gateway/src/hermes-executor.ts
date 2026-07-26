import type { TaskEnvelope, TaskResult } from "./contracts.js";
import { scrubPii } from "./guardrails.js";

export class HermesExecutor {
  public constructor(
    private readonly endpoint: string | undefined,
    private readonly token: string | undefined,
  ) {}

  public async execute(task: TaskEnvelope): Promise<TaskResult> {
    if (!this.endpoint || !this.token) {
      return {
        status: "degraded",
        answer: "Atendimento temporariamente indisponível. Um escrevente pode continuar o atendimento.",
        toolCalls: [], evidence: ["executor_not_configured"], errors: [], riskFlags: ["no_executor"],
      };
    }
    const response = await fetch(this.endpoint, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${this.token}` },
      body: JSON.stringify(task),
      signal: AbortSignal.timeout(task.timeoutMs),
    });
    if (!response.ok) throw new Error(`Hermes executor rejected request: ${response.status}`);
    const result = await response.json() as TaskResult;
    return { ...result, answer: scrubPii(result.answer) };
  }
}
