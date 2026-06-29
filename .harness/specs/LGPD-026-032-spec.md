# LGPD-026 a LGPD-032 — Spec Consolidada dos 7 Endpoints de Direitos do Titular

> **Spec escrita por**: cartorio-lgpd (mvs_f83d53b5fff2495eaac7e3829b08e7cf)
> **Para implementação por**: cartorio-dev (mvs_6cd75d5f...)
> **Data**: 2026-06-29
> **Base normativa**: Lei 13.709/2018 (LGPD) + Provimento 74/2018 CNJ
> **Blocker global**: LGPD-014 (DPA DeepSeek PENDENTE) → backend **STAGING ONLY** até assinatura

## Contexto

Esta spec define os 7 endpoints de direitos do titular (LGPD art. 18) que fecham o compliance de 68% → 100% em Sprint 3.

### Naming canônico (D26-D32)

**Importante — não confundir com D19-D25 do `PLAN_100_TASKS_LOOP.md`**: D19-D25 naquele plano são itens **policy/process** (consent banner, DPO dashboard policy, privacy by design checklist, training, site policy v2, DPO contato publicado, auditoria ANPD) — escopo histórico de cartorio-lgpd, NÃO código HTTP.

**Esta spec é sobre D26-D32** = 7 endpoints HTTP reais que fecham o compliance técnico. Cartorio-dev implementa; cartorio-lgpd revisa.

### Ground truth verificado

`git log --oneline -25` + `backend/app/api/v1/lgpd_direitos.py`:
- 6 stubs existentes em `/api/v1/cliente/{id}/lgpd/*` (anonimizar, corrigir, oposicao, optout, portabilidade, portabilidade/download) — commit `3c2f961` 2026-06-25
- TODOS os stubs usam auth X-API-Key (escrevente), NÃO JWT/DPO
- TODOS os stubs retornam `{status: ok, audit: logged}` SEM realmente anonimizar/corrigir/exportar
- Compliance theater: pytest verde, código vazio (lesson 2026-06-23)

### Esta spec exige

1. Substituir TODOS os 6 stubs por implementação real com auth JWT + claim `dpo=true`
2. Adicionar 1 endpoint novo (D26 — DPO dashboard)
3. Upgrade de `auth_jwt.py:_build_payload` para incluir claim `dpo: bool`
4. Helper `require_dpo_role()` em `app/api/deps.py`
5. Path prefix canônico: **`/api/v1/lgpd/*`** (mantém versionamento v1, upgrade de auth)

### Mapeamento endpoint ↔ número de task

| Task | Endpoint | LGPD art. | Auth |
|---|---|---|---|
| D26 | `GET /api/v1/lgpd/dashboard` | art. 41 + 50 + 37 | JWT + dpo |
| D27 | `POST /api/v1/lgpd/consent` | art. 7º I + 8º | JWT (cliente OU dpo) |
| D28 | `DELETE /api/v1/lgpd/cliente/{id}` | art. 18 VI + 16 | JWT + dpo OU cliente_id=own |
| D29 | `GET /api/v1/lgpd/export/{cliente_id}` | art. 18 V + 19 | JWT (cliente OU dpo) |
| D30 | `POST /api/v1/lgpd/correct/{cliente_id}` | art. 18 III | JWT (cliente OU dpo) |
| D31 | `POST /api/v1/lgpd/revogar-consent` | art. 18 IX + 8º §5º | JWT (cliente OU dpo) |
| D32 | `GET /api/v1/lgpd/audit/{cliente_id}` | art. 18 VII + 37 | JWT (cliente OU dpo) |

---

## Auth Upgrade — JWT + claim `dpo=true`

### Mudanças em `auth_jwt.py`

```python
# Em _build_payload(), adicionar:
"dpo": dpo_flag,  # bool — True se usuario tem role DPO

# issue_access_token ganha param:
def issue_access_token(
    user_id: str,
    *,
    dpo: bool = False,  # NEW: role claim
    settings: Settings | None = None,
) -> str:
```

### Helper `require_dpo_role()` em `app/api/deps.py` (NEW)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_jwt import verify_token, JWTError

bearer_scheme = HTTPBearer(auto_error=False)


async def require_dpo_role(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Valida JWT + exige claim dpo=True. Retorna payload."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "UNAUTHORIZED", "mensagem": "Bearer token obrigatorio."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(credentials.credentials, expected_typ="access")
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "INVALID_TOKEN", "mensagem": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not payload.get("dpo"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"erro": "FORBIDDEN", "mensagem": "Role DPO obrigatoria."},
        )
    return payload


async def require_cliente_or_dpo(
    cliente_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """JWT onde sub==cliente_id OU claim dpo=True. Para endpoints do titular."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "UNAUTHORIZED", "mensagem": "Bearer token obrigatorio."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(credentials.credentials, expected_typ="access")
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "INVALID_TOKEN", "mensagem": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("dpo"):
        return payload  # DPO pode tudo
    if str(payload.get("sub")) == str(cliente_id):
        return payload  # titular vê os proprios dados
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"erro": "FORBIDDEN", "mensagem": "Acesso restrito ao titular ou DPO."},
    )
```

### Migração dos 6 stubs X-API-Key → JWT

Os 6 stubs em `/api/v1/cliente/{id}/lgpd/*` (anonimizar, corrigir, oposicao, optout, portabilidade, portabilidade/download) DEVEM ser migrados para usar `require_cliente_or_dpo` no lugar de `_require_api_key`. Path **permanece o mesmo** (compatibilidade com integrações N8N legadas).

**Decisão sobre sunset**: X-API-Key em endpoints LGPD **NÃO será removido** em 2027-12-31 conforme previa `auth_jwt.py:29` (que se refere ao sunset GERAL de X-API-Key, não específico a LGPD). Para LGPD, X-API-Key será removido quando (e se) todas as integrações N8N usarem JWT — manter `TODO` no código com data alvo `2027-12-31` para revisão.

---

## D26 — `GET /api/v1/lgpd/dashboard` (DPO Dashboard)

### Base legal
- LGPD art. 41 — designação e contato do DPO (Encarregado)
- LGPD art. 50 — boas práticas e governança
- LGPD art. 37 — registro de operações (alimenta os KPIs)

### Auth
- `require_dpo_role()` (JWT + claim `dpo=true`)

### Response shape

```json
{
  "kpis": {
    "total_clientes_ativos": 42,
    "total_clientes_revocados": 3,
    "total_clientes_anonimizados": 1,
    "consents_ativos": 38,
    "consents_revogados_30d": 2,
    "exports_solicitados_30d": 5,
    "audit_entries_24h": 1543,
    "audit_chain_status": "healthy"
  },
  "graficos": {
    "consents_por_finalidade": [
      {"finalidade": "atendimento", "granted": 40, "revoked": 2},
      {"finalidade": "marketing", "granted": 5, "revoked": 8},
      {"finalidade": "compartilhamento_terceiros", "granted": 3, "revoked": 4}
    ],
    "revogacoes_por_dia_30d": [
      {"data": "2026-05-30", "count": 0},
      {"data": "2026-05-31", "count": 1}
    ],
    "direitos_exercidos_30d": {
      "anonimizacao": 0,
      "correcao": 4,
      "portabilidade": 2,
      "revogacao": 2,
      "auditoria_titular": 1
    }
  },
  "dpo_contact": "dpo@2notasudi.com.br",
  "gerado_em": "2026-06-29T11:35:00Z"
}
```

### Audit chain entry

```python
AuditService.log(
    db,
    actor_id=f"dpo:{payload['sub']}",
    actor_type="dpo",
    action="lgpd.dashboard.read",
    resource="dashboard:lgpd",
    payload={
        "lgpd_art": "41 + 50",
        "kpis_returned": list(kpis.keys()),
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal="api_v1",
)
```

### Retenção
- Audit da leitura = 5 anos (LGPD art. 37)

### Testes TDD
1. **RED**: DPO com `dpo=true` retorna 200 com todos KPIs presentes
2. **RED**: usuário sem `dpo=true` retorna 403
3. **RED**: sem JWT retorna 401
4. **RED**: audit chain entry gerado com `action="lgpd.dashboard.read"`
5. **GREEN**: implementar query agregada (SQL `COUNT`, `GROUP BY` por finalidade)
6. **REFACTOR**: extrair queries para `app/services/lgpd_relatorio.py:metricas_dashboard()`

---

## D27 — `POST /api/v1/lgpd/consent` (Consentimento Granular)

### Base legal
- LGPD art. 7º I — consentimento
- LGPD art. 8º — consentimento deve ser livre, informado, inequívoco
- LGPD art. 9º — revogação a qualquer momento

### Auth
- `require_cliente_or_dpo` (cliente_id do path = cliente_id do JWT, OU DPO)

### Request schema (Pydantic v2)

```python
class ConsentRequest(BaseModel):
    cliente_id: int
    finalidade: Literal["atendimento", "marketing", "compartilhamento_terceiros",
                          "analytics", "prospeccao"]
    granted: bool
    canal: Literal["whatsapp", "telegram", "web", "presencial", "email"]
    justificativa_dpo: str | None = None  # obrigatorio se registrado por DPO
    
    model_config = ConfigDict(extra="forbid")
```

### Response shape

```json
{
  "status": "ok",
  "cliente_id": 42,
  "finalidade": "marketing",
  "granted": true,
  "consent_id": "uuid-v4",
  "registrado_em": "2026-06-29T11:35:00Z",
  "revogavel": true,
  "copy_juridica": {
    "base_legal": "LGPD art. 7º I + art. 8º",
    "direito_revocacao": "A qualquer momento via chat ou dpo@2notasudi.com.br",
    "dpo_contact": "dpo@2notasudi.com.br"
  }
}
```

### Audit chain entry

```python
AuditService.log(
    db,
    actor_id=f"cliente:{cliente_id}" if not justificativa_dpo else f"dpo:{payload['sub']}",
    actor_type="cliente" | "dpo",
    action="lgpd.consent.granted" if granted else "lgpd.consent.revoked",
    resource=f"cliente:{cliente_id}:consent:{finalidade}",
    payload={
        "lgpd_art": "7 I + 8",
        "finalidade": finalidade,
        "granted": granted,
        "canal": canal,
        "consent_id": consent_id,
        "justificativa_dpo": justificativa_dpo,
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal=canal,
)
```

### Retenção
- Registro de consent = enquanto durar relação + 5 anos (LGPD art. 16 + Provimento 74)
- Registro de revogação = 5 anos (manter prova)
- Ver `LGPD-retention-policy.md` para detalhes

### Testes TDD
1. **RED**: `granted=true` registra consent + audit + retorna 200
2. **RED**: `granted=false` registra revogação + audit + retorna 200
3. **RED**: `finalidade` inválida retorna 422
4. **RED**: `cliente_id` inexistente retorna 404
5. **RED**: DPO sem `justificativa_dpo` retorna 422
6. **RED**: Cliente revoga consent que tinha granted → `consent_history` mostra revogação
7. **RED**: Audit chain tem 2 entries (1 grant + 1 revoke) com action correta
8. **GREEN**: implementar usando `app/services/lgpd_consent.py:registrar_consentimento()` (já existe)
9. **REFACTOR**: extrair `consent_history(cliente_id)` para consulta histórica

---

## D28 — `DELETE /api/v1/lgpd/cliente/{id}` (Anonimização Real)

### Base legal
- LGPD art. 18 VI — direito de eliminação dos dados desnecessários
- LGPD art. 16 — minimização (anonimização > eliminação quando há retenção legal)

### Auth
- `require_cliente_or_dpo` (cliente_id=own OU DPO)

### Implementação real (substituindo stub)

Ver `app/services/lgpd/direito_esquecimento.py` (já existe e funciona). Mudanças no endpoint:

```python
# Se cliente TEM protocolos ativos (ato lavrado) → SOFT DELETE
#   - nome → "TITULAR_REVOGADO_<cpf_hash[:8]>"
#   - email → None
#   - telefone_hash → None
#   - consentimento_lgpd → False
#   - motivo_encerramento → REVOGACAO_CONSENTIMENTO
#   - deleted_at → now()
#   - cpf_hash MANTÉM (integridade referencial + audit chain)
#   - Cascade: conversas.documento_id PII scrubbed, nao deleted
#
# Se cliente NAO TEM protocolos → HARD DELETE
#   - LGPD permite, Provimento 74 CNJ nao se aplica
```

### Response shape

```json
{
  "status": "ok",
  "cliente_id": 42,
  "tipo": "soft",
  "protocolos_ativos": 3,
  "data_encerramento": "2026-06-29T11:35:00Z",
  "motivo": "revogacao_consentimento",
  "purged_tables": ["conversa_pii", "documento_metadata_pii"],
  "audit": "logged",
  "copy_juridica": {
    "base_legal": "LGPD art. 18 VI + art. 16",
    "retencao_minima_legal": "Protocolo COM ato: 5 anos (Provimento 74)",
    "dpo_contact": "dpo@2notasudi.com.br"
  }
}
```

### Audit chain entry

```python
AuditService.log(
    db,
    actor_id=f"cliente:{cliente_id}" if payload['sub'] == str(cliente_id) else f"dpo:{payload['sub']}",
    actor_type="cliente" | "dpo",
    action="lgpd.cliente.anonimizar",
    resource=f"cliente:{cliente_id}",
    payload={
        "lgpd_art": "18 VI + 16",
        "tipo": "soft" | "hard",
        "protocolos_ativos": count,
        "motivo_encerramento": "revogacao_consentimento",
        "purged_fields": ["nome", "email", "telefone_hash"],
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal="api_v1",
)
```

### Retenção
- Cliente COM ato → soft delete preserva registro + cpf_hash 5 anos, depois anonimiza cpf_hash também
- Cliente SEM ato → hard delete imediato
- Audit da anonimização = 5 anos (LGPD art. 37)

### Testes TDD
1. **RED**: Cliente COM protocolo → soft delete, PII substituído, registro mantido, 200
2. **RED**: Cliente SEM protocolo → hard delete, registro apagado, 200
3. **RED**: PII (nome, email) sumiu do DB mas `cpf_hash` ainda presente (soft)
4. **RED**: Cascade em conversas — PII scrubbed (texto vira `[PII_REDACTED]`)
5. **RED**: Cascade em documentos — metadata PII scrubbed
6. **RED**: Cliente já anonimizado → 409 Conflict (idempotência)
7. **RED**: Cliente inexistente → 404
8. **RED**: Não-DPO aplica em outro cliente → 403
9. **RED**: Cliente aplica em outro cliente_id → 403 (SoD)
10. **GREEN**: implementar usando `direito_esquecimento()` (já existe — completar)
11. **REFACTOR**: extrair cascade para `app/services/lgpd/cascade_pii_scrub.py`

---

## D29 — `GET /api/v1/lgpd/export/{cliente_id}` (Portabilidade Real)

### Base legal
- LGPD art. 18 V — portabilidade
- LGPD art. 19 — formato estruturado e de uso comum

### Auth
- `require_cliente_or_dpo` (cliente_id=own OU DPO)
- Rate limit: 5 exports/hora/cliente (anti-abuso)

### Response shape (JSON estruturado, art. 19)

```json
{
  "cliente": {
    "id": 42,
    "nome": "João Silva",
    "cpf_hash": "a1b2c3...",
    "email": "joao@example.com",
    "telefone_hash": "d4e5f6...",
    "consentimentos": [
      {"finalidade": "atendimento", "granted": true, "em": "2026-01-15T10:00:00Z"}
    ],
    "created_at": "2026-01-10T08:30:00Z",
    "deleted_at": null,
    "motivo_encerramento": null
  },
  "protocolos": [
    {
      "id": 100,
      "numero": "CART-2026-000123",
      "ato": "escritura_compra_venda",
      "valor": 50000.00,
      "status": "concluido",
      "data_lavratura": "2026-02-15T14:00:00Z"
    }
  ],
  "conversas": [
    {
      "id": 500,
      "canal": "whatsapp",
      "scrubbed_text": "[SCRUBBED: cliente perguntou sobre escritura, CPF 123.456.789-00 REDACTED]",
      "created_at": "2026-02-10T09:15:00Z"
    }
  ],
  "documentos": [
    {"id": 700, "tipo": "rg", "metadata_scrubbed": true, "filename_hash": "g7h8i9..."}
  ],
  "emolumentos": [
    {"id": 800, "valor": 2500.00, "snapshot_at": "2026-02-15T14:00:00Z"}
  ],
  "audit_logs": [
    {
      "id": 900,
      "action": "cliente.lgpd.anonimizar",
      "actor_id": "escrevente:abc12345",
      "timestamp": "2026-03-01T11:00:00Z",
      "payload_hash": "j0k1l2..."
    }
  ],
  "export_metadata": {
    "exported_at": "2026-06-29T11:35:00Z",
    "export_hash": "sha256:...",
    "lgpd_art": "18 V + 19",
    "formato": "json",
    "ttl_download_dias": 90,
    "dpo_contact": "dpo@2notasudi.com.br"
  }
}
```

### Implementação

Reusar `app/services/lgpd_export.py:exportar_dados_titular()` (já existe). Mudanças:
- Auth: trocar `_require_api_key` por `require_cliente_or_dpo`
- Cascade de conversas: aplicar `pii.scrub()` no texto antes de incluir (defense-in-depth)
- TTL do download: 90 dias (após isso regenerar)

### Audit chain entry

```python
AuditService.log(
    db,
    actor_id=f"cliente:{cliente_id}" if payload['sub'] == str(cliente_id) else f"dpo:{payload['sub']}",
    actor_type="cliente" | "dpo",
    action="lgpd.cliente.export",
    resource=f"cliente:{cliente_id}",
    payload={
        "lgpd_art": "18 V + 19",
        "export_hash": bundle.export_hash,
        "ttl_download_dias": 90,
        "tamanho_bytes": len(bundle_json),
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal="api_v1",
)
```

### Retenção (DECISÃO HÍBRIDA — ver `LGPD-retention-policy.md`)
- **Payload JSON exportado (com PII)**: até revogação (consentimento, art. 7 I) + TTL 90 dias
- **Audit da solicitação**: 5 anos (LGPD art. 37)
- **Hash SHA256 do payload**: 5 anos (LGPD art. 50)

### Testes TDD
1. **RED**: Cliente exporta próprios dados → 200 com todos campos
2. **RED**: Outro cliente exporta → 403
3. **RED**: DPO exporta qualquer cliente → 200
4. **RED**: Cliente exporta 6ª vez em 1h → 429 (rate limit)
5. **RED**: `export_hash` é SHA256 válido do JSON
6. **RED**: Conversas no export têm `scrubbed_text` (NUNCA texto cru)
7. **RED**: CPF no campo `cliente.cpf_hash` é HASH (não o CPF puro)
8. **RED**: Audit chain entry gerado com `action="lgpd.cliente.export"`
9. **GREEN**: reusar `exportar_dados_titular()` + auth nova
10. **REFACTOR**: extrair `apply_pii_scrub_to_bundle()`

---

## D30 — `POST /api/v1/lgpd/correct/{cliente_id}` (Correção)

### Base legal
- LGPD art. 18 III — correção de dados incompletos/incorretos

### Auth
- `require_cliente_or_dpo` (cliente_id=own OU DPO)

### Request schema (Pydantic v2)

```python
class CorrectionRequest(BaseModel):
    campos: dict[str, Any]
    justificativa: str | None = None
    
    model_config = ConfigDict(extra="forbid")
```

### Whitelist de campos alteráveis
- ✅ `nome`, `email`, `telefone`, `endereco`, `observacoes`
- ❌ `cpf_hash`, `cpf` (nunca), `deleted_at`, `motivo_encerramento`, `consentimento_lgpd` (use D27), `id`

### Response shape

```json
{
  "status": "ok",
  "cliente_id": 42,
  "diff": [
    {"campo": "email", "antes_hash": "sha256:abc...", "depois_hash": "sha256:def..."},
    {"campo": "telefone", "antes_hash": "sha256:ghi...", "depois_hash": "sha256:jkl..."}
  ],
  "corrigido_em": "2026-06-29T11:35:00Z",
  "audit": "logged",
  "copy_juridica": {
    "base_legal": "LGPD art. 18 III",
    "prazo_resposta": "Imediato (identificação) / 15 dias (outros)",
    "dpo_contact": "dpo@2notasudi.com.br"
  }
}
```

### Audit chain entry

```python
AuditService.log(
    db,
    actor_id=f"cliente:{cliente_id}" if payload['sub'] == str(cliente_id) else f"dpo:{payload['sub']}",
    actor_type="cliente" | "dpo",
    action="lgpd.cliente.correct",
    resource=f"cliente:{cliente_id}",
    payload={
        "lgpd_art": "18 III",
        "campos_alterados": list(diff.keys()),
        "diff_hashes": {campo: {"antes": h_antes, "depois": h_depois} for ...},
        "justificativa": justificativa,
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal="api_v1",
)
```

### Testes TDD
1. **RED**: Cliente corrige próprio email → 200, email atualizado
2. **RED**: Cliente tenta corrigir cpf_hash → 422 (whitelist)
3. **RED**: Outro cliente corrige → 403
4. **RED**: DPO corrige qualquer cliente → 200
5. **RED**: Diff no response tem hashes, NÃO valores puros
6. **RED**: Audit chain tem diff completo em `payload`
7. **RED**: hash chain íntegra após correção (`verify_chain`)
8. **GREEN**: implementar com whitelist + scrub + diff hash
9. **REFACTOR**: extrair `apply_correction_with_audit()`

---

## D31 — `POST /api/v1/lgpd/revogar-consent` (Revogação)

### Base legal
- LGPD art. 18 IX — revogação do consentimento
- LGPD art. 8º §5º — revogação a qualquer momento, sem ônus

### Auth
- `require_cliente_or_dpo` (cliente_id=own OU DPO)

### Request schema

```python
class RevokeConsentRequest(BaseModel):
    cliente_id: int
    finalidade: Literal["atendimento", "marketing", "compartilhamento_terceiros",
                          "analytics", "prospeccao"] | Literal["TODAS"] = "TODAS"
    
    model_config = ConfigDict(extra="forbid")
```

### Response shape

```json
{
  "status": "ok",
  "cliente_id": 42,
  "revogado_em": "2026-06-29T11:35:00Z",
  "finalidades_revogadas": ["marketing", "compartilhamento_terceiros"],
  "efeitos": {
    "prospect_marketing_bloqueado": true,
    "compartilhamento_terceiros_bloqueado": true,
    "atendimento_continua": true,
    "protocolos_preservados": true,
    "anonimizacao_sugerida": true
  },
  "copy_juridica": {
    "base_legal": "LGPD art. 18 IX + art. 8º §5º",
    "efeito": "Revogação effective immediately. Atendimento cartorário mantido por obrigação legal (art. 7 II + Provimento 74).",
    "direito_anonimizacao": "Para eliminação completa, exerça art. 18 VI via D28.",
    "dpo_contact": "dpo@2notasudi.com.br"
  },
  "audit": "logged"
}
```

### Side effects (effective immediately)

1. `Cliente.consentimento_lgpd = False`
2. `Cliente.consentimento_em = None`
3. Marcar TODAS as finalidades como revogadas no `consent_history`
4. Bloquear canais de marketing
5. Se revogou TODAS → flag `sugerir_anonimizacao = true` (NÃO aplicar D28 automaticamente)
6. Processamentos dependentes (prospecção, marketing) parados
7. Atendimento cartorário CONTINUA (base legal art. 7 II)

### Audit chain entry

```python
AuditService.log(
    db,
    actor_id=f"cliente:{cliente_id}" if payload['sub'] == str(cliente_id) else f"dpo:{payload['sub']}",
    actor_type="cliente" | "dpo",
    action="lgpd.consent.revoked",
    resource=f"cliente:{cliente_id}",
    payload={
        "lgpd_art": "18 IX + 8 §5",
        "finalidades_revogadas": finalidades_revogadas,
        "efeitos_aplicados": efeitos_dict,
        "anonimizacao_sugerida": True,
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal="api_v1",
)
```

### Retenção
- Registro da revogação = 5 anos (art. 37)

### Testes TDD
1. **RED**: Cliente revoga "marketing" → 200, `consentimento_lgpd` continua True (atendimento mantido)
2. **RED**: Cliente revoga "TODAS" → 200, `consentimento_lgpd = False`, `sugerir_anonimizacao = true`
3. **RED**: Após revogação TODAS, prospecção bloqueada
4. **RED**: Após revogação TODAS, atendimento cartorário CONTINUA funcional
5. **RED**: Cliente revoga, audit chain tem entry com `action="lgpd.consent.revoked"`
6. **RED**: hash chain íntegra após revogação
7. **GREEN**: implementar side effects + copy jurídica
8. **REFACTOR**: extrair `apply_revogacao_efeitos()`

---

## D32 — `GET /api/v1/lgpd/audit/{cliente_id}` (Transparência)

### Base legal
- LGPD art. 18 VII — informação sobre entidades públicas e privadas com quem compartilhou
- LGPD art. 37 — registro de operações

### Auth
- `require_cliente_or_dpo` (cliente_id=own OU DPO)

### Response shape

```json
{
  "cliente_id": 42,
  "periodo": {"inicio": "2026-01-01T00:00:00Z", "fim": "2026-06-29T23:59:59Z"},
  "total_eventos": 1543,
  "categorias": {
    "consentimentos": 5,
    "atendimentos": 1200,
    "protocolos": 15,
    "anonimizacoes": 0,
    "exports": 2,
    "compartilhamentos_subprocessadores": 320,
    "outros": 1
  },
  "sub_processadores": [
    {"nome": "OpenCode-Go (DeepSeek)", "finalidade": "LLM provider",
     "pais": "China", "dpa_status": "PENDENTE", "eventos_30d": 320},
    {"nome": "Supabase", "finalidade": "Postgres + Storage",
     "pais": "EUA", "dpa_status": "ASSINADO", "eventos_30d": 0},
    {"nome": "MiniMax (Mavis)", "finalidade": "AI agent harness",
     "pais": "Brasil", "dpa_status": "ASSINADO", "eventos_30d": 0}
  ],
  "eventos_recentes": [
    {
      "id": 900,
      "timestamp": "2026-06-29T10:00:00Z",
      "acao": "cliente.atendimento.iniciar",
      "ator": "cliente:42",
      "ip_truncado": "203.0.113.0/24",
      "payload_resumo": {"canal": "whatsapp", "protocolo_id": null}
    }
  ],
  "copy_juridica": {
    "base_legal": "LGPD art. 18 VII + art. 37",
    "retencao_audit": "5 anos (LGPD art. 16)",
    "dpo_contact": "dpo@2notasudi.com.br"
  }
}
```

### Implementação

1. Query `audit_log` filtrado por `resource LIKE 'cliente:{id}%'`
2. **Aplicar `pii.scrub()` em `payload_resumo`** (defense-in-depth)
3. **Truncar IP** (`/24` IPv4, `/48` IPv6) — NUNCA retornar IP completo
4. Listar sub-processadores conhecidos do `app/services/lgpd_subprocessadores.py` (NEW)
5. Marcar `dpa_status` por provider

### Audit chain entry (meta-auditoria)

```python
AuditService.log(
    db,
    actor_id=f"cliente:{cliente_id}" if payload['sub'] == str(cliente_id) else f"dpo:{payload['sub']}",
    actor_type="cliente" | "dpo",
    action="lgpd.audit.transparency",
    resource=f"cliente:{cliente_id}",
    payload={
        "lgpd_art": "18 VII + 37",
        "eventos_retornados": total_eventos,
        "periodo": {"inicio": periodo_inicio, "fim": periodo_fim},
    },
    ip=request.client.host,
    user_agent=request.headers.get("user-agent"),
    request_id=request.state.request_id,
    canal="api_v1",
)
```

### Retenção
- Eventos retornados = até 5 anos (LGPD art. 16)
- Meta-auditoria da consulta = 5 anos

### Testes TDD
1. **RED**: Cliente vê próprio histórico → 200 com `total_eventos > 0`
2. **RED**: Outro cliente vê → 403
3. **RED**: DPO vê qualquer cliente → 200
4. **RED**: IP retornado está TRUNCADO (`/24` ou `/48`)
5. **RED**: Payload retornado passou por `pii.scrub()` (CPF no payload vira `[CPF_REDACTED]`)
6. **RED**: Sub-processador com DPA pendente aparece com `dpa_status: "PENDENTE"`
7. **RED**: Cliente não recebe PII de OUTROS clientes (filtrar por `cliente_id` no WHERE)
8. **GREEN**: implementar query + scrub + truncation
9. **REFACTOR**: extrair `format_audit_event_for_titular()` helper

---

## Critérios Done (TODOS os 7)

- [ ] 7 endpoints implementados em `/api/v1/lgpd/*` (D26-D32)
- [ ] 6 stubs em `/api/v1/cliente/{id}/lgpd/*` migrados para JWT/dpo (path permanece)
- [ ] `auth_jwt.py:_build_payload` com claim `dpo: bool`
- [ ] `require_dpo_role()` + `require_cliente_or_dpo()` em `app/api/deps.py`
- [ ] Testes: DPO OK + não-DPO 403 + cliente OK no próprio + outro 403
- [ ] Audit chain entry em CADA endpoint
- [ ] PII scrub antes de QUALQUER log/response
- [ ] Soft delete preserva cpf_hash (D28)
- [ ] Hash chain íntegra após cada operação (`verify_chain` no test teardown)
- [ ] Coverage >= 90.18%
- [ ] mypy 0 / ruff 0
- [ ] LGPD-014 flag `STAGING ONLY` em response enquanto DPA não assinado
- [ ] OpenAPI documentado (FastAPI gera)
- [ ] Commit Conventional Commits, mensagem termina com `Modified by Gustavo Almeida`

## Blockers Documentados (não escalonar — só registrar)

1. **LGPD-014**: DPA DeepSeek PENDENTE → backend STAGING ONLY (escalar via Gustavo em 2026-07-15 se não resolvido)
2. **Lesson 163**: Working tree corruption mid-session — `git status` antes de cada commit
3. **Briefing stale x4**: Confiar em `git log`, não em `PROMPT.json`

## Cross-reference

- Specs auxiliares (mesma sessão):
  - `.harness/specs/LGPD-review-checklist.md` — checklist TDD obrigatório
  - `.harness/specs/LGPD-copy-juridica.md` — templates D27 + D31
  - `.harness/specs/LGPD-retention-policy.md` — política retenção D29

Modified by cartorio-lgpd (Pietra root mvs_97612f6bb1824cbdaf7c134fa34bf057)
Spec commit: pending