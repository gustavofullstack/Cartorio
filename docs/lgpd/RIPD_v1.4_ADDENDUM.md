# RIPD v1.4 — Addendum de Integrações (G6.C.T1)

**Documento:** Relatório de Impacto à Proteção de Dados Pessoais  
**Controlador:** 2º Serviço Notarial de Uberlândia  
**Versão base:** RIPD 1.3 (`docs/ripd.md`)  
**Addendum:** 1.4 — 2026-07-16  
**Owner:** `cartorio-lgpd`  
**Status:** 🟢 RASCUNHO TÉCNICO (aguardando sign-off DPO / Gustavo)

---

## 1. Motivo do addendum

Entre 2026-07-06 (v1.3) e 2026-07-16 o stack passou a incluir canais e
sub-processadores de IA que **não estavam descritos** no RIPD 1.3:

| Integração | Papel | Dados que tocam | Status prod 2026-07-16 |
|---|---|---|---|
| **LobeChat** (`agent.2notasudi.com.br`) | UI chat operador / agente cartório | texto de atendimento (PII scrub pre-LLM) | UP (env key placeholder HOLD) |
| **OpenClaw Gateway** | Router multi-provider LLM + skills | prompts scrubbed, tool calls | UP (cartorio-bot E8 HOLD deploy) |
| **LiteLLM proxy** | Gateway 7+ providers | prompts/respostas scrubbed | UP (coding-vps + cartorio) |
| **MiniMax-M3 XMax Thinking** | Provider LLM coding/ops | prompts técnicos (sem CPF raw) | DPA pending Gustavo |
| **Telegram Bot** | Canal titular | chat_id, texto, consent | Token revogado HOLD |
| **Evolution API / WhatsApp** | Canal titular | telefone, texto, mídia meta | 502 / QR HOLD |
| **Chatwoot** | CRM + handoff humano | conversa, labels, contact | 502 / DNS NXDOMAIN |
| **Redis 8** | Idempotência, rate limit, cache | keys hashed, TTL 24h | online (via API radar) |
| **Postgres / Supabase** | System of record | PII full (cripto at-rest) | online |

---

## 2. Novos tratamentos (Tratamentos 13–18)

### T13 — LobeChat UI → OpenClaw
- **Finalidade:** interface do agente cartório para escrevente/operador.
- **Base legal:** art. 7º V (contrato) + art. 7º II (obrigação legal notarial).
- **Categorias:** texto livre de atendimento; **proibido** CPF/RG raw (scrub pre-LLM).
- **Retenção:** sessão LobeChat efêmera; audit chain na API (5y se protocolo).
- **Mitigação:** CORS origin allowlist (Lesson 170), timeout 30s, HITL obrigatório.

### T14 — OpenClaw multi-agent + skills
- **Finalidade:** roteamento de intents + tools (emolumento, protocolo, handoff).
- **Base legal:** art. 7º V + VI.
- **Risco residual:** context overflow (ADR-016) — mitigado threshold + TTL.
- **Mitigação:** cartorio-bot spec E6, scopes operator token, PII scrub 3 camadas.

### T15 — LiteLLM multi-provider
- **Finalidade:** fallback chain providers (MiniMax → DeepSeek → free chain).
- **Sub-processadores:** ver `docs/LLM_DPA_MATRIX.md` + `scripts/dpa_sign_flow.py`.
- **Mitigação:** output scrub LGPD-015, rate limit, audit `llm.output_scrubbed`.

### T16 — MiniMax-M3 Coding Plan
- **Finalidade:** coding agents / raciocínio avançado (não atendimento titular direto preferencialmente).
- **DPA:** template em `docs/lgpd/dpa_minimax_template.md` — **assinatura HOLD-GUSTAVO**.
- **Data residency:** conforme contrato MiniMax (documentar no DPA assinado).

### T17 — Telegram + WhatsApp multicanal
- **Finalidade:** atendimento remoto titular.
- **Consent:** banner primeira mensagem + keyword PARAR/SAIR (opt-out).
- **Mitigação:** HMAC webhook, Redis SETNX 24h, parse dual Evolution, parse_mode seguro.

### T18 — Chatwoot handoff humano
- **Finalidade:** HITL — escrevente assume conversa.
- **Mitigação:** sem eco de CPF raw; labels LGPD; audit `handoff.human`.

---

## 3. Matriz de risco atualizada (delta v1.3 → v1.4)

| Risco | Prob. | Impacto | Mitigação v1.4 |
|---|---|---|---|
| PII em prompt LobeChat/OpenClaw | Média | Alto | scrub input + pre-LLM + output; testes 35/35 PII |
| Provider LLM sem DPA assinado | Alta | Médio | tracker 9 DPAs; 4 signed; MiniMax pending |
| Canal 502 / DNS NXDOMAIN | Alta (hoje) | Médio | radar expanded + SUI Gustavo DNS/env |
| Token Telegram revogado | Alta | Médio | HOLD BotFather; monitores Uptime Kuma |
| Context overflow OpenClaw | Baixa | Médio | ADR-016 threshold + TTL |
| Idempotência webhook falha | Baixa | Alto | injector G6.B.T6 (21/21 webhooks) |

---

## 4. Direitos do titular — sem regressão

Todos os 7 direitos Art. 18 permanecem implementados (v1.3 §5). Canais novos
**não** criam decisão automatizada com efeitos jurídicos — HITL mandatory
(`protocolo` nasce `DRAFT`).

---

## 5. Checklist sign-off DPO (cartorio-lgpd)

- [ ] DPO nominal preenchido no RIPD base
- [ ] DPA MiniMax assinado + arquivo no vault
- [ ] LobeChat OPENAI_API_KEY real (não placeholder)
- [ ] OpenClaw cartorio-bot deploy + scopes operator
- [ ] DNS Cloudflare 3 A records (chatwoot/n8n/supabase)
- [ ] Revisão trimestral agendada

---

## 6. Referências

- `docs/ripd.md` (v1.3 base → bump para 1.4 no header)
- Lesson 170 LobeChat · 177 OpenClaw E8 · 178 Telegram/LobeChat · 180 SUPER PLANO
- `docs/LLM_DPA_MATRIX.md` · `docs/lgpd/dpa_minimax_template.md`
- `backend/app/services/pii.py` · `audit.py` · `lgpd_*`

---

**Modified by Gustavo Almeida + cartorio-lgpd — G6 Wave 13 (2026-07-16)**
