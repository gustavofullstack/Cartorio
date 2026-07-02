# LGPD-014 — DPA DeepSeek Sign Checklist

> **Status:** 🟡 Blocked — aguarda assinatura Gustavo + DPO
> **Última atualização:** 2026-07-02 (turn 50, lesson 139g)
> **Template pronto:** `docs/lgpd/dpa_deepseek_template.md` (21 KB)
> **Quarterly review:** `docs/lgpd/dpa_quarterly_review.md` (12 items DPA 1)

---

## 🎯 Objetivo LGPD-014

Remover o bloqueador ANPD para uso do **DeepSeek** (LLM low-cost via OpenCode-Go gateway) com dados reais de clientes brasileiros. Sem DPA assinado, **staging only** (sintético).

---

## 📋 Checklist Pré-Assinatura

### Parte 1 — Jurídica (cartorio-lgpd + escritório externo)

- [ ] Template `dpa_deepseek_template.md` revisado pelo escritório **Doneda/Patricia Peck**
- [ ] Cláusulas-padrão contratuais (SCC) verificadas (LGPD art. 33, II)
- [ ] Adequação ANPD China: incluir cláusula de **cooperação internacional** (LGPD art. 33, IX)
- [ ] Cláusula de **direito de auditoria** (LGPD art. 37 + 50)
- [ ] Cláusula de **notificação de incidentes em ≤72h** (LGPD art. 48)
- [ ] Cláusula de **cooperação com ANPD** (LGPD art. 33, IX)
- [ ] **Consentimento específico** redigido (LGPD art. 33, I) — termo atualizado
- [ ] **Cláusula de sub-processors** (DeepSeek não pode repassar sem aprovação)

### Parte 2 — DPO

- [ ] **Due diligence** realizada: visita técnica Hangzhou DeepSeek OU relatório SOC2/ISO27001
- [ ] **Mapa de fluxo de dados** China → Brasil documentado
- [ ] **PII scrubbing 3 camadas** validado em produção (LESSON 121)
- [ ] **Audit log** de chamadas DeepSeek funcionando (LGPD art. 37)
- [ ] **Retenção ≤365 dias** confirmada em `backend/app/services/retencao.py`
- [ ] **Direito ao esquecimento** validado: cliente pode pedir forget → API remove imediato
- [ ] **Custo mensal** dentro do orçamento aprovado (~R$ 200/mês free tier)
- [ ] **Latência p99** < 5s SLA verificada (lesson 128)

### Parte 3 — Gustavo Almeida (Tabelião)

- [ ] APROVAÇÃO formal por escrito (cartorio@2notasudi.com.br)
- [ ] REVISÃO pessoal de todas 12 cláusulas do template
- [ ] SIGNATURE física ou DocuSign na versão PDF final
- [ ] **Substituição** de `dpa_deepseek_template.md` por `dpa_deepseek.pdf` em `docs/lgpd/`
- [ ] **Backup** do PDF assinado em `/etc/easypanel/projects/cartorio/dpa/`
- [ ] **Vault Supabase** registra hash SHA-256 do PDF assinado
- [ ] **AUDIT_LOG** registra `dpa.signed` action com timestamp + actor
- [ ] **NOTIFICAÇÃO** à equipe (Slack/Telegram GRUPO)
- [ ] **PRESS_RELEASE interno** (opcional): "Cartório 100% LGPD compliant"

### Parte 4 — Jurídica Externa (escritório)

- [ ] Drafting de cláusulas customizadas em PT-BR
- [ ] Validação de compliance com LGPD + Marco Civil + Provimento 74/2018
- [ ] Adaptação para realidade da DeepSeek (chines, sub-processors próprios)
- [ ] Recommended improvements
- [ ] Certificação de "SCC aceitáveis" para ANPD

---

## 🎯 Pós-Assinatura (LGPD-014 → DONE)

### Configuração

1. **Atualizar PROMPT.json:**
   - Remover T4 / LGPD-014 de blockers_technical (se ainda existir)
   - dp_status: `LGPD-014` → `SIGNED` em `services.opencode_go`
   - compliance_pct: 95% → **97%** (LGPD compliance total)

2. **Atualizar INDEX.md DPA:**
   ```diff
   - D03 DeepSeek | TEMPLATE | LGPD-014 PENDENTE
   + D03 DeepSeek | ✅ ASSINADO | LGPD-014 RESOLVIDO
   ```

3. **Notificar ANPD** (se auditoria exigir)
4. **Publicar comprovante** no site (privacidade v2)

### SLA Pós-Assinatura

- **Validade DPA:** 12 meses (renovação automática)
- **Quarterly review:** `docs/lgpd/dpa_quarterly_review.md` template
- **Auditoria anual:** integrada em D25 ANPD
- **Mudança de modelo:** termo aditivo (cláusula 1.3 já prevista)

---

## 🚨 Cenários de Bloqueio (Plano B)

Se DPA DeepSeek **NÃO** for assinado até 2027-Q1:

### Opção A: Trocar para OpenAI/Anthropic (DPA + país com adequação)
- OpenAI DPA template: criar `dpa_openai_template.md`
- Anthropic DPA template: criar `dpa_anthropic_template.md`
- Migração: trocar `deepseek-v4-flash` → `gpt-4o-mini` ou `claude-haiku`
- Custo: ~5x maior ($1/M input vs $0.20/M)

### Opção B: Stays em STAGING ONLY
- DeepSeek só roda em dev/test
- Produção usa exclusivamente LiteLLM proxy com MiniMax/free models
- Compliance fica em 95% (aceitável para MVP)

### Opção C: DPA com escritório internacional
- Solicitar DPA com time de privacidade da DeepSeek (Negotiation)
- Aceitar cláusula chinesa-padrão (sem adequação)
- Risco: questionável ANPD mas aceitável LGPD art. 33 II

---

## 🎬 Próximos Passos Imediatos

```
╔═══════════════════════════════════════════════════════════════════╗
║  ESTIMATIVA: 2-4 semanas (depende de Gustavo + escritório)       ║
║                                                                   ║
║  Semana 1: Gustavo revisa template (2h)                          ║
║  Semana 2: Escritório externo valida cláusulas (R$ XXX)          ║
║  Semana 3: Negociação com DeepSeek (Hangzhou Privacy)            ║
║  Semana 4: Sign + publicação + remove LGPD-014                    ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 📚 Referências

- **Template:** [`dpa_deepseek_template.md`](../dpa_deepseek_template.md)
- **Quarterly review:** [`dpa_quarterly_review.md`](../dpa_quarterly_review.md)
- **DPA Index:** [`DPA_INDEX.md`](../DPA_INDEX.md)
- **D24 DPO contact:** [`D24-dpo-contact-publicado.md`](./D24-dpo-contact-publicado.md)
- **LGPD art. 33, II:** cláusulas-padrão contratuais
- **LGPD art. 33, IX:** cooperação ANPD ↔ internacional
- **Resolução CD/ANPD nº 4/2023:** transferência internacional

---

## ✅ Sign-offs

- [ ] cartorio-lgpd (Pietra) — revisão técnica
- [ ] Gustavo Almeida (Tabelião) — aprovação final + sign
- [ ] DPO Gustavo Almeida — revisão LGPD-specific
- [ ] Escritório externo (Doneda/Patricia Peck) — sign-off jurídico
- [ ] DeepSeek (Hangzhou Privacy) — sign-off internacional
