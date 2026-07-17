# G7 — Definition of Ready / Definition of Done (G7.23.T2)

Scrum master lightweight para o super plano 100 tasks.

---

## Definition of Ready (antes de pegar a task)

- [ ] Task ID `G7.XX.TY` no `SUPER_PLANO_G7_100_TASKS.md`
- [ ] Rein owner claro (`cartorio-dev|n8n|lgpd|sre`)
- [ ] Critério de aceite em 1–3 bullets mensuráveis
- [ ] Dependência SUI listada **ou** marcada N/A
- [ ] Não toca `audit*`/`pii*` sem plan de review `cartorio-lgpd`
- [ ] Ambiente local: `uv sync` + `.env` template ok

---

## Definition of Done (wave de 4 agents)

- [ ] Código/docs/tests commitáveis (ou explicitamente HOLD-SUI)
- [ ] `ruff` + testes da área **pass**
- [ ] Tipagem: sem `raise Exception(` (gate `scripts/check_no_bare_exception.py`)
- [ ] Conventional Commit + `Modified by Gustavo Almeida` se commitar
- [ ] `PROGRESS.md` append da wave
- [ ] Lesson em `.harness/memory/` se lição cross-rein
- [ ] `SUPER_PLANO_G7_100_TASKS.md` checkbox `[x]`
- [ ] `make g7-validate` não piorou (FAIL local = bloqueia; HOLD prod SUI ok)

---

## MVP cut-line (G7.23.T4)

**In MVP:** emolumento consult · protocolo status read · handoff humano · audit/PII · Telegram/WA receive when SUI done  

**Out of MVP:** certidão auto-emit · pagamento · multi-cartório SaaS · BI full

---

## Cadência de wave

1. Orquestrador escolhe 4 tasks (1 por rein quando possível)  
2. Analyze → test → fix → document → memory  
3. `make g7-validate`  
4. Próxima wave até 100/100  

---

**Modified by Gustavo Almeida — G7 Wave 16 (scrum)**
