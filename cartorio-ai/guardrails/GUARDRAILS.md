# GUARDRAILS

Guardrails de segurança e conformidade (2026-07-20).

## Hard limits (fail-closed)

1. **PII nunca sai raw** — CPF/RG/protocolo/escritura mascarados antes de qualquer LLM pública, log, Sentry ou storage externo. 3 camadas: validators Pydantic → `pii.py` pre-LLM → scrub de output.
2. **Bot nunca decide ato jurídico** — isenção, urgência, validação, emissão: sempre HITL (`DRAFT` → escrevente).
3. **Audit append-only** — edição retroativa quebra a cadeia e dispara alerta (dead-man's-switch 15min).
4. **Segredos nunca literais** — checker bloqueia `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`, `gAAAAA`, `ghp_*`, `xox*`, `AKIA*`, `AIza*`, hex-64. Opt-out exige `# noqa: ALLOW_KEY_FALLBACK`.
5. **Sem rotação de chaves** sem ordem expressa do dono.

## Soft limits (degradam com aviso)

- Confiança LLM baixa → resposta conservadora + sugestão de handoff.
- Rate limit próximo do teto → degradação graceful (fail-open se Redis cair).
- Latência LLM > 45s → timeout, próximo slot da fallback chain; usuário recebe mensagem de espera.

## Controle de alucinação

- Respostas de emolumento/prazo/documento só a partir de dados de domínio (`emolumento.py`, checklists) — nunca de memória do LLM.
- Canary tokens em testes: se o LLM ecoar PII mascarada na entrada, o teste falha.
- Validação de saída e política de recusa em `guardrails/OUTPUT_VALIDATION.md` / `guardrails/REFUSAL_POLICY.md`.

## Disclaimers obrigatórios

- Toda orientação jurídica carrega disclaimer de não-substituição de análise do escrevente.
- Estimativa de emolumento: "valor sujeito a conferência".
