---
description: Checklist LGPD obrigatório (5 itens) para review de workflows N8N/Make/Zapier que movem dado pessoal — consent gate, scrub 3 camadas, audit log + IP /24, LGPDBlockedResponse copy, RequestContextMiddleware. Inclui matriz de severidade e gate leve para workflows não-PII. Carrega quando revisar workflow N8N que toca PII, ou criar novo workflow que integra com LLM/provider externo.
---

# N8N workflow LGPD review checklist

## Quando aplicar

Workflow que move dado pessoal via N8N (ou Make, Zapier, similar) — qualquer projeto que use essas ferramentas + coleta/processa PII.

## Os 5 itens obrigatórios

### 1. Consent gate ANTES de chamar LLM/provider externo (LGPD art. 7 I + 8)

- Node Function/IF verifica `{{$json.consent.granted}} == true` ANTES de chamar OpenCode-Go/DeepSeek/LiteLLM
- Se False → bloqueia, chama HITL, registra `LGPDBlockedResponse`
- Padrão copy jurídica plugada: commit 116afe0

### 2. Scrub 3 camadas (input/pre-LLM/output)

- **Camada 1: input do webhook** (pii.scrub no node Function)
- **Camada 2: pre-LLM** (regex 11+ tipos — ver `pii-scrubbing-helpers.md`)
- **Camada 3: output do LLM** (scrub no response antes de persistir/enviar)
- Defense-in-depth — LLM pode ecoar PII memorizada de treino

### 3. Audit log com request_id + IP /24 truncado (LGPD art. 37 + D5)

- Toda execução grava `execution_entity` (N8N Postgres) com `payload_hash` (SHA-256) + `scrubbed_payload` + `pii_tokens`
- IP truncado /24 (IPv4) ou /48 (IPv6) para privacy-by-design
- Sem payload bruto em log

### 4. LGPDBlockedResponse copy juridica plugada (commit 116afe0)

- Citação art. + inciso + parágrafo
- Contato DPO (art. 41)
- Link política privacidade
- Como remediar (consentimento=true ou DPO)
- Direito revogação (art. 8 § 5º)
- Status 422 (LGPDBlocked = precondição semântica/regulatória)

### 5. RequestContextMiddleware ativo

- Captura `request.client.host` (fallback `X-Forwarded-For` se proxy)
- Persiste IP completo com retenção curta (2y)
- Canal/agent_id visíveis no audit

## Severidade por gap

| Gap | Severidade |
|-----|-----------|
| Ausência consent gate em WF PII-tocando | BLOQUEIO P0 |
| Scrub ausente em 1 das 3 camadas | BLOQUEIO P1 (caso a caso) |
| Audit log sem IP /24 | P2 (privacy-by-design) |
| LGPDBlockedResponse copy errada | P2 |
| RequestContextMiddleware off | P2 |

## Gate mais leve (workflows NAO-PII)

Backup, monitoramento, audit, FAQ-only — basta revisão básica de:
- Segredos em variáveis de ambiente (não hardcoded)
- RLS em queries de banco
- Retenção configurada

## Cross-project

Esse checklist NAO é específico de cartório. Aplicável a QUALQUER projeto com N8N/Make/Zapier + dado pessoal. Usar em udiapods se migrar para N8N.

**Cross-ref:** review de cartorio-dev (LGPD-015) acelerado se este checklist já estiver satisfeito — revisor sabe o que procurar.
