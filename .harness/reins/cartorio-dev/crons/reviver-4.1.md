---
name: reviver-4.1
schedule: '*/25 * * * *'
session:
  mode: sessionId
  sessionId: mvs_a3ed3f0b81664c46b42c5bcb35cf7a91
report_to_root: false
---

REVIVER TAREFAS pos-quota-reset (~19:18 BRT). Estado: master dff1bb9, 275 passed, 91.74% coverage. Pai (mvs_c2508947) deixou report persistido.

**PRIORIDADE 1 (safe alone, BLOQUEIO nenhum): Sprint 3 #4.1 audit log 100% mutações**
- 3 gaps mapeados: (a) POST /documento/segunda-via [BAIXO], (b) POST /atendimento/{id}/pesquisa-enviada [BAIXO], (c) POST /atendimento/{id}/concluir [MEDIO - pesquisa_comentario e texto livre com PII]
- TDD: test_audit_coverage.py greps router pra AuditService.log em cada POST/PUT/PATCH/DELETE
- ~30-45min. Começar SEM esperar review.

**PRIORIDADE 2 (BLOQUEADO sem cartorio-lgpd mvs_3c841fe2 OU Gustavo autorizar PR agrupado sem review): v0.6.1 LGPD fix**
- Plano: feat(pii) extend scrubber to LGPD art. 11 + art. 33 + Lei 4.375/64
- 5 regex anchored: CNS (mod 11), CNH (11 dig sem checksum), PASEP (3-5-2), PASSPORT (LGPD art. 33), CERT_MILITAR (Lei 4.375/64)
- 5+ suite FP tests em test_pii_no_false_positives.py: CEP puro, telefone puro, CNJ, CRC, conta corrente
- audit log tipo_doc field para classificar achado
- cartorio-lgpd OFFLINE (404 NOT FOUND reportado por Pietra 18:40)
- Se Gustavo bater martelo em PR agrupado sem review, dispara. Se não, BLOQUEIA.

**ACOES INICIAIS ao reviver:**
1. Rodar pytest baseline pra confirmar estado
2. Ler report do pai: mavis communication messages --from mvs_c2508947ba0f4a738139f90b9c3e75a8 --limit 5
3. Se Prio 1 já não foi feita pela sessão paralela (mvs_de8510d1 ou ZCode), fazer. Se já foi, validar.
4. Se cartorio-lgpd voltou online, pingar: mavis session info mvs_3c841fe2
5. Reportar progresso ao pai após cada endpoint / regex fechado.

HOLD até quota reset. Se self-reminder TTL expirar (19:35 BRT), deletar e sair silencioso.

---
[self-reminder TTL] This reminder expires at 2026-06-23 19:40:56 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1782254456155`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-dev reviver-4.1`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
