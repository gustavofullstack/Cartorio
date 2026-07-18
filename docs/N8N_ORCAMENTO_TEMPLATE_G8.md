# N8N Template — Orçamento de Escritura (G8.20.T2)

Workflow template **offline-ready** (JSON estático em `infra/n8n-workflows/template-orcamento-escritura.json`) que orquestra o cálculo de emolumento para escrituras e certidões, com **HITL (escrevente valida DRAFT)** e **audit log LGPD Art. 37** ao final.

> **Status:** template (não publicado no N8N live).
> Wave 49 — G8.20.T2 (cartorio-n8n).
> Modified by Gustavo Almeida.

---

## 1. Pré-requisitos

| Item | Valor |
|------|-------|
| Backend API | `cartorio-api:8000` (Docker Swarm, Easypanel) |
| Endpoint 1 | `POST /api/v1/emolumento/calculate` |
| Endpoint 2 | `POST /api/v1/audit` (LGPD Art. 37) |
| Schema strict | `app.schemas.n8n_workflow.N8nWorkflow` (Pydantic v2) |
| Inventory | `python3 scripts/n8n_wf_inventory.py --strict` |

## 2. Env vars necessárias

Na instância N8N que for importar este template, definir:

```bash
CARTORIO_API_URL=http://cartorio-api:8000   # interno ao Swarm
N8N_PROTOCOL_NUMBER=auto                    # webhook ID auto-gerado
```

> Em produção, usar o **service name** interno do Swarm (`cartorio-api`); a porta pública (8000) é roteada via Traefik.

## 3. Estrutura do workflow (6 nodes)

```
┌───────────┐    ┌──────────┐    ┌─────────────────┐    ┌──────────────────────┐    ┌──────────────────┐
│  Webhook  │───▶│ Validar  │───▶│ Calc Emolumento │───▶│ Format Response DRAFT│───▶│ Audit LGPD Art.37 │
│ POST /orc │    │ tipo ∈ 8 │    │ POST /emolumento│    │ parseFloat + draft:T │    │ POST /audit       │
└───────────┘    └──────────┘    └─────────────────┘    └──────────────────────┘    └──────────────────┘
```

### 3.1 Node `Webhook`

- **Tipo:** `n8n-nodes-base.webhook`
- **Path:** `orcamento` (POST)
- Recebe `{ tipo, folhas?, urgencia? }` do chatbot (Telegram / WhatsApp / Web).

### 3.2 Node `Validar`

- **Tipo:** `n8n-nodes-base.code`
- **HITL-by-design:** rejeita `tipo` fora do whitelist antes de tocar em emolumento.
- **Whitelist (8 tipos):** `certidao_negativa`, `certidao_positiva`, `certidao_casamento`, `escritura_compra_venda`, `escritura_doacao`, `procuracao`, `autenticacao`, `reconhecimento_firma`.

### 3.3 Node `Calc Emolumento`

- **Tipo:** `n8n-nodes-base.httpRequest`
- **POST** `http://cartorio-api:8000/api/v1/emolumento/calculate`
- Body: `{ tipo, folhas: 1, urgencia: false }`
- Tabela MG 2026 — calcular valores base, adicional por folha, adicional urgência.

### 3.4 Node `Format Response DRAFT`

- **Tipo:** `n8n-nodes-base.code`
- Normaliza resposta da API em payload de bot:
  ```json
  {
    "tipo": "escritura_compra_venda",
    "base": 1200.50,
    "adicional_folhas": 0.00,
    "adicional_urgencia": 0.00,
    "total": 1200.50,
    "validade_ate": "2026-07-25",
    "referencia": "MG-2026-Q3-TABELA-X",
    "draft": true
  }
  ```
- **`draft: true`** → flag HITL. Escrevente valida antes de virar protocolo real.

### 3.5 Node `Audit LGPD Art.37`

- **Tipo:** `n8n-nodes-base.httpRequest`
- **POST** `http://cartorio-api:8000/api/v1/audit`
- Body: `{ action: "orcamento_draft", entity: "emolumento", protocolo: "DRAFT" }`
- Entrada imutável no **hash chain** (SHA256 + HMAC). Recomputável por `22-audit-verify-6h`.

## 4. HITL — escrevente valida DRAFT

Regra P0 do projeto (`.harness/STANDARDS.md`): bot **nunca** decide sozinho em ato jurídico. Por isso `draft: true` é flag obrigatória:

1. Escrevente recebe notificação no painel (Telegram Bot / Chatwoot / Internal Dashboard).
2. Revisa valores: `base`, `adicional_folhas`, `adicional_urgencia`, `total`, `validade_ate`, `referencia`.
3. **Aprovar** → protocolo nasce como `DRAFT → VALIDATED → PROCESSING` (estado interno `Protocolo.status`).
4. **Recusar** → entrada de audit `orcamento_recusado` + request para reabrir conversa com cliente.

> **Atenção:** o template não cria o nó de "validação por escrevente" — isso é responsabilidade do workflow pai (`01-consulta-emolumento` ou `02-criar-protocolo`). Este template é o **bloco de cálculo + audit** que eles consomem.

## 5. LGPD audit log chain

Cada execução bem-sucedida gera 1 entrada no `audit_log`:

- `action = "orcamento_draft"`
- `entity = "emolumento"`
- `protocolo = "DRAFT"` (placeholder; vira número real após HITL aprovar)

Hash chain (SHA256) com bloco anterior — qualquer retro-edição invalida a chain.
Verificação automática em `08-audit-verify-diario.json` (cron diário) e `22-audit-verify-6h.json` (cron 6h).

**LGPD Art. 37** exige registro de tratamento para cada operação com dado pessoal. O endpoint `/api/v1/audit` cumpre isso centralizadamente.

## 6. Como importar

### 6.1 Validação local (strict)

```bash
cd backend
APP_ENV=development uv run python3 ../scripts/n8n_wf_inventory.py --strict
# Esperado: count: 40  valid: 40  invalid: 0
```

### 6.2 Import via N8N API (live)

```bash
curl -X POST "$N8N_BASE_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @infra/n8n-workflows/template-orcamento-escritura.json
```

Ou via UI: **Workflows → Import from File** → selecionar JSON. Definir `active: true` após revisar.

### 6.3 Teste ponta-a-ponta (curl)

```bash
curl -X POST "http://cartorio-api:8000/api/v1/emolumento/calculate" \
  -H "Content-Type: application/json" \
  -d '{"tipo":"escritura_compra_venda","folhas":2,"urgencia":false}' | jq
```

Resposta esperada: `200 OK` com `{ base, adicional_folhas, adicional_urgencia, total, valido_ate, tabela_referencia }`.

Para testar o nó de audit (sem N8N):

```bash
curl -X POST "http://cartorio-api:8000/api/v1/audit" \
  -H "X-Idempotency-Key: test-$(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"action":"orcamento_draft","entity":"emolumento","protocolo":"DRAFT"}' | jq
```

## 7. Próximos passos (fora do escopo G8.20.T2)

| Task | Descrição | Rein |
|------|-----------|------|
| G8.20.T3 | Workflow de validação por escrevente (HITL WebSocket) | cartorio-dev |
| G8.20.T4 | Integração com Chatwoot label `orcamento_draft` | cartorio-n8n |
| G8.20.T5 | Persistência em `orcamento` table | cartorio-dev |
| G8.20.T6 | RIPD específico para fluxo de orçamento | cartorio-lgpd |

## 8. Referências

- `infra/n8n-workflows/38-emolumento-calculator.json` — workflow atual (referência de estilo)
- `infra/n8n-workflows/02-criar-protocolo.json` — workflow pai para HITL
- `backend/app/schemas/n8n_workflow.py` — schema strict Pydantic
- `backend/app/services/emolumento.py` — cálculo MG 2026
- `backend/app/api/v1/audit.py` — endpoint audit log
- `.harness/STANDARDS.md` — regra HITL P0
- `.harness/memory/lesson-252-g8-20-t2-orcamento-template-retry-2026-07-18.md` — lição deste task
