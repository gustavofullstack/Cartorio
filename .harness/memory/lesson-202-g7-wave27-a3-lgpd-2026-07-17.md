# Lesson 202 — G7 Wave 27 A3 LGPD: DPA MiniMax READY_TO_SIGN + Privacy Policy v3 (2026-07-17)

Type: project + reference  
Agent: cartorio-lgpd  
Tasks: **G7.19.T2**, **G7.19.T3**

## Deliverables

| Task | Artifact | Status agent | Residual SUI |
|------|----------|--------------|--------------|
| G7.19.T2 | `docs/DPA_MINIMAX_READY_TO_SIGN_G7.md` | READY_TO_SIGN package | Assinatura bilateral + PDF + flag env |
| G7.19.T2 | `docs/LLM_DPA_MATRIX.md` row MiniMax | **READY_TO_SIGN** | → SIGNED após assinar |
| G7.19.T2 | `docs/DPA_FLOW_REPORT_2026-07-16.md` + `docs/lgpd/DPA_INDEX.md` | ready_to_sign | Gustavo assina |
| G7.19.T3 | `docs/PRIVACY_POLICY_V3_G7.md` | draft publicável PT-BR | Placeholders DPO/CNPJ |
| G7.19.T3 | `docs/PRIVACY_POLICY_V3_PUBLISH_CHECKLIST_G7.md` | HOLD-GUSTAVO site | curl 200 + bot hash |

## Regras aplicadas

- **Sem assinatura falsa** — blocos de assinatura em branco; status READY_TO_SIGN ≠ SIGNED.
- **No raw CPF** no escopo MiniMax: categorias limitadas a inputs scrubbed (pii 3 camadas).
- Privacy v3 cobre controlador, multi-canal, bases legais, Art. 18, retenção, LLMs, DPO, cookies.
- Publicação de site e assinatura de DPA são **SUI** — mesmo padrão de waves anteriores (runbook [x] + residual HOLD).

## Cross-refs

- Template longo: `docs/lgpd/dpa_minimax_template.md`
- RIPD T16: `docs/lgpd/RIPD_v1.4_ADDENDUM.md`
- D23 v3 técnico: `docs/lgpd/policy/D23-site-privacy-policy-v3.md`
- Tracker: `scripts/dpa_sign_flow.py` (atualizar quando assinar de verdade)

## Anti-patterns

1. Marcar MiniMax como **SIGNED** só porque o pacote READY existe.  
2. Publicar política com placeholders `[NOME_DO_DPO]` no HTML público.  
3. Enviar CPF raw a MiniMax “porque o DPA está pronto”.  
4. Confundir DPA harness-only do template antigo com finalidade **bot multi-canal** do pacote G7 (pacote G7 é a fonte para assinatura).

**Modified by Gustavo Almeida + cartorio-lgpd — G7 Wave 27 A3**
