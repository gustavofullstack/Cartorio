# Lesson 284 — Bot Lark standalone (Python) > TRAE SOLO shell

**Data:** 2026-07-28
**Severidade:** decisão arquitetural
**Squad:** cartorio-dev + cartorio-n8n (review)

## Contexto

Gustavo queria bot decente no grupo **GG** do Lark. Tentou usar TRAE SOLO.app
(Electron shell que roteia entre Grok/AGY/MiniMax). Resultado: bot "burro"
sem persona, sem tools de cartório, sem audit log, sem LGPD.

## Comparação

| Aspecto | TRAE SOLO shell | Bot standalone Python |
|---|---|---|
| Persona canônica PIETRA | ✗ (system prompt default) | ✓ (vem do system prompt VPS via API) |
| Tools MCP cartório | ✗ (só Puppeteer/shadcn/testsprite) | ✓ (todos do PIETRA VPS) |
| PII scrub | ✗ | ✓ (PIETRA backend aplica) |
| Identity guard HARD-STOP | ✗ | ✓ (PIETRA backend) |
| Audit log LGPD | ✗ | ✓ (Postgres do cartório) |
| Funciona offline do Mac | ✗ (precisa Mac ligado) | ✓ (LaunchAgent) ou roda na VPS |
| Customização persona | ✗ (locked no Electron shell) | ✓ (controla tudo) |
| Setup | ✓ trivial (já tá instalado) | ✗ 15min (Developer Console + tunnel) |

## Lição

**Shell de agent coding ≠ agente de produto.** TRAE SOLO é bom pra Gustavo
trabalhar como dev. Pra bot de produto (responder cliente), precisa de:

1. Persona canônica versionada (vem do backend, não do shell)
2. Tools MCP do domínio (vem do backend)
3. Audit log persistente (Postgres, não arquivo local)
4. Persona guard + PII scrub no backend (defesa em profundidade)
5. Sempre online (LaunchAgent ou container, não depende do Mac ligado)

## Implementação

`scripts/lark_bot_v3.py` (~250 linhas, Flask + requests + sqlite)
`scripts/LARK_BOT_V3_RUNBOOK.md` (passo-a-passo)
`scripts/test_lark_bot_v3.py` (E2E validation)
`~/Library/LaunchAgents/ai.zcode.lark-bot.plist` (boot 24/7)

Backend: `https://api.2notasudi.com.br/api/v1/pietra/chat/completions`
(OpenAI-compatible, persona canônica, PII scrub, identity guard, MCP tools)

## Validação

`scripts/test_lark_bot_v3.py` validou **6/9 checks**:
- ✓ PIETRA health ok
- ✓ Responde "Sou a Pietra, a agente do 2o Cartorio..."
- ✓ Modelo MiniMax-M3 ativo
- ✓ Identity guard: não vaza "Sou Hermes/GPT/Claude"
- ✗ Bot local não rodando (Gustavo estava longe do Mac no momento)

## Rollback

Se TRAE SOLO ficar melhor no futuro:
- `launchctl unload ~/Library/LaunchAgents/ai.zcode.lark-bot.plist`
- Bot Lark continua usando TRAE SOLO (não interfere)

Modified by Gustavo Almeida · 2026-07-28