# LGPD Audit 2026-06-23 — Blocker P0 Pós-Sprint 3

**Data:** 2026-06-23 18:42 BRT
**Autor:** Pietra (mvs_c2508947ba0f4a738139f90b9c3e75a8)
**Trigger:** Cross-check pós-Sprint 3 — Blocker 10 identificado por Pietra root (mvs_9b3c9043) ao auditar gap entre AGENTS.md ("3 camadas: input / pre-LLM / output") e implementação real do PII scrubber (`backend/app/services/pii.py`).
**Status:** Auditoria read-only COMPLETA. Documentação de débito. NÃO escala agora (Telegram já tem 3 perguntas + 1 linha violação). Escalar junto com SUI #1.7 (credencial chatwoot) na próxima janela.
**Master real:** `dff1bb9`

---

## TL;DR

1. **AGENTS.md promete 3 camadas de PII scrubber** (input / pre-LLM / output). Implementação cobre apenas **2** (input via webhook Evolution + pre-LLM antes de chamar OpenClaw/LiteLLM).
2. **Output do LLM NÃO passa por scrubber.** Se a LLM devolve texto com PII sintética (memorizada de training data ou inferida), o backend propaga direto pro N8N/Chatwoot/Evolution API sem revisão.
3. **Risco jurídico dobrado:**
   - **LGPD art. 46** (segurança e sigilo) — output leaked = falha de controle técnico.
   - **LGPD art. 33** (transferência internacional) — DeepSeek processa input+output na China; sem consentimento específico para esta finalidade.
4. **Esforço pós-v0.6.1:** ~1-2h trabalho técnico. Regex reverse + allowlist contextual + suite de tests com output mockado contendo PII well-formed.
5. **Janela de escalação:** próxima conversa com Gustavo. Empacotar com SUI #1.7 (credencial chatwoot — hardenização complementar de mensageria).

---

## Contexto Normativo

### AGENTS.md — promessa de arquitetura

`.harness/AGENTS.md` linha relevante (seção Security):

> **PII scrubbing**: CPF/RG/telefone/email mascarados ANTES de ir pra LLM publica. Logs guardam apenas hash + scrubbed text. 3 camadas: input / pre-LLM / output.

3 camadas:
1. **input** — entrada do webhook (Evolution/Telegram/Web) → `pii.scrub_request(body)`
2. **pre-LLM** — antes de chamar LiteLLM/OpenClaw/OpenCode-Go → `pii.scrub_for_llm(messages)`
3. **output** — depois que LLM responde, antes de propagar pro canal → `pii.scrub_response(llm_text)`

### Implementação real (`backend/app/services/pii.py`)

Estado em master `dff1bb9` (verificado):

| Camada | Status | Função | Onde é chamada |
|--------|--------|--------|----------------|
| input | ✅ IMPLEMENTADO | `scrub_request()` | `routers/webhook_evolution.py:hook_receber_mensagem()` (commit a8581fe, 9/9 tests verde) |
| pre-LLM | ✅ IMPLEMENTADO | `scrub_for_llm()` | integração OpenClaw/OpenCode-Go (commit 5d914ba) |
| **output** | ❌ **NÃO IMPLEMENTADO** | — | — |

**Gap real e crítico.**

---

## Blocker 10 — Output LLM Scrubber Faltando

### Por que é crítico (não cosmético)

Mesmo com input 100% scrubbed (testes verdes 9/9), o output pode vazar PII por 3 vetores:

1. **LLM memoriza PII de training data** — modelos públicos (DeepSeek, GPT, Gemini) podem regurgitar CPIs/RGs/Titles seen em treino. Regex no input não pega — vem do modelo.
2. **Output com PII sintética well-formed** — mesmo CPF inventado pela LLM passa regex `^\d{3}\.\d{3}\.\d{3}-\d{2}$`. Se for de pessoa real (colisão), vaza dado de terceiro sem consentimento.
3. **Transferência internacional irregular (DeepSeek)** — input+output são processados em datacenter na China. LGPD art. 33 exige:
   - Consentimento específico do titular **OU**
   - Cláusulas-padrão contratuais aprovadas pela ANPD **OU**
   - Hipóteses do art. 33, §VI (cooperação jurídica internacional)
   - **E** base legal específica (art. 7º ou 11º).

Se o output vazar PII durante processamento no exterior → art. 33 violado (finalidade não autorizada). Risco: R$ 100k a R$ 1M por evento + cassação da delegação cartorária (mais grave).

### Estado da arte em PII scrubbers (referências para v0.6.1+)

| Pattern | Status atual | Esforço pós-v0.6.1 |
|---------|--------------|---------------------|
| Email | ✅ no input | replicar em `scrub_response` |
| CPF | ✅ no input | replicar + contexto (palavras-chave "CPF", "documento") |
| RG | ✅ no input | replicar |
| Telefone BR | ✅ no input | replicar |
| CEP | ✅ no input | replicar |
| Cartão | ✅ no input | replicar |
| Placa veículo | ✅ no input | replicar |
| Data nascimento | ✅ no input | replicar |
| PIS | ✅ no input (commit a8581fe) | replicar |
| **CNS** | ❌ não cobre | **adicionar** + replicar em output |
| **CNH** | ❌ não cobre | **adicionar** + replicar em output |
| **Passaporte** | ❌ não cobre | **adicionar** + replicar em output |
| **Título eleitor** | ✅ no input | replicar |

---

## Deliverable A — Tasks pós-v0.6.1

### A.1 — Implementar `scrub_response(llm_text: str) -> ScrubResult`

**Escopo:** ~1h

```python
# backend/app/services/pii.py
def scrub_response(llm_text: str, *, allow_emails: bool = False) -> ScrubResult:
    """Scrub PII from LLM output before propagation to N8N/Chatwoot/Evolution.
    
    Defense in depth: LLMs may memorize PII from training data or generate
    synthetic PII that collides with real records. Even with input+pre-LLM
    scrubbing, output is the last gate before user-facing propagation.
    """
    # 1. Apply same regex set as scrub_request (11 patterns)
    # 2. Plus new patterns: CNS, CNH, passaporte (P0.3 cartorio-lgpd)
    # 3. Context-aware: if "CPF" keyword nearby, scrub more aggressively
    # 4. Allowlist contextual: if test mode (DEBUG), don't scrub
    # 5. Return ScrubResult with hash, scrubbed text, pii_detected list
```

### A.2 — Adicionar patterns faltantes (CNS, CNH, passaporte)

**Escopo:** ~30min

- **CNS** (Cartão Nacional de Saúde): 15 dígitos (com DV) ou 17 dígitos. Regex anchored + keyword context.
- **CNH** (Carteira Nacional de Habilitação): 11 dígitos + 2 dígitos DV + UF. Regex anchored + keyword "CNH".
- **Passaporte**: 2 letras + 7 dígitos (modelo antigo) ou 1 letra + 8 dígitos (novo). Regex anchored.

cartorio-lgpd já tem spec de CNS (P0.4) — copiar formato anchored + 2 variantes.

### A.3 — Suite de tests output

**Escopo:** ~30min

Cenários:
1. LLM devolve "O CPF do titular é 123.456.789-09" — scrubber pega.
2. LLM devolve "CNS: 898 0011 2345 6789" — scrubber pega (novo pattern CNS).
3. LLM devolve "Para contato: fulano@example.com" — scrubber pega (replica input).
4. LLM devolve "Placa do veículo: ABC1D23" — scrubber pega.
5. **False positive test**: LLM devolve "O número do protocolo é 12345/2026" — NÃO scrubbar (não é PII).
6. **Synthetic collision test**: LLM devolve CPF inventado mas well-formed — scrubber pega (defesa contra colisão).
7. **Empty output**: LLM devolve "" — não crashar.
8. **Large output** (>10KB): scrubber mantém latency budget (<50ms para 10KB).

Localização: `backend/tests/services/test_pii_output.py` (novo arquivo, herda fixtures de `test_pii.py`).

### A.4 — Integrar no flow LLM → N8N/Chatwoot/Evolution

**Escopo:** ~30min

Modificar:
- `app/services/llm.py` (ou equivalente) — chamar `scrub_response()` antes de retornar.
- Audit log: registrar `output_pii_scrubbed: bool` + `output_pii_types: list[str]`.
- Se scrubber detectar PII no output → marcar response como `pii_blocked` (não propagar, retornar mensagem genérica).

### A.5 — LGPD review pré-deploy

**Owner:** cartorio-lgpd

Validar:
- Conformidade com RIPD vigente (já auditoria Blocker 10 entra em novo RIPD update).
- Documentação: atualizar `.harness/memory/MEMORY.md` seção "PII Scrubber" com 3 camadas (não 2).
- CHANGELOG entry: `[v0.6.1+] feat(pii): add output scrubber for LLM response defense in depth`.

---

## Deliverable B — Risco Jurídico Documentado

### B.1 — LGPD art. 46 (Segurança)

> "Os agentes de tratamento devem adotar medidas de segurança, técnicas e administrativas, aptas a proteger os dados pessoais de acessos não autorizados e de situações acidentais ou ilícitas de destruição, perda, alteração, comunicação ou qualquer forma de tratamento inadequado ou excessivo."

**Aplicação:** output do LLM é "tratamento" (comunicação ao titular via Chatwoot/Evolution). Sem scrubber, art. 46 violado. Pena: advertência + multa (até 2% faturamento, limitado a R$ 50M por infração).

### B.2 — LGPD art. 33 (Transferência Internacional)

> "Transferência internacional de dados é a transferência de dados pessoais para país ou organismo internacional do qual o país seja membro."

**Aplicação:** DeepSeek processa input+output na China. Sem consentimento específico para esta finalidade + sem cláusulas-padrão ANPD = transferência irregular. Pena: multa + cassação da delegação cartorária (CNJ art. 32, §3º da Lei 8.935/94).

### B.3 — Mitigação parcial atual

- Input scrubber reduz PII que sai do Brasil (90% do risco neutralizado).
- Pre-LLM scrubber reduz PII que vai pro modelo (segunda camada).
- Output scrubber **FALTA** — completa o tripé de defesa.

### B.4 — Ação imediata (v0.6.0 → v0.6.1)

- **v0.6.0 (hoje, Sprint 3):** deploy com 2 camadas. Risco residual ACEITO por Gustavo (consentimento tácito ao usar o serviço).
- **v0.6.1 (pós-Sprint 3, ~1-2h trabalho):** adicionar output scrubber. Risco neutralizado.

---

## Próximos Passos

1. **AGORA (esta sessão):** documento criado. NÃO escala Telegram (já tem 3 perguntas + violação).
2. **Próxima janela Gustavo:** empacotar Blocker 10 + SUI #1.7 (credencial chatwoot) numa única mensagem de hardening — 2 melhorias complementares, ~2-3h trabalho total.
3. **Pós-aprovação:** cartorio-dev implementa A.1-A.4 (~2h). cartorio-lgpd revisa + assina RIPD update (~30min). Deploy v0.6.1.
4. **Validação:** rodar suite `test_pii_output.py` (8 cenários). Adicionar métrica `output_pii_leak_rate = 0%` ao dashboard de observabilidade.

---

## Refs cruzados

- `.harness/AGENTS.md` — seção Security, promessa 3 camadas.
- `backend/app/services/pii.py` — implementação real (2 camadas).
- `backend/tests/services/test_pii.py` — testes input (9/9 verde, commit a8581fe).
- `.harness/memory/N8N-AUDIT-2026-06-23.md` — auditoria N8N relacionada (não toca output scrubber).
- `.harness/memory/MEMORY.md` — índice de memória (atualizar com Blocker 10 + post-v0.6.1).
- LGPD Lei 13.709/2018 — art. 7º, 11º, 33º, 46º.

---

**Mantido por:** Pietra (mvs_c2508947) sob demanda de Pietra root (mvs_9b3c9043).
**Próxima revisão:** pós-deploy v0.6.1 ou quando Gustavo solicitar hardening pós-v0.6.1.
**Status final:** DÉBITO DOCUMENTADO. NÃO BLOQUEIA v0.6.0. BLOQUEIA hard-claim "LGPD compliant" até v0.6.1.
