# PII WF #15 Session Sync — Pre-fill Checklist for cartorio-lgpd review

> WF: #15 Session Sync (Redis <-> DB 5min)
> ID N8N: h7Qf9AnmUkvAfnmO
> Ativo: false (LGPD gate pending)
> Trigger: cron 5min
> JSON canonico: `/Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/15-session-sync.json` (148 lines)

## Por que Session Sync é o mais simples de revisar

3 nodes, fluxo linear, sem branching:
- Node 1: Cron 5min (`cron-5min`, lines 8-25)
- Node 2: GET Sessoes Ativas Redis (`get-sessoes-ativas-redis`, lines 27-51)
- Node 3: Diff vs DB (`diff-vs-db`, lines 53-66)
- Node 4: POST Sync to DB (`post-sync-to-db`, lines 68-99)

Conexoes: lines 101-134.
Settings/tags: lines 136-147.

PII exposure minima: apenas `cliente_id` (UUID nao-PII em si, mas permite join com tabela cliente que TEM PII). Sessoes sao struct Redis com TTL 24h (nao é dado pessoal ate join).

## LGPD gate 5 itens com EVIDENCIA

### 1. Consent gate ANTES LLM/provider externo (LGPD art. 7 I + 8)

**STATUS: N/A com EVIDENCIA**

EVIDENCIA por WF #15:
- WF #15 NAO chama LLM (lines 8-99, nao tem node type n8n-nodes-langchain.*)
- WF #15 NAO chama provider externo (so httpRequest para backend proprio api.2notasudi.com.br)
- WF #15 NAO envia mensagem a cliente
- WF #15 NAO cria cliente/protocolo (so sincroniza sessao Redis→DB)

CODIGO NAO EXISTE por design. Sem consent gate porque nao ha decisao comercial/juridica sendo tomada. Operacao puramente tecnica (sync cache→DB).

Se quiser gate explicito: backend `POST /sessao/sync` ja valida que sessao existe no DB (FK constraint). Adicionar validacao extra seria redundante.

### 2. PII scrub 3 camadas (input/pre-LLM/output)

**STATUS: N/A com EVIDENCIA**

EVIDENCIA por WF #15:
- **Camada 1 (input)**: WF NAO recebe msg body de cliente. So recebe JSON `{count, sessions, ts, source}` do backend. Sem regex scrubber necessario.
- **Camada 2 (pre-LLM)**: N/A — WF NAO chama LLM.
- **Camada 3 (output)**: WF NAO envia msg. POST /sessao/sync vai pro DB interno Supabase (mesma infra backend, auditado via RequestContextMiddleware).

EXPOSICAO PII em transito: apenas `cliente_id` (UUID, nao-PII em si). Join com tabela `cliente` permitira acesso a CPF/nome/telefone, MAS:
- DB destino = Supabase (mesma infra do backend)
- RequestContextMiddleware (116afe0) garante que toda chamada fica logada
- RLS policies em `cliente` (E6.S4.T18 pendente) vai restringir acesso por owner

OBSERVACAO PARA REVIEW: cliente_id em transito é ACEITAVEL (UUID, nao-PII). Cuidado maior deve ser RLS em DB destino (escalonar cartorio-dev E6.S4.T18).

### 3. Audit log (request_id + IP /24 truncado)

**STATUS: AUTOMATICO via backend, sem acao no WF**

EVIDENCIA por WF #15:
- WF #15 NAO faz `POST /api/v1/audit/log` direto (sem node com essa URL)
- MAS: 2 endpoints backend chamados (GET /sessao/list-active, POST /sessao/sync) tem RequestContextMiddleware ativo (116afe0)
- RequestContextMiddleware automaticamente grava: request_id (UUID), IP truncado /24 (ex: 172.16.1.0), user_agent (curl/8.7.1), X-Canal (n8n-wf15), timestamp ISO

REFERENCIA NO WF:
- POST Sync to DB (lines 68-99): `X-API-Key: {{ $env.CARTORIO_API_KEY }}` permite backend identificar `actor=n8n-wf15` via `body.source: "n8n-wf15"` (line 86)

GAP POTENCIAL: se cartorio-dev nao gravou `actor` no audit log middleware, a trace fica anonima. Pedir cartorio-dev para adicionar campo `actor: n8n-wf{N}` automatico (sugestao pre-activate).

### 4. LGPDBlockedResponse copy juridica (116afe0)

**STATUS: N/A com EVIDENCIA**

EVIDENCIA por WF #15:
- WF #15 NAO tem IF node (lines 100-134, connections linear sem branching)
- WF #15 NAO chama LLM, portanto NAO ha caso onde response.shape == 'pii_blocked'
- LGPDBlockedResponse copy juridica (116afe0) é para response do LLM ao cliente. WF #15 NAO responde a cliente.

NAO APLICAVEL.

### 5. RequestContextMiddleware ativo (116afe0)

**STATUS: BACKEND ATIVO, WF herda automaticamente**

EVIDENCIA por WF #15:
- Backend merged em 116afe0: middleware popula `request.state.request_id` em todo request
- WF #15 chamadas:
  - GET /sessao/list-active (line 28): backend gera request_id automatico
  - POST /sessao/sync (line 70): backend gera request_id, retorna 200 com mesmo ID no response header
- WF #15 NAO precisa propagar request_id explicitamente (backend gera)
- MAS: se quisermos correlacionar N8N execution com audit log, podemos passar `X-Request-Id: {{ $execution.id }}` como header

SUGESTAO pre-activate (não bloqueador): adicionar header `X-Request-Id` em ambos httpRequest do WF #15:
```json
{
  "name": "X-Request-Id",
  "value": "={{ $execution.id }}"
}
```

Permite trace de N8N execution → backend audit log via shared request_id.

## Cross-ref backend deps (cartorio-dev)

WF #15 depende de 2 endpoints backend:
- `GET /api/v1/sessao/list-active` (E6.S1.T8) — endpoint de leitura Redis
- `POST /api/v1/sessao/sync` (E6.S1.T9) — endpoint de persistencia DB

Status backend (cartorio-dev mvs_ab6f9e82 ETA ~19:37 BRT para /health/backup): **NAO VERIFICADO** se /sessao/* estao deployed. Pedir cartorio-dev para confirmar antes de activate.

## Riscos residuais (post-activate)

1. **Backend endpoint nao deployed** (Risco medio): se /sessao/list-active ou /sessao/sync nao existem, WF vai dar 404 no GET. Backoff: WF #15 fica em loop de erro a cada 5min. Mitigacao: WF #15 NAO faz nada destrutivo, so le/escreve em DB proprio. Alerta via /api/v1/health/radar mostrara latencia alta. **Pre-activate check: curl /sessao/list-active deve retornar 200.**

2. **PII exposure via cliente_id** (Risco medio-baixo): cliente_id em si nao é PII, mas join com tabela cliente é. RLS policies em `cliente` (E6.S4.T18) garante que so owner le. **Risco medio** se RLS nao deployed — escalonar cartorio-dev E6.S4.T18 pre-activate.

3. **Sessao TTL 24h vs retencao DB 5y/2y** (Risco baixo): WF #15 NAO apaga sessoes, so sincroniza Redis (24h) → DB (5y/2y conforme retenção). Nao conflita com WF #24 Daily Cleanup.

4. **Cron sem retry/backoff** (Risco baixo): se 1 tick falha, proximo tick em 5min. Sem alerta imediato a nao ser via /health/radar.

## Sequencia de activate (pos cartorio-lgpd GO)

```bash
# Pre-check: backend endpoints deployed
curl -X GET -H "X-API-Key: $CARTORIO_API_KEY" \
  "https://api.2notasudi.com.br/api/v1/sessao/list-active" | jq
# Esperado: 200 + {sessions: [...], count: N}

# Activate WF
curl -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/h7Qf9AnmUkvAfnmO/activate"

# Monitor first 3 ticks (15min)
sleep 15
curl -X GET -H "X-API-Key: $CARTORIO_API_KEY" \
  "https://api.2notasudi.com.br/api/v1/audit/log?actor=n8n-wf15&limit=3" | jq
# Esperado: 3 entries com action=sessao.sync, request_id presente
```

## Decisao solicitada ao cartorio-lgpd

- [ ] **APROVAR**: WF #15 pode ser ativado em prod (gate OK, fluxo linear sem LLM)
- [ ] **APROVAR COM CONDICAO**: requer backend /sessao/* deployed + RLS cliente ativo
- [ ] **REJEITAR**: motivo + alternativa

## Cross-coord necessario

- cartorio-dev (mvs_ab6f9e82): confirmar E6.S1.T8 e T9 deployed antes de activate
- cartorio-lgpd (mvs_d4fa1b1a): review deste checklist + opcionalmente do JSON canonico
- pietra/orquestrador (mvs_c2508947): aciona activate=true se APROVAR

## Resumo executivo (1 paragrafO)

WF #15 Session Sync é o PII-touching WF de menor risco: 3 nodes, sem LLM, sem msg body, sem IF/branching. LGPD gate items 1/2/4 sao N/A com EVIDENCIA por design. Items 3/5 sao cobertos automaticamente pelo backend RequestContextMiddleware. Recomendacao: APROVAR COM CONDICAO de pre-check backend endpoints deployed.

Modified by Gustavo Almeida (via cartorio-n8n 19:36 BRT)
