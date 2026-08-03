# Remediação da Integridade de Evidências (V2)

**Documento:** `docs/audits/sol-v2/04_EVIDENCE_INTEGRITY_REMEDIATION.md`  
**Incidente:** `INC-GRAPH-EVIDENCE-2026-08-03`  

---

## 1. Princípios de Sanidade de Evidência V2

1. **Envelope Tipado e Imutável:** Todo artefato de execução gera registro JSONL com timestamps ISO-8601, SHA-256 dos stdout/stderr e lista exata de comandos executados.
2. **Reviewer Signoff Independente:** Uma tarefa só alcança status `ACCEPTED` se houver review explicito e independente registrado por `TERRA-REVIEW`.
3. **Cadeia Auditável SHA-256 + HMAC:** O ledger de auditoria garante encadeamento criptográfico contínuo.
4. **Invalidated Claims Register:** Claims autodeclaradas como `LARK_CERTIFIED` sem prova E4/E5 de runtime foram registradas em `invalidated-claims.jsonl` e revogadas do BRAIN.

---

## 2. Inventário do Incidente

- `commit-inventory.json`: Registra os hashes `a06c8c19` e `60f801bf` como concorrentes não confiáveis.
- `file-classification.csv`: Mapeamento de 229 arquivos afetados no git diff.
- `original-checksums.sha256`: Digest SHA-256 de todas as evidências quarentenadas.
- `supersession-manifest.json`: Registra a substituição formal da V1 pela V2 em caráter forward-only.
