# SESSAO 2026-06-23 PARTE 4 — N8N workflow swap (v1 → v2) + Chatwoot bot URL

## Conquistas desta sessao (continuacao)

### OpenClaw: 7 skills confirmadas em container

Verifiquei que `docker exec cartorio_openclaw-gateway.1.x ls /home/node/.openclaw/plugin-skills/` mostra:

```
cartorio-agendamento.md
cartorio-emolumento-calc.md
cartorio-handoff-trigger.md
cartorio-pesquisa-satisfacao.md
cartorio-protocolo-tracker.md
cartorio-saudacoes.md
cartorio-segunda-via.md
```

**SIGHUP anterior foi suficiente** - restart nao necessario.

### Supabase: 3 storage buckets auditados

```
conversas       | private | 10MB  | 0 objects
documentos      | private | 50MB  | 0 objects
pdfs-assinados  | private | 50MB  | 0 objects
```

**Todos vazios, prontos para uso.** Nenhum cleanup necessario.

### N8N: workflow #12 swap (v1 → v2)

Workflow **#12 - Chatbot LLM End-to-End** tem 3 versoes:
- v1: `(PII + OpenCode-Go)` (id: WuQAi2ttarGGdPyD) - ativa
- v2: `(PII + MCP + OpenCode-Go)` (id: bryQNXccPvOgNhIL) - inativa (criada por mim)
- enhanced: `(PII + Redis + Supabase)` (id: 8mY2uxWByRbYeJdn) - inativa (criada em paralelo)

**Acoes**:
1. Desativar v1: `POST /api/v1/workflows/WuQAi2ttarGGdPyD/deactivate` -> 200 OK
2. Ativar v2: `POST /api/v1/workflows/bryQNXccPvOgNhIL/activate` -> 200 OK

**Resultado**: v1 OFF, v2 ON. Webhook unico (sem conflito).

### N8N: workflow #26 ja estava ativo

Workflow **#26 - Monitor OpenClaw (cron 1min, alerta Chatwoot)** (id: 6e7c830b-4ab8-465e-b9e2-b2a86bc0aca9) ja estava com `active=true` (sessoes paralelas ativaram).

### Chatwoot: Agent Bot outgoing URL

Agent Bot `cartorio-bot` (id=1) configurado com:
- outgoing_url: `http://172.16.2.18:18789/v1/chatwoot/webhook`

**PROBLEMA**: o OpenClaw nao tem um endpoint /v1/chatwoot/webhook ainda. Em Sprint 3.5+:
- Criar endpoint OpenClaw que recebe POST do Chatwoot
- Faz PII scrub
- Encaminha para LLM (OpenCode-Go)
- Retorna resposta humanizada

Quando o cliente manda msg no Chatwoot, o OpenClaw recebe via webhook e responde.

## Estatisticas finais

| Metrica | Valor |
|---|---|
| N8N workflows ativos | 30 (v1 #12 desativada, v2 #12 ativada) |
| OpenClaw skills | 7 |
| Supabase storage buckets | 3 (todos vazios) |
| Supabase indices em webhook_events | 2 (event_id + received_at) |
| RLS policies | 15 (auditadas) |

## Comandos executados

```bash
# Desativar #12 v1
curl -X POST https://cartorio-n8n.dfgdxq.easypanel.host/api/v1/workflows/WuQAi2ttarGGdPyD/deactivate \
  -H "X-N8N-API-KEY: $KEY"
# Ativar #12 v2
curl -X POST https://cartorio-n8n.dfgdxq.easypanel.host/api/v1/workflows/bryQNXccPvOgNhIL/activate \
  -H "X-N8N-API-KEY: $KEY"

# Configurar Chatwoot Agent Bot outgoing URL
docker exec cartorio_chatwoot sh -c "RAILS_ENV=production bundle exec rails runner -e production 'bot = AgentBot.find(1); bot.update(outgoing_url: ...); puts bot.outgoing_url'"
```

## Pendente (SUI Gustavo)

- OpenClaw: criar endpoint `POST /v1/chatwoot/webhook` (Sprint 3.5+)
- Testar manualmente o Chatwoot Agent Bot (conectar conversa de teste)
- Conectar WhatsApp real na Evolution instance
- Rotacionar 5 credenciais expostas (N8N, MCP, Chatwoot, OpenCode-Go, Supabase)

## Licoes aprendidas

1. **Workflows em paralelo podem sumir/renomear** - sempre verificar com `GET /workflows` antes de tentar ativar
2. **Webhook path collision** - so pode ter 1 workflow ativo por path. Antes de ativar v2, desativar v1
3. **OpenClaw nao tem endpoint HTTP por padrao** - o bot precisa ser exposto via reverse proxy ou custom node
4. **N8N API key antiga (rotacionada ontem) ainda eh a unica funcional** - tentativas de criar nova via SQL/UI falharam
