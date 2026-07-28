# SESSAO 2026-06-23 PARTE 5 — N8N #03 swap + Chatwoot Agent Bot URL

## Decisao arquitetural: Chatwoot -> N8N (NAO OpenClaw)

Tentei criar endpoint custom no OpenClaw (POST /v1/chatwoot/webhook)
mas:

- OpenClaw eh um app **Node.js bundled** (`/app/dist/`)
- **NAO ha API publica** para criar rotas custom
- Endpoint health existe (200 OK) mas qualquer outro path retorna 404

**Conclusao**: o handler de eventos do Chatwoot deve ser o **N8N**, nao o OpenClaw.
OpenClaw continua sendo o **cerebro do CartorioBot** (LLM + skills), mas o
**gateway de entrada de mensagens** eh o N8N (que ja tem os webhooks).

## Fluxo final

```
Cliente WhatsApp
    -> Evolution API
        -> POST /api/v1/webhook/evolution (workflow #12 v2 chatbot LLM com MCP)
            -> PII scrub
            -> LLM (deepseek-v4-flash via OpenCode-Go MCP)
            -> Response com cartorio-bot skills
        -> Resposta volta para Evolution -> WhatsApp

Cliente Chatwoot (outros canais)
    -> Chatwoot (integra com WhatsApp, email, etc)
        -> Chatwoot Agent Bot 'cartorio-bot' (outgoing_url configurada)
            -> POST https://cartorio-n8n.dfgdxq.easypanel.host/webhook/handoff-human
                -> N8N workflow #03 v2 (handoff com n8n-nodes-chatwoot)
                    -> Processa mensagem
                    -> Faz handoff para escrevente humano
                    -> Notifica Chatwoot Agent Bot da resposta
```

## Acoes executadas

### 1. Workflow #03 v2 importado e ativado

```bash
# Import (POST /workflows)
KEY="<jwt>"
curl -X POST "https://cartorio-n8n.dfgdxq.easypanel.host/api/v1/workflows" \
  -H "X-N8N-API-KEY: $KEY" -H "Content-Type: application/json" \
  -d @/tmp/wf03_v2.json
# id: 00PbDJUpJlrUxAir

# Desativar v1 (conflito de webhook)
curl -X POST ".../workflows/OQRIOVHcOjpkQ0Of/deactivate" -H "X-N8N-API-KEY: $KEY"

# Ativar v2
curl -X POST ".../workflows/00PbDJUpJlrUxAir/activate" -H "X-N8N-API-KEY: $KEY"
```

### 2. Chatwoot Agent Bot outgoing_url

```ruby
# Rails runner no Chatwoot container
bot = AgentBot.find(1)
bot.update(outgoing_url: 'https://cartorio-n8n.dfgdxq.easypanel.host/webhook/handoff-human')
```

**Resultado**: Agent Bot `cartorio-bot` (id=1) agora envia para N8N #03 v2.

## Estatisticas finais

| Metrica | Valor |
|---|---|
| N8N workflows ativos | **30** (3 swap: #03 v1 -> v2, #12 v1 -> v2, #26 ja ativa) |
| OpenClaw skills | 7 (independente de webhooks) |
| Chatwoot Agent Bots | 1 (`cartorio-bot`, outgoing_url -> N8N) |
| Supabase storage buckets | 3 (vazios) |
| Supabase RLS policies | 15 |

## Teste E2E

Para validar o fluxo, o Gustavo precisaria:
1. Abrir Chatwoot UI
2. Conectar uma inbox (whatsapp/email)
3. Mandar uma mensagem de teste
4. Verificar se chega no N8N #03 v2 (N8N UI -> Executions)
5. Verificar se N8N responde no Chatwoot

**Hoje** tudo esta **configurado mas NAO testado** (precisa de inbox real conectada).

## Pendente (SUI Gustavo)

- OpenClaw LLM key (Sprint 3 SUI #5) - sem ela, OpenClaw cai no deepseek-v4-flash
- Conectar WhatsApp real na Evolution instance
- Rotacionar 5 credenciais expostas (N8N, MCP, Chatwoot, OpenCode-Go, Supabase)
- Testar Chatwoot -> N8N -> OpenClaw -> Chatwoot round-trip

## Licoes aprendidas

1. **OpenClaw NAO tem API publica para rotas custom** - eh um app bundled
2. **Chatwoot Agent Bot outgoing_url** aponta para **N8N**, NAO OpenClaw
3. **N8N eh o gateway de integracao**, OpenClaw eh o **cerebro do bot** (LLM + skills)
4. **Webhook path collision** - so pode ter 1 workflow ativo por path
5. **NoOp auto-add** (via import_all_to_n8n.sh) facilita a importacao
