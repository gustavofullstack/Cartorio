# Sprint 3 Design — Fechar o WhatsApp Pilot Ready

**Data:** 2026-06-23
**Autor:** ZCode (Mavis)
**Status:** DRAFT aguardando aprovação Gustavo
**Versão alvo:** v0.5.1 → v0.6.0

## Contexto

Sprint 0 (diagnóstico da verdade) + Sprint 1 (emolumento WhatsApp) + Sprint 2 (webhooks blindados, v0.5.0) estão fechados. O gap real entre o que existe (já verificado, ~85% do briefing) e o que falta é dominado por **tarefas SUI** (UI no Easypanel/N8N/Chatwoot que só Gustavo pode fechar) + **2 bugs P0 com ADRs prontos** + **LGPD legal** (DPA, 2-4 semanas, fora do nosso controle).

Este spec cobre **Sprint 3 = WhatsApp Pilot Ready**: tudo o que falta para conectar 1 número real de WhatsApp e servir 1 cliente real do cartório sem cair.

## Princípios

1. **SUI-first**: não inventar 100 tasks. As 6 SUI já mapeadas no Sprint 0 são o gargalo #1.
2. **Bugs com ADR pronto primeiro**: B1 (Chatwoot loop) e B2 (OpenClaw overflow) já têm RCA documentada — aplicar é mecânico.
3. **YAGNI**: Telegram bot, multi-canal, white-label, mobile RN — tudo isso é **E3+**, não Sprint 3.
4. **TDD**: qualquer código novo vai com teste primeiro.
5. **Security-by-default**: HMAC, idempotency, audit chain — tudo que entra em produção v0.6.0 passa por aqui.

## Não-objetivos (declarados pra não voltar)

- ❌ Telegram bot (E3.T1, semana 9-10)
- ❌ Mobile RN (E5.T2, Q3 2026)
- ❌ White-label multi-cartório (E5.T3, Q4 2026)
- ❌ BI Looker/Metabase (E5.T4, Q1 2027)
- ❌ LiteLLM gateway HA (E3.T4, semana 9-10) — se OpenCode-Go cair, fallback já existe
- ❌ LLM local Llama 3.1 8B (E3.T5) — Prematuro sem carga real
- ❌ Reescrever workflows N8N do zero
- ❌ Reescrever OpenClaw persona
- ❌ Criar 7 subdomínios novos
- ❌ Reconsolidar DB (já feito, ADR-010)

## Tasks (18 reais, baseadas no gap verificado)

### Bloco 1 — SUI Gustavo (6 tasks, ~80min UI, 0 código)

| # | Task | Dono | Tempo | Bloqueia |
|---|------|------|-------|----------|
| 1.1 | DNS `chatwoot.2notasudi.com.br` (Easypanel UI) | Gustavo | 10min | handoff humano |
| 1.2 | Credencial Evolution API no N8N (N8N UI) | Gustavo | 5min | workflow #07 + piloto WhatsApp |
| 1.3 | Agent Bot Chatwoot "Cartório Assistant" (Chatwoot UI 5 cliques) | Gustavo | 30min | handoff humano completo |
| 1.4 | Regenerar Easypanel API key (foi exposta no chat) | Gustavo | 2min | segurança VPS |
| 1.5 | OpenClaw LLM key (requer L1 LGPD primeiro) | Gustavo | 2min | persona OpenClaw ativa |
| 1.6 | Decisão DNS typo `supbase` → `supabase` | Gustavo | 15min | domínio final correto |

### Bloco 2 — Bugs P0 com fix aplicável (2 tasks, ~10min SSH ZCode)

| # | Task | Dono | Tempo | Bloqueia |
|---|------|------|-------|----------|
| 2.1 | B1 Chatwoot: `docker service update --limit-memory 1G` (ADR-015) | ZCode (com SSH Gustavo) | 5min | estabilidade Chatwoot |
| 2.2 | B2 OpenClaw: ajustar YAML threshold 50 msgs + TTL 24h + `curl /compact` (ADR-016) | ZCode (com SSH) | 5min | overflow OpenClaw |

### Bloco 3 — Segurança / credenciais (4 tasks, ~60min)

| # | Task | Dono | Tempo | Bloqueia |
|---|------|------|-------|----------|
| 3.1 | Rotacionar OpenCode-Go `sk-` (foi exposta) | Gustavo | 5min | staging-only hoje |
| 3.2 | Rotacionar N8N MCP HTTP JWT + N8N public API JWT | Gustavo | 10min | produção |
| 3.3 | Rotacionar OpenClaw Gateway Token + Password | Gustavo | 10min | produção |
| 3.4 | Rotacionar Redis default password + Supabase DB | Gustavo | 15min | produção |

### Bloco 4 — Backend débitos pré-merge (3 tasks, ~4h ZCode, TDD)

| # | Task | Dono | Tempo | Bloqueia |
|---|------|------|-------|----------|
| 4.1 | Migrar TODAS as chamadas `AuditService.log(...)` para incluir `request_id/ip/user_agent` do `request.state` (atualmente só 1/6 rotas faz) | ZCode | 2h | LGPD art. 37 |
| 4.2 | Implementar `DELETE /api/v1/cliente/{id}` (LGPD art. 18 VI) | ZCode | 1.5h | direito ao esquecimento |
| 4.3 | Job diário `backend/app/jobs/retencao.py` (5y COM protocolo / até-revogação SEM, conforme D4) | ZCode | 1h | LGPD art. 7 II |

### Bloco 5 — Workflows N8N melhorias (2 tasks, ~1h ZCode)

| # | Task | Dono | Tempo | Bloqueia |
|---|------|------|-------|----------|
| 5.1 | Ativar `n8n-nodes-mcp` em workflow #12 (chatbot LLM) — usar o MCP Server #22 que reativamos | ZCode | 30min | protocolo padronizado |
| 5.2 | Ativar `n8n-nodes-chatwoot` em workflow #03 (handoff humano) — substituir inbox URL fallback | ZCode | 30min | handoff oficial |

### Bloco 6 — Documentação (1 task, ~30min ZCode)

| # | Task | Dono | Tempo | Bloqueia |
|---|------|------|-------|----------|
| 6.1 | Atualizar `docs/ENV_PRODUCTION.md` + `.env.example` com CARTORIO_API_KEY novo + tokens pós-rotação | ZCode | 30min | produção segura |

## Critérios de Done (v0.6.0 release-ready)

- [ ] Todos 6 SUI do Bloco 1 fechados
- [ ] B1 + B2 aplicados e validados por 24h
- [ ] Credenciais rotacionadas (Bloco 3)
- [ ] Audit log em 100% das mutações com `request_id/ip/user_agent`
- [ ] `DELETE /cliente/{id}` testado
- [ ] Job retenção rodando há 1 dia sem erro
- [ ] Workflows #12 e #03 usando MCP Client + Chatwoot node
- [ ] `.env` documentado com tokens rotacionados
- [ ] 199+ tests passando, coverage ≥ 90%
- [ ] Smoke E2E: webhook Evolution → API → N8N → WhatsApp com PII zero
- [ ] Tag `v0.6.0` em `master`

## Riscos conhecidos

| Risco | Mitigação |
|-------|-----------|
| Gustavo sem tempo para SUI (80min) | SUI-first, Bloco 4-6 em paralelo. ZCode não bloqueia. |
| L1 LGPD DPA trava OpenClaw LLM key (1.5) | Staging continua com modelo dummy. Cartório pode testar tudo MENOS OpenClaw com LLM real. |
| Backup mount desaparece de novo (B3 histórico) | Watchdog ADR-013 ativo; SUI backup. |
| PII leak em webhook Evolution (E1.S1.T7 ainda pendente) | 4.1 fecha + PII regex perf (já TDD) |
| `asyncio_mode=auto` no pyproject mascarando issues de teste | Coberto: 199/199 passa |

## Sprint 4 (declarado, fora deste spec)

- Conectar número real do cartório
- Servir 1 cliente real, ver falhar, melhorar
- Telegram bot (E3.T1) — agora faz sentido com carga real
- DPA OpenCode-Go assinada (L1) — destrava OpenClaw LLM
- Encryption at-rest Postgres (L3)
- GitHub Actions CI/CD

## ADRs a criar durante Sprint 3

- ADR-017: rotação de credenciais (Bloco 3, padrão 90d)
- ADR-018: `DELETE /cliente/{id}` LGPD art. 18 VI — quando cascade, quando soft delete
- ADR-019: job retenção 5y / até-revogação (D4)

## Especificação aprovada?

- [ ] Gustavo: OK com 18 tasks e 4 SUI-only blocks?
- [ ] Gustavo: ordem Bloco 1 → 2 → 3 → 4 → 5 → 6 está OK?
- [ ] Gustavo: quer ajustar não-objetivos (tirar ou adicionar algo)?
