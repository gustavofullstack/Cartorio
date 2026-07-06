# RUNBOOK — DNS Hostinger (2notasudi.com.br)

**Data:** 2026-07-06 17:40 BRT | **Owner:** Gustavo Almeida (UI manual) | **PLAN:** v21 T011-T020

## Status atual (dig @1.1.1.1)

| Host | IP | Status |
|---|---|---|
| api.2notasudi.com.br | 187.77.236.77 | 🟢 OK |
| flow.2notasudi.com.br | 187.77.236.77 | 🟢 OK (N8N) |
| whatsapp.2notasudi.com.br | 187.77.236.77 | 🟢 OK (Evolution) |
| agent.2notasudi.com.br | 187.77.236.77 | 🟢 OK (OpenClaw) |
| easypanel.2notasudi.com.br | 187.77.236.77 | 🟢 OK |
| supbase.2notasudi.com.br | 187.77.236.77 | 🟢 OK (typo aceito) |
| **chatwoot.2notasudi.com.br** | **NXDOMAIN** | 🔴 **CRIAR** |
| **n8n.2notasudi.com.br** | **NXDOMAIN** | 🔴 **CRIAR** |
| **supabase.2notasudi.com.br** | **NXDOMAIN** | 🔴 **CRIAR** |

## Passo-a-passo (5min total)

1. **Login Hostinger** → https://hpanel.hostinger.com
2. **Domínios** → `2notasudi.com.br` → **Gerenciar** → aba **DNS / Zone DNS**
3. **Adicionar registro A** (3 vezes):
   - Nome: `chatwoot` | IP: `187.77.236.77` | TTL: 3600
   - Nome: `n8n`      | IP: `187.77.236.77` | TTL: 3600
   - Nome: `supabase` | IP: `187.77.236.77` | TTL: 3600
4. **Salvar** todos
5. **Aguardar propagação** (~5min para Hostinger; até 24h para ISPs antigos)
6. **Validar**:
   ```bash
   for h in chatwoot n8n supabase; do
     echo "$h.2notasudi.com.br -> $(dig +short $h.2notasudi.com.br @1.1.1.1)"
   done
   ```
7. **ACME Letsencrypt** gera cert automático (Traefik monitora main.yaml + custom.yaml)
8. **Validar HTTPS**:
   ```bash
   curl -sk -o /dev/null -w "%{http_code}\n" https://chatwoot.2notasudi.com.br/api/v1/accounts
   curl -sk -o /dev/null -w "%{http_code}\n" https://n8n.2notasudi.com.br/healthz
   curl -sk -o /dev/null -w "%{http_code}\n" https://supabase.2notasudi.com.br/auth/v1/health
   ```

## Por que Hostinger e não Cloudflare?

DNS provider do domínio `2notasudi.com.br` é **Hostinger** (não Cloudflare).
Lesson 142 (Pietra mvs_6663ee57): "DNS provider mismatch: cron/agent SEMPRE verificar nameservers ANTES de assumir Cloudflare."

## Traefik routers (já configurados)

- `chatwoot-http` + `chatwoot-https` + `chatwoot-service` em `/etc/easypanel/traefik/config/custom.yaml` (Pietra 2026-06-24)
- Routers `n8n` e `supabase` precisam ser adicionados (não foram escritos ainda)
- ACME tenta gerar cert quando router existe, falha com NXDOMAIN se DNS não resolve

## SUI Gustavo — 5min manual

Bloqueia 3 subdomínios: chatwoot, n8n, supabase. Sem isso:
- N8N exposto só em `flow.2notasudi.com.br` (works)
- Chatwoot exposto só em `cartorio-chatwoot.dfgdxq.easypanel.host` (instável)
- Supabase exposto só em `supbase.2notasudi.com.br` (typo aceito)

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 17:40 BRT
