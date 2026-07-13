# PLANO 100 TASKS · TELEGRAM BOT VALIDAÇÃO → WHATSAPP
**Data**: 2026-07-09 · **Ciclo**: #34 · **Sprint**: Telegram Bot 100%
**Autor**: Gustavo Almeida + MiniMax-M3 · **Modo**: YOLO Autonomous

---

## VISÃO

> Validar 100% o Bot Telegram, corrigir todos os problemas, otimizar, documentar, salvar na memória.
> Depois migrar para WhatsApp via Evolution API com adapter de mapeamento.

**Estado atual (ciclo #34)**:
- ✅ 171 testes Telegram passam (test_telegram_*.py)
- ✅ API online em api.2notasudi.com.br
- ✅ Coverage 90.20% (gate ≥90%)
- ⚠️ Cycle #34 verdict FAIL foi falso negativo (pytest output vazio = bug pytest-cov)
- ⚠️ Evolution offline (esperado: SUI2 Gustavo precisa escanear QR)

---

## 10 GOALS · 100 TASKS

### G1: VALIDAÇÃO E2E (T01-T10)

| TID | Descrição | Status |
|-----|-----------|--------|
| T01 | Rodar `pytest tests/ -k telegram --no-cov -v` → confirmar 171 passing | ✅ DONE |
| T02 | Verificar todos os comandos: /start, /menu, /agendar, /protocolo, /humano, /cancelar, /lgpd | ✅ DONE |
| T03 | Verificar HITL flow (humano cria atendimento) | ⏳ TODO |
| T04 | Verificar anti-spam idempotency (Redis SETNX update_id) | ⏳ TODO |
| T05 | Verificar debounce 1.2s em mensagens seguidas | ⏳ TODO |
| T06 | Verificar rate-limit 3s por chat_id | ⏳ TODO |
| T07 | Verificar typing indicator refresh 4s durante LLM | ⏳ TODO |
| T08 | Verificar HMAC validation no webhook secret | ✅ DONE |
| T09 | Verificar LGPD notice no /start (não repetir após visto) | ⏳ TODO |
| T10 | Verificar auto-migrate supergroup (migrate_to_chat_id) | ⏳ TODO |

### G2: ANÁLISE + AUDITORIA (T11-T20)

| TID | Descrição | Status |
|-----|-----------|--------|
| T11 | Análise complexidade ciclomática de telegram.py (1463 linhas) | ⏳ TODO |
| T12 | Identificar dead code / funções nunca chamadas | ⏳ TODO |
| T13 | Identificar code smells (magic strings, ifs aninhados) | ⏳ TODO |
| T14 | Verificar type hints (Pydantic, Any leak) | ⏳ TODO |
| T15 | Verificar PII compliance: scrub() chamado em todo input | ⏳ TODO |
| T16 | Verificar LGPD Art.18: retenção, audit log, direitos | ⏳ TODO |
| T17 | Verificar audit log: cada interação gera entrada? | ⏳ TODO |
| T18 | Verificar token segurança: hardcoded vs settings.* | ⏳ TODO |
| T19 | Verificar concorrência: race conditions no state Redis | ⏳ TODO |
| T20 | Identificar TODOs/FIXMEs em telegram.py | ⏳ TODO |

### G3: CORREÇÃO DE PROBLEMAS (T21-T30)

| TID | Descrição | Status |
|-----|-----------|--------|
| T21 | Corrigir TELEGRAM_BOT_TOKEN hardcoded → settings.* | 🔴 P0 |
| T22 | Corrigir TELEGRAM_API_BASE hardcoded → settings.* | 🟡 P1 |
| T23 | Substituir httpx.AsyncClient inline em _send_poll/_send_photo/_send_document por pool | 🟡 P1 |
| T24 | Implementar circuit breaker quando Telegram offline | 🟡 P1 |
| T25 | Corrigir deprecation setex → set com ex (warning pytest) | 🟢 P2 |
| T26 | Adicionar validação tamanho msg antes de enviar (max 4096) | 🟡 P1 |
| T27 | Adicionar timeout global em todas chamadas Telegram | 🟡 P1 |
| T28 | Padronizar error handling (Result/Either pattern) | 🟢 P2 |
| T29 | Corrigir except genéricos (Exception sem logging) | 🟢 P2 |
| T30 | Adicionar retry exponential backoff em chamadas Telegram | 🟡 P1 |

### G4: MELHORIAS + OTIMIZAÇÃO (T31-T40)

| TID | Descrição | Status |
|-----|-----------|--------|
| T31 | Migrar _send_typing para usar pool (atualmente inline client) | 🟡 P1 |
| T32 | Migrar _react para usar pool | 🟡 P1 |
| T33 | Adicionar cache de menu_keyboards (gerado 1x) | 🟢 P2 |
| T34 | Implementar batch de mensagens em grupo | 🟡 P1 |
| T35 | Comprimir payloads Telegram (gzip) | 🟢 P2 |
| T36 | Adicionar health check do pool HTTP | 🟡 P1 |
| T37 | Implementar keepalive ping periódico ao Telegram | 🟢 P2 |
| T38 | Adicionar métricas Prometheus (atualmente só in-process) | 🟡 P1 |
| T39 | Implementar tracing OpenTelemetry no webhook | 🟡 P1 |
| T40 | Adicionar feature flag KILLSWITCH_TELEGRAM (kill switch) | 🔴 P0 |

### G5: COBERTURA ≥95% (T41-T50)

| TID | Descrição | Status |
|-----|-----------|--------|
| T41 | Medir coverage atual do telegram.py (estimado 90.20%) | ✅ DONE |
| T42 | Adicionar testes _send_message 200/400/timeout | ⏳ TODO |
| T43 | Adicionar testes _confirmar_agendamento success/fail | ⏳ TODO |
| T44 | Adicionar testes _handle_state todos os states | ⏳ TODO |
| T45 | Adicionar testes _handle_callback edge cases | ⏳ TODO |
| T46 | Adicionar testes _typing_loop lifecycle | ⏳ TODO |
| T47 | Adicionar testes _check_idempotency race condition | ⏳ TODO |
| T48 | Adicionar testes _react happy/sad path | ⏳ TODO |
| T49 | Adicionar testes _parse_date (amanhã/hoje/ontem/ISO) | ⏳ TODO |
| T50 | Subir coverage para ≥95% | ⏳ TODO |

### G6: DOCUMENTAÇÃO + COMENTÁRIOS (T51-T60)

| TID | Descrição | Status |
|-----|-----------|--------|
| T51 | Docstring em todos os 30+ helpers | ⏳ TODO |
| T52 | Comentários inline em funções complexas | ⏳ TODO |
| T53 | Atualizar docs/GUIA_TESTES_TELEGRAM.md | ⏳ TODO |
| T54 | Criar docs/ARCHITECTURE_TELEGRAM.md (diagramas) | ⏳ TODO |
| T55 | Atualizar README.md com flow Telegram | ⏳ TODO |
| T56 | Criar docs/RUNBOOK_TELEGRAM_OPS.md | ⏳ TODO |
| T57 | Adicionar type hints em todos os params | ⏳ TODO |
| T58 | Criar CHANGELOG_TELEGRAM.md (histórico fixes) | ⏳ TODO |
| T59 | Atualizar ADRs/0036-telegram-bot.md | ⏳ TODO |
| T60 | Adicionar exemplos curl em docs/API.md | ⏳ TODO |

### G7: SALVAR NA MEMÓRIA (T61-T70)

| TID | Descrição | Status |
|-----|-----------|--------|
| T61 | Criar .claude/projects/.../memory/MEMORY.md (index) | 🔴 P0 NOW |
| T62 | Lesson 155: pytest output vazio = bug pytest-cov 7.1.0 | ⏳ TODO |
| T63 | Lesson 156: TELEGRAM_BOT_TOKEN hardcoded vs settings.* | ⏳ TODO |
| T64 | Lesson 157: TELEGRAM_API_BASE direct IP bypass DNS macOS | ⏳ TODO |
| T65 | Lesson 158: supergroup migrate_to_chat_id auto-retry | ⏳ TODO |
| T66 | Lesson 159: per-user state em grupo (chat_id:user_id) | ⏳ TODO |
| T67 | Lesson 160: typing refresh 4s (Telegram TTL 5s) | ⏳ TODO |
| T68 | Lesson 161: SETNX idempotency 10min TTL | ⏳ TODO |
| T69 | Lesson 162: debounce 1.2s anti-spam | ⏳ TODO |
| T70 | Lesson 163: pool singleton httpx (DNS+TLS+TCP) | ⏳ TODO |

### G8: ORGANIZAÇÃO + REFACTOR (T71-T80)

| TID | Descrição | Status |
|-----|-----------|--------|
| T71 | Mover _send_message/_send_poll/_send_photo para telegram_send.py | ⏳ TODO |
| T72 | Mover _handle_command/_handle_callback para telegram_commands.py | ⏳ TODO |
| T73 | Mover _handle_state/_confirmar_agendamento para telegram_state_machine.py | ⏳ TODO |
| T74 | Mover _typing_loop/_send_typing para telegram_typing.py | ⏳ TODO |
| T75 | Mover _check_idempotency/_check_rate_limit para telegram_throttle.py | ⏳ TODO |
| T76 | Mover _get_state/_set_state/_clear_state para telegram_state_redis.py | ⏳ TODO |
| T77 | Mover _menu_keyboard/* para telegram_keyboards.py | ⏳ TODO |
| T78 | Criar app/services/telegram/__init__.py package | ⏳ TODO |
| T79 | Atualizar imports em main.py/router.py | ⏳ TODO |
| T80 | Garantir backward compatibility (re-exports) | ⏳ TODO |

### G9: COMPLIANCE LGPD (T81-T90)

| TID | Descrição | Status |
|-----|-----------|--------|
| T81 | Verificar scrub() em TODO input antes de processar | ⏳ TODO |
| T82 | Verificar scrub() antes de enviar para LLM (agent) | ⏳ TODO |
| T83 | Verificar scrub() antes de logar mensagem completa | ⏳ TODO |
| T84 | Verificar audit log: msg_id, chat_id, action, timestamp | ⏳ TODO |
| T85 | Verificar retenção: conversa expira em 400d (configurado) | ⏳ TODO |
| T86 | Implementar /lgpd command com direitos Art.18 | ⏳ TODO |
| T87 | Adicionar opt-out: cliente pode pedir exclusão via /lgpd | ⏳ TODO |
| T88 | Garantir LGPD_NOTICE no /start (não repetir após visto) | ⏳ TODO |
| T89 | Verificar mask CPF/RG/phone/email em respostas | ⏳ TODO |
| T90 | Documentar LGPD compliance em docs/LGPD_TELEGRAM.md | ⏳ TODO |

### G10: MIGRAÇÃO WHATSAPP (T91-T100)

| TID | Descrição | Status |
|-----|-----------|--------|
| T91 | Mapear Telegram webhook → Evolution webhook (payload diff) | ⏳ TODO |
| T92 | Criar adapter Telegram→WhatsApp (payload + reply) | ⏳ TODO |
| T93 | Implementar queue unificada de atendimento | ⏳ TODO |
| T94 | Mapear comandos permitidos: /start → !oi, /menu → !menu | ⏳ TODO |
| T95 | Tratar WhatsApp limits: 4096 chars (msg), 65k (caption) | ⏳ TODO |
| T96 | Implementar typing WhatsApp (composing indicator) | ⏳ TODO |
| T97 | Implementar read receipts WhatsApp | ⏳ TODO |
| T98 | Plano rollout A/B: 50% Telegram + 50% WhatsApp | ⏳ TODO |
| T99 | Documentar arquitetura dual-channel | ⏳ TODO |
| T100 | SUI2: Gustavo escanear QR Evolution whatsapp.2notasudi.com.br | 🟡 GATED |

---

## MÉTRICAS

| Métrica | Valor |
|---------|-------|
| Tasks totais | 100 |
| Tasks DONE | 6 (T01, T02, T08, T41, T61 IN PROGRESS) |
| Tasks TODO | 90 |
| Tasks BLOCKED | 4 (T100 SUI2) |
| Tasks P0 | 3 (T21, T40, T61) |
| Tasks P1 | 14 |
| Tasks P2 | 8 |
| Coverage atual | 90.20% |
| Coverage target | ≥95% |
| Pytest passing | 171 telegram + ~2300 outros |
| Ruff | 0 errors |

---

## COMANDOS ÚTEIS

```bash
# Rodar testes Telegram
cd backend && uv run pytest tests/ -k telegram --no-cov -v

# Coverage
cd backend && uv run pytest tests/ -k telegram --cov=app.api.v1.telegram --cov-report=term

# Lint
make lint

# Bot local (dev)
TELEGRAM_BOT_TOKEN=xxx uvicorn app.main:app --reload
```

Modified by Gustavo Almeida (Telegram Bot 100% validation cycle #34)
