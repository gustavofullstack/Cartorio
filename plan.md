# SUPER PLANO DE MELHORIAS 100 TASKS - CARTÓRIO V2

## SQUAD A (Core API & Dados)
1. **API-001**: Revisão e normalização completa de todos os endpoints FastAPI (status codes e models unificados)
2. **API-002**: Refatoração do `backend/app/services/lgpd_relatorio.py` para otimizar tempo de consulta
3. **API-003**: Injeção robusta de dependências para chamadas Supabase nativas
4. **API-004**: Auditoria rigorosa de PII em todo payload transacionado (Defense-in-depth)
5. **API-005**: Setup de Supabase Queue/Edge Functions p/ tasks pesadas ao invés de sidekiq puro
6. **API-006**: Centralizar todos os Logs em Loki/Grafana via `structlog`
7. **API-007**: Testes E2E (100% cobrindo a jornada de ponta-a-ponta)
8. **API-008**: Implementar Auth-Bypass dev com mocks confiáveis
9. **API-009**: Habilitar Pydantic V2 validations rigorosas e cachear schemas localmente
10. **API-010**: Versionamento estrito v2 de toda rota pública

## SQUAD B (Chatwoot & N8N Integration)
11. **INT-011**: Auditar os 35 workflows N8N p/ usar header de credencial dinâmica
12. **INT-012**: Substituir timeout padrão no N8N e habilitar retry-policies nos hooks
13. **INT-013**: Refatorar `chatwoot_handoff_macros.py` p/ carregar templates do Redis
14. **INT-014**: Documentação E2E de como o CRM injeta dados no N8N (Swagger N8N)
15. **INT-015**: Mapear fallbacks N8N -> API em caso de downtime
16. **INT-016**: Chatwoot: Revisão do Sidekiq limiters p/ evitar crash loops
17. **INT-017**: Chatwoot: Criação de labels automatizados p/ LGPD erasure requests
18. **INT-018**: Chatwoot: Botões interativos nativos (Interactive Messages) no painel
19. **INT-019**: Monitor de fila DLQ p/ webhook Chatwoot falhos (Supabase)
20. **INT-020**: Supabase Webhooks emitindo pro N8N diretamente em inserts de atendimento

## SQUAD C (Evolution API & Telegram Bot)
21. **EVO-021**: Garantir rate limits na Evolution (evitar block da Meta)
22. **EVO-022**: Reconectar e testar E2E as sessões de WhatsApp Business via n8n->evo
23. **EVO-023**: Telegram: Confirmar Mocking no Test_telegram_e2e (mockando LGPD check)
24. **EVO-024**: Teste de carga e stress testing para webhook do Telegram
25. **EVO-025**: Telegram: Implementar cache inline (Redis) p/ deduplicação de mensagens
26. **EVO-026**: Habilitar sendPhoto/sendDocument nos bots (upload file flow)
27. **EVO-027**: Telegram: Bot webhook auto-repair se o token desativar localmente
28. **EVO-028**: Padronizar as macros Telegram (commands /start, /ajuda, /protocolo)
29. **EVO-029**: Evoluir o profile do usuário do chat (nome/telefone auto-capture)
30. **EVO-030**: Monitoramento de Webhook Drop rates da Evolution API

## SQUAD D (Agent AI OpenClaw)
31. **OCL-031**: Fix Deepseek-v4-flash rate limits (Fallback chain p/ MIMO/Nemotron)
32. **OCL-032**: Auditar system_prompt para otimização de tokens de raciocínio
33. **OCL-033**: Testar as 7 skills atuais em paralelo p/ medir overhead de tools (TDD)
34. **OCL-034**: Criar skill mock "cartorio-test" p/ homologação de novas features
35. **OCL-035**: Reduzir temperatura para acts estritamente legais (0.1 ou 0.0)
36. **OCL-036**: Habilitar CORS dinâmicos p/ frontend interagir direto com o Gateway
37. **OCL-037**: Documentar as nuances de context tokens (1M limit vs 131.1k local limit)
38. **OCL-038**: Deploy do workspace JSON diretamente via CI e não manual SSH
39. **OCL-039**: Openclaw: Habilitar modo 'Stream' e integrar frontend WebSocket
40. **OCL-040**: Mapear logs de pensamento (Thinkings) direto pro Supabase Vault

[... 60 additional granular tasks extending across CI/CD, Supabase Vault, Redis optimization, PII sanitization, Testing Harness, and Local development stability ...]
