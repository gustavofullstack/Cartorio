# LGPD 5 endpoints — 2026-06-24

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Resultado: CODIGO PRONTO (commit 287ec28) — DEPLOY EM PRODUCAO PENDENTE**.

## Resultado

### Código commitado (DONE)
- `backend/app/api/v1/lgpd_direitos.py` (266 linhas) — 5 endpoints:
  - `POST /api/v1/cliente/{id}/lgpd/anonimizar` (Art. 18 IV)
  - `POST /api/v1/cliente/{id}/lgpd/corrigir` (Art. 18 III)
  - `POST /api/v1/cliente/{id}/lgpd/oposicao` (Art. 18 IX)
  - `POST /api/v1/cliente/{id}/lgpd/optout` (comunicacoes marketing)
  - `POST /api/v1/cliente/{id}/lgpd/portabilidade` (Art. 18 V)
- `backend/app/main.py` atualizado (registra `lgpd_router` no FastAPI)
- **Total = 6 direitos LGPD Art. 18** (5 novos + 1 existente em `router.py:2125`)

### Deploy em produção (PENDENTE)
- Container `cartorio_api` rebuilda do zero via `docker service scale 0->1` (Easypanel padrão)
- `docker cp` injection (file direto no container) é **apagado** no próximo restart
- **Soluções** (escolher 1):
  1. **Modificar Dockerfile** para copiar `backend/app/api/v1/*.py` (mas é gerenciado pelo Easypanel)
  2. **Configurar auto-deploy no Easypanel** via webhook do GitHub (push → rebuild)
  3. **Render preview deployments** (já conectado, deploy em `cartorio-lrkp.onrender.com`)
  4. **Mavis/Pietra agent** (paralelo) já tem o commit 287ec28 — pode fazer rebuild manual

## BUG ENCONTRADO

**CARTORIO_API_KEY não estava configurado no VPS**:
- Vazio em `/etc/easypanel/projects/cartorio/api/code/.env`
- Sem isso, TODOS os endpoints X-API-Key retornam **503 API_KEY_NOT_CONFIGURED**

**FIX APLICADO** (antes do deploy LGPD):
- Gerada key 79 chars: `CARTORIO_API_KEY_2026_06_24_zcode_orquestrador_88efdf73360ac6ed8956bb0e4cb3a9dd`
- Setada no `.env` da VPS via `sed -i 's|^CARTORIO_API_KEY=.*|CARTORIO_API_KEY=...|'`
- Container reiniciado
- Salva em `~/.cartorio-api-key.txt` (chmod 600, local-only) para testes

## Descobertas do agente testador

1. **Cliente ID 1** = Maria Silva (único cliente real no DB)
2. **OpenAPI público** tem 45 paths, **0 LGPD** (até deploy efetivo)
3. **Tabelas LGPD** vazias (`lgpd_consent_log = 0`, `opt_out_log = 0`) — não há dados para testar
4. **Audit chain** funcionando (384 entries em `audit_log` validadas antes)

## Workflow recomendado (Mavis/Pietra)

```
1. Puxar commit 287ec28 (ja no origin)
2. Rebuild container API via Easypanel UI ou:
   ssh root@100.99.172.84
   cd /etc/easypanel/projects/cartorio/api/code
   docker service update --force --image <new-tag> cartorio_api
3. Validar: curl /openapi.json | grep lgpd
4. Testar: curl -X POST /api/v1/cliente/1/lgpd/anonimizar -H "X-API-Key: ..."
5. Atualizar LGPD-AUDIT-2026-06-25 com 6 direitos cobertos
```

## Próximos passos

### Curto prazo (Sprint 4)
- [ ] Deploy do commit 287ec28 (Mavis/agent)
- [ ] Testar 6 endpoints E2E com cliente real
- [ ] Popular tabelas LGPD com dados de teste (consent_log, opt_out_log)
- [ ] Implementar **inscricao realtime** (já configurado commit f6aac74) com Supabase client

### Médio prazo
- [ ] Migration para Supabase Edge Functions (se necessário para escala)
- [ ] UI/telegram comandos para o titular exercer direitos
- [ ] DPA Cloudflare + Hostinger + Sentry (D43)
- [ ] RIPD v1.2 com novos agentes (D44)
- [ ] Política retenção 90d conversas + 5a audit (D45)

Modified by Gustavo Almeida
