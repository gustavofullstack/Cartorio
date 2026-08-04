# SUPER_PLANO: Plano de Melhoria Contínua (100 Tasks)

Este plano foca em melhorias iterativas do sistema sem refatorações extremas.

## S1 - Squad 1: Core API & N8N Integration Hardening
**Foco:** Robustez nas centrais do sistema (API e N8N)

- [x] T1: Auditar e documentar todos os endpoints da FastAPI.
- [x] T2: Adicionar testes E2E básicos para os fluxos principais da API.
- [ ] T3: Configurar retry policies nos workflows do N8N.
- [ ] T4: Consolidar logs do N8N na API para centralização.
- [ ] T5: Revisar autenticação entre API e N8N.
- [ ] T6: Otimizar tempo de resposta da API (caching de dependências).
- [ ] T7: Testar e validar webhook receptor no N8N.
- [ ] T8: Testar e validar webhook emissor na API.
- [ ] T9: Padronizar payloads JSON entre API e N8N.
- [ ] T10: Documentar arquitetura exata API <-> N8N no repositório.

## S2 - Squad 2: Supabase Mastery (Database, Auth, Storage)
**Foco:** Aproveitar recursos nativos do Supabase

- [ ] T1: Integrar MCP do Supabase para consultas administrativas.
- [ ] T2: Configurar Database Webhooks para notificar API de mudanças.
- [ ] T3: Revisar RLS (Row Level Security) nas 134 tabelas.
- [ ] T4: Migrar jobs de limpeza para Cron nativo do Supabase.
- [ ] T5: Habilitar Supabase Vault para segredos de integração.
- [ ] T6: Utilizar Supabase Queues para processamento assíncrono.
- [ ] T7: Mapear acesso via GraphQL para integrações frontend futuras.
- [ ] T8: Otimizar índices do PostgreSQL (pg_stat_statements).
- [ ] T9: Configurar backups contínuos via Supabase.
- [ ] T10: Documentar procedimentos de disaster recovery do Supabase.

## S3 - Squad 3: Redis In-Memory & Caching Strategy
**Foco:** Otimizar uso do Redis para velocidade

- [ ] T1: Revisar TTLs de cache no Redis.
- [ ] T2: Configurar eviction policy adequada no Redis 8.
- [ ] T3: Implementar rate limiting distribuído usando Redis.
- [ ] T4: Migrar sessões efêmeras do Chatwoot para Redis de forma segura.
- [ ] T5: Monitorar hit/miss ratio do Redis.
- [ ] T6: Otimizar serialização de dados no Redis (msgpack vs json).
- [ ] T7: Testar failover e persistência AOF no Redis.
- [ ] T8: Integrar Redis ao N8N para controle de estado de workflows.
- [ ] T9: Documentar arquitetura de cache do sistema.
- [ ] T10: Configurar alertas para uso de memória do Redis.

## S4 - Squad 4: Chatwoot & CRM Enhancements
**Foco:** Melhorias no CRM e handoff humano

- [ ] T1: Validar fluxo de handoff OpenClaw -> Chatwoot.
- [ ] T2: Configurar webhooks do Chatwoot para a API.
- [ ] T3: Personalizar canned responses no Chatwoot.
- [ ] T4: Testar Chatwoot Sidekiq workers.
- [ ] T5: Configurar automações nativas do Chatwoot.
- [ ] T6: Adicionar tags automáticas baseadas no fluxo da API.
- [ ] T7: Testar integração nativa do Evolution API no Chatwoot.
- [ ] T8: Criar painel de relatórios operacionais baseado no Chatwoot.
- [ ] T9: Otimizar persistência de conversas Chatwoot -> Supabase.
- [ ] T10: Documentar guia de uso do Chatwoot para operadores.

## S5 - Squad 5: Evolution API & WhatsApp Stability
**Foco:** Estabilidade no gateway de mensageria

- [ ] T1: Atualizar Evolution API (se necessário, sem quebrar).
- [ ] T2: Monitorar latência de mensagens Evolution -> API.
- [ ] T3: Tratar webhooks de status de mensagens (sent, delivered, read).
- [ ] T4: Implementar retry para falhas de envio no Evolution.
- [ ] T5: Testar envio de mídias (PDF, imagens) via Evolution API.
- [ ] T6: Validar fluxo de reconexão de sessão WhatsApp.
- [ ] T7: Otimizar webhook queue no Evolution API.
- [ ] T8: Garantir scrub de PII nos logs do Evolution.
- [ ] T9: Documentar fluxo de autenticação e pareamento WhatsApp.
- [ ] T10: Testar envio massivo com controle de rate limit.

## S6 - Squad 6: OpenClaw Agent AI Readiness
**Foco:** Preparar o bot final (Config, Prompt, Skills)

- [ ] T1: Revisar system prompt do OpenClaw (curto, sério, sem emojis).
- [ ] T2: Habilitar thinkings e deepseek-v4-flash.
- [ ] T3: Validar context window de 1M no OpenClaw.
- [ ] T4: Testar skill 'pii_scrubber' no OpenClaw.
- [ ] T5: Integrar OpenClaw aos MCPs (API, Supabase, Chatwoot).
- [ ] T6: Testar fallback de providers do OpenClaw.
- [ ] T7: Validar hooks do OpenClaw (on_message_in, on_tool_call).
- [ ] T8: Auditar logs gerados pelo OpenClaw Agent.
- [ ] T9: Otimizar consumo de tokens nas chamadas de ferramentas.
- [ ] T10: Documentar capacidades e limitações do Agent.

## S7 - Squad 7: E2E Integration (The Golden Path)
**Foco:** Garantir o fluxo: EVO -> API -> N8N -> CHATWOOT -> REDIS -> SUPA -> EVO

- [ ] T1: Testar fluxo completo de solicitação de certidão.
- [ ] T2: Testar fluxo de agendamento de atendimento.
- [ ] T3: Validar cálculo de emolumentos via N8N -> API.
- [ ] T4: Testar fluxo LGPD (opt-out/esquecimento).
- [ ] T5: Validar handoff humano e retorno ao bot.
- [ ] T6: Testar fluxo com falha em componente (ex: N8N fora).
- [ ] T7: Validar persistência e audit log imutável no Supabase.
- [ ] T8: Testar fallback do Telegram Bot.
- [ ] T9: Verificar latência end-to-end do fluxo.
- [ ] T10: Documentar diagrama atualizado do Golden Path.

## S8 - Squad 8: Security, LGPD & Audit
**Foco:** Segurança, privacidade e logs

- [ ] T1: Auditar regras de PII em todos os pontos de entrada.
- [ ] T2: Verificar integridade do SHA256 chain nos logs.
- [ ] T3: Testar endpoints de exclusão/exportação de dados (LGPD).
- [ ] T4: Revisar permissões SSH e Tailscale da VPS.
- [ ] T5: Validar segredos no Easypanel (sem hardcode).
- [ ] T6: Aplicar rate limits rígidos na API pública.
- [ ] T7: Revisar dependências Python por vulnerabilidades (pip audit).
- [ ] T8: Revisar configurações do Traefik no Easypanel.
- [ ] T9: Documentar política de retenção de dados.
- [ ] T10: Executar simulado de incidente de segurança.

## S9 - Squad 9: Observability, Metrics & FinOps
**Foco:** Monitoramento e controle de custos

- [ ] T1: Integrar painéis do Grafana para API e N8N.
- [ ] T2: Configurar Prometheus para raspar métricas da FastAPI.
- [ ] T3: Monitorar consumo de tokens do OpenClaw.
- [ ] T4: Criar alertas no Telegram para erros 5xx na API.
- [ ] T5: Monitorar uso de disco/CPU da VPS Hostinger.
- [ ] T6: Auditar custos de API externas (LLM, Evolution).
- [ ] T7: Centralizar logs no Loki.
- [ ] T8: Otimizar tamanho das imagens Docker.
- [ ] T9: Validar uptime checks.
- [ ] T10: Documentar arquitetura de observabilidade.

## S10 - Squad 10: Documentation & Final Polish
**Foco:** Documentação completa e polimento

- [ ] T1: Completar documentação técnica da API no docs/.
- [ ] T2: Documentar todos os workflows do N8N.
- [ ] T3: Revisar documentação das plataformas no docs/platforms/.
- [ ] T4: Atualizar README principal com status final.
- [ ] T5: Refinar logs no PROGRESS.md de cada etapa.
- [ ] T6: Criar guia de troubleshooting operacional.
- [ ] T7: Garantir que 0 warnings existam nos linters (Ruff/MyPy).
- [ ] T8: Limpar comentários antigos e TODOs no código.
- [ ] T9: Preparar release notes da v1.0.0.
- [ ] T10: Ativação final do Agent OpenClaw (Go-Live).
