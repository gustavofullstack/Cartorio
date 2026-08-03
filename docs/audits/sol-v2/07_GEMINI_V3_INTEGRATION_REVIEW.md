# Diretrizes de Revisão e Integração do Gemini V3

**Documento:** `docs/audits/sol-v2/07_GEMINI_V3_INTEGRATION_REVIEW.md`  
**Origem:** Gemini 3.6 Flash High (`/private/tmp/cartorio-gemini36-v3-remediation-*`)  

---

## 1. Critérios de Ingestão do Gemini V3

O resultado produzido em paralelo pelo Gemini 3.6 Flash High **não** é integrado de forma automática ou cega no repositório canônico. O processo segue o protocolo de segurança V2:

1. **Gate Exclusivo:** Ingestão autorizada somente após `python3 scripts/v3_completion_gate.py` retornar `PASS`.
2. **Revisão TERRA Independente:** A instância `TERRA-REVIEW` deve analisar diff a diff os commits produzidos pelo Gemini V3.
3. **Cherry-Pick Atômico:** Somente commits isolados com testes unitários associados e sem mutação de arquivos quarentenados podem ser incorporados via `git cherry-pick`.
4. **Resolução de Conflitos:** Qualquer colisão com trabalho do SOL V2 favorece o código com prova de teste real (`make test-fast`).
