import type { ArenaAgentId, ArenaDecision, ArenaMessage } from "./arena.js";
import { ArenaTurnCoordinator, payloadHash } from "./arena.js";

export interface ArenaTransport {
  send(message: ArenaMessage): Promise<{ readonly providerMessageId: string; readonly deliveredAt: string }>;
}

export interface ArenaRunRecord {
  readonly scenarioId: string;
  readonly sender: ArenaAgentId;
  readonly target: ArenaAgentId;
  readonly payloadHash: string;
  readonly decision: ArenaDecision["code"];
  readonly providerMessageIdHash?: string;
  readonly deliveredAt?: string;
  readonly errorCode?: "TRANSPORT_ERROR";
}

/**
 * Safe boundary between the offline coordinator and a future provider adapter.
 * It never keeps raw messages, phone numbers, provider secrets, or provider IDs.
 */
export class ArenaRunner {
  private readonly records: ArenaRunRecord[] = [];

  public constructor(
    private readonly coordinator: ArenaTurnCoordinator,
    private readonly transport: ArenaTransport
  ) {}

  public async attempt(message: ArenaMessage): Promise<ArenaRunRecord> {
    const decision = this.coordinator.evaluate(message);
    const base = {
      scenarioId: message.scenarioId,
      sender: message.sender,
      target: message.target,
      payloadHash: payloadHash(message.text),
      decision: decision.code,
    } as const;
    if (!decision.allowed) return this.record(base);

    try {
      const result = await this.transport.send(message);
      return this.record({
        ...base,
        providerMessageIdHash: payloadHash(result.providerMessageId),
        deliveredAt: result.deliveredAt,
      });
    } catch {
      return this.record({ ...base, errorCode: "TRANSPORT_ERROR" });
    }
  }

  public getRecords(): readonly ArenaRunRecord[] {
    return [...this.records];
  }

  private record(record: ArenaRunRecord): ArenaRunRecord {
    this.records.push(record);
    return record;
  }
}
