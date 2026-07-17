# Lesson 217 — G8 Wave 33: MCP hash sequence + PII MCP + X-Idempotency + WS concurrent

**Type:** project  
**Date:** 2026-07-17  
**Agents:** A1 dev · A2 lgpd · A3 n8n/dev · A4 dev (4 slots)  
**Evidence gate:** Lesson 216 honesty — only real code+tests

---

## Tasks closed (evidenced)

| ID | Entrega | Evidence |
|----|---------|----------|
| **G8.07.T2** | `AuditService.verify_hash_sequence` + MCP tool `cartorio_audit_hash_sequence` | offline chain OK/tamper/empty |
| **G8.07.T3** | `app/services/mcp_pii.py` `scrub_mcp_output` + apply on audit/protocol tools | CPF nested mask |
| **G8.05.T2** | Middleware aceita **`X-Idempotency-Key`** além de `Idempotency-Key` | 3 webhook paths cache+conflict |
| **G8.01.T4** | WS mock 50 sequential + 20 threaded concurrent ping/pong | no crash |

**Tests:** `backend/tests/test_g8_wave33_mcp_idempotency_ws.py` + inventory update → **35 passed** (com inventory suite parcial).

**G8 total evidenced:** **9/100** (antes 5; +4 Wave 33).

---

## Design notes

1. **Hash sequence offline** ≠ `verify_chain(db)` — útil para drills/mutmut sem Postgres; MCP limita 5000 entries.
2. **scrub_mcp_output** é defense-in-depth; services ainda devem scrubar na origem.
3. **X-Idempotency-Key** é alias N8N-friendly; cache key ainda hash(method+path+key) — aliases diferentes = keys diferentes (OK).
4. **WS “100 concurrent”** no super plano: implementamos 50 seq + 20 threaded (TestClient limita true fan-out). Não marcar G8.01.T1 como done até stress ≥100 real.

---

## Files

- `backend/app/services/audit.py` (+verify_hash_sequence)
- `backend/app/services/mcp_pii.py` (new)
- `backend/mcp_server.py` (tool + scrub)
- `backend/app/middleware/idempotency.py` (X- alias)
- `backend/tests/test_g8_wave33_mcp_idempotency_ws.py`
- `backend/tests/test_mcp_tools_inventory_g8.py` (canônico +hash_sequence)

---

## Next wave (4 agents)

| Slot | Task |
|------|------|
| A1 | G8.01.T1 — 100+ WS concurrent (melhorar além do mock) |
| A2 | G8.01.T3 — heartbeat robusto (já ping; idle timeout) |
| A3 | G8.07.T4 — MCP tools status no radar |
| A4 | G8.05.T4 — stress idempotency keys |

G7 SUI residual permanece (DNS×3, tokens, QR).

## Cross-refs

lesson-216 (honesty) · 212–215 (MCP/DLQ) · 209 (G7)

Modified by Gustavo Almeida — G8 Wave 33
