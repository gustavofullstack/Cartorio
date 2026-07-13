# Loop Objective — Cartório 2notas
# Context Loop Engineer v4.0.0
# Atualizado: 2026-06-26 19:20 BRT

## OBJETIVO ATUAL

**GOAL**: Finalizar o projeto Cartório 2notas — conectar Telegram + Chatwoot + OpenClaw + API em E2E funcional com ZERO erros, validar WhatsApp via Evolution API, e completar Squads C e J pendentes.

**COMPLETION CRITERIA**:
1. ✅ Telegram Bot conectado no Chatwoot (Inbox 1)
2. ✅ API/N8N/OpenClaw/Redis/Supabase integrados e testados
3. ✅ CHATWOOT_API_KEY real configurada
4. ✅ 5 MCP Skills criadas (chatwoot/n8n/supabase/easypanel/hostinger)
5. [ ] E2E flow: Telegram → Chatwoot → OpenClaw → resposta automática
6. [ ] Squad C docs 100% (12/25 → 25/25)
7. [ ] Squad J obs+ci/cd 100% (5/10 → 10/10)
8. [ ] Multi-provider fallback testado 3x
9. [ ] WhatsApp Evolution API conectado (QR scan — SUI Gustavo)
10. [ ] pytest 1300+ passing

## ESTADO ATUAL (2026-06-26 19:20 BRT)

- Squads: 9/10 squads 100% DONE + Skills MCP 5/5
- Gates: mypy 0 | ruff 0 | pytest 1281+ passed
- Infra: /health/radar GREEN, 7/7 SSL OK, 12/12 Docker UP
- Backups: 26/06 OK (corrigido chmod +x)
- OpenClaw: 3 providers, deepseek-v4-flash primário, 1M context

## PRÓXIMAS TASKS (ordem de prioridade)

### P0: E2E Telegram → OpenClaw
- Enviar msg no Telegram para @CartorioAssistantBot
- Verificar se aparece no Chatwoot (Inbox 1)
- Verificar se OpenClaw responde via WS /v1/chat
- Verificar audit trail no Supabase

### P1: Squad C Docs (13 restantes)
- C13: docs/INTEGRACOES.md
- C14: docs/FALLBACK_PROVIDERS.md
- C15: docs/REDIS_USAGE.md
- C16-C25: documentação restante

### P1: Squad J Obs+CI/CD (5 restantes)
- J6: Prometheus alerting rules
- J7: GitHub Actions smoke tests pós-deploy
- J8: Automated rollback workflow
- J9: CI/CD pipeline completo
- J10: Dead man's switch verification

### P2: Multi-Provider Fallback
- Criar `tests/test_openclaw_integration.py`
- Testar fallback: opencode_go → opencode_free_1 → opencode_free_2
- Testar retry 3x com troca de modelo
- Documentar em `docs/FALLBACK_PROVIDERS.md`

## CRONS CONFIGURADOS

| Cron | Frequência | Ação |
|------|-----------|------|
| cartorio-backup | 3:00 diário | Backup completo VPS |
| cartorio-pgbase | 0,6,12,18h | pg_basebackup |
| cartorio-deadmans-switch | 1min | Audit log stale check |
| cartorio-evolution-health | 5min | Evolution API health |
| cartorio-network-monitor | 5min | Network connectivity |
| cartorio-backup-monitor | 4h | Backup status monitor |
| N8N WF21 | 5min | Backup heartbeat |
| N8N WF25 | 1min | Prometheus metrics |
| N8N WF30 | 15min | Health deep check |

## SUI — Só Gustavo Resolve

1. **DNS Cloudflare**: `n8n.2notasudi.com.br` + `supabase.2notasudi.com.br` → A record 187.77.236.77
2. **WhatsApp QR**: `whatsapp.2notasudi.com.br/manager` → Instância `cartorio-2notas` (state=close)
3. **Testar Telegram Bot**: Mandar msg para @CartorioAssistantBot e confirmar recepção no Chatwoot

## NOTES

- **Backup problema resolvido**: `chmod +x /usr/local/bin/cartorio-backup.sh` — cron vai rodar normalmente às 03:00
- **OpenClaw UI vs API**: `/v1/agents` retorna HTML UI. Comunicação real é via WS `/v1/chat`  
- **OpenClaw config VPS**: `/home/node/.openclaw/agents/main/agent/`
- **REDIS_URL**: `redis://default:%40Techno832466@cartorio_redis:6379/0` (URL-encoded @)
- **N8N_API_KEY**: JWT token (3 partes separadas por ponto)
