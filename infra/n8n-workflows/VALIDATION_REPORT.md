# N8N Workflow Validation Report

**Data**: 2026-07-16T14:33:53.542636+00:00
**Total workflows**: 33
**Blockers**: 1
**Warnings**: 11

## [HOLD] 1 blocker(s) — MERGE BLOQUEADO

### Blockers (DEVEM ser corrigidos antes do merge)

| Workflow | Regra | Node | Mensagem |
|---|---|---|---|
| `lgpd-esqueci-fix.json` | DUPLICATE_WEBHOOK | `LGPD Esqueci Webhook` | Webhook path 'lgpd-esqueci' DUPLICADO (tambem em 23-lgpd-esqueci-v2.json) |

### Warnings (recomendado corrigir)

| Workflow | Regra | Node | Mensagem |
|---|---|---|---|
| `03-handoff-human-chatwoot-v3-staging.json` | MISSING_CORRELATION | - | WF sem node 'Init Correlation' (degradacao observabilidade) |
| `12-chatbot-llm-end-to-end.json` | INACTIVE_WORKFLOW | - | WF exportado como inactive |
| `12-chatbot-llm-end-to-end.json` | MISSING_CORRELATION | - | WF sem node 'Init Correlation' (degradacao observabilidade) |
| `14-opencode-go-fallback.json` | INACTIVE_WORKFLOW | - | WF exportado como inactive |
| `14-opencode-go-fallback.json` | MISSING_CORRELATION | - | WF sem node 'Init Correlation' (degradacao observabilidade) |
| `23-lgpd-esqueci-v2.json` | INACTIVE_WORKFLOW | - | WF exportado como inactive |
| `23-lgpd-esqueci-v2.json` | MISSING_CORRELATION | - | WF sem node 'Init Correlation' (degradacao observabilidade) |
| `27-welcome-first-time.json` | INACTIVE_WORKFLOW | - | WF exportado como inactive |
| `evo-in.json` | INACTIVE_WORKFLOW | - | WF exportado como inactive |
| `lgpd-esqueci-fix.json` | INACTIVE_WORKFLOW | - | WF exportado como inactive |
| `lgpd-esqueci-fix.json` | MISSING_CORRELATION | - | WF sem node 'Init Correlation' (degradacao observabilidade) |

## Regras verificadas

| Regra | Severidade |
|---|---|
| HARDCODED_CRED (pattern) | BLOCKER |
| HARDCODED_CRED_KEY (literal) | BLOCKER |
| UNSAFE_NODE (MySQL/FTP/SSH) | BLOCKER |
| PII_LEAK_HTTP (cpf/rg/email em body) | BLOCKER |
| DUPLICATE_WEBHOOK | BLOCKER |
| UNSAFE_URL (http://, IP interno) | WARNING |
| LARGE_WORKFLOW (>30 nodes) | WARNING |
| INACTIVE_WORKFLOW | WARNING |
| MISSING_CORRELATION | WARNING |

---

**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 3 (auto-gerado)**