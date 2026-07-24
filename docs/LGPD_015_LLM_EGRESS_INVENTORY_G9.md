# LGPD-015 — Inventário de pontos de saída LLM (G9.S3.T9)

**Data:** 2026-07-24 · **Status:** inventário técnico (sem PII real)  
**Owner:** cartorio-dev · **Review:** cartorio-lgpd

## Regra

PII (CPF/RG/telefone/email/protocolo/escritura) **nunca** sai raw para LLM pública,
canal de usuário, log ou Sentry. Pipeline: input scrub → pre-LLM → output scrub.

## Pontos de saída

| # | Caminho | Pré-LLM scrub | Output scrub | HITL | Evidência |
|---|---|---|---|---|---|
| 1 | `cartorio_agent.run_cartorio_agent` → MiniMax/LiteLLM/Zen | `scrub(raw)` + history scrub | `scrub(clean)` + `_offline_reply` scrub + `sanitize_bot_output` | tools não aprovam ato jurídico | `test_cartorio_agent_g9` + `test_pii_telegram_output_g9` |
| 2 | `telegram.py` outbound | N/A (recebe AgentReply) | `scrub_bot_outbound` em todos os sends | FSM DRAFT | `test_pii_telegram_output_g9` |
| 3 | WhatsApp / Evolution reply | via pipeline N8N/agent | depende de n8n + pii service | HITL protocolo | contract tests; **WA session BLOCKED_SUI** |
| 4 | Logs (`logger.*`) | `log_masker.MaskingFilter` | N/A | N/A | `test_secrets_log_filter_g8` |
| 5 | Sentry | `before_send` scrubber | N/A | N/A | `app/services/sentry.py` |
| 6 | OpenClaw / LiteLLM proxy | scrub no agent antes do POST | resposta re-scrub no agent | tools locais only | fallback chain |
| 7 | MCP tools mutação | schema + audit | PII scrub tools sensíveis | **protocolo DRAFT only** | MCP inventory tests |
| 8 | CNJ export / DSAR | DPO JWT + scrub package | streaming scrub | dual-control | `cnj_export` audit-fail-closed |

## Gaps residuais

| Gap | Severidade | Mitigação |
|---|---|---|
| n8n workflow pode ecoar campo raw se node pular API | médio | revisar workflows que tocam PII + cartorio-lgpd |
| WA E2E real | SUI | QR reconnect |
| Prompt injection → ato jurídico | controlado | system prompt + tools não emitem certidão; protocolo DRAFT |

## Decisão

Inventário **completo o suficiente** para G9.S3.T9 com gaps documentados.
Mudança futura em egress LLM exige atualizar esta tabela + teste de regressão PII.

Modified by Gustavo Almeida
