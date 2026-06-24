# DPA Quarterly Review Checklist

> **Revisao trimestral dos DPAs (Data Processing Agreements) do Cartorio.**
> Frequencia: a cada 3 meses (LGPD art. 33 + boas praticas).
> Owner: DPO (Gustavo Almeida) + cartorio-lgpd rein.
> Proxima revisao: 2026-09-24.

## DPA 1: Opencode-Go (DeepSeek-v4-flash)

- [ ] **DPA assinado** por ambas as partes (Opencode + Cartorio)?
- [ ] **Data flow documentado** - China -> Brazil? (LGPD art. 33)
- [ ] **Sub-processors listados** - Opencode-Go tem outros sub-processors?
- [ ] **Adequacao ANPD** - China NAO tem adequacy (ANPD ainda nao publicou lista)
- [ ] **SCCs (Standard Contractual Clauses)** incluidas? (LGPD art. 33 II + 33 IV)
- [ ] **Audit log de chamadas LLM** funciona? (LGPD art. 37)
- [ ] **PII scrubbing 3 camadas** ativo? (LGPD art. 6 VIII)
- [ ] **Retencao 365 dias** configurada? (LGPD art. 16)
- [ ] **Direito ao esquecimento** via API funciona? (LGPD art. 18 VI)
- [ ] **Incidentes reportados** nos ultimos 90 dias? (LGPD art. 48)
- [ ] **Custo mensal** dentro do orcamento aprovado?
- [ ] **Latencia p99** < 5s SLA?

**Status atual**: Template pronto em `docs/lgpd/dpa_opencode_go_template.md`. NAO ASSINADO.

## DPA 2: Evolution API (WhatsApp BR)

- [ ] **DPA assinado**?
- [ ] **Sub-processors** (Meta Platforms/WhatsApp) documentados?
- [ ] **Retencao de logs** 90 dias (meta WhatsApp) ou configurado outro?
- [ ] **Webhook URL** seguro (HTTPS + HMAC)?
- [ ] **PII scrubbing** no payload antes de enviar para API?
- [ ] **Audit log** de todas as mensagens (LGPD art. 37)?
- [ ] **Rate limit** (Evolution API: 100 req/min)?
- [ ] **LGPD-016 output scrub** no response?

**Status atual**: Template pronto em `docs/lgpd/dpa_evolution_api_template.md`. NAO ASSINADO.

## DPA 3: MiniMax (LLM)

- [ ] **DPA assinado**?
- [ ] **Sub-processors** (DeepSeek? Anthropic? OpenAI?)?
- [ ] **Data flow** MiniMax -> ? -> Brasil
- [ ] **Adequacao** pais onde esta o data center?
- [ ] **Custo mensal** dentro do orcamento?

**Status atual**: Template em `docs/lgpd/dpa_minimax_template.md`. NAO ASSINADO.

## DPA 4: Supabase (Postgres + Storage)

- [ ] **DPA assinado**?
- [ ] **Sub-processors** listados (Kong, GoTrue, PostgREST, Storage)?
- [ ] **Encryption at-rest** habilitado? (Sprint 4+ - P1.BE.1)
- [ ] **RLS** ativo em TODAS as tabelas?
- [ ] **Backup automatico** configurado (Sprint 2 - 30 dias)?
- [ ] **Replicacao geografica** configurada? (LGPD art. 33 - transferencia internacional NAO)

**Status atual**: NAO EXISTE DPA com Supabase. Self-hosted no Brasil = LGPD-friendly.

## DPA 5: Hostinger (VPS Easypanel)

- [ ] **Contrato de hospedagem** revisado (LGPD art. 33)?
- [ ] **Data center** no Brasil?
- [ ] **Backup** da VPS (Easypanel auto)?
- [ ] **Acesso SSH** registrado + auditado?

**Status atual**: NAO FORMALIZADO.

## DPA 6: N8N (workflows self-hosted)

- [ ] **Self-hosted** = sem DPA externo (OK)
- [ ] **Credentials** encriptados (N8N has built-in)?
- [ ] **Audit log** de execucao de workflows?
- [ ] **Backup** de workflows (Sprint 2 - infra/n8n-workflows/*.json)?

**Status atual**: Self-hosted, OK.

## DPA 7: OpenClaw Gateway

- [ ] **Self-hosted** = sem DPA externo (OK)
- [ ] **Persona files** (SOUL.md, IDENTITY.md) atualizados?
- [ ] **Thinkings** configurados adaptativamente?

**Status atual**: Self-hosted, OK.

## DPA 8: Tailscale (rede privada)

- [ ] **DPA assinado**?
- [ ] **Encryption** end-to-end ativo?
- [ ] **Audit log** de quem conectou?

**Status atual**: NAO FORMALIZADO (mas Tailscale e' zero-trust, LGPD-friendly).

## DPA 9: Easypanel (deploy)

- [ ] **Contrato** revisado?
- [ ] **API key** rotacionada? (NAO - Gustavo + ZCode unicos com acesso)
- [ ] **Logs** de deploy retidos por quanto?

**Status atual**: NAO FORMALIZADO.

## DPA 10: Cloudflare (CDN/WAF)

- [ ] **DPA assinado**?
- [ ] **Logs** de WAF retidos por quanto?
- [ ] **WAF rules** revisadas trimestralmente?

**Status atual**: NAO FORMALIZADO.

---

## Resumo executivo

| DPA | Status | Prioridade | Owner |
|---|---|---|---|
| Opencode-Go (DeepSeek) | Template pronto, NAO ASSINADO | P0 | DPO + Juridico |
| Evolution API | Template pronto, NAO ASSINADO | P0 | DPO + Juridico |
| MiniMax | Template pronto, NAO ASSINADO | P1 | DPO + Juridico |
| Supabase | Self-hosted (sem DPA) | - | - |
| Hostinger | NAO FORMALIZADO | P2 | Juridico |
| N8N | Self-hosted | - | - |
| OpenClaw | Self-hosted | - | - |
| Tailscale | NAO FORMALIZADO | P2 | DPO |
| Easypanel | NAO FORMALIZADO | P2 | Juridico |
| Cloudflare | NAO FORMALIZADO | P2 | DPO |

## Acoes imediatas (P0/P1)

1. **DPA Opencode-Go**: Gustavo (DPO) + Juridico negociar e assinar (BLOQUEIO ATIVO ate assinatura)
2. **DPA Evolution API**: Gustavo (DPO) + Juridico (mais simples, BR)
3. **DPA MiniMax**: Gustavo (DPO) + Juridico

## Referencias

- LGPD art. 33 (transferencia internacional): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- Templates DPA: `docs/lgpd/dpa_*_template.md`
- RIPD: `docs/ripd.md`

Modified by ZCode/Mavis - 2026-06-24
