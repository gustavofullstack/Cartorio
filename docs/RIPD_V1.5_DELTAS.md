# RIPD v1.5 — Deltas vs v1.4 (2026-07-18)

**Owner:** `cartorio-lgpd`  
**TASK:** G8.18.T3 (Wave 48)  
**Comparação:** RIPD v1.4 (`docs/ripd.md` 2026-07-16 + `docs/lgpd/RIPD_v1.4_ADDENDUM.md`)
↔ RIPD v1.5 (`docs/RIPD_CARTORIO_V1.5_2026-07-18.md`)  
**Status LGPD-REVIEW-PENDING:** sim (DPO assina antes de publicar).

---

## 1. Visão geral das mudanças

| Categoria | v1.4 | v1.5 | Delta |
|---|---|---|---|
| Estrutura | 8 seções (1.Controlador, 2.Tratamento, 3.Riscos, 4.Mitigação, 5.Art.18, 6.Incidentes, 7.Revisão, 8.Addendum) | **10 seções** (inclui 3.Avaliação Necessidade/Proporcionalidade + 9.Aprovação + 10.Anexos) | +2 seções |
| Riscos catalogados | 4 riscos (vazamento LLM, acesso, retenção, webhook) | **5 riscos** (+ risco de **segredo vazado em código**) | +1 risco |
| Salvaguardas Art. 18 | 7 endpoints | 7 endpoints + Art. 20 revisão automática (`/api/v1/lgpd/v2/review`) | +1 endpoint alpha |
| Medidas de mitigação | 8 itens | 11 itens (+ RLS 100%, secrets scanning CI, dead-man's-switch + retenção scheduler, radar expandido) | +3 itens |
| Plano resposta | 6 bullet points | Estruturado em 7 etapas (detecção/resposta/DPO/ANPD/titulares/audit/lesson) | refinado |
| Aprovação | Implícita no rodapé | Tabela formal (DPO / Controlador / Owner técnico) com status | formalização |
| Anexos | Addendum único | 8 anexos (Lições + LGPD-016 + versões histórica) | +7 anexos |

## 2. Seções adicionadas em v1.5

### §3 — Avaliação de Necessidade e Proporcionalidade
- Princípio da necessidade (Art. 6º III): coleta mínima.
- Princípio da adequação (Art. 6º I): finalidade legítima.
- Princípio da finalidade (Art. 6º IV): vedada reutilização.
- Princípio da livre acesso (Art. 6º II): titular pode consultar/corrigir/portabilizar.

**Justificativa**: v1.4 misturava este conteúdo dentro de §4 (Riscos);
v1.5 separa formalmente conforme modelo ANPD.

### §9 — Aprovação formal
- Tabela com DPO (PENDING), Controlador (tableholder), Owner técnico.
- Bloqueio explícito de publicação até assinatura do Encarregado.

**Justificativa**: atende Art. 38 §2º (responsabilização) e
facilita auditoria externa (ANPD + Tribunal de Contas).

### §10 — Anexos
- 8 referências cruzadas (Lições 246/216, LGPD-016, RIPDs históricos,
  DPA templates, AUDITORIA_BLOCKERS).

**Justificativa**: rastreabilidade exigida em conformidade.

## 3. Riscos adicionados em v1.5

### §4.4 — Risco de segredo vazado em código (NOVO)
- **Probabilidade**: Média.
- **Impacto**: Alto.
- **Mitigação**: Secrets scanning CI (`scripts/check_no_literal_keys.py`,
  G8.14.T3) bloqueia patterns `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`,
  `gAAAAA`, `ghp_*`, `xox*`, `AKIA*`, `AIza*` no PR.
- **Resíduo**: Baixo.

**Justificativa de inclusão**: G8.14.T3 (Wave 48) implementou o gate
de CI que v1.4 não cobria; precisa aparecer no RIPD como salvaguarda
ativa para evitar regressão.

### §4.5 — Risco de quebra do canal (NOVO)
- **Probabilidade**: Média.
- **Impacto**: Médio.
- **Mitigação**: Telegram wrap + retry/backoff; Evolution parser
  aceita ambos formatos (legado + aninhado); HMAC + idempotência.
- **Resíduo**: Baixo.

**Justificativa de inclusão**: incidentes Wave 47-48 destacaram
3 vetores (Telegram 502, Evolution parser ambíguo, webhook replay).

## 4. Endpoints adicionados em v1.5 (Tabela Art. 18)

| Direito | v1.4 | v1.5 |
|---|---|---|
| Revisão de decisão automatizada | ❌ não documentado | ✅ `/api/v1/lgpd/v2/review` (Art. 20) |

**Justificativa**: API v2(alpha) já estava implementada mas não constava
em v1.4. Sunset declarado: 2027-12-31.

## 5. Medidas de mitigação adicionadas em v1.5

| Medida | Onde | Origem |
|---|---|---|
| RLS 100% tabelas com PII | `infra/supabase/schema.sql` | G8.Wave 44 |
| Secrets scanning CI | `scripts/check_no_literal_keys.py` | G8.14.T3 (Wave 48) |
| Dead-man's-switch audit | `app/main.py` lifespan (15min) | G6 |
| LGPD retenção scheduler | `app/main.py` lifespan (03:00 BRT) | G6 |
| Radar expandido | `/health/radar/expanded` | G6 |

## 6. Pontos explicitamente NÃO alterados

- Art. 6º bases legais primárias (serviço público delegado + execução
  contrato + obrigação legal).
- Art. 7º hipóteses (consentimento para marketing opcional).
- Art. 16 retenção mínima 5 anos.
- Art. 18 endpoints principais v1 (confirm/access/correct/erase/
  portability/opposition).
- Categorias de dados (não sensíveis — sem religião, saúde, etc.).
- DPO placeholder (aguarda definição antes de publicação).
- Inventário de sub-processadores (8 DPAs já em `docs/lgpd/dpa_*.md`).

## 7. Pendências para DPO sign-off

1. **DPO placeholder** (`[definir]`) — definir nome + email + telefone.
2. **HOLD sign-off** — DPA MiniMax (`docs/lgpd/dpa_minimiz_template.md`)
   ainda sem `signature_2`.
3. **Publicação externa** — bloqueada até coleta de assinatura.
4. **CNPJ/Endereço** — preencher antes do go-live final (não bloqueia
   revisão técnica).

## 8. Cross-references

- v1.4 base: `docs/ripd.md` (2026-07-16) e `docs/lgpd/RIPD_v1.4_ADDENDUM.md`.
- v1.3 histórico: `docs/archive/ripd_v1.3_2026-06-23.md`.
- v1.0 detalhado: `docs/ripd-cartorio-2026-06-25.md`.
- LIÇÃO 246: `.harness/memory/lesson-246-g8-wave-48-direct-master-2026-07-18.md`.
- LIÇÃO 250: `.harness/memory/lesson-250-g8-14-t3-secrets-scanning-2026-07-18.md`.

---

**Modified by Gustavo Almeida + cartorio-lgpd — 2026-07-18 (G8.18.T3)**
