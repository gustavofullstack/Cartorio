# KNOWLEDGE_BASE

Base de conhecimento do agente — fontes, prioridade e política de atualização (2026-07-20).

## Fontes canônicas (ordem de prioridade)

1. `AGENTS.md` (raiz) + `.harness/AGENTS.md` — regras operacionais; vencem qualquer conflito.
2. `SUPER_PLANO_G9_100_TASKS.md` — plano ativo (10 squads × 10 tasks).
3. `PROMPT.MD` / `PROMPT.json` (v4.6.0) — contexto mestre da aplicação.
4. `PROMPT-2.MD` / `PROMPT-2.json` (v2.1) — camada de infraestrutura Easypanel/Swarm.
5. `docs/` — runbooks, ADRs, relatórios de bateria (ver `docs/TEST-REPORT.md`).
6. `.harness/memory/MEMORY.md` + `.brain/memory/` — lições cross-rein e de sessão.

## Domínio cartorário

- Tabela de emolumentos MG 2026 em `backend/app/services/emolumento.py` — única fonte de cálculo.
- Provimentos/CNJ, checklists de documentos e prazos em `cartorio-ai/cartorio/`.
- FAQ de atendimento (certidões, escrituras, reconhecimento de firma) em `channels/FAQ.md`.

## Regras de escrita no conhecimento

- PII nunca entra na base (CPF/RG/protocolo só mascarados — `app/services/pii.py`).
- Toda lição reutilizável → `.harness/memory/MEMORY.md` (commitada); fato de sessão → `.brain/memory/AAAA-MM-DD.md`.
- Não duplicar o que já está em git ou código; registrar só o não-óbvio.
- Freshness: fatos de infra/topologia revalidados a cada sessão (SSH probe bounded).

## Recuperação (RAG)

- Chunking e citações: `knowledge/CHUNKING.md`, `knowledge/CITATIONS.md`.
- Conflitos entre fontes: `knowledge/CONFLICT_RESOLUTION.md` — AGENTS.md > plano ativo > docs > memória.
