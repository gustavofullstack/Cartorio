/**
 * Control plane é opcional e não é fonte de verdade de conversas ou LGPD.
 * Phantom Panel permanece não configurado até existir documentação/API real.
 */
export interface ControlPlaneAdapter {
  getHealth(): Promise<{ readonly ok: boolean; readonly detail?: string }>;
  listAgents(): Promise<readonly { readonly id: string; readonly name: string }[]>;
  handoff(conversationId: string, reason: string): Promise<void>;
}

export class PhantomPanelAdapter implements ControlPlaneAdapter {
  public async getHealth(): Promise<{ readonly ok: boolean; readonly detail?: string }> {
    return { ok: false, detail: "Phantom Panel adapter is not configured" };
  }

  public async listAgents(): Promise<readonly { readonly id: string; readonly name: string }[]> {
    throw new Error("Phantom Panel API is not documented/configured");
  }

  public async handoff(_conversationId: string, _reason: string): Promise<void> {
    throw new Error("Phantom Panel API is not documented/configured");
  }
}
