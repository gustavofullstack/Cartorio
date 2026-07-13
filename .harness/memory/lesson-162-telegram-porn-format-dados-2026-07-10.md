---
name: telegram-porn-format-dados-2026-07-10
description: Free LLM injetava porn; formatacao robótica; cartorio deve aceitar CPF/RG com LGPD
type: project
date: 2026-07-10
priority: P0
status: closed
---

# Lesson 162 — Anti-porn, formatacao humana, dados cartorio

## Sintomas (prints Gustavo)
1. Respostas em bloco denso, sem paragrafo
2. Links pornograficos na conversa oficial do cartorio
3. Bot recusava/confusa com CPF — cartorio PRECISA aceitar com LGPD

## Causa
- `chat_with_fallback` → modelos free (nemotron) alucinam spam/porn
- scrub remove CPF antes do agent → intent `dados` nunca disparava
- formatacao fraca

## Fix LIVE
1. **Sem free LLM** no cartorio_agent (so MiniMax ou offline)
2. `sanitize_bot_output` bloqueia porn/URLs nao oficiais
3. Paths offline para preco/saudacao/catalogo/dados/memoria
4. Aceite CPF/RG/email: ack LGPD + hash Redis `tg:client:{key}`
5. Marcador `DADOS_PESSOAIS_RECEBIDOS` pos-scrub + tokens `[CPF_REDACTED]`
6. `format_bot_text` com paragrafos e linha em branco

Modified by Gustavo Almeida
