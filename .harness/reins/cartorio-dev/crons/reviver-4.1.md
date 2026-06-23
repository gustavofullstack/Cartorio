---
name: reviver-4.1
schedule: '*/25 * * * *'
session:
  mode: sessionId
  sessionId: mvs_a3ed3f0b81664c46b42c5bcb35cf7a91
report_to_root: false
---

REVIVER pos-quota-reset (~19:18 BRT). master dff1bb9, 270 passed committed + 7 fix uncommitted (test_cliente_historico 7/7) + 5 fail uncommitted (test_agent_health endpoint nao existe, patches wrong module). Pai (mvs_c2508947) report persistido.

**HARD HOLD ATIVO 19:18 BRT** (per Pietra msg 2095 to root mvs_6699c48e, 18:47 BRT). Nao quebrar.

**NOVO P0 Blocker #13 (Pietra 18:47):** LLM output sem scrub() em router.py:553 + integrations.py:190 ecoa PII (CNS/CNH/CPF) de volta pro cliente via WhatsApp. Mais grave que #10 pq caminho real + cliente vitima. cartorio-lgpd subiu como P0 agora.

**ORDEM DE PRIORIDADE pos-19:18 (per Pietra 18:47):**
1. [TOPO NOVO] Blocker #13 fix (output scrub router.py:553) ~30min
2. cliente_historico 5 fails (test infra ja fixado, falta commit apos Gustavo OK)
3. P0.1 / P0.4 / P0.2 / P0.3 / E1.S3.T7 (fila original)
4. v0.6.1 LGPD (5 regex anchored: CNS, CNH, PASEP, PASSPORT, CERT_MILITAR + audit tipo_doc + 5+ suite FP tests)
5. Sprint 3 #4.1 audit log 100% (3 gaps: /documento/segunda-via, /atendimento/{id}/pesquisa-enviada, /atendimento/{id}/concluir) - so se nao conflitar com acima

**DECISAO GUSTAVO PENDENTE 19:18 BRT:**
- (a) Blocker #13 primeiro pos-HOLD
- (b) Override HOLD, fix imediato
- DEFAULT se Gustavo mudo: aplicar (a)

**ACOES INICIAIS ao reviver (gate-discipline):**
1. mavis session info mvs_3c841fe2 (cartorio-lgpd) - se online, pingar pra Blocker #13 review
2. mavis communication messages --from mvs_c2508947ba0f4a738139f90b9c3e75a8 --limit 5 (checar se Gustavo decidiu)
3. Se Gustavo escolheu (b): quebrar HOLD, fixar Blocker #13 IMEDIATO
4. Se Gustavo escolheu (a) ou mudo: aguardar 19:18, depois Blocker #13 primeiro
5. Se ja passou 19:18 e Gustavo mudo: aplicar (a) automaticamente

**TEST STATE ATUAL (verificado 18:50 BRT):**
- master dff1bb9 committed: 270/0/2/37
- test_cliente_historico.py: 7/7 PASSING (3 fixes em test infra, NAO commitado)
- test_agent_health.py: 0/5 failing (endpoint nao existe, test patches wrong module)
- Total: 285 passed, 5 failed (todas em test_agent_health)

**HARD HOLD: NAO COMITAR NADA, NAO IMPLEMENTAR NADA, ate 19:18 BRT ou Gustavo explicito green light.**

Se TTL expirar (19:40 BRT) e ainda HOLD, deletar e sair silencioso.

---
[self-reminder TTL] This reminder expires at 2026-06-23 19:52:03 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1782255123722`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-dev reviver-4.1`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
