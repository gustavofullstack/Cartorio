---
name: telegram-memory-catalog-series-2026-07-10
description: Bot perdia memoria multi-turn e truncava catalogo; fix history Redis + catalogo_serie deterministico
type: project
date: 2026-07-10
priority: P0
status: closed
---

# Lesson 161 — Memoria multi-turn + catalogo multi-msg

## Sintoma (screenshot Gustavo)
- Pediu cada servico em msgs separadas → so veio #1
- Depois bot: "prompt cortado" / "sou stateless e nao guardo historico"
- Frustracao real na validacao Telegram

## Causa
1. `run_cartorio_agent(text)` SEM `history` (API ja existia, telegram nao passava)
2. LiteLLM MiniMax falha (401/DNS) → fallback free model alucina "stateless"
3. Catalogo multi-msg nao era path deterministico

## Fix (deploy live 2026-07-10)
- Redis `tg:hist:{key}` 24 entradas / 2h TTL
- Intent `catalogo_serie` → 1 intro + 5 servicos + fecho (offline, extras=6)
- Intent `memoria` → resposta firmando memoria ativa
- Scrub frases ruins (stateless / prompt cortado)
- `/start` e `/cancelar` limpam historico

## Evidencia prod
```
TG agent provider=offline:catalogo_serie extras=6 hist=0
TG agent provider=offline tools=['intent:memoria'] hist=8
```

Modified by Gustavo Almeida
