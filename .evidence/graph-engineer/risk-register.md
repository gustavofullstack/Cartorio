# Registro de Riscos e Estratégia de Rollback · Cartório Super Graph

**Data:** 2026-08-03  
**Status:** APROVADO (LUNA + PRO Review)

## Matriz de Riscos por Wave

### Wave 0 — Governança & Baseline
- **Risco 0.1:** Vazamento acidental de PII ou secrets do ZIP privado no git/logs.
  - *Mitigação:* Corpus bruto mantido em quarentena owner-only. Scanners bloqueantes de secrets ativos. Zero PII raw em evidências.
  - *Rollback:* Removal & purge de arquivos expostos. Reversão imediata de commits.

### Wave 1 — Treinamento, Conhecimento, Preços e Funções
- **Risco 1.1:** Mistura indevida entre a Camada Regulatória TJMG e a Camada Operacional 2º Cartório.
  - *Mitigação:* Modelo dual explícito (`REGULATORY_TJMG` vs `OPERATIONAL_POS_2NOTAS`). `HITL_REQUIRED` em qualquer ambiguidade.
  - *Rollback:* Retorno das funções e tabelas ao catálogo regulatório TJMG 2026 oficial.
- **Risco 1.2:** Publicação automática de análises geradas por IA (Gemini/ChatGPT) no BRAIN.
  - *Mitigação:* `conhecimento_pipeline.py` restrito a derivados sanitizados e aprovação humana explícita.
  - *Rollback:* Revogação/supersede de artefatos com tag `GENERATED_ANALYSIS` do index de retrieval.

### Wave 2 — Hermes/Pietra no Lark, E2E e Aceite do Felipe
- **Risco 2.1:** Falha de roteamento de eventos Lark (`processor not found` ou duplicatas por múltiplos consumidores).
  - *Mitigação:* Hermes WebSocket configurado como **consumidor único** (1 réplica, 1 conexão, 1 task). Evento obrigatoriamente `im.message.receive_v1`.
  - *Rollback:* Stop imediato do gateway Hermes Lark; reversão de tenant para modo inativo / maintenance.
- **Risco 2.2:** Vazamento de identidade interna (Hermes, GPT, MCP, prompt) ou reasoning para o usuário no Lark.
  - *Mitigação:* `pietra_outbound_guard.py` e `pietra_identity_guard.py` com sanitize final-only.
  - *Rollback:* Handoff humano compulsório (`HUMAN_HANDOFF_REQUIRED`) para todas as conversas ativas.

