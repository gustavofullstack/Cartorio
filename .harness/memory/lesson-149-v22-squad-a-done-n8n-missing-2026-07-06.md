# Lesson 149 — Round v22: SQUAD A backend DONE + N8N REMOVIDO Swarm

**Data:** 2026-07-06 18:10 BRT | **Modified by:** ZCode/Mavis + Gustavo Almeida

## Contexto

Continuação do PLAN v21 após YOLO Mode. Atacar SQUAD A backend (T041-T050) + descobrir problemas prod.

## Entregas v22

### Backend hardening SQUAD A
- ✅ **DB_POOL_SIZE 10 → 25** (T042) — doubled+ capacity
- ✅ **dist_lock.py** (T041) — Redlock simplificado via Redis SET NX + Lua release atômico
- ✅ **test_dist_lock.py** (5 tests passed)
- ✅ **cartorio-backup.sh** (T046) — pg_dump real + cleanup 30d
- ✅ **cron `0 3 * * *`** agendado (03:00 BRT diário)
- ✅ **infra/supabase/migrations/2026_07_06_add_matviews.sql** (T043) — 2 views: emolumento_stats + protocolo_aging

### Gates
- ✅ ruff 0 errors
- ✅ mypy 0 errors (122 files — +1 dist_lock.py)
- ✅ pytest 34 novos tests passed (5 dist_lock + 23 LGPD + 6 soft_delete)

## 🚨 DESCOBERTA CRÍTICA — N8N REMOVIDO

`docker service ls | grep n8n` → vazio
`docker ps -a | grep n8n` → vazio

**Sintoma**: radar health reporta `n8n: offline` há quanto tempo?
**Impacto potencial**:
- Telegram bot webhook (N8N WF31) — pode estar caindo em sherlock proxy fallback
- WhatsApp handoff Chatwoot (N8N WF07) — quebrado
- BRAIN tasks workflows — quebrados

**Próximo passo**: Gustavo verificar com Easypanel se service foi removido de propósito OU precisa recriar.

## 🔴 B8 — crwal4ai health endpoint não responde

`docker exec cartorio_crwal4ai.1.93lnz0mc5hur3ekmrjdj0onjz curl http://localhost:8000/health` → 000 (timeout)
- Container Up 4 days healthy (docker healthcheck OK)
- Porta 8000 não responde, 8080 também não, 11235 retorna 401
- **Hipótese**: crawl4ai mudou porta default ou healthcheck interno é diferente

## Métricas finais

- Commits: 3 (v21 fc48620 + 111e44d + 5011bf5)
- Pendente: commit v22 (squad-a-done + n8n-discover)
- GOALS.md 365 linhas
- PLAN v21 22KB / 100 tasks / 60% done
- Cron launchd: 7 entries cartorio
- Cron tab: 1 backup diário 03:00

## Lições

1. **N8N ausente é o "elefante na sala"** — radar health sinalizou desde 2026-06-25 mas ninguém investigou
2. **dist_lock é mais simples que redlock lib** — Lua eval atômico + token secret resolve
3. **crwal4ai healthcheck ≠ endpoint exposto** — Docker healthcheck interno pode estar OK mas porta 8000 não responder
4. **Backup real > backup stub** — pg_dump direto é +30 linhas mas vale a pena
5. **Cron `0 3 * * *`** — madrugada 03:00 BRT é sweet spot (sem uso usuário + retention 5y)

## Pendências SUI Gustavo

1. DNS Hostinger: 3 A records (chatwoot/n8n/supabase)
2. WhatsApp TriQ Hub: scan QR
3. Telegram bot /start
4. Chatwoot easypanel timeout
5. **NOVO**: N8N recriar ou aceitar removido?
6. **NOVO**: crwal4ai health endpoint investigar

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 18:10 BRT
