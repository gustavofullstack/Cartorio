---
description: Estado vivo dos workflows N8N ativos no cartorio - typos de URL, credenciais pendentes, IDs dos 18 WFs E6, gaps conhecidos. Carregar quando for editar/migrar WF ou reportar status para Gustavo.
---

# N8N Current State (snapshot 2026-06-23)

## E6 Sprint: 18 WFs criados em flow.2notasudi.com.br

| Status | IDs |
|--------|-----|
| ATIVOS (non-PII) | #14, #16, #18, #21, #22, #24-daily, #25, #26, #28, #29, #30 |
| DRAFT (PII, LGPD review) | #13, #15, #17, #19, #20, #23-lgpd-esqueci, #27 |

JSON sources canonicos: `/Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/{NN}-{slug}.json`. Todos com env refs `$env.X` (zero hardcoded secrets — auditoria limpa).

**Gate activate=true para PII WFs**: cartorio-dev PR LGPD-015 merged + cartorio-lgpd review (mvs_d4fa1b1a).

**Total**: 37 WFs (era 18 antes E6). Ativos: 28 (era 15).

IDs salvos em scratchpad parent `mvs_c2508947ba0f4a738139f90b9c3e75a8`.

## Chatwoot: typo + credencial mismatch

Estado em prod (15 WFs ativos):

- URL `chatwoot.2notasudi.com.br` hardcoded em 3 WFs: #03, #08, #09
- URL `chat.2notasudi.com.br` hardcoded em 1 WF: #11 (**TYPO**)
- Credencial `chatwoot-api` (`qGyW9nc36pWXo7ow`) **EXISTE mas NAO eh usada por NENHUM WF ativo**. So #11-ENHANCED INATIVA referencia
- Credencial cadastrada como tipo `httpHeaderAuth` GENERICA, NAO como `ChatWootApi` (do node `@devlikeapro`). Perdeu campo `url` requerido pelo node oficial
- `@devlikeapro/n8n-nodes-chatwoot` esta INSTALADA no container mas ZERO WFs ativos usam

**Decisao canonica**: `chatwoot.2notasudi.com.br` (3 votos vs 1). WF #11 deve ser corrigido.

DNS externo (Cloudflare):
- `api.2notasudi.com.br` → 187.77.236.77 (RESOLVE)
- `chatwoot.2notasudi.com.br` → NXDOMAIN (esperado, DNS pendente - cartorio-lgpd review)
- `chat.2notasudi.com.br` → NXDOMAIN
- DNS interno Docker Swarm resolve via service name (Easypanel/Traefik)

## Pendencias (gate GO Gustavo)

1. Re-cadastrar credencial `chatwoot-api` como tipo `ChatWootApi` com `url=chatwoot.2notasudi.com.br`
2. Migrar WF #03, #08, #09, #11 para usar node oficial `n8n-nodes-chatwoot` (substituindo httpRequest)
3. WF #11 corrigir typo de URL hardcoded

## Bug latente WF #00 Error Handler v4

Node 'Alerta Chatwoot' aponta URL = `https://api.2notasudi.com.br/api/v1/atendimento`. **BUG no nome** — eh backend `/atendimento`, nao Chatwoot. Renomear node.

## Pai/orquestrador pode ter contexto stale do master

Pai me pediu para commitar 18 workflows N8N (13-30) assumindo master = `3b85746` e arquivos como untracked. REALIDADE: master = `60a715f` (avancou 4 commits alem de `3b85746`), arquivos 13-30 JA FORAM COMMITADOS em `3713d10` (autor Pietra, 2026-06-23 19:21 BRT).

**3 checks obrigatorios antes de aceitar tarefa de commit em massa**:
1. `git status -uall <dir>` → working tree realmente tem os arquivos untracked?
2. `git ls-files <dir>` → arquivos ja tracked?
3. `git log master -5` → master HEAD real confere com referencia do pai?

Se working tree CLEAN e arquivos tracked, **REPORTAR BLOCK com evidencia**, NAO tentar git add (no-op silencioso) nem re-commit vazio. Pai provavelmente teve contexto pre-snapshot (handoff file stale).