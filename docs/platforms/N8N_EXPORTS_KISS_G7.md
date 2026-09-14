# N8N Exports KISS — Inventário G7.20.T4

| Campo | Valor |
|-------|--------|
| **Task** | G7.20.T4 — KISS: delete unused N8N exports |
| **Wave** | G7 Wave 26 |
| **Rein** | cartorio-n8n / cartorio-brain |
| **Regra** | **Sem mass delete**. Só inventário + archive de near-dup **claramente morto**. Source of truth remoto = N8N live. |
| **Audit date** | 2026-07-17 |
| **Root JSON** | `infra/n8n-workflows/*.json` |

---

## 0. TL;DR

- **39 → 38** JSONs na raiz (1 near-dup arquivado).
- **0** colisões de hash de conteúdo (nenhum byte-idêntico na raiz).
- **1** colisão de *display name* resolvida por archive: `lgpd-esqueci-fix.json` ≈ `23-lgpd-esqueci-v2.json`.
- **5** colisões de *prefixo numérico* (dois WFs com o mesmo `NN-`) — **não são duplicatas**, só debt de naming.
- **Já arquivados** (2026-06-23/29): `backups/legacy-v1-2026-06-23/` (17) + snapshots pre-migration Chatwoot/MCP.
- **Não deletar** WFs `active: false` / sem flag sem confirmação no painel N8N — vários são standby (LLM fallback, LGPD, EVO-IN).

---

## 1. Ação tomada (KISS seguro)

| Ação | Arquivo | Destino | Motivo |
|------|---------|---------|--------|
| **ARCHIVE** | `lgpd-esqueci-fix.json` | `infra/n8n-workflows/backups/kiss-g7-2026-07-17/` | Mesmo `name` display que `23-lgpd-esqueci-v2.json`; near-dup WIP (dedup key `lgpd-esqueci-fix`); ambos inactive/`NOFLAG`; VALIDATION_REPORT já apontava risco de path duplicado |

**Não movidos** (precisam decisão humana / still useful):

| Arquivo | Motivo de manter na raiz |
|---------|--------------------------|
| `23-lgpd-esqueci-v2.json` | Candidato canônico LGPD esqueci (mesmo inactive) |
| `12-chatbot-llm-end-to-end.json` | Fallback LLM E2E (NOFLAG) |
| `14-opencode-go-fallback.json` | Fallback OpenCode (NOFLAG) |
| `27-welcome-first-time.json` | Consent LGPD (`active: false` export) |
| `evo-in.json` | Evolution inbound canônico (NOFLAG) |
| Pares `04/22/23/24/25-*` | Prefixos colidem, **funções diferentes** |

---

## 2. Inventário raiz (pós-archive)

Regenerar com: `python3 scripts/n8n_index_gen.py` (atualiza `INDEX.md`).

| Prefixo | Arquivo | active export | Nodes | Notas |
|---------|---------|---------------|-------|-------|
| 00 | `00-error-handler.json` | ✅ | 15 | Error trigger global |
| 01 | `01-consulta-emolumento.json` | ✅ | 11 | Canônico WA emolumento |
| 02 | `02-criar-protocolo.json` | ✅ | 11 | Protocolo + LGPD |
| 03 | `03-handoff-human-chatwoot-v3-staging.json` | ✅ | 7 | Chatwoot official node (staging label) |
| 04 | `04-boas-vindas-lgpd.json` | ✅ | 10 | **prefix clash** com consulta |
| 04 | `04-consulta-protocolo.json` | ✅ | 11 | **prefix clash** com boas-vindas |
| 05 | `05-agendamento.json` | ✅ | 11 | |
| 06 | `06-2-via-protocolo.json` | ✅ | 11 | |
| 07 | `07-pesquisa-satisfacao.json` | ✅ | 6 | |
| 08 | `08-audit-verify-diario.json` | ✅ | 9 | Diário 03:30 — distinto do 6h |
| 10 | `10-faq-bot.json` | ✅ | 8 | |
| 11 | `11-monitor-cartorio.json` | ✅ | 18 | + JS standalone `11_monitor_cartorio.js` |
| 12 | `12-chatbot-llm-end-to-end.json` | NOFLAG | 8 | Keep — LLM path |
| 14 | `14-opencode-go-fallback.json` | NOFLAG | 7 | Keep — fallback |
| 16 | `16-prospeccao-enrichment.json` | ✅ | 10 | |
| 18 | `18-prospeccao-followup-d7.json` | ✅ | 8 | |
| 21 | `21-backup-status-5min.json` | ✅ | 7 | |
| 22 | `22-audit-verify-6h.json` | ✅ | 7 | **prefix clash** com MCP — freq diferente do 08 |
| 22 | `22-mcp-server.json` | ✅ | 4 | **prefix clash** com audit 6h |
| 23 | `23-cron-stale-detector.json` | ✅ | 8 | **prefix clash** com lgpd |
| 23 | `23-lgpd-esqueci-v2.json` | NOFLAG | 24 | **prefix clash**; canônico LGPD WF |
| 24 | `24-daily-cleanup.json` | ✅ | 6 | **prefix clash** com retenção |
| 24 | `24-retencao-diaria.json` | ✅ | 7 | LGPD 5y/2y |
| 25 | `25-metrics-collector.json` | ✅ | 6 | 1min — **≠** `34` (5min) |
| 25 | `25-protocolo-concluido-pdf.json` | ✅ | 11 | |
| 26 | `26-alerta-critico.json` | ✅ | 10 | |
| 27 | `27-welcome-first-time.json` | ❌ | 9 | Keep até confirmar remoto |
| 28 | `28-audit-snapshot.json` | ✅ | 5 | |
| 29 | `29-rate-limit-reset.json` | ✅ | 5 | |
| 30 | `30-health-deep-check.json` | ✅ | 10 | |
| 31 | `31-telegram-listener.json` | ✅ | 12 | |
| 33 | `33-whatsapp-qr-scan-helper.json` | ✅ | 6 | |
| 34 | `34-metrics-collector-5min.json` | ✅ | 3 | Complementa 25 (janela diferente) |
| 35 | `35-llm-fallback-3x.json` | ✅ | 8 | |
| 36 | `36-chatwoot-telegram-sync.json` | ✅ | 9 | |
| 37 | `37-agendamento-notarial-sync.json` | ✅ | 7 | Google Calendar |
| 38 | `38-emolumento-calculator.json` | ✅ | 6 | |
| — | `evo-in.json` | NOFLAG | 7 | Evolution inbound |

---

## 3. Colisões de prefixo (debt de naming — não archive)

| Prefixo | Arquivos | Ação recomendada (futuro, humano) |
|---------|----------|-----------------------------------|
| `04` | boas-vindas + consulta-protocolo | Renomear consulta → `09-consulta-protocolo` (slot 09 livre) |
| `22` | audit-6h + mcp-server | Renomear MCP → `39-mcp-server` ou manter ID histórico T22 |
| `23` | cron-stale + lgpd-esqueci-v2 | Renomear lgpd → `40-lgpd-esqueci` |
| `24` | daily-cleanup + retencao | Renomear cleanup → `41-daily-cleanup` |
| `25` | metrics-1min + protocolo-pdf | Renomear metrics → `42-metrics-collector-1min` |

> **Não renomear em mass** nesta task: quebra docs, `import_all`, diagramas e IDs mentais do time. Só inventariar.

---

## 4. Pares “parecidos mas NÃO duplicata”

| Par | Por que manter ambos |
|-----|----------------------|
| `08-audit-verify-diario` vs `22-audit-verify-6h` | Frequências e fan-out de alerta diferentes |
| `25-metrics-collector` vs `34-metrics-collector-5min` | 1min Prometheus vs 5min system metrics |
| `04-boas-vindas-lgpd` vs `27-welcome-first-time` | Consent webhook vs first-time welcome (27 inactive) |
| `12` / `14` / `35` LLM | Caminhos de fallback distintos (E2E / OpenCode / 3x chain) |

---

## 5. Já em `backups/` (não mexer)

### `backups/legacy-v1-2026-06-23/` (17 WFs)

Ver README local. Retenção até **2026-09-30** → depois `git rm` ok.

Inclui: emolumento v2/v3-fixed, handoff v1/v2, pesquisa-evolucao, backup-status antigo, chatbot-mcp, openclaw-bridge, session-sync, prospeccao-send, cliente/protocolo criados, lgpd-esqueci v1, welcome-first, alertas-pietra, evo-in v2/v3.

### `backups/` snapshots pontuais

| Arquivo | Contexto |
|---------|----------|
| `WF03_pre_chatwoot_2026-06-29.json` | Pre-migration Chatwoot node |
| `WF12_pre_mcp_2026-06-29.json` | Pre-migration MCP |

### `backups/kiss-g7-2026-07-17/` (esta wave)

| Arquivo | Motivo |
|---------|--------|
| `lgpd-esqueci-fix.json` | Near-dup de `23-lgpd-esqueci-v2.json` |

---

## 6. Não-JSON na pasta (keep)

| Path | Tipo |
|------|------|
| `11_monitor_cartorio.js` + README | Script Node standalone (health fora do N8N) |
| `diagrams/*.mmd` | Mermaid |
| `INDEX.md`, `CHANGELOG.md`, runbooks `T7`/`T8`, audits | Docs ops |
| `import_all_to_n8n.sh`, `check_all_workflows.sh`, `migra-workflows-v1-to-v2.sh` | Ops scripts |

---

## 7. Política KISS (contrato)

1. **Source of truth remoto** = N8N live (`flow.2notasudi.com.br` / EasyPanel). Export repo = mirror.
2. **Nunca** `rm` mass de `active: true` ou WFs sem prova de 0 exec + substituto.
3. Archive preferível a delete: `backups/<motivo>-YYYY-MM-DD/`.
4. Após archive: rodar `python3 scripts/n8n_index_gen.py` + `python3 scripts/n8n_workflow_validator.py`.
5. README raiz `infra/n8n-workflows/README.md` está **stale** (ainda cita `03-handoff-human.json`, `07-pesquisa-evolucao.json`, etc. já em legacy) — follow-up opcional, **fora** do escopo desta task (evitar rewrite grande).

---

## 8. Follow-ups (não feitos)

- [ ] Confirmar no painel N8N quais IDs batem com os 38 exports
- [ ] Renomear prefix clashes (tabela §3) em PR dedicado
- [ ] Atualizar `README.md` da pasta workflows (lista canônica = `INDEX.md`)
- [ ] Após 2026-09-30: purge `legacy-v1-2026-06-23/` se remoto ok
- [ ] Decidir se `23-lgpd-esqueci-v2` vira rota API-only (já há path backend LGPD) e archive completo

---

## 9. Validação local pós-archive

```bash
# Contagem raiz
ls infra/n8n-workflows/*.json | wc -l   # esperado: 38

# Validator (pre-commit hook workflow-validator)
python3 scripts/n8n_workflow_validator.py

# Regenerar INDEX
python3 scripts/n8n_index_gen.py
```

---

**Modified by Gustavo Almeida** — G7 Wave 26 (G7.20.T4) · cartorio-n8n/brain
