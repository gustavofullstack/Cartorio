<!-- Modified by ZCode/Mavis (SQUAD D D01-D05 - 2026-06-24) -->

# DPA Index — Data Processing Agreements do Projeto Cartório

**Versão:** 1.0
**Data:** 24 de junho de 2026
**Squad:** SQUAD_D_LGPD
**Status geral:** **TEMPLATES PRONTOS — AGUARDANDO ASSINATURA GUSTAVO + DPO**

---

## Sumário

| DPA | Provider | Função | Status | Template | Bloqueio LGPD |
|-----|----------|--------|--------|----------|---------------|
| D01 | MiniMax (MiniMax-M2.7/M3) | LLM provider (harness operacional) | TEMPLATE | [dpa_minimax_template.md](dpa_minimax_template.md) | LGPD-015 |
| D02 | Evolution API | WhatsApp Business API gateway | TEMPLATE | [dpa_evolution_api_template.md](dpa_evolution_api_template.md) | LGPD-013 |
| D03 | Opencode-Go (DeepSeek-v4 flash) | LLM provider (clientes finais) | TEMPLATE | [dpa_opencode_go_template.md](dpa_opencode_go_template.md) | LGPD-014 |
| D04 | Cloudflare | CDN/WAF/DNS/Edge | **TEMPLATE NOVO** | [dpa_cloudflare_template.md](dpa_cloudflare_template.md) | LGPD-018 |
| D05 | Hostinger (VPS) | Infraestrutura hosting | **TEMPLATE NOVO** | [dpa_hostinger_template.md](dpa_hostinger_template.md) | LGPD-019 |

---

## Status por DPA

### D01 — MiniMax (SQUAD D D01)
- **Status:** TEMPLATE PRONTO (16k bytes, 2026-06-23 20:12)
- **Diferencial:** processa PII **operacional do harness** (código-fonte com PII hardcoded)
- **Pendente:** assinatura Gustavo + DPO + contraparte MiniMax
- **Bloqueio:** LGPD-015

### D02 — Evolution API (SQUAD D D02)
- **Status:** TEMPLATE PRONTO (16k bytes, 2026-06-23 19:35)
- **Diferencial:** processa mensagens WhatsApp de **clientes finais** (texto, mídia, contatos)
- **Sede:** Brasil (BR — sem transferência internacional)
- **Pendente:** assinatura Gustavo + DPO + contraparte Evolution
- **Bloqueio:** LGPD-013

### D03 — Opencode-Go (SQUAD D D03)
- **Status:** TEMPLATE PRONTO (13k bytes, 2026-06-23 19:35)
- **Diferencial:** LLM gateway → DeepSeek-v4 flash para **clientes finais**
- **Sede:** Opencode (US) → DeepSeek (China) — transferência跨境 dupla
- **Mecanismo:** SCC EU-US + consent específico (LGPD art. 33, I+II)
- **Pendente:** assinatura Gustavo + DPO + contrapartes
- **Bloqueio:** LGPD-014

### D04 — Cloudflare (SQUAD D D04) ✨ NOVO
- **Status:** **TEMPLATE NOVO CRIADO 2026-06-24** (este sprint)
- **Diferencial:** processa apenas **metadata de borda** (IP truncado, UA, path) — não payload
- **Sede:** US — adequacy decision via EU-US Data Privacy Framework
- **Mecanismo:** SCC + Data Privacy Framework
- **Pendente:** assinatura Gustavo + DPO + contraparte Cloudflare
- **Bloqueio:** LGPD-018

### D05 — Hostinger VPS (SQUAD D D05) ✨ NOVO
- **Status:** **TEMPLATE NOVO CRIADO 2026-06-24** (este sprint)
- **Diferencial:** **infraestrutura física** — armazena TODOS os dados de negócio (clientes, audit log, PII)
- **Sede:** Brasil (datacenter São Paulo) — sem transferência internacional para storage
- **Painel admin:** Cyprus/EU — usar SCC Module 4
- **Pendente:** assinatura Gustavo + DPO + contraparte Hostinger
- **Bloqueio:** LGPD-019

---

## Quarterly Review

- **Processo:** [dpa_quarterly_review.md](dpa_quarterly_review.md) (4.9k bytes, 2026-06-24)
- **Frequência:** trimestral
- **Próxima revisão:** 2026-09-24

---

## Pendências para Gustavo

1. **Aprovar conteúdo** dos 5 templates (D01-D05) ✅ revisão técnica ok, ❌ revisão jurídica pendente
2. **Indicar DPO** (D24 SQUAD D — designação formal + contato público)
3. **Autorizar início de tratativas** com MiniMax, Evolution, Opencode-Go, Cloudflare, Hostinger
4. **Definir escritório de advocacia externo** para revisão LGPD (Doneda/Patricia Peck)

---

## Próximos passos SQUAD D (D6-D25)

Após D01-D05 assinados, próximas tarefas D6-D12 (direitos titular) e D13-D25 (LGPD ops):

- **D6** GET /cliente/{id}/historico (finalizar WIP)
- **D7** PATCH /cliente/{id} com audit
- **D8** POST /cliente/{id}/anonimizar
- **D9** GET /cliente/{id}/export JSON+CSV+PDF
- **D10** DELETE /cliente/{id} cascade
- **D11** POST /cliente/{id}/opar
- **D12** POST /cliente/{id}/opt-out-bot
- **D13-D25** logs, retenção, criptografia, auditoria ANPD, DPO, etc

---

**Modified by ZCode/Mavis — 2026-06-24 — Sprint 4 SQUAD D D01-D05 = 5/25 ✅**
