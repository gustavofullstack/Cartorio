# DNS Health Report — 2notasudi.com.br

**Data**: 2026-07-16T14:15:28.523356+00:00
**IP esperado**: `187.77.236.77`
**Resolvers**: 1.1.1.1 (Cloudflare) / 8.8.8.8 (Google) (via system resolver)

## Resumo

- ✅ OK: **7/10**
- ❌ NXDOMAIN: **3/10**
- ⚠️ WRONG_IP: **0/10**
- 🔴 ERROR: **0/10**

## [HOLD] 3 host(s) precisam de ação

Hosts pendentes:
- `chatwoot.2notasudi.com.br` → NXDOMAIN ([Errno 8] nodename nor servname provided, or not known)
- `n8n.2notasudi.com.br` → NXDOMAIN ([Errno 8] nodename nor servname provided, or not known)
- `supabase.2notasudi.com.br` → NXDOMAIN ([Errno 8] nodename nor servname provided, or not known)

## Tabela detalhada

| # | Host | Subdomínio | Status esperado | Resolved IP | Status | Serviço |
|---|---|---|---|---|---|---|
| 1 | `api` | `api.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | cartorio_api |
| 2 | `flow` | `flow.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | n8n workflow engine |
| 3 | `whatsapp` | `whatsapp.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | Evolution API 2.3.7 |
| 4 | `chat` | `chat.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | Chatwoot 3.x (alias legado) |
| 5 | `agent` | `agent.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | OpenClaw 0.4.x |
| 6 | `supbase` | `supbase.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | Supabase (typo aceito) |
| 7 | `easypanel` | `easypanel.2notasudi.com.br` | OK | `187.77.236.77` | ✅ OK | Easypanel admin UI |
| 8 | `chatwoot` | `chatwoot.2notasudi.com.br` | PENDENTE | - | ❌ NXDOMAIN | Chatwoot canonico (HOLD-GUSTAVO-UI) |
| 9 | `n8n` | `n8n.2notasudi.com.br` | PENDENTE | - | ❌ NXDOMAIN | N8N admin UI (HOLD-GUSTAVO-UI) |
| 10 | `supabase` | `supabase.2notasudi.com.br` | PENDENTE | - | ❌ NXDOMAIN | Supabase canonico (HOLD-GUSTAVO-UI) |

## Próximos passos

### 🔴 Criar A records faltantes no Cloudflare UI

Para cada host NXDOMAIN, criar A record `187.77.236.77` no Cloudflare:

- `chatwoot.2notasudi.com.br` → A → `187.77.236.77` (proxy recomendado)
- `n8n.2notasudi.com.br` → A → `187.77.236.77` (proxy recomendado)
- `supabase.2notasudi.com.br` → A → `187.77.236.77` (proxy recomendado)

**Passo-a-passo**: ver `infra/dns/CLOUDFLARE_RUNBOOK.md` (~5min total).

Após criar, rodar `make dns-check` para validar.

---

**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 2 (auto-gerado)**