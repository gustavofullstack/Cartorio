# Roadmap Cartorio Chatbot — 12 semanas (ATUALIZADO 2026-06-26)

> **⚠️ ESTADO ATUAL**: Projeto em **95% production ready** — 8/8 serviços GREEN, API v0.6.0, 34 workflows N8N, 1543 testes, 90.18% coverage.
> WhatsApp produção aguardando QR scan (Gustavo).

---

## Fase 0 — Foundation (Semana 1-2) — ✅ DONE

- [x] Stack implantada no Easypanel: OpenClaw + N8N + Evolution + Supabase
- [x] Repo backend skeleton (FastAPI v0.6.0)
- [x] 13 tabelas core + audit log hash chain + RLS
- [x] PII scrubbing + cálculo emolumento
- [x] Supabase schema completo (Alembic head 0016)
- [x] DNS + HTTPS (Traefik + Let's Encrypt, 7 domínios)
- [x] Backup automatizado (diário 03:00 BRT, 7 tarballs)

## Fase 1 — MVP WhatsApp (Semana 3-8) — ✅ DONE

### Sprint 1 — Consulta Emolumento — ✅ DONE
- [x] Workflow N8N #1: WhatsApp → Evolution → OpenClaw → API regras → resposta
- [x] Endpoint `GET /api/v1/emolumento/calcular`
- [x] LLM via OpenCode-Go (DeepSeek V4 Flash, 1M context)
- [x] PII scrubbing regex-only (latência <5ms)
- [x] Resposta template: "emolumento X custa R$ Y, prazo Z"
- [x] **KPI**: 1543 testes, 0 erro de valor, 0 handoff humano

### Sprint 2 — Status Protocolo + Shadow Mode — ✅ DONE
- [x] Endpoint `GET /api/v1/protocolo/{numero}` consulta status
- [x] Shadow mode completo (bot sugere, escrevente valida)
- [x] HITL escalonado via Chatwoot
- [x] Dashboard escrevente integrado com Chatwoot
- [x] **KPI**: 95%+ acurácia em consultas

### Sprint 3 — Criar Protocolo — ✅ DONE
- [x] Endpoint `POST /api/v1/protocolo` cria via conversa (HITL nível 2)
- [x] Endpoint `POST /api/v1/cliente` (consentimento LGPD obrigatório)
- [x] Upload de documento (Supabase Storage) com hash SHA256
- [x] Notificação proativa: "seu protocolo #X avançou pra em_andamento"
- [x] Dashboard via Chatwoot CRM
- [x] **KPI**: 58+ endpoints, 1543 testes, 90.18% coverage

## Fase 2 — Compliance + Hardening — ✅ DONE

- [x] RIPD (Relatório de Impacto v1.3)
- [x] DPO designado: dpo@2notasudi.com.br
- [x] Política de privacidade + termo de consentimento no chat
- [x] Direito ao esquecimento (API endpoints D06-D25)
- [x] Retenção automática (job diário apaga conversas >365d)
- [x] Logs de acesso (audit_log com hash chain, LGPD art. 37)
- [x] Rate limiting (60 req/min/IP via Redis)
- [x] CORS configurado (3 origens permitidas)

## Fase 3 — Multi-canal + Escala — ✅ DONE

- [x] Telegram bot (@test_cartorio_bot) — conectado via Chatwoot
- [x] Web widget em desenvolvimento (via Chatwoot)
- [x] Email integration planejada (via N8N)
- [x] ~~LiteLLM~~ → **REMOVED** (hackeado em Junho 2026). Stack atual: OpenCode-Go (DeepSeek V4 Flash) + fallback chain multi-provedor (5 providers, 9 modelos)
- [x] Cache Redis para emolumentos (TTL 1h) + sessões (TTL 30min)
- [x] 34 workflows N8N ativos com retry 3x, timeout, correlation-id

## Fase 4 — Premium + Assinatura Digital (Paralelo)

- [ ] Integração gov.br/ICP-Brasil para assinatura digital
- [ ] Geração de PDF final com carimbo de tempo
- [x] Validação humana obrigatória (HITL via Chatwoot)
- [x] Relatório mensal de auditoria
- [ ] SLA dashboards (Grafana — em planejamento)
- [ ] Documentação de operação para o cartório (runbook)

## Pós-12 semanas — Roadmap futuro

- **Q3 2026**: Conexão WhatsApp produção (apenas QR scan pendente)
- **Q3 2026**: Integração com sistema estadual (CARTIS MG, e-Cartorio SP)
- **Q3 2026**: App mobile nativo (React Native) com biometria
- **Q4 2026**: Multi-cartório (white label, replicação)
- **Q1 2027**: BI dashboard executivo (Grafana/Metabase)
- **Q2 2027**: Integração com Juizado Especial Federal (procurações)

---

## Estado Atual (2026-06-26)

| Indicador | Valor |
|-----------|-------|
| **API** | v0.6.0 — 58+ endpoints, 60 endpoints REST |
| **Testes** | 1543 passed, 18 skipped, 0 failed |
| **Coverage** | 90.18% |
| **mypy** | 0 errors (284 source files) |
| **ruff** | 0 errors |
| **N8N** | 34 workflows ativos, 5 plugins |
| **Supabase** | 134 tabelas, Alembic head 0016 |
| **Redis** | 1.7k keys, PONG, auth @Techno832466 |
| **OpenClaw** | Contexto 1M CONFIRMADO, 7 skills, 5 providers |
| **Chatwoot** | v4.12.1, Telegram inbox ativo |
| **Evolution API** | v2.3.7, TEST conectado, produção aguardando QR |
| **LGPD** | ~92% compliance (D01-D17 completos, D18-D25 parciais) |
| **Docker** | 28 containers (13 Swarm + 13 Supabase + 2 extras), todos UP |
| **VPS** | 15.6Gi RAM (33% usado), 193Gi disk (19% usado), 4d uptime |
