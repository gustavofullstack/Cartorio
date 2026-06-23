# ADR-019: Job de retenção de dados (5y / até-revogação)

**Data:** 2026-06-23
**Status:** APROVADA (Sprint 3, Bloco 4.3)
**Autor:** ZCode (Mavis)
**Sprint:** 3 (Bloco 4.3)
**Decisão D4 (2026-06-23):** base de decisão

## Contexto

LGPD art. 7, II: tratamento de dados pessoais pode ocorrer para cumprimento
de obrigação legal/regulatória, **independentemente de consentimento**. Esse
é o caso dos atos cartorários (escrituras, procurações, registros), onde:

- **Provimento CNJ 74/2018**: retenção mínima de 5 anos para atos cartorários.
- **LGPD art. 16**: dados serão eliminados após cessada a finalidade, MAS
  finalidade cartorária cessa após 5 anos, não antes.

Em paralelo, clientes SEM ato cartorário (ex: só atendimento WhatsApp) podem
revogar consentimento a qualquer momento, e nesse caso os dados devem ser
**eliminados sob demanda** (LGPD art. 18 VI) ou **automaticamente** ao fim
de um prazo razoável de inatividade.

## Decisão

**Duas políticas concorrentes, avaliadas caso a caso pelo job diário**:

### Política 1: Cliente COM protocolo (5 anos)

- Retenção: 5 anos a partir da data do **último protocolo** (concluído ou em andamento).
- Após 5 anos: marcar `motivo_encerramento=retencao_5y` + anonimizar PII
  (mesmo processo do soft delete do ADR-018).
- NÃO fazer hard delete: o ato cartorário em si é imutável (fé pública).

### Política 2: Cliente SEM protocolo (até revogação OU 2 anos inativo)

- Retenção: até revogação explícita (DELETE /cliente/{id}) OU
  2 anos de inatividade (sem protocolo criado, sem atendimento, sem contato).
- Após 2 anos de inatividade: marcar `motivo_encerramento=outros` + soft delete.
- Hard delete permanece disponível via endpoint DELETE.

### Auditoria

O job emite **um único audit log** `retencao.run` por execução com:
- `scanned_clientes`: total analisado
- `soft_deleted`: quantos soft-deleted
- `hard_deleted`: quantos hard-deleted (se aplicável, hoje zero)
- `cutoff_date_5y`: ISO date usado como corte
- `cutoff_date_2y_inativo`: ISO date usado como corte
- `duration_ms`: tempo de execução

Cada cliente afetado recebe também `cliente.retencao.expired` no audit.

## Implementação

### Job: `app/jobs/retencao.py`

```python
def run_retencao(db: Session, *, now: datetime | None = None) -> RetencaoResult:
    """Aplica politica de retencao. Retorna contadores + lista de IDs afetados."""
    now = now or datetime.now(timezone.utc)
    cutoff_5y = now - timedelta(days=5 * 365)
    cutoff_2y_inativo = now - timedelta(days=2 * 365)

    # Politica 1: cliente COM protocolo + ultimo protocolo > 5y
    # Politica 2: cliente SEM protocolo + sem atividade > 2y
    ...
```

### Trigger

- **Manual**: `python -m app.jobs.retencao --dry-run` (apenas conta, não aplica)
- **Cron**: N8N workflow `#24-retencao-diaria` (criar) rodando 02:00 BRT diariamente
- **API interna**: `POST /api/v1/admin/retencao/run` (DPO only, X-API-Key + canal=dpo)

### Configurabilidade

- `RETENCAO_5Y_DAYS` (env var, default 1825) — permite encurtar pra testes
- `RETENCAO_INATIVO_DAYS` (env var, default 730) — 2 anos
- `RETENCAO_ENABLED` (env var, default true) — kill switch de emergência

## Consequências

**Positivas**
- Conformidade LGPD art. 7 II + 16 + Provimento CNJ 74/2018.
- Idempotente: rodar 2x no mesmo dia não causa dano (clientes já marcados
  são pulados pela query `WHERE deleted_at IS NULL`).
- Auditável: cada execução deixa rastro, cada cliente afetado também.
- Dry-run permite QA antes de aplicar em prod.
- Kill switch desliga tudo em emergência (P0 incident).

**Negativas**
- Performance: scan full de `clientes` em DB grande. Mitigação: índice
  parcial em `deleted_at IS NULL AND updated_at < cutoff_X` (Sprint 4).
- Edge case: cliente que tem protocolo CONCLUIDO há 6 anos mas volta pra
  novo protocolo hoje. Política atual usa **último protocolo**, não o mais
  antigo — correto.
- Não cobre backup off-band (Postgres dump, S3). Backups têm retenção
  própria (já em ADR-011).

## Não-objetivos

- Retenção de **documentos PDF** (Supabase Storage) — política separada
  (Sprint 4, sem delete API).
- Retenção de **audit log** (imutável, 5y próprio, sem delete).
- Retenção de **logs de erro** (15 dias, operacional, não jurídico).
- Anonimização retroativa de clientes com `consentimento_lgpd=false`
  ANTES do GDPR. Decisão: deixar como está; LGPD não retroage.

## Referências

- LGPD Lei 13.709/2018, art. 7 II; art. 16; art. 18 VI; art. 37
- Provimento CNJ 74/2018
- Decisão arquitetural D4 (2026-06-23, ver `.harness/TASKS.md`)
- ADR-018 (DELETE /cliente/{id} — mesmo serviço `direito_esquecimento`)
