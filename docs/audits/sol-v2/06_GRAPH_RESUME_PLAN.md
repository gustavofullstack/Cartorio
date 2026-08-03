# Plano de Retomada do Grafo de 100 Nós (V2)

**Documento:** `docs/audits/sol-v2/06_GRAPH_RESUME_PLAN.md`  
**Escopo:** Grafo Completo — 12 Globais (G0), 48 Tarefa 1 (G1) e 40 Tarefa 2 (G2)  

---

## 1. Regras de Despacho (Dispatch Rules)

1. **Paralelismo Controlado:** No máximo 4 instâncias simultâneas de execução TERRA.
2. **Serialização por Hotspot:** Nós que tocam os mesmos arquivos (`app/services/emolumento.py`, `app/services/pii.py`, `backend/mcp_server.py`) não podem ser despachados no mesmo lote.
3. **Maturidade Criptográfica:** Nível mínimo `E2_TESTED_LOCAL` para todos os nós de código e `E3_RUNTIME_READ_ONLY_VERIFIED` para nós de integração.

---

## 2. Primeiro Lote de Retomada (Batch 1 — Post-GO)

| Nó | Componente / Foco | Executor Delegado | Revisor |
| :--- | :--- | :--- | :--- |
| **G1.01** | Tabela Emolumentos MG 2026 Dual-Layer Schema | `TERRA-DATA` | `TERRA-REVIEW` |
| **G1.02** | Suíte de Validação PII 3-Camadas | `TERRA-QA` | `TERRA-REVIEW` |
| **G2.01** | Lark Client Webhook & Dedupe Store | `TERRA-SRE` | `TERRA-REVIEW` |
| **G2.02** | Auditoria e Validação de Envelopes MCP | `TERRA-QA` | `TERRA-REVIEW` |
