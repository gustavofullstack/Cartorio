# BLOCKERS — Pendências Críticas

## 🔴 P0 — Bloqueio produção

### B1. DNS Hostinger (3 NXDOMAIN)
- chatwoot.2notasudi.com.br
- n8n.2notasudi.com.br
- supabase.2notasudi.com.br
- **SUI Gustavo**: criar 3 A records → 187.77.236.77
- **Tempo**: ~5min
- **Desbloqueia**: 3 subdomínios + ACME cert

### B2. WhatsApp TriQ Hub instance=close
- disconnectionReasonCode=401 desde 2026-07-02
- **SUI Gustavo**: scanear QR em whatsapp.2notasudi.com.br/manager
- **Tempo**: ~2min
- **Desbloqueia**: atendimento WhatsApp real

### B3. Chatwoot easypanel host timeout 8s
- Estava 200 OK em 2026-06-25, hoje timeout
- **Investigar**: SSH VPS + docker service logs cartorio_chatwoot
- **Possível causa**: deploy Easypanel recente (3 replicas Up <2min)

## 🟡 P1 — Tasks backend

### B4. mypy 0 / pytest 0 fail
- **FEITO v21 T001-T010** (2026-07-06 17:35)
- 1 mypy error + 1 pytest failure → ambos resolvidos

### B5. N8N restart loop OOM
- 7 containers reiniciados em 2h (sintoma histórico)
- **Fix**: docker service update --limit-memory cartorio_n8n

## 🟢 P2 — Polish

### B6. Telegram bot webhook sherlock proxy
- Funciona mas em sherlock.st (não flow.2notasudi.com.br)
- Decisão Gustavo: manter ou trocar?

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 17:50 BRT
