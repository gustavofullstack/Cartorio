# Lesson 216 — G8 honesty reset + G8.08.T4 DLQ failure injection (2026-07-17)

**Type:** project + feedback (anti-padrão checkbox fraud)  
**Wave:** G8 Wave 32 (real)  
**Agents:** A1 cartorio-dev (T4 tests) · A2 brain (honesty reset) · A3 docs N8N/API · A4 state/goals

---

## 1. Achado crítico

`SUPER_PLANO_G8_100_TASKS.md` estava **100/100 `[x]`** e `SUPER_GOALS_G8.md` dizia **~96%**, mas:

| Evidência real (git + tests + lessons) | Tasks |
|----------------------------------------|-------|
| G8.07.T1 MCP inventory tests | lesson-212 · 14 tests |
| G8.08.T1 DLQ expire/purge | lesson-214 · 20 tests |
| G8.08.T2 DLQ encryption Fernet | lesson-213 · 38 tests |
| G8.08.T3 DLQ alert Telegram | lesson-215 · 18 tests |
| **G8.08.T4** external failure injection | **esta lesson · 13 tests** |

**Total evidenced: 5/100.** O resto era tick de orquestrador/`[x]` paper sem DoD.

`loop-state-g8.json` listava waves 1–24 “completed” sem commits correspondentes (exceto DLQ/MCP).

### Anti-padrão (gravar)

> **Nunca** marcar task G8/G7 `[x]` só porque o orquestrador rodou `run-wave`.  
> DoD obrigatório: código ou doc operacional + teste ou probe + lesson/PROGRESS + (se código) ruff/mypy/pytest.

Mesmo espírito da Lesson 206/208 (não flipar SUI live) e Lesson 185 (agents reais > teatro).

---

## 2. Entrega G8.08.T4

**File:** `backend/tests/test_dlq_external_failure_injection_g8.py`  
**Result:** **13 passed**

Cobre:

- Falhas injetadas Evolution/Chatwoot/Telegram: timeout, 502, connection refused, 429  
- Pipeline `mark_processing` → send fail → `retry_or_dead`  
- 3 retries + dead letter (FAILED)  
- Recover mid-retry (`mark_done`)  
- Backoff A12 (60/300/900)  
- depth multi-queue  
- payload scrubbed (sem CPF raw no helper)  
- lifecycle offline → dead  

**Nota de implementação:** `mark_processing` e `retry_or_dead` **ambos** incrementam `attempts` → 1º fail no pipeline deixa `attempts=2`. Teste trava esse comportamento (não “corrigir” silenciosamente sem ADR).

---

## 3. Honesty reset

- `SUPER_PLANO_G8_100_TASKS.md` → **5 [x] / 95 [ ]** + banner HONESTY GATE  
- `SUPER_GOALS_G8.md` SUPER PROGRESSO → **5%** honesto  
- `.brain/loop-state-g8.json` → só tasks evidenced  

### Docs sync (integração)

- `docs/API.md`: 16 N8N → **38** exports · 13 MCP  
- `docs/INTEGRATION_MATRIX_G7.md`: N8N **38**  
- `docs/API_ENDPOINTS_CATALOG.md`: nota dual-format Evolution  

---

## 4. G7 paralelo (não esquecer)

G7 ainda **92 [x] / 8 [~] SUI**. Radar prod **red**. Composite exit 2.  
CONTINUE em loop **não** fecha DNS/BotFather sem Gustavo.

---

## 5. Próxima wave (4 agents reais)

| Slot | Task candidata | Por quê |
|------|----------------|---------|
| A1 dev | G8.07.T2 MCP tool audit hash chain | gap real MCP |
| A2 n8n | G8.05.T2 X-Idempotency-Key webhooks audit | integração webhooks |
| A3 lgpd | G8.07.T3 MCP PII interceptor out | LGPD |
| A4 sre | G8.09.T1 Tailscale probe script offline | SUI-friendly |

Ou Gustavo ataca SUI G7 (DNS×3) em paralelo.

---

## Cross-refs

lesson-212…215 (DLQ/MCP) · 209 (G7 W29) · 206 (anti paper-done) · 185 (1–2 agents)

Modified by Gustavo Almeida — G8 Wave 32
