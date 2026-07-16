# RIPD — Relatório de Impacto à Proteção de Dados Pessoais
**Cartório 2º Notas de Uberlândia** | **Versão:** 1.4 | **Atualizado:** 2026-07-16

> **Addendum v1.4:** integrações LobeChat + OpenClaw + LiteLLM + MiniMax +
> multicanal Telegram/WhatsApp/Chatwoot. Detalhe completo em
> [`docs/lgpd/RIPD_v1.4_ADDENDUM.md`](lgpd/RIPD_v1.4_ADDENDUM.md) (G6.C.T1).

## 1. Identificação do Controlador
- **Razão social**: 2º Serviço Notarial de Uberlândia
- **CNPJ**: XX.XXX.XXX/0001-XX
- **Endereço**: Av. XX, nº XXX, Centro, Uberlândia/MG
- **DPO (Encarregado)**: [nome + email + telefone — preencher antes do deploy final]
- **DPO designado por**: Gustavo Almeida (tableholder)

## 2. Descrição do Tratamento
- **Finalidade**: atendimento cartorário remoto via WhatsApp/Telegram/Web
- **Bases legais**: 
  - Execução de contrato (Art. 7º V)
  - Obrigação legal (Art. 7º II) — fé pública
  - Exercício regular de direitos (Art. 7º VI)
- **Categorias de dados**: nome, CPF, RG, telefone, email, dados do ato notarial
- **Titulares**: clientes que solicitam serviços notariais
- **Volume estimado**: 100-500 atendimentos/mês

## 3. Riscos Identificados
| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Vazamento de PII via LLM | Média | Alto | 3 camadas scrub (input/pre-LLM/output) |
| Acesso não autorizado | Baixa | Alto | Auth JWT + audit chain SHA256 + HMAC |
| Retenção excessiva | Média | Médio | Retenção 5y + job diário anonimização |
| Webhook malicioso | Baixa | Médio | HMAC signature + idempotência 24h |

## 4. Medidas de Mitigação (LGPD Art. 38)
- ✅ Audit log imutável (SHA256 chain + HMAC)
- ✅ PII scrubbing em 3 camadas (Pydantic + Sentry + log)
- ✅ Human-in-the-loop em ato jurídico
- ✅ Criptografia em trânsito (HTTPS + WSS) e repouso (Supabase at-rest)
- ✅ DPO designado
- ✅ Política de privacidade publicada
- ✅ Direito de acesso, correção, anonimização, portabilidade, oposição

## 5. Direitos do Titular (Art. 18)
- ✅ Confirmação de existência de tratamento — `/api/v1/lgpd/confirm`
- ✅ Acesso aos dados — `/api/v1/lgpd/access`
- ✅ Correção — `/api/v1/lgpd/correct`
- ✅ Anonimização, bloqueio ou eliminação — `/api/v1/lgpd/erase`
- ✅ Portabilidade — `/api/v1/lgpd/portability` (T064 implementado)
- ✅ Oposição — `/api/v1/lgpd/opposition` (T065 implementado)
- ✅ Não-automação de decisões — HITL mandatory

## 6. Plano de Resposta a Incidentes
- DPO notificado em <24h (LGPD Art. 48)
- ANPD notificada em <2 dias úteis se risco elevado
- Titulares notificados em <72h
- Audit log consultado para timeline
- Root cause + fix em Lesson MEMORY.md

## 7. Revisão Periódica
- Trimestral: DPO + cartorio-lgpd
- Anual: conselho / tableholder
- Ad-hoc: mudança de stack, novo canal, incidente

## 8. Addendum v1.4 — Novos canais e sub-processadores (2026-07-16)

Incluídos no tratamento (ver addendum completo):

| # | Tratamento | Sistema |
|---|---|---|
| T13 | UI agente cartório | LobeChat |
| T14 | Router multi-agent + skills | OpenClaw Gateway |
| T15 | Fallback multi-provider | LiteLLM |
| T16 | LLM coding/ops | MiniMax-M3 (DPA pending) |
| T17 | Canais titular | Telegram + WhatsApp/Evolution |
| T18 | Handoff humano HITL | Chatwoot |

**Medidas extras v1.4:** scrub 3 camadas em todo caminho LLM; idempotência
Redis em 21/21 webhooks N8N; dead-man switch audit → Telegram GRUPO PIETRA;
radar expanded (DNS/Traefik/SSH/disk); inventory 18 campos PII.

**HOLD sign-off DPO:** DPA MiniMax + DNS 3 A records + tokens LobeChat/Telegram.

---

**Modified by Gustavo Almeida + cartorio-lgpd — 2026-07-16 (G6.C.T1 Wave 13)**
