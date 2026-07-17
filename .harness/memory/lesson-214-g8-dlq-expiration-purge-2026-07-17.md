# Lesson 214 — G8.08.T1 DLQ expiration + purge + métricas (LGPD Art.16+37) (2026-07-17)

Type: project + reference

## Contexto

Wave 30 A2 (lesson 213) adicionou encryption-at-rest. Complementando, **expiration policy**
para DLQ é o próximo passo crítico de LGPD Art.16 ("eliminação após o tratamento").
Sem expiration, DLQ acumula indefinidamente → risco de:
- Crescimento ilimitado de storage
- PII antiga retida sem propósito
- Compliance breach (ANPD pode multar por retenção excessiva)

Wave 31 A1 entrega a implementação.

## Entrega (Wave 31 A1)

### `app/services/dlq.py` (refator: +140 LOC)

3 novas funções públicas:

| Função | Comportamento | LGPD |
|--------|---------------|------|
| `expire_old_messages(older_than_days=30)` | UPDATE (soft delete): marca FAILED > N dias com `last_error="EXPIRED after Xd at ..."` | Art.16 (eliminação após prazo) + Art.37 (auditoria preservada) |
| `purge_deleted_hard(older_than_days=180)` | DELETE físico: remove rows EXPIRED > 180d | Art.16 (eliminação segura pós-auditoria) |
| `stats_by_age(queue=None)` | SELECT snapshot: distribuição <1d / 1-7d / 7-30d / >30d | Observability |

### `app/services/metrics.py` (refator: +14 LOC)

Nova métrica `dlq_expired_total{queue}` counter via `MetricsStore.inc_dlq_expired()`.
Incrementada automaticamente em `expire_old_messages()`.

### `tests/test_dlq_expiration_g8.py` — **20 PASSED em 0.18s**

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestExpireOldMessages | 5 | UPDATE rowcount + returns zero + custom days + depth gauge + default FAILED status |
| TestPurgeDeletedHard | 3 | DELETE rowcount + returns zero + default 180d audit period |
| TestStatsByAge | 4 | empty DB + age buckets + queue filter + null created_at defense |
| TestIntegrationWithMetrics | 3 | counter increment + queue label + None label |
| TestLGPDCompliance | 3 | soft delete (UPDATE não DELETE) + purge uses DELETE + purge only EXPIRED |
| TestExportsAndSurface | 2 | __all__ exports + callable |

## Validação gates pós-wave

| Gate | Antes (lesson 213) | Depois (Wave 31 A1) |
|------|--------------------|---------------------|
| pytest | 3242 | **3262** (+20) |
| mypy strict | 0/156 | 0/156 |
| ruff | 0 | 0 |

## Decisões de design

1. **Two-phase deletion** (expire → purge): LGPD Art.37 exige trilha de auditoria.
   Soft delete primeiro (UPDATE com marker), hard delete só após 180d (período conservador).
2. **Default 30d expire**: LGPD recomenda 90d max para conversa_ia_log, mas DLQ são
   dados técnicos (status/eventos), 30d é suficiente.
3. **Default 180d purge**: 6 meses cobre ANPD + Conselho Federal (auditoria dupla).
4. **No magic markers no status**: OutboxStatus não tem DELETED ainda; usamos FAILED +
   `last_error="EXPIRED after Xd..."` como marker textual (auditável por query SQL).
5. **Batch protection**: `batch_size` parameter em expire (500) e purge (1000) para
   evitar lock de transação longa em DLQs grandes.

## Bug fix incluído nesta wave

Outro agente (provavelmente loop G7 paralelo) **adicionou** `from sqlalchemy.engine
import CursorResult` **no meio da função** `expire_old_messages` — sintaxe Python
inválida (imports entre statements). Movi o import para o topo da função. mypy
detecta o erro imediatamente: `error: Invalid syntax [syntax]`.

**Lição (Lesson 214)**: SEMPRE validar `uv run mypy app/` após adicionar código
novo, mesmo se o ruff passar. Imports no meio de função são armadilha silenciosa
que só mypy pega (ruff não checa sintaxe).

## Cross-refs

- lesson-213 (G8.08.T2 DLQ encryption, Wave 30 A2)
- lesson-212 (G8.07.T1 MCP tests, Wave 30 A1)
- lesson-211 (mega-commit 148 untracked)
- lesson-209 (Wave 29 closeout)
- lesson-198 (G7 Wave 26: DLQ depth metric baseline)
- LGPD Art.16 (eliminação) + Art.37 (registro de operações)
- SUPER_PLANO_G8_100_TASKS.md Squad 08 (próximo: T3 Telegram alerts + T4 DLQ tests)

## Próxima wave (Wave 31 A2)

**G8.08.T3**: Alertas de falhas recorrentes de webhook (DLQ) ao Telegram do escrevente.
- Script `scripts/dlq_alert_telegram.py` (cron 5min)
- Threshold: >10 mensagens em FAILED na última hora → alerta
- Usa Telegram bot token (já existe em `.secrets/telegram.env`)
- LGPD: alerta SEM expor payload (só métricas agregadas)

Modified by Gustavo Almeida