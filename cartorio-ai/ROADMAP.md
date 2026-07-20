# cartorio-ai · ROADMAP

## Fase 0 — CONCLUÍDA (2026-07-20)
- [x] Scaffold do diretório com layout completo (placeholders de 1 linha).
- [x] **Núcleo de 15 arquivos** preenchido com conteúdo real do projeto (G9.11.T1/T2, G9.12.T1–T3):
  raiz institucional + `brain/BRAIN.md` + `identity/SOUL.md`/`IDENTITY.md` +
  `planning/GOALS.md`/`TASKS.md` + `memory/MEMORY.md` + `security/SECURITY.md` + `compliance/CNJ.md`.

## Fase 1 — Núcleo guardado (G9, waves 62+)
- [ ] G9.11.T4 — Gate CI: arquivo-núcleo não pode regredir a placeholder.
- [ ] G9.12.T4 — Sync quinzenal `AGENTS.md` raiz → `cartorio-ai/AGENTS.md` (script + diff no CI).

## Fase 2 — Expansão por prioridade (pós-G9)
Ordem sugerida de promoção de placeholders a conteúdo real (cada item = 1 task própria):

1. **Operação diária** — `operations/`, `recovery/`, `observability/`: runbooks que hoje vivem em
   `../docs/` (espelhar e linkar, nunca duplicar).
2. **Segurança profunda** — `security/THREAT_MODEL.md`, `security/SECRETS.md`,
   `security/KEY_MANAGEMENT.md`, `guardrails/`: derivar de `security/SECURITY.md` + LGPD.
3. **Compliance LGPD completo** — `compliance/LGPD.md`, `compliance/RETENTION.md`,
   `compliance/DPIA.md`, `compliance/DATA_INVENTORY.md`: derivar do RIPD e dos services `lgpd*`.
4. **Canais** — `channels/`: Telegram (webhook+debounce), WhatsApp/Evolution (dual-format),
   Chatwoot (handoff HITL), Web.
5. **Cérebro operacional** — demais `brain/*` (DELEGATION, QUALITY_GATE, CONTEXT_BUDGET...):
   codificar práticas do `.harness/`.
6. **Restante** — `agents/`, `autonomy/`, `commands/`, `contracts/`, `evaluation/`, `events/`,
   `evolution/`, `governance/`, `hooks/`, `integrations/`, `knowledge/`, `mcp/`, `models/`,
   `prompts/`, `runtimes/`, `skills/`, `tools/`, `workflows/` (~350 arquivos).

## Critérios de promoção (placeholder → real)
1. Conteúdo derivado de fonte real (código, AGENTS.md, lessons, fatos validados) — nunca genérico.
2. Sem valores de segredos; PII sempre como classe de dado, nunca exemplo real.
3. Link de volta para a fonte (arquivo de código ou doc canônico).
4. Checkbox atualizado aqui e entrada em `memory/MEMORY.md`.

**Não criar os ~400 arquivos de uma vez** — decisão registrada em 2026-07-20 (G9.11.T3):
volume sem uso vira ruído; promover por demanda das squads.
