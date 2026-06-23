# ADR-018: DELETE /cliente/{id} — LGPD art. 18 VI

**Data:** 2026-06-23
**Status:** APROVADA (Sprint 3, Bloco 4.2)
**Autor:** ZCode (Mavis)
**Sprint:** 3 (Bloco 4.2)

## Contexto

LGPD art. 18, VI dá ao titular o direito de **eliminação** dos dados pessoais
tratados com seu consentimento. Para um cartório, isso colide com:

1. **Provimento CNJ 74/2018**: retenção mínima de 5 anos para atos cartorários
   (escrituras, procurações, registros) — independente de consentimento.
2. **LGPD art. 7, II**: cumprimento de obrigação legal dispensa consentimento
   e **autoriza retenção** mesmo sem anuência do titular.
3. **LGPD art. 16**: dados pessoais serão eliminados após cessada a finalidade
   do tratamento (mas cessação ≠ revogação para atos cartorários — see #1).

Em outras palavras: **nem todo cliente pode ter seus dados eliminados**.
Depende se há ato cartorário vinculado.

## Decisão

**Soft delete por padrão + hard delete apenas para clientes SEM protocolo**.

### Implementação

| Estado do cliente | Ação do DELETE | Motivo |
|-------------------|----------------|--------|
| **Cliente SEM protocolo** (apenas atendimento/atendimento WhatsApp) | **HARD DELETE**: remove do DB | Sem ato cartorário, sem obrigação legal, pode eliminar |
| **Cliente COM protocolo (ativo ou histórico)** | **SOFT DELETE**: marca `motivo_encerramento=revogacao_consentimento` + `data_encerramento=now()` + anonimiza PII (CPF hash + nome → "TITULAR_REVOGADO_<hash>") | Provimento CNJ 74/2018 + LGPD art. 7 II; mantém integridade da cadeia cartorária |
| **Cliente que JA É soft-deleted** | **409 Conflict** (já revogado) | Idempotência, evita re-anonimizar |
| **Cliente inexistente** | **404 Not Found** | |
| **Cliente de outro tenant** (futuro multi-cartório) | **403 Forbidden** | |

### Schema

Já temos `cliente.motivo_encerramento` (Sprint 1.1, ENUM: revogacao_consentimento | retencao_5y | exercicio_direito_titular | outros) e `cliente.data_encerramento` foi adicionado no model na Sprint 0.

Vou validar com o model atual:

### Endpoint

```http
DELETE /api/v1/cliente/{id}
Headers:
  X-API-Key: $CARTORIO_API_KEY  (escrevente autorizado)
  X-Request-Id: <trace>         (opcional, ecoado no response)

Response 200:
{
  "status": "deleted",
  "tipo": "hard" | "soft",
  "cliente_id": 42,
  "protocolos_ativos": 0,        // se 0 -> hard, se >0 -> soft
  "data_encerramento": "...",
  "audit_id": 1234
}

Response 404: { "erro": "CLIENTE_NOT_FOUND", ... }
Response 409: { "erro": "CLIENTE_JA_REVOGADO", ... }
```

### Quem pode chamar

- **Escrevente** com `X-API-Key` (auditado)
- **DPO** com endpoint dedicado em `/admin/dpo/*` (futuro Sprint 4)
- **Cliente via Chatwoot** (futuro: "Responda REVOGAR para apagar seus dados")

### Audit log

Sempre emite `cliente.delete` com:
- `actor_id`: quem pediu (escrevente nome/id)
- `action`: `cliente.delete.hard` ou `cliente.delete.soft`
- `payload`: { cliente_id, protocolos_ativos, motivo, hash_cpf_antes }
- `request_id`, `ip`, `user_agent`, `canal` (do middleware)
- HMAC + hash chain (já garantido pelo AuditService)

### Anonimização no soft delete

Para clientes COM protocolo:
- `nome` → `TITULAR_REVOGADO_<8 primeiros chars do cpf_hash>`
- `cpf_hash` → **mantém** (necessário para o hash chain referenciar a entry original)
- `email` → NULL
- `telefone` → NULL
- `consentimento_lgpd` → False
- `motivo_encerramento` → `revogacao_consentimento`
- `data_encerramento` → now()
- `audit_log_revogacao` → referência ao audit_id da operação

## Consequências

**Positivas**
- Conformidade LGPD art. 18 VI sem violar Provimento CNJ 74/2018.
- Idempotente: chamar DELETE 2x não causa dano.
- Auditável: cada delete deixa rastro imutável.
- Reversível apenas pelo DPO com ferramenta especial (não pelo endpoint).

**Negativas**
- "Anonimização" não é verdadeiramente irreversível se o hash do CPF
  permanecer. Mitigação: aceita-se o risco porque o hash é SHA256+salt;
  revogação do titular **não** dá direito de reverter o ato cartorário,
  apenas de apagar o que é apagável.
- Testes precisam de fixture que crie cliente COM e SEM protocolo.
- Não cobre cenário "cliente quer apagar apenas 1 conversa, manter o
  protocolo". Solução: rota adicional `DELETE /cliente/{id}/conversa/{id}`.

## Não-objetivos

- Direito ao esquecimento de **documentos anexos** (PDFs de escrituras) —
  estes ficam em Supabase Storage com retenção 5y fixa, sem delete API.
- Esquecimento **retroativo** de audit log (imutável por design).
- Soft delete de atendente (escrevente) — fora do escopo do LGPD art. 18 VI.

## Referências

- LGPD Lei 13.709/2018, art. 7, II; art. 16; art. 18, VI; art. 37
- Provimento CNJ 74/2018 (retenção mínima cartorária)
- LGPD art. 41 (DPO - quem supervisiona essas decisões)
