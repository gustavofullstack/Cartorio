# SUPER PLANO G10 — 100 Tasks · 10 Squads · 10 Tasks/Squad
**Cartório 2º Notas · Otimização, Documentação e Deployment Final**
**Base:** pós-G9 + sessão 2026-07-20
**Orquestrador:** harness + reins (dev / n8n / lgpd / sre / docs)

---

## META

Finalizar integrações pendentes, garantir que toda a documentação oficial esteja local, corrigir G9/A1 (telegram webhook sync), e expandir coverage/monitoramento antes de virar a chave para produção no WhatsApp.

---

## SQUADS (10 × 10 tasks = 100)

### Squad S1 — Documentação Oficial Local (docs)
- S1.T1: Baixar documentação oficial do Evolution API (`curl -sL https://doc.evolution-api.com/`).
- S1.T2: Baixar documentação oficial do N8N (`curl -sL https://docs.n8n.io/`).
- S1.T3: Baixar documentação oficial do Chatwoot (`curl -sL https://www.chatwoot.com/docs/`).
- S1.T4: Baixar documentação oficial do Supabase (`curl -sL https://supabase.com/docs/`).
- S1.T5: Baixar documentação oficial do Redis (`curl -sL https://redis.io/docs/`).
- S1.T6: Consolidar documentação baixada em Markdown acessível pelo agent.
- S1.T7: Criar/atualizar `docs/super-memory.html` para visualização rápida.
- S1.T8: Criar/atualizar `docs/super-plan.html` para visualização rápida.
- S1.T9: Criar/atualizar `docs/super-tasks.html` (dashboard interativo).
- S1.T10: Revisar e atualizar `docs/project-history.html`.

### Squad S2 — Webhook & Resiliência Telegram (dev)
- S2.T1: Investigar status do Webhook no endpoint de prod.
- S2.T2: Corrigir inicialização multi-worker e webhook secret handling (G9.A1).
- S2.T3: Validar `sync_telegram_webhook` com mock do secret de produção.
- S2.T4: Testar debounce de mensagens repetidas do Telegram.
- S2.T5: Garantir idempotência e HTTP 200 nas requisições.
- S2.T6: Refinar parser de HTML para mensagens Telegram (se houver).
- S2.T7: Ajustar tratamento de grupos e menções de forma silenciosa e assertiva.
- S2.T8: Garantir uso correto de `typing` refresh e cancelamento (anti-spam).
- S2.T9: Passar bateria 1000+ no `test_telegram_1000.py`.
- S2.T10: Stress-test scripts e documentação do fix.

### Squad S3 — Integração N8N Polish (n8n)
- S3.T1: Revisar e rodar testes automatizados para os 34 workflows N8N.
- S3.T2: Adicionar alertas Telegram para falhas críticas via N8N (B15).
- S3.T3: Criar dashboard de monitoramento para workflows N8N (B14).
- S3.T4: Documentar credentials faltantes, inclusive `Evolution API` para WF #07.
- S3.T5: Confirmar uso de plugins nativos (Chatwoot, MCP, PDFKit, etc).
- S3.T6: Refinar timeout e retry policies em chamadas HTTP não mapeadas.
- S3.T7: Mapear novas requisições da OpenClaw via MCP N8N.
- S3.T8: Documentar padrões obrigatórios em workflows novos.
- S3.T9: Criar scripts/templates padrão B13 para facilitar expansão.
- S3.T10: Atualizar logs/métricas para os workflows melhorados.

### Squad S4 — OpenClaw & Agent (ai/dev)
- S4.T1: Validar correção do contexto do agente Pietra (131.1k -> 1M).
- S4.T2: Garantir que `thinking` adaptativo está ON para queries complexas.
- S4.T3: Documentar nova chave `OpenCode-Go` no `.env.example` e fallback system.
- S4.T4: Configurar fallback chain coerente (Minimax, Kimi, etc).
- S4.T5: Expandir skills (protocolo, emolumento, lgpd, agendamento, segunda-via, handoff).
- S4.T6: Resolver `gateway.http schema` rejeitado ou focar inteiramente em WS.
- S4.T7: Adicionar logs de tracking LLM token costs via `codex-bar`.
- S4.T8: Integrar testes unitários E2E (Telegram -> N8N -> API -> OpenClaw -> Resp).
- S4.T9: Adicionar suporte para lidar de forma mais polida com erros/rate limit do provider.
- S4.T10: Revisão de persona Pietra (seriedade, zero emojis).

### Squad S5 — Supabase Foundation + Hardening (dba/dev)
- S5.T1: Configurar uso de RPCs/REST via `PostgREST` na API.
- S5.T2: Documentar uso de `pg_graphql` para queries futuras.
- S5.T3: Revisão da tabela `lgpd_audit_anpd` (compliance).
- S5.T4: Documentar `pgmq` para filas assíncronas do webhook N8N.
- S5.T5: Explorar e documentar uso de Edge Functions Deno.
- S5.T6: Verificar triggers de `updated_at` (A18).
- S5.T7: Refinar Soft Delete / Right to be Forgotten logic (A19).
- S5.T8: Corrigir eventuais desalinhamentos Alembic vs DB (0014 base).
- S5.T9: Setup materialized views para dashboard DPO (A17).
- S5.T10: Expandir roles e RLS verification.

### Squad S6 — API Performance & Security (sre/dev)
- S6.T1: Verificar API rate limiting e circuit breakers (A24/A25).
- S6.T2: Aplicar Redlock distribuído no Redis (A20).
- S6.T3: RFC 7807 problem details uniformization (A23).
- S6.T4: Configuração `API versioning` routes (/v2/).
- S6.T5: Garantir Pydantic v2 ConfigDict em modelos novos.
- S6.T6: Dead man's switch config review (A13).
- S6.T7: Setup `Slow query detector` e alertas (A16).
- S6.T8: Otimizar pools de conexão banco de dados.
- S6.T9: Adicionar metricas Prometheus (J06).
- S6.T10: Passar bateria mypy/ruff global em toda a API.

### Squad S7 — Monitoramento e Infra (sre)
- S7.T1: Revisar DNS resolution e pendências A records SUI (n8n, supabase, chatwoot).
- S7.T2: Health checks Docker Swarm services (verificar se ainda 27/27).
- S7.T3: Validar backup de DB (pg_dump automático + S3 incremental).
- S7.T4: Otimizar caching strategy (Redis) para evitar out-of-memory.
- S7.T5: Monitorar/corrigir Tailscale nodes and routes.
- S7.T6: Teste de carga endpoints core.
- S7.T7: Documentar Dashboard Grafana / Log aggregation (J07/J08).
- S7.T8: Tracing/Tempo setup plan (J09/J10).
- S7.T9: Preparar runbook DNS hostinger/Cloudflare fallback.
- S7.T10: Validar deploy zero-downtime da API.

### Squad S8 — LGPD Compliance Endpoints (lgpd)
- S8.T1: Validar `/lgpd/dashboard` dashboard DPO.
- S8.T2: Validar endpoints de consentimento `POST /lgpd/consent` (D27).
- S8.T3: Validar revogação de consentimento `POST /lgpd/revogar-consent` (D31).
- S8.T4: Endpoints de anonimização e exclusão `DELETE /lgpd/cliente/{id}` (D28/D09).
- S8.T5: Exportação de portabilidade de dados `GET /lgpd/export/{cliente_id}` (D29).
- S8.T6: Atualização/correção de dados `POST /lgpd/correct/{cliente_id}` (D30).
- S8.T7: Transparência `GET /lgpd/audit/{cliente_id}` (D32).
- S8.T8: Job retenção 5 anos / DPO log rotation verify.
- S8.T9: Relatório de export massivo CNJ (`/lgpd/cnj-exports/massive-dump`).
- S8.T10: Atualizar e publicar `docs/ripd.md` (v1.3+).

### Squad S9 — Chatwoot CRM & Operações (dev/n8n)
- S9.T1: Validação do `handoff-humano` skill do agent.
- S9.T2: Verificação do webhook Chatwoot -> API.
- S9.T3: Garantir inbox conectada Evolution API (pós QR-scan do dono).
- S9.T4: Validação dos macros e labels via Chatwoot API.
- S9.T5: Validação do agent 'Pietra' integrado no Chatwoot (bot user).
- S9.T6: Testar script helper criar API key.
- S9.T7: Configuração de canned responses.
- S9.T8: Validação das integrações Redis para Chatwoot Sidekiq.
- S9.T9: Teste HITL (Human-in-the-loop) pause agent.
- S9.T10: Runbook operações atendentes.

### Squad S10 — Evolution API & Go-Live Final (dev/sre)
- S10.T1: Revisar Evolution API webhooks (`evo-in` via N8N).
- S10.T2: Verificar instancia `cartorio-2notas` properties.
- S10.T3: Suporte a arquivos/audio no parser de webhook (opcional/future-proof).
- S10.T4: Implementar bloqueio ou tratativa correta para spam no WA.
- S10.T5: Validar PII scrubbing na entrada e saída via WhatsApp.
- S10.T6: Garantir que QR-scan foi realizado pelo admin e inst. on.
- S10.T7: Setup Prospecção de cartórios (manual via CEO).
- S10.T8: Teste E2E massivo Final via mock numbers ou TriQ Hub.
- S10.T9: Atualização README.md e HANDOVER.md final.
- S10.T10: Commit Master Final com Tag Version (v0.8.0 ou v1.0).
