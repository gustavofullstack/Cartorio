# 🚀 PLANO DE TRANSFORMAÇÃO N8N → AI — Turno 45

> **Objetivo**: Transformar N8N em ORQUESTRADOR LEVE. Todo trabalho pesado vai para OpenClaw (AI agents via MCP/SDK/CLI/ACPX).
> **Entrega HOJE**: Telegram 100% funcional para teste com galera do cartório.

## 1. Arquitetura Target

### Antes (N8N faz tudo)
```
[WhatsApp/Telegram] → N8N workflow (HTTP + LLM + DB + formatação) → resposta
```

### Depois (N8N orquestra, OpenClaw processa)
```
[WhatsApp/Telegram/Web] 
    → N8N webhook (TRIAGEM RÁPIDA)  [N8N: <50ms]
        → OpenClaw AI agent (MCP/SDK/ACPX)  [OpenClaw: 1-30s, faz tudo]
            → Resposta inteligente contextual
```

## 2. Workflows MANTIDOS (N8N)

Apenas **3 essenciais**:
- **EVO-IN** (Evolution Webhook) — entrada WhatsApp
- **Telegram Webhook** — entrada Telegram
- **Webhook Handoff** — escalonamento para humano

Tudo mais vai para OpenClaw como **AI tool** (cada `tool` no OpenClaw = 1 capability).

## 3. Workflows ELIMINADOS (viram tools OpenClaw)

| N8N workflow | OpenClaw tool |
|---|---|
| 01-Consulta-Emolumento | `consultar_emolumento(tipo, folhas)` |
| 02-Criar-Protocolo | `criar_protocolo(...)` |
| 04-Boa-Vinda-LGPD | `boas_vindas_lgpd(cliente)` |
| 04-Consulta-Protocolo | `consultar_protocolo(numero)` |
| 05-Agendamento | `agendar_atendimento(...)` |
| 06-Segunda-Via | `gerar_segunda_via(protocolo)` |
| 10-FAQ | `responder_faq(pergunta)` — RAG knowledge |
| 12-Chatbot-LLM | substituído por OpenClaw direto |
| 14-OpenCode-Fallback | removido — OpenClaw já é AI |
| 16-Prospeccao | `enriquecer_lead(...)` |
| 18-Followup | `followup_d7(cliente)` |
| 23-LGPD-Esqueci | `processar_esquecimento_lgpd(cliente_id)` |
| 26-Alerta-Critico | `alerta_critico(tipo, msg)` |
| 27-Welcome-First | `welcome_lgpd(cliente)` |
| All monitor/audit/metrics | permanece no backend (FastAPI) |

## 4. Workflows MANTIDOS (cron + auditoria)

- 00 - Error Handler Global
- 08 - Audit Verify Diario
- 11 - Monitor Cartório
- 21 - Backup Status 5min
- 22 - Audit Verify 6h
- 23 - Cron Stale Detector
- 24 - Daily Cleanup
- 24 - Retenção Diaria
- 25 - Metrics Collector
- 25 - Protocolo Concluido (cron → PDF)
- 28 - Audit Snapshot
- 29 - Rate Limit Reset
- 30 - Health Deep Check
- 31 - Telegram Listener (mantido com fix)

## 5. Telegram 100% (HOJE)

### Camadas:
1. **N8N webhook** `telegram-cartoriobot` recebe update do Telegram
2. N8N faz **triagem** (comando vs mensagem)
3. Se for comando → executa direto (N8N node)
4. Se for mensagem → encaminha para **OpenClaw AI**
5. OpenClaw processa e responde
6. N8N envia resposta via Telegram Bot API

### Comandos (N8N resolve direto):
- `/start` → menu principal
- `/menu` → mostra opções
- `/agendar` → inicia agendamento
- `/documento` → consulta documento
- `/humano` → handoff para escrevente

### Mensagens livres → OpenClaw:
- Saudação, perguntas, reclamações, etc.

## 6. Cronograma de Execução (HOJE)

| # | Tarefa | ETA |
|---|---|---|
| 1 | Investigar `/webhook/telegram-cartoriobot` 404 | 5min |
| 2 | Recriar webhook Telegram com fluxo AI | 15min |
| 3 | Ativar webhook de teste com OpenClaw | 10min |
| 4 | Validar fluxo end-to-end | 5min |
| 5 | Documentar para galera do cartório | 5min |
| 6 | Salvar memory | 5min |

**Total**: ~45 min para Telegram 100%

## 7. Próximo (depois de Telegram)

- WhatsApp Evolution API (similar ao Telegram)
- Handoff para humanos (Chatwoot)
- Documentação
