# G8 — Definition of Ready / Definition of Done (G8.16.T2)

Scrum / honesty gate para o super plano G8 (100 tasks · 25 squads).

**Fonte de metas:** [`SUPER_GOALS_G8.md`](../SUPER_GOALS_G8.md)  
**Fonte de tasks:** [`SUPER_PLANO_G8_100_TASKS.md`](../SUPER_PLANO_G8_100_TASKS.md)  
**Precedente G7:** [`docs/G7_DOR_DOD.md`](G7_DOR_DOD.md)  
**Lessons de honestidade:** 216 (reset), 217–219 (waves reais)

---

## Honesty Gate (obrigatório — Lesson 216+)

Um checkbox `[x]` em `SUPER_PLANO_G8_100_TASKS.md`, bloco “COMPLETED” em `PROGRESS.md`, ou % em `SUPER_GOALS_G8.md` **só é válido** se existir **evidência tripla** (ou equivalente documentado):

| Pilar | O que conta | O que **não** conta |
|-------|-------------|---------------------|
| **1. Artefato** | Código, script, doc ou config **commitável** no path real da task | Checkbox de orquestrador sem arquivo; “Gates Status: All tests passed” genérico |
| **2. Testes / verificação** | `pytest` da área **PASS** (ou gate Makefile/script com exit 0 e relatório path) | Afirmação sem comando/output; suite inventada |
| **3. Lesson / progress honesto** | Lesson em `.harness/memory/` se mudança crítica **ou** append honesto em `PROGRESS.md` com paths + contagem de testes | Tick em massa S05–S25 paper; flip de 100/100 sem commits |

**Regra de ouro:** se não dá para apontar `path` + `comando de teste` + (lesson **ou** progress com IDs), a task permanece `[ ]` ou `[~]` (HOLD-SUI).

**HOLD-SUI** é honesto: depende de prod/DNS/Tailscale/Chatwoot live. Não vira `[x]` até evidência live ou script/report de SUI.

---

## Definition of Ready (antes de pegar a task)

Checklist **antes** do agent/orquestrador iniciar `G8.XX.TY`:

- [ ] Task ID `G8.XX.TY` existe em `SUPER_PLANO_G8_100_TASKS.md` e ainda está `[ ]` ou `[~]` com motivo
- [ ] Rein owner claro: `cartorio-dev` | `cartorio-n8n` | `cartorio-lgpd` | `cartorio-sre` (brain só orquestra)
- [ ] Critério de aceite em **1–3 bullets mensuráveis** (número, path, comando, ou comportamento observável)
- [ ] Dependência SUI listada **ou** marcada N/A (DNS, Tailscale, Chatwoot live, Evolution, Cloudflare)
- [ ] Escopo não toca `audit*` / `pii*` / HMAC / RLS sem plano de review `cartorio-lgpd`
- [ ] Ambiente local pronto: `make install` (ou `uv sync` em `backend/`) + `.env` a partir de `.env.example` (sem secrets no repo)
- [ ] Conflito multi-agent: arquivos alvo identificados; se wave paralela no mesmo path, combinar API única **antes** de escrever
- [ ] PYTHONPATH hermético: preferir `cd backend && unset PYTHONPATH && .venv*/bin/python -m pytest …` (Lesson 219)

**Não Ready se:** aceite só “melhorar X”, rein ambíguo, ou task já marcada `[x]` sem evidência (reset honesty primeiro).

---

## Definition of Done (task individual)

Uma task G8 só fecha (`[x]`) quando **todos** os itens aplicáveis passam:

### A. Entrega

- [ ] Artefato no repo (código/docs/tests/scripts/config) alinhado ao texto da task
- [ ] Sem secrets/chaves/PII raw em diffs (scanner local / review)
- [ ] Tipagem: type hints em APIs públicas; sem `raise Exception(` genérico (`make bare-exception` / `scripts/check_no_bare_exception.py` se a área for Python app)
- [ ] HITL / LGPD: bot não decide sozinho em ação jurídica; PII mascarada antes de LLM/log externo

### B. Qualidade (gates locais)

Rodar da **raiz** ou `backend/` conforme Makefile:

- [ ] Lint da área: `make lint` **ou** `uv run ruff check app/` sem erros novos na superfície tocada
- [ ] Tipagem (se tocou `app/`): `uv run mypy app/` sem falhas novas
- [ ] Testes da área **PASS** com comando reproduzível, por exemplo:
  ```bash
  cd backend && unset PYTHONPATH && .venv312/bin/python -m pytest \
    tests/test_<area>_g8.py --no-cov -q
  ```
- [ ] Wave de código: preferir `make test-fast` / suite G8 tocada; CI-facing: coverage global não regredir sem justificativa (gate CI ≥90%; meta G8 goals ≥96% em `SUPER_GOALS_G8.md`)

### C. Honestidade / rastreio

- [ ] `SUPER_PLANO_G8_100_TASKS.md`: checkbox `[x]` **somente** com artefato + teste acima
- [ ] `PROGRESS.md`: append **honesto** (IDs, paths, N passed) — **nunca** bloco “Wave G8.Sxx COMPLETED ✅” sem evidência
- [ ] Lesson em `.harness/memory/lesson-XXX-…md` se: multi-rein, anti-pattern, SUI, audit/PII, ou workaround de ambiente
- [ ] Contadores em `SUPER_GOALS_G8.md` / banner do plano: **só** “evidenced N/100” batendo com checkboxes reais
- [ ] Footer de commit/docs: `Modified by Gustavo Almeida` (Conventional Commit se commitar)

### D. HOLD / não-feito

- [ ] Se bloqueado por prod: marcar `[~]` + doc/report SUI; **não** inventar PASS
- [ ] Se orquestrador tickou papel: honesty reset (Lesson 216) antes de continuar waves

---

## Definition of Done (wave de 4 agents)

Uma wave (squad slot A1–A4) só é **DONE** se:

1. **Cada** task da wave satisfaz o DoD de task (acima) **ou** está explicitamente `[~]` HOLD-SUI com path de report
2. **Lint + testes da wave** verdes (comando e contagem no `PROGRESS.md`)
3. **Sem vazamento de segredos** no diff da wave
4. **Um** bloco de progress honesto (não quatro ticks paper)
5. **Lesson** se a wave gerou aprendizado cross-rein ou corrigiu fraude de checkbox
6. Banner / loop-state G8 atualizado só com IDs evidenciados
7. Validadores existentes não pioraram sem nota:
   - `make g7-validate` / composite: FAIL local bloqueia; HOLD prod SUI é ok se documentado
   - Quando existir `g8-validate`, usar o mesmo espírito (local fail ≠ paper green)

---

## Definition of Done (goal G8.1–G8.12)

Alinhado a [`SUPER_GOALS_G8.md`](../SUPER_GOALS_G8.md):

| Goal | DoD resumido (evidence) |
|------|-------------------------|
| G8.1 API/WS | Testes concorrência/heartbeat/buffer com paths e N passed |
| G8.2 Telegram multi-turn | Dialog history + cenários longos; sem stacktrace raw ao user |
| G8.3 Chatwoot HITL | Mute bot Redis + handoff; Art.18 onde aplicável |
| G8.4 LobeChat/OpenClaw | Radar/roteamento/credenciais sem secret em git |
| G8.5 Redis | TTL/eviction + chaves com hash de documento (não CPF raw) |
| G8.6 DB/RLS | Indexes/dumps/RLS verificados com report |
| G8.7 MCP | Tools mockadas + interceptor PII saída |
| G8.8 Webhooks/DLQ | DLQ TTL/crypto + failure injection multi-canal |
| G8.9 Tailscale | Probe/MagicDNS — SUI ok como `[~]` até live |
| G8.10 Traefik/DNS | Script DNS + logs sem PII |
| G8.11 SOLID | Controllers finos; mypy/Pydantic strict na superfície |
| G8.12 CI/Radar 72h | CI verde + cobertura meta + radar estável (não paper) |

% de goal sobe **apenas** com tasks evidenced daquele goal — nunca média inventada.

---

## Cadência de wave (G8)

1. Orquestrador escolhe até **4** tasks Ready (1 por rein quando possível)
2. Ciclo: analisar → testar baseline → implementar → testar → documentar → memory
3. Registrar evidência (paths + pytest) **antes** de `[x]`
4. Atualizar `SUPER_PLANO_G8_100_TASKS.md` + `SUPER_GOALS_G8.md` (honest %) + `PROGRESS.md`
5. Próxima wave até 100/100 **evidenced** (não paper)

---

## Anti-padrões (rejeitar no review)

| Anti-padrão | Ação |
|-------------|------|
| Orquestrador marca S05–S25 COMPLETED sem commits | Honesty reset; reabrir tasks |
| `PROGRESS.md` com “All tests passed” sem arquivo de teste | Não creditar task |
| Duplicar lesson number / overwrite multi-agent no mesmo path | Re-ler HEAD; unificar API; lesson de conflito |
| Amend de commit alheio | Proibido |
| Secrets em doc/Makefile/test fixtures “reais” | Bloquear merge |

---

## Comandos úteis (Makefile raiz)

```bash
make install          # deps backend
make lint             # ruff + mypy
make test-fast        # pytest sem coverage (loop)
make test             # pytest + coverage gate
make pre-commit       # lint + test-fast
make qa               # lint + test (CI local)
make bare-exception   # zero raise Exception( em app/
make g7-validate      # validador G7 (não substitui evidence G8)
```

DoR/DoD canônico G8: **este arquivo** (`docs/G8_DOR_DOD.md`).  
DoD resumido por wave também em [`SUPER_GOALS_G8.md`](../SUPER_GOALS_G8.md#definition-of-done-dod-por-task--wave) — manter os dois alinhados; em conflito de honestidade, **prevalece este doc + evidência git**.

---

**Modified by Gustavo Almeida — G8.16.T2 (DoR/DoD + honesty gate)**
