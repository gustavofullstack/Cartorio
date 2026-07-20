# Relatório de Exportação CNJ — Dados de Proteção LGPD

> Projeto Cartório 2º Notas Uberlândia  
> Atualizado em 2026-07-19  
> Documentação do sistema de exportação agregada para o Conselho Nacional de Justiça (CNJ)

## Visão Geral

O sistema de exportação CNJ gera relatórios **agregados e minimizados** sobre as operações de tratamento de dados pessoais realizadas pelo cartório. **Nenhum dado pessoal (PII) é exportado** — apenas métricas consolidadas por período.

## Arquitetura

```
DPO Solicita ──► create_request() ──► status=requested
                      │
                      ▼
DPO Aprova (dual) ──► approve_request() ──► status=approved
                      │
                      ▼
build_approved_export() ──► status=generated
                      │
                      ├──► report.json (indicadores agregados)
                      └──► manifest.json (SHA256 + integridade)
```

### Controles de Segurança

| Controle | Implementação |
|----------|---------------|
| **Dupla aprovação humana** | DPO solicitante ≠ DPO aprovador |
| **Sem dados pessoais** | Apenas contagens COUNT(*) no DB, sem SELECT de linhas |
| **Integridade SHA256** | Manifesto com hash do relatório + hash do manifesto |
| **Validação da cadeia de auditoria** | `AuditService.verify_chain()` antes de gerar |
| **Justificativa com PII scrubbing** | `pii.scrub()` na justificativa de aprovação |
| **Período calendário válido** | Apenas YYYY-MM, entre 2000-2100 |

> **Ponto de consistência:** `audit_integrity` é um snapshot da cadeia validado
> imediatamente antes da geração. O evento `cnj.export.generated` é acrescentado
> depois, como trilha append-only da própria operação; portanto, uma verificação
> posterior da cadeia pode ter uma cabeça/contagem maior que a declarada no
> artefato. O manifesto continua válido para o conteúdo exportado.

## Endpoints da API

### 1. Criar Pedido de Exportação

```http
POST /api/v1/lgpd/cnj-exports/requests
Content-Type: application/json
Authorization: Bearer <dpo_token>
X-API-Key: <cartorio_api_key>

{
  "reference_period": "2026-06"
}
```

**Response (201):**
```json
{
  "request_id": "uuid-do-pedido",
  "status": "requested"
}
```

### 2. Aprovar Pedido (Dual Control)

```http
POST /api/v1/lgpd/cnj-exports/requests/{id}/approval
Content-Type: application/json
Authorization: Bearer <dpo_token_diferente>
X-API-Key: <cartorio_api_key>

{
  "reason": "Exportacao mensal para atendimento a requisicao CNJ referente ao periodo junho/2026"
}
```

**Regras:**
- `requested_by` ≠ `approved_by` (pessoas diferentes)
- Justificativa: 10-500 caracteres, sem PII
- Pedido deve estar com status `requested`

### 3. Gerar Artefato (após aprovação)

```http
POST /api/v1/lgpd/cnj-exports/requests/{id}/generate
Authorization: Bearer <dpo_token>
X-API-Key: <cartorio_api_key>
```

**Response (200):**
```json
{
  "report": {
    "schema_version": "1.0",
    "report_type": "CNJ_LGPD_AGGREGATED",
    "reference_period": "2026-06",
    "data_classification": "RESTRICTED_AGGREGATED",
    "indicators": {
      "new_data_subjects": 42,
      "notarial_protocols_created": 156,
      "audit_events": 3421,
      "rights_exercised": 8,
      "security_incidents": 0,
      "exports_generated": 1
    },
    "audit_integrity": {
      "chain_valid": true,
      "chain_length": 15000,
      "chain_head_sha256": "a1b2c3d4..."
    },
    "controls": {
      "human_approval": "dual_control_required",
      "automatic_external_transmission": false
    }
  },
  "manifest": {
    "schema_version": "1.0",
    "artifact_type": "CNJ_LGPD_AGGREGATED_MANIFEST",
    "report_sha256": "abc123...",
    "manifest_sha256": "def456..."
  }
}
```

## Indicadores Exportados

| Indicador | Descrição | Fonte |
|-----------|-----------|-------|
| `new_data_subjects` | Novos titulares de dados no período | `Cliente.created_at` |
| `notarial_protocols_created` | Protocolos notariais criados | `Protocolo.created_at` |
| `audit_events` | Total de eventos de auditoria | `AuditLog.timestamp` |
| `rights_exercised` | Direitos LGPD exercidos pelo catálogo explícito de ações de titular (exclui dashboard/consentimento) | `AuditLog.action` |
| `security_incidents` | Incidentes de segurança (ação `security.*`) | `AuditLog.action` |
| `exports_generated` | Exportações CNJ geradas (ação `cnj.export.generated`) | `AuditLog.action` |

## Campos Excluídos (Minimização)

Nenhum dos seguintes campos é incluído no relatório:

- `nomes`
- `cpf_cnpj`
- `telefones`
- `emails`
- `enderecos`
- `ips`
- `mensagens`
- `documentos`
- `payloads_audit`
- `identificadores_de_titulares`

## Logs de Proteção de Dados (para envio ao CNJ)

O relatório gerado pode ser enviado ao CNJ como evidência de conformidade LGPD. O manifesto SHA256 garante a integridade do documento.

### Exemplo de Log Consolidated (JSON)

```json
{
  "schema_version": "1.0",
  "report_type": "CNJ_LGPD_AGGREGATED",
  "reference_period": "2026-06",
  "generated_at": "2026-07-19T12:00:00Z",
  "data_classification": "RESTRICTED_AGGREGATED",
  "indicators": {
    "new_data_subjects": 42,
    "notarial_protocols_created": 156,
    "audit_events": 3421,
    "rights_exercised": 8,
    "security_incidents": 0,
    "exports_generated": 1
  },
  "audit_integrity": {
    "chain_valid": true,
    "chain_length": 15000,
    "chain_head_sha256": "a1b2c3d4e5f6..."
  },
  "controls": {
    "human_approval": "dual_control_required",
    "automatic_external_transmission": false,
    "integrity": "sha256_manifest_plus_append_only_audit_log"
  }
}
```

## Testes

O sistema possui **13 casos coletados** de serviço/API, todos passando na validação local:

- `test_create_request_success` — Criação de pedido
- `test_approve_request_dual_control` — Dupla aprovação (DPO diferente)
- `test_approve_rejects_same_person` — Rejeita mesmo DPO como aprovador
- `test_build_approved_export_rejects_unapproved` — Rejeita geração sem aprovação
- `test_export_is_aggregate_and_never_serializes_source_pii` — Garante que NUNCA serializa PII

---

**Nota:** O envio do relatório ao CNJ é um procedimento operacional externo a este sistema. O artefato gerado deve ser transmitido via canal institucional autorizado pelo DPO.
