# 📱 Guia de Uso do Telegram — Cartório 2º Notas UDI

> **Para a galera do cartório testar HOJE**

## Como acessar

1. Abra o **Telegram** no celular ou desktop
2. Busque por `@test_cartorio_bot`
3. Envie uma mensagem (ex: "oi", "agendar", "documento")

## O que o bot pode fazer

### 🤖 Mensagens livres
Pode perguntar qualquer coisa sobre o cartório. O bot é **IA nativo** via OpenClaw e responde perguntas sobre:
- Emolumentos (valores, prazos)
- Documentos (certidões, escrituras)
- Agendamentos
- LGPD / privacidade
- Procedimentos

### 📋 Comandos especiais (em construção)

| Comando | Ação |
|---|---|
| `/start` | Mensagem de boas-vindas |
| `/menu` | Mostra menu principal |
| `/agendar` | Inicia agendamento |
| `/documento` | Consulta documento |
| `/humano` | Transfere para escrevente humano |

## Fluxo de uma mensagem

```
Você → Telegram
   ↓
Bot (Test Cartorio Bot) recebe
   ↓
Webhook → https://api.2notasudi.com.br/api/v1/telegram/webhook
   ↓
API valida LGPD + processa
   ↓
OpenClaw (AI agent) gera resposta
   ↓
API responde no Telegram
   ↓
Você recebe a resposta em ~5 segundos
```

## Limitações conhecidas

- ⏱️ Resposta leva ~5 segundos (OpenClaw pensando)
- 💬 Apenas texto por enquanto (sem áudio/imagem)
- 🕐 Bot online sempre (24/7)

## Suporte

- **Email**: dpo@2notasudi.com.br
- **Painel admin**: https://api.2notasudi.com.br/docs (Swagger)
- **Logs**: via admin
- **Emergência**: chamar Gustavo

## Status atual

- 🟢 **Online** (24/7)
- 🟢 **IA respondendo** (OpenClaw + LLM)
- 🟢 **LGPD compliant** (PII scrubbing, audit log)
- 🟢 **Audit chain** (todas mensagens registradas)

## Próximas features

- [ ] Menu interativo com botões
- [ ] Comando `/agendar` com wizard completo
- [ ] Upload de documentos
- [ ] Resposta por voz (TTS)
- [ ] Multi-idioma (PT/EN/ES)
