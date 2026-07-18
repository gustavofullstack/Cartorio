# SUPER PLANO G8 — 100 Tasks · 25 Squads · 4 Agents/Squad
**Cartório 2º Notas · Integração Total & Hardening Extremo**
**Base:** pós-G7 Wave 28 (2026-07-17)
**Orquestrador:** harness + 4 reins (dev / n8n / lgpd / sre)

---

> **HONESTY GATE:** `[x]` só com evidência. **48/100** (Wave 44: G8.16.T4).

## META

Fechar integração completa e hardening de toda a stack: API ↔ Telegram ↔ Chatwoot ↔ LobeChat ↔ Redis ↔ Postgres ↔ MCPs ↔ WS ↔ Webhooks ↔ Tailscale ↔ Proxy ↔ DNS ↔ OpenClaw agent ↔ tools/skills ↔ brain ↔ harness ↔ Postman ↔ Swagger ↔ radar com SOLID/DRY/KISS, tipagem forte, CI/CD verde e MVP operacional.

Ver **SUPER_GOALS_G8.md** para metas percentuais e Definition of Done resumido.  
**DoR/DoD canônico (honesty gate):** [`docs/G8_DOR_DOD.md`](docs/G8_DOR_DOD.md).

---

## SQUADS (25 × 4 tasks = 100)

### Squad 01 — API Core & WebSockets Hardening (dev×4)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.01.T1 | Testar resiliência de conexões WebSocket sob concorrência de 100+ conexões simultâneas simuladas. | [x] | cartorio-dev |
| G8.01.T2 | Otimizar buffering de mensagens grandes em streams de logs e radar endpoints. | [x] | cartorio-dev |
| G8.01.T3 | Implementar heartbeat ping/pong robusto no WebSocket de atendimento. | [x] | cartorio-dev |
| G8.01.T4 | Criar testes automatizados para conexões de WebSocket concorrentes no mock da API. | [x] | cartorio-dev |

### Squad 02 — Telegram Production & Multi-Turn (dev+n8n)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.02.T1 | Configurar histórico multi-turn Redis com limite de profundidade dinâmica de tokens. | [x] | cartorio-dev |
| G8.02.T2 | Tratar erros de payload e formatação do Telegram de modo amigável e sem vazamento de stacktrace. | [x] | cartorio-dev |
| G8.02.T3 | Desenhar workflow de debounce para mensagens duplicadas vindas da API do Telegram. | [x] | cartorio-n8n |
| G8.02.T4 | Criar 10 cenários de teste de integração para o bot de Telegram simulando sessões longas. | [x] | cartorio-dev |

### Squad 03 — Chatwoot Handoff & HITL (n8n+lgpd)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.03.T1 | Desenvolver webhook receiver na API FastAPI para eventos `conversation_status_changed` do Chatwoot. | [x] | cartorio-dev |
| G8.03.T2 | Desativar respostas automáticas do bot no Redis assim que o escrevente assumir a conversa (HITL). | [x] | cartorio-dev |
| G8.03.T3 | Implementar workflow n8n que sincroniza estados do Chatwoot para desvio de mensagens a humanos. | [x] | cartorio-n8n |
| G8.03.T4 | Validar o fluxo de exclusão/anonimização de dados no Chatwoot para cumprir Art. 18 LGPD. | [x] | cartorio-lgpd |

### Squad 04 — LobeChat & OpenClaw Agent Sync (dev+sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.04.T1 | Integrar OpenClaw no radar de status da API FastAPI (`/health/radar/expanded`). | [x] | cartorio-dev |
| G8.04.T2 | Desenvolver script para empacotamento e export do prompt de sistema do LobeChat. | [x] | cartorio-dev |
| G8.04.T3 | Validar rotação de credenciais do OpenClaw no ambiente local de forma segura. | [x] | cartorio-lgpd |
| G8.04.T4 | Configurar roteamento de requisições de LobeChat para múltiplos nós do OpenClaw no Traefik. | [x] | cartorio-sre |

### Squad 05 — Redis Caching & Idempotency (dev+n8n)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.05.T1 | Revisar configurações de expiração (TTL) e eviction no Redis para dados temporários de sessões. | [x] | cartorio-dev |
| G8.05.T2 | Padronizar validação de `X-Idempotency-Key` em todos os webhooks de entrada. | [x] | cartorio-n8n |
| G8.05.T3 | Criptografar chaves de busca baseadas em CPF/CNPJ no cache do Redis. | [x] | cartorio-lgpd |
| G8.05.T4 | Criar testes de estresse para validação de chaves idempotentes sob alta concorrência. | [x] | cartorio-dev |

### Squad 06 — Postgres & Supabase Database Engineering (dev+sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.06.T1 | Otimizar índices nas tabelas `atendimento`, `protocolo` e `audit_log` para acelerar relatórios. | [x] | cartorio-dev |
| G8.06.T2 | Implementar dumps criptografados automatizados e verificar rotas de restauração seguras. | [x] | cartorio-sre |
| G8.06.T3 | Validar políticas de RLS (Row Level Security) em todas as tabelas com informações de clientes. | [x] | cartorio-lgpd |
| G8.06.T4 | Criar triggers no Supabase para alertar o n8n sobre modificações críticas em metadados. | [x] | cartorio-n8n |

### Squad 07 — MCP Servers & Tools Expansion (dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.07.T1 | Implementar testes de integração mockados para todas as tools expostas no `mcp_server.py`. | [x] | cartorio-dev |
| G8.07.T2 | Criar nova ferramenta MCP para validação de hash sequencial da cadeia de auditoria. | [x] | cartorio-dev |
| G8.07.T3 | Adicionar interceptor no MCP server para filtrar e mascarar dados sensíveis de saída. | [x] | cartorio-lgpd |
| G8.07.T4 | Integrar status de execução de tools MCP no painel de radar. | [x] | cartorio-dev |

### Squad 08 — Webhooks, DLQ & Retry (dev+n8n)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.08.T1 | Refatorar a classe `dlq.py` para permitir expiração e descarte de eventos obsoletos. | [x] | cartorio-dev |
| G8.08.T2 | Adicionar criptografia de payload de webhooks falhos na tabela de persistência do DLQ. | [x] | cartorio-lgpd |
| G8.08.T3 | Integrar alertas de falhas recorrentes de webhook (DLQ) ao Telegram do escrevente. | [x] | cartorio-n8n |
| G8.08.T4 | Escrever testes de integração injetando falhas nas conexões externas para validar DLQ. | [x] | cartorio-dev |

### Squad 09 — Tailscale & SSH Private Routing (sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.09.T1 | Criar probe interna de conectividade para testar latência dentro da VPN Tailscale. | [x] | cartorio-sre |
| G8.09.T2 | Configurar MagicDNS para redirecionar tráfego interno de banco e API sem expor portas publicamente. | [x] | cartorio-sre |
| G8.09.T3 | Assegurar que dados pessoais e logs trafeguem estritamente por túneis privados. | [x] | cartorio-lgpd |
| G8.09.T4 | Validar o fluxo de acesso SSH seguro apenas a partir de nós autorizados na Tailscale. | [x] | cartorio-sre |

### Squad 10 — Proxy Traefik & DNS Cloudflare Routing (sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.10.T1 | Adicionar identificador dinâmico de host de processamento nas respostas HTTP. | [x] | cartorio-sre |
| G8.10.T2 | Integrar verificação de DNS automatizada via API Cloudflare no pipeline CI/CD. | [x] | cartorio-sre |
| G8.10.T3 | Configurar mascaramento de requisições de auditoria nos arquivos de log do Traefik. | [x] | cartorio-lgpd |
| G8.10.T4 | Criar testes automatizados de roteamento externo simulando perda de pacotes. | [x] | cartorio-sre |

### Squad 11 — SOLID & Clean Architecture Drivers (dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.11.T1 | Refatorar controllers FastAPI para isolar lógica de negócio em services desacoplados. | [x] | cartorio-dev |
| G8.11.T2 | Implementar injeção de dependências explícita para serviços de e-mail e mensageria. | [x] | cartorio-dev |
| G8.11.T3 | Isolar a lógica de validação fiscal de emolumentos notariais de outras regras da API. | [x] | cartorio-dev |
| G8.11.T4 | Adicionar testes de unidade focados em acoplamento e independência de camadas. | [x] | cartorio-dev |

### Squad 12 — DRY, KISS & Codebase Cleanup (dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.12.T1 | Identificar e unificar rotinas duplicadas de PII masking no backend. | [x] | cartorio-dev |
| G8.12.T2 | Remover arquivos e diretórios n8n órfãos da pasta de infraestrutura. | [x] | cartorio-n8n |
| G8.12.T3 | Padronizar formatação e nomenclatura de chaves no Redis em todas as classes de serviço. | [x] | cartorio-dev |
| G8.12.T4 | Validar ausência de código morto no diretório `/app` via análise estática. | [x] | cartorio-dev |

### Squad 13 — Strong Typing & Strict Validation (dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.13.T1 | Forçar Pydantic ConfigDict strict=True em todos os modelos de requisição notarial. | [ ] | cartorio-dev |
| G8.13.T2 | Validar schemas de imports JSON no n8n de forma estrita. | [ ] | cartorio-n8n |
| G8.13.T3 | Implementar tipos personalizados Pydantic (ex: CPFStr, CNPJStr) para validações de formato rígidas. | [ ] | cartorio-lgpd |
| G8.13.T4 | Resolver quaisquer advertências remanescentes do mypy strict no backend. | [ ] | cartorio-dev |

### Squad 14 — CI/CD Pipeline Automation (sre+dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.14.T1 | Otimizar cache e tempos de execução do pytest no GitHub Actions. | [ ] | cartorio-sre |
| G8.14.T2 | Configurar deploys condicionais baseados no sucesso absoluto de todas as quality gates. | [ ] | cartorio-sre |
| G8.14.T3 | Adicionar secrets scanning avançado no CI para detectar chaves brutas de homologação. | [ ] | cartorio-lgpd |
| G8.14.T4 | Automatizar export e linting dos workflows JSON do n8n pré-commit. | [ ] | cartorio-n8n |

### Squad 15 — Radar, Metrics & Observability (sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.15.T1 | Adicionar instrumentação com Prometheus para latência de processamento de IA. | [ ] | cartorio-sre |
| G8.15.T2 | Habilitar alertas no AlertManager do Prometheus enviando logs formatados ao Telegram. | [ ] | cartorio-sre |
| G8.15.T3 | Validar que labels do Prometheus e campos do Loki não exponham dados sensíveis. | [ ] | cartorio-lgpd |
| G8.15.T4 | Integrar status de filas do Redis no radar `/health/radar/expanded`. | [ ] | cartorio-dev |

### Squad 16 — Agility, Scrum & Progress Tracking (brain)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.16.T1 | Criar automação para persistência do progresso diário no `PROGRESS.md`. | [ ] | cartorio-sre |
| G8.16.T2 | Definir e documentar o DoR (Definition of Ready) e DoD (Definition of Done) do G8. | [x] | cartorio-dev |
| G8.16.T3 | Integrar verificação de consentimento de privacidade no ciclo de tarefas de negócio. | [ ] | cartorio-lgpd |
| G8.16.T4 | Gerar relatórios automatizados de estabilidade a cada iteração de loop finalizada. | [x] | cartorio-dev |

### Squad 17 — Postman & Swagger Real Sync (dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.17.T1 | Criar script python para regenerar e sincronizar Postman Collection a partir do Swagger OpenAPI. | [ ] | cartorio-dev |
| G8.17.T2 | Documentar schemas de payload detalhados para todos os webhooks no Swagger. | [ ] | cartorio-dev |
| G8.17.T3 | Identificar e marcar campos que possuem dados sensíveis nos schemas OpenAPI. | [ ] | cartorio-lgpd |
| G8.17.T4 | Validar o fluxo de autenticação persistida (persistAuthorization) do Swagger local. | [ ] | cartorio-dev |

### Squad 18 — PII Scrubbing & LGPD (lgpd)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.18.T1 | Ampliar expressões regulares e dicionários de termos sensíveis do interceptor pré-LLM. | [ ] | cartorio-lgpd |
| G8.18.T2 | Escrever testes simulando vazamento de múltiplos documentos judiciais no chat. | [ ] | cartorio-dev |
| G8.18.T3 | Concluir e revisar o Relatório de Impacto à Proteção de Dados (RIPD) do Cartório v1.5. | [ ] | cartorio-lgpd |
| G8.18.T4 | Configurar o Sentry before_send para remover PII dos metadados de requisição em falhas de produção. | [ ] | cartorio-lgpd |

### Squad 19 — Audit Logging & HMAC Chain (lgpd+dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.19.T1 | Validar a integridade da blockchain de auditoria comparando hashes salvos vs recalculados. | [ ] | cartorio-dev |
| G8.19.T2 | Criar roteador de chaves para rotação de HMAC sem parada ou rejeição de logs ativos. | [ ] | cartorio-dev |
| G8.19.T3 | Implementar travas de banco de dados (rules/RLS) que impeçam edits e deletes na tabela `audit_log`. | [ ] | cartorio-lgpd |
| G8.19.T4 | Desenhar auditoria interna para modificações nos workflows críticos do n8n. | [ ] | cartorio-n8n |

### Squad 20 — Emolumentos MG 2026 Upgrades (dev)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.20.T1 | Atualizar e testar precisão matemática da calculadora de emolumentos notariais de MG para 2026. | [ ] | cartorio-dev |
| G8.20.T2 | Desenhar workflow de orçamento de escrituras e certidões no n8n. | [ ] | cartorio-n8n |
| G8.20.T3 | Mascarar valores financeiros atrelados ao nome de clientes em relatórios e logs de depuração. | [ ] | cartorio-lgpd |
| G8.20.T4 | Criar testes unitários para verificação de limites mínimos, máximos e isenções tributárias. | [ ] | cartorio-dev |

### Squad 21 — OpenClaw Skills Orchestration (dev+n8n)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.21.T1 | Registrar e testar novas skills criadas para o OpenClaw no diretório `.agents/skills`. | [ ] | cartorio-dev |
| G8.21.T2 | Criar barramento de mensageria assíncrona entre OpenClaw e n8n para jobs longos. | [ ] | cartorio-n8n |
| G8.21.T3 | Garantir o fluxo de HITL escrevente em todas as sugestões do OpenClaw para minutas notariais. | [ ] | cartorio-lgpd |
| G8.21.T4 | Otimizar limites de uso de memória dos contêineres de plugins do OpenClaw. | [ ] | cartorio-sre |

### Squad 22 — Evolution API WhatsApp (n8n+sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.22.T1 | Testar robustez de tratamento de mensagens de áudio, imagem e documentos na Evolution API. | [ ] | cartorio-n8n |
| G8.22.T2 | Criar workflows de monitoramento e alertas se a instância Evolution perder conexão. | [ ] | cartorio-n8n |
| G8.22.T3 | Implementar TTL rígido de 24 horas no banco de dados temporário de mensagens de WhatsApp. | [ ] | cartorio-lgpd |
| G8.22.T4 | Otimizar concorrência de chamadas entre a API do Evolution e o backend via Redis. | [ ] | cartorio-sre |

### Squad 23 — Security & Secrets Scanning (sre)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.23.T1 | Garantir que segredos em env vars lidos de `.env` não vazem para stderr/stdout no startup. | [ ] | cartorio-sre |
| G8.23.T2 | Executar scripts de escaneamento de credenciais no pipeline de pre-commit e CI/CD. | [ ] | cartorio-sre |
| G8.23.T3 | Validar segurança física e RLS de acesso à criptografia de dados (envelope encryption). | [ ] | cartorio-lgpd |
| G8.23.T4 | Implementar rotação de tokens de autenticação n8n no backend. | [ ] | cartorio-n8n |

### Squad 24 — Super Teste Validador (all)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.24.T1 | Expandir o `scripts/g7_super_validator.py` para incluir asserções do G8. | [ ] | cartorio-dev |
| G8.24.T2 | Habilitar verificação integrada de DNS, rotas de API e conexões de rede no validador Make. | [ ] | cartorio-sre |
| G8.24.T3 | Assegurar cobertura mínima geral de 96% de código em todos os módulos alterados. | [ ] | cartorio-lgpd |
| G8.24.T4 | Testar robustez com payloads fakes complexos no validador do n8n. | [ ] | cartorio-n8n |

### Squad 25 — Go-Live & Memory Matrix (all)
| ID | Task | Done | Agent |
|----|------|------|-------|
| G8.25.T1 | Documentar todas as lições aprendidas (lessons) do ciclo G8 no índice `.harness/memory/MEMORY.md`. | [ ] | cartorio-dev |
| G8.25.T2 | Gerar pacote final exportado de workflows n8n com tags de versão no Git. | [ ] | cartorio-n8n |
| G8.25.T3 | Atualizar e publicar a política de privacidade do Cartório na versão v4. | [ ] | cartorio-lgpd |
| G8.25.T4 | Iniciar o monitoramento de estabilidade por 72 horas com os healthchecks verdes em produção. | [ ] | cartorio-sre |

---

## WAVE MAP (4 tasks por wave)

| Wave | Tasks | Focus |
|------|-------|-------|
| W29 | G8.01.T1, G8.01.T2, G8.01.T3, G8.01.T4 | **Squad 01** WS Concorrência e Buffering |
| W30 | G8.02.T1, G8.02.T2, G8.02.T3, G8.02.T4 | **Squad 02** Telegram Multi-turn & Erros |
| W31 | G8.03.T1, G8.03.T2, G8.03.T3, G8.03.T4 | **Squad 03** Chatwoot Webhooks & HITL |
| W32 | G8.04.T1, G8.04.T2, G8.04.T3, G8.04.T4 | **Squad 04** LobeChat & OpenClaw sync |
| W33 | G8.05.T1, G8.05.T2, G8.05.T3, G8.05.T4 | **Squad 05** Redis TTL & Idempotency |
| W34 | G8.06.T1, G8.06.T2, G8.06.T3, G8.06.T4 | **Squad 06** Postgres índices & Backup |
| W35 | G8.07.T1, G8.07.T2, G8.07.T3, G8.07.T4 | **Squad 07** MCP mock tests & Audit tools |
| W36 | G8.08.T1, G8.08.T2, G8.08.T3, G8.08.T4 | **Squad 08** Webhooks, DLQ & Expiry |
| W37 | G8.09.T1, G8.09.T2, G8.09.T3, G8.09.T4 | **Squad 09** Tailscale probes & DNS |
| W38 | G8.10.T1, G8.10.T2, G8.10.T3, G8.10.T4 | **Squad 10** Proxy Traefik headers & Logs |
| W39 | G8.11.T1, G8.11.T2, G8.11.T3, G8.11.T4 | **Squad 11** SOLID decoupling & Injectors |
| W40 | G8.12.T1, G8.12.T2, G8.12.T3, G8.12.T4 | **Squad 12** DRY & KISS cleanup |
| W41 | G8.13.T1, G8.13.T2, G8.13.T3, G8.13.T4 | **Squad 13** Strict Pydantic Custom types |
| W42 | G8.14.T1, G8.14.T2, G8.14.T3, G8.14.T4 | **Squad 14** CI/CD optimization & Secrets scanning |
| W43 | G8.15.T1, G8.15.T2, G8.15.T3, G8.15.T4 | **Squad 15** Radar metrics & AlertManager |
| W44 | G8.16.T1, G8.16.T2, G8.16.T3, G8.16.T4 | **Squad 16** Agility DoR/DoD & Status |
| W45 | G8.17.T1, G8.17.T2, G8.17.T3, G8.17.T4 | **Squad 17** Postman sync & Swagger schemas |
| W46 | G8.18.T1, G8.18.T2, G8.18.T3, G8.18.T4 | **Squad 18** PII Scrubbing regex & Sentry |
| W47 | G8.19.T1, G8.19.T2, G8.19.T3, G8.19.T4 | **Squad 19** Audit sequence & HMAC rotation |
| W48 | G8.20.T1, G8.20.T2, G8.20.T3, G8.20.T4 | **Squad 20** Emolumentos MG precision & budget |
| W49 | G8.21.T1, G8.21.T2, G8.21.T3, G8.21.T4 | **Squad 21** OpenClaw plugins & memory limit |
| W50 | G8.22.T1, G8.22.T2, G8.22.T3, G8.22.T4 | **Squad 22** Evolution API files & WhatsApp TTL |
| W51 | G8.23.T1, G8.23.T2, G8.23.T3, G8.23.T4 | **Squad 23** Security scans & Secrets isolation |
| W52 | G8.24.T1, G8.24.T2, G8.24.T3, G8.24.T4 | **Squad 24** Super Teste Validador checks |
| W53 | G8.25.T1, G8.25.T2, G8.25.T3, G8.25.T4 | **Squad 25** Go-Live docs & stability |

---

## LOOP COMMANDS

```bash
# Executar a próxima wave (orquestrador)
python3 scripts/super_loop_orchestrator.py --wave next --agents 4

# Rodar os testes validadores
make lint && make test-fast && make radar-smoke && make dns-check
```

---

**Modified by Gustavo Almeida + Antigravity AI orquestrador — 2026-07-17 Wave28**
(Plano de Integração Total G8 consolidado de 100 tasks em 25 squads)

### Honesty note (Wave 32)
- Plano G8 foi reescrito com tick fraudulento 100/100 → **reset para 5/100** evidenced.
- Próximas waves: 4 tasks reais com testes/código antes de `[x]`.
- G7 residual SUI 8 [~] permanece em SUPER_PLANO_G7.

### Wave 33 (2026-07-17) — REAL
- G8.07.T2 MCP audit hash sequence + AuditService.verify_hash_sequence
- G8.07.T3 scrub_mcp_output interceptor
- G8.05.T2 X-Idempotency-Key alias webhooks
- G8.01.T4 WS 50 sequential + 20 threaded concurrent mock
- Tests: `backend/tests/test_g8_wave33_mcp_idempotency_ws.py` (35 w/ inventory)
