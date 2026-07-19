# Programa de Integração — 100 tarefas

Status: **ciclo 1 em execução** — 2026-07-19  
Objetivo: disponibilizar atendimento multicanal confiável, observável e LGPD-by-design sem permitir decisão jurídica automática.

## Objetivos mensuráveis

1. Todos os canais passam por autenticação, idempotência, scrubbing de PII e trilha de auditoria.
2. Operações jurídicas permanecem em `DRAFT` até ação humana verificável.
3. SLOs publicados: API P95 < 200 ms (sem LLM), webhooks ACK < 2 s, disponibilidade mensal >= 99,9%.
4. CI/CD bloqueia regressões de tipagem, segurança, audit chain, PII, contratos e E2E críticos.
5. Nenhum segredo é versionado, exibido em logs, documentação ou coleções Postman.

## Regras de execução

- Executar em lotes de quatro tarefas independentes; no máximo quatro responsáveis ativos.
- Toda tarefa segue `analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → memória`.
- Ações sobre `audit*`, `pii*`, dados pessoais, retenção ou LLM exigem revisão LGPD.
- Produção só após aprovação humana, backup validado, rollback documentado e smoke pós-deploy.
- Legenda: `[ ]` pendente, `[~]` em execução, `[x]` validada.

## Gates P0 de entrada

- [ ] G0.1 Inventariar e revogar/rotacionar, por canal seguro, credenciais expostas em arquivos versionados; remover valores sem reexibi-los.
- [ ] G0.2 Corrigir a indisponibilidade pública do Chatwoot (502) com RCA, rollback e teste autenticado de inbox.
- [ ] G0.3 Confirmar endpoint de saúde canônico do n8n e registrar resposta esperada autenticada.
- [ ] G0.4 Conciliar mudanças locais existentes com seus autores; não sobrescrever trabalho em curso.

## Progresso do ciclo 1

- [x] Mitigação imediata: `/api/v1/telegram/debug/last-updates` agora exige `X-API-Key` e retorna somente metadados, sem texto, chat ID ou resposta.
- [x] Lint bloqueante local removido; Ruff e mypy estão verdes.
- [~] 081 Baseline de testes: há duas falhas de contrato a decidir (redação de IP e esquema de segurança OpenAPI); não foram mascaradas.
- [!] Gate impedido: há credenciais aparentes em conteúdo rastreado e o CI atualmente tolera falha do scanner; rotação segura e saneamento precedem ativação.

## E1 — Arquitetura e contratos

| ID | Tarefa | Dono | Critério de aceite |
|---|---|---|---|
| [ ] 001 | Atualizar diagrama C4 de contexto | arquitetura | Canais, bordas de confiança e dados pessoais mapeados. |
| [ ] 002 | Atualizar diagrama de containers | arquitetura | Serviços, redes, portas e dependências reais conferidos. |
| [ ] 003 | Definir contratos de eventos | dev | Schemas versionados para entrada, saída, erro e DLQ. |
| [ ] 004 | Publicar matriz integração × dono | scrum | RACI, SLA, dependências e escalonamento definidos. |
| [ ] 005 | Catalogar APIs e versões | dev | OpenAPI e endpoints obsoletos marcados. |
| [ ] 006 | Catalogar MCPs e tools | dev | Inventário derivado do código, permissões e riscos. |
| [ ] 007 | Definir ACL por integração | dev | Adaptadores isolam modelos Evolution, Telegram e Chatwoot. |
| [ ] 008 | Formalizar estados HITL | lgpd | Transições permitidas e atores auditáveis. |
| [ ] 009 | Definir SLO/SLI e error budget | ops | Métricas, limiares e alertas aprovados. |
| [ ] 010 | Criar ADR de arquitetura alvo | arquitetura | Decisões e rollback registrados. |

## E2 — Segurança, LGPD e segredos

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 011 | Fazer varredura segura de segredos | lgpd | Relatório sem valores e lista de rotação. |
| [ ] 012 | Rotacionar segredos comprometidos | ops | Novos segredos em cofre; antigos revogados. |
| [ ] 013 | Sanitizar histórico/documentação ativa | dev | Nenhuma credencial em arquivos rastreados. |
| [ ] 014 | Validar filtro de logs | dev+lgpd | Testes provam remoção de tokens e PII. |
| [ ] 015 | Validar scrubbing de entrada | dev+lgpd | CPF, RG, telefone e e-mail não chegam a LLM externa. |
| [ ] 016 | Validar scrubbing de saída | dev+lgpd | Saída e erros não ecoam PII. |
| [ ] 017 | Validar audit append-only | dev+lgpd | Chain/HMAC e permissões DB resistem a alteração. |
| [ ] 018 | Revisar RLS e privilégios Postgres | lgpd | Menor privilégio e testes de negação. |
| [ ] 019 | Revisar retenção e eliminação | lgpd | Prazos, hold legal e evidência de execução. |
| [ ] 020 | Atualizar RIPD e política | lgpd | Fluxos multicanal e subprocessadores cobertos. |

## E3 — API, Postgres e Redis

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 021 | Verificar heads Alembic e staging | dev | Uma cabeça e upgrade/reversão testados. |
| [ ] 022 | Validar esquema e índices | dev | Queries críticas sem N+1 e plano documentado. |
| [ ] 023 | Testar backup e restauração Postgres | ops+lgpd | Restore isolado validado com RPO/RTO. |
| [ ] 024 | Validar health/readiness | dev | DB, Redis e audit com respostas corretas. |
| [ ] 025 | Consolidar cliente Redis | dev | Uma abstração tipada e fail-open deliberado. |
| [ ] 026 | Testar idempotência Redis 24h | dev | Reentrega de webhook não duplica efeitos. |
| [ ] 027 | Testar rate limit por IP/chave | dev | Limites e headers corretos em Redis indisponível. |
| [ ] 028 | Validar locks distribuídos | dev | Scheduler multi-réplica executa uma vez. |
| [ ] 029 | Validar DLQ e reprocessamento | dev | Backoff, criptografia e replay auditados. |
| [ ] 030 | Medir latência e cache | dev | P95 e hit ratio publicados. |

## E4 — Webhooks e mensageria

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 031 | Contrato webhook Evolution legado/aninhado | n8n | Ambos formatos aceitos e assinados. |
| [ ] 032 | Validar HMAC de webhooks | dev | Assinaturas inválidas são rejeitadas e auditadas. |
| [ ] 033 | Contrato webhook Telegram | n8n | Secret path e update_id deduplicados. |
| [ ] 034 | Contrato webhook Chatwoot | n8n | Eventos permitidos, assinatura e retry definidos. |
| [ ] 035 | Padronizar envelope de evento | dev | correlation_id e schema_version obrigatórios. |
| [ ] 036 | Implementar inbox transacional | dev | Outbox persiste antes de publicação. |
| [ ] 037 | Testar reentrega e ordem | dev | Eventos duplicados/fora de ordem são seguros. |
| [ ] 038 | Configurar DLQ por canal | n8n | Alertas e replay com aprovação humana. |
| [ ] 039 | Criar testes de contrato | dev | Fixtures sem PII para todos provedores. |
| [ ] 040 | Criar painel de eventos | ops | Volume, falhas, idade e DLQ visíveis. |

## E5 — Telegram, WhatsApp e Chatwoot

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 041 | Reparar e testar Chatwoot | n8n | Saúde, inbox, Sidekiq e API autenticada verdes. |
| [ ] 042 | Configurar bot Telegram canônico | n8n | Webhook e `/start` verificados sem token em log. |
| [ ] 043 | E2E Telegram consulta segura | n8n+dev | Consulta permitida retorna resposta mascarada. |
| [ ] 044 | E2E Telegram HITL | n8n+lgpd | Ação jurídica cria somente DRAFT/handoff. |
| [ ] 045 | E2E Evolution/WhatsApp | n8n+dev | Entrada, resposta e idempotência validadas. |
| [ ] 046 | Handoff Chatwoot | n8n+lgpd | Conversa, motivo, labels e responsável auditados. |
| [ ] 047 | Sincronizar status bot/humano | n8n | Pausa humana bloqueia automação imediatamente. |
| [ ] 048 | Templates de resposta seguros | lgpd | Sem promessa jurídica e com escopo claro. |
| [ ] 049 | Testar erro/retry por canal | n8n | Backoff não gera duplicidade. |
| [ ] 050 | Publicar runbook multicanal | n8n | On-call consegue diagnosticar e reverter. |

## E6 — OpenClaw, LobeChat, LLM e MCP

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 051 | Inventariar OpenClaw e LobeChat | n8n | Versões, rotas, auth e dependências confirmadas. |
| [ ] 052 | Validar proxy LobeChat/OpenClaw | ops | Rotas Traefik, timeout e websocket funcionam. |
| [ ] 053 | Revisar persona e brain.md | lgpd | Escopo, HITL e proibições explícitos. |
| [ ] 054 | Versionar skills e tools | dev | Registry tipado, permissões e owner por tool. |
| [ ] 055 | Aplicar allowlist MCP | dev+lgpd | Tools perigosas exigem confirmação/actor humano. |
| [ ] 056 | Testar MCP PII boundary | dev+lgpd | Inputs/outputs MCP são scrubbed. |
| [ ] 057 | Testar fallback LLM | dev | Failover previsível, sem vazamento de contexto. |
| [ ] 058 | Limitar contexto e memória | lgpd | Retenção, redaction e budget de tokens definidos. |
| [ ] 059 | Avaliar prompt injection | lgpd | Casos hostis falham fechados e geram alerta. |
| [ ] 060 | E2E agente→tool→HITL | dev+n8n | Tool só realiza ação autorizada e auditada. |

## E7 — WebSocket, tempo real e frontend operacional

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 061 | Mapear endpoint WebSocket | dev | Auth, origem, mensagens e limites documentados. |
| [ ] 062 | Validar upgrade no proxy | ops | Ping/pong, timeout e headers sobrevivem Traefik. |
| [ ] 063 | Testar concorrência WS | dev | Conexões paralelas não vazam dados entre atendimentos. |
| [ ] 064 | Testar reconexão e cursor | dev | Cliente recupera eventos sem duplicar estado. |
| [ ] 065 | Implementar autorização por conversa | dev+lgpd | Usuário só lê conversas permitidas. |
| [ ] 066 | Criar dashboard de escrevente | n8n | Fila, sugestão, HITL e auditoria utilizáveis. |
| [ ] 067 | Exibir status de integrações | ops | Radar mostra degradado, não apenas online/offline. |
| [ ] 068 | Criar alerta de WS degradado | ops | Alarmes incluem taxa de reconexão e backlog. |
| [ ] 069 | E2E atendimento em tempo real | dev+n8n | Cenário humano validado em ambiente seguro. |
| [ ] 070 | Testar acessibilidade e erro UI | n8n | Estados de falha têm ação clara. |

## E8 — Rede, proxy, DNS e plataforma

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 071 | Inventariar DNS público e interno | ops | Domínio, destino, TTL e dono registrados. |
| [ ] 072 | Validar TLS e renovação | ops | Cadeia, expiração e monitoramento corretos. |
| [ ] 073 | Revisar Traefik middlewares | ops+lgpd | Auth, CORS, rate limit e logs seguros. |
| [ ] 074 | Validar Tailscale ACL/MagicDNS | ops | Apenas dispositivos/rotas necessários permitidos. |
| [ ] 075 | Testar conectividade privada | ops | Serviços internos indisponíveis pela internet. |
| [ ] 076 | Segmentar redes Docker | ops | DB/Redis sem portas públicas não autorizadas. |
| [ ] 077 | Verificar healthchecks Swarm | ops | Falha aciona restart seguro e alerta. |
| [ ] 078 | Testar rollback de serviço | ops | Imagem/configuração anterior restaura serviço. |
| [ ] 079 | Validar capacidade e recursos | ops | CPU, memória, disco e conexão dentro de limites. |
| [ ] 080 | Publicar runbook incidente rede | ops | RCA, mitigação e comunicação padronizadas. |

## E9 — Qualidade, CI/CD e observabilidade

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 081 | Executar baseline de testes | dev | Resultado e lacunas registrados. |
| [ ] 082 | Fazer lint/format/typecheck | dev | Ruff e mypy sem erros novos. |
| [ ] 083 | Cobrir contratos críticos | dev | Testes Telegram, Chatwoot, Evolution, MCP e WS. |
| [ ] 084 | Validar cobertura >= 90% | dev | Gate CI reproduzível localmente. |
| [ ] 085 | Revisar pipeline CI | dev | Dependências, cache e secrets por ambiente corretos. |
| [ ] 086 | Revisar CD e approvals | ops | Staging antes de produção e rollback obrigatório. |
| [ ] 087 | Validar scanner SAST/dependências | dev+lgpd | Achados priorizados e sem bypass indevido. |
| [ ] 088 | Validar traces ponta a ponta | ops | correlation_id atravessa canal, API e worker. |
| [ ] 089 | Validar métricas e alertas | ops | Dashboards têm owner, limiar e runbook. |
| [ ] 090 | Executar teste de carga seguro | dev+ops | Limites e degradação controlada documentados. |

## E10 — Operação, documentação e lançamento

| ID | Tarefa | Dono | Critério de aceite |
| [ ] 091 | Atualizar Swagger/OpenAPI | dev | Exemplos sem PII e códigos de erro completos. |
| [ ] 092 | Atualizar coleção Postman | dev | Variáveis vazias, testes e ambiente seguro. |
| [ ] 093 | Atualizar brain.md e harness | arquitetura | Metas, regras e skills refletem o sistema real. |
| [ ] 094 | Consolidar runbooks | ops | Onboarding, incidentes, backup e rollback acessíveis. |
| [ ] 095 | Registrar ADRs pendentes | arquitetura | Decisões de risco com alternativas e data. |
| [ ] 096 | Registrar memória reutilizável | todos | Somente lições não óbvias e sem segredos. |
| [ ] 097 | Fazer revisão de segurança final | lgpd | Checklist LGPD, PII, audit e HITL assinado. |
| [ ] 098 | Fazer homologação operacional | scrum | Donos aprovam cenários e evidências. |
| [ ] 099 | Fazer go/no-go | direção | Riscos aceitos explicitamente e rollback pronto. |
| [ ] 100 | Monitorar janela de estabilidade | ops | 72h com SLOs e incidentes reportados. |

## Primeiro lote proposto

Após finalizar os gates G0, iniciar simultaneamente as tarefas 001, 011, 021 e 041. Elas atacam contrato, segredos, dados e o canal atualmente indisponível, sem sobrepor arquivos críticos.
