# AUDIT_INTEGRITY_G8 — Verificador de integridade da blockchain de auditoria

**Wave:** G8 (Wave 50, 70/100)
**Task:** G8.19.T1
**Rein:** `cartorio-dev`
**LGPD:** Art. 37 (continuidade da auditoria) + Art. 50 (boa-fé) + Art. 46 (segurança)

## O que é

Ferramenta CLI + service Python que **recalcula hashes** de cada entrada do
`audit_log` e compara com os valores armazenados, reportando **qualquer
divergência**. É o complemento do **dead-man's-switch** (que detecta
quando o log *para de receber mutações*): o integridade checker detecta
quando o log *sofre mutação retroativa* (tamper-evident).

## Por que importa

`AuditService.verify_chain` original (G8.07.T2) já verifica integridade
mas **para no primeiro índice quebrado**. Para detectar:

- tamper mid-chain (entry 3 editada → quebra entries 3..N)
- HMAC forjado (assinatura inconsistente mesmo com hash consistente)
- edição retroativa que preserva `prev_hash` mas viola hash/HMAC

…precisamos enumerar **todos** os pontos de quebra, não só o primeiro.

## Arquitetura

```
backend/app/services/audit_integrity.py   ← service novo (chain + HMAC)
backend/scripts/audit_integrity_check.py  ← CLI ad-hoc + dead-man's-switch
backend/tests/test_audit_integrity_g8.py   ← 12 testes de regressao
```

### API exposta

```python
from app.services.audit_integrity import (
    verify_hash_sequence,  # pure function, retorna list[int]
    from_db,               # generator stream-friendly (yield_per 500)
    verify_full_chain,     # orquestrador: from_db + verify + summary
)

# Pure: 5 entries canonicas -> []
broken = verify_hash_sequence([...])

# Orquestrado (SQLAlchemy Session):
result = verify_full_chain(db_session)
# {
#   "total_entries": 1234,
#   "broken_indices": [42, 43, 44],
#   "integrity_score": 0.9976,
#   "chain_intact": False,
#   "first_break_id": 42,
#   "error": None,
# }
```

### Regras verificadas (por entry)

1. **Chain rule**: `prev_hash[N] == hash[N-1]` (ou `0*64` se `N == 0`)
2. **Hash rule**: `hash[N] == SHA256(prev_hash_canonico, payload, timestamp)`
3. **HMAC rule**: `hmac_signature[N] == HMAC(key, f"{hash}:{timestamp}:{actor_id}:{action}")`

Se qualquer regra falha, o índice é adicionado à lista `broken_indices`.
Uma entry com múltiplas falhas aparece **uma única vez** na lista.

## CLI

```bash
cd backend

# 1. Modo humano (texto formatado, exit 0/1/2)
uv run python scripts/audit_integrity_check.py

# 2. Modo JSON (machine-readable, ideal para Prometheus/Grafana)
uv run python scripts/audit_integrity_check.py --json

# 3. Modo strict (falha em chain OK se houver inconsistencias HMAC)
uv run python scripts/audit_integrity_check.py --strict-hmac
```

### Exit codes

| Code | Significado |
|------|-------------|
| 0    | Cadeia íntegra |
| 1    | 1+ índices divergentes (chain quebrada) |
| 2    | Erro de I/O (DB offline, sem permissão) |

### Integração com dead-man's-switch

O `app/main.py` lifespan já dispara a cada 15min o job
`app.jobs.cron_dead_mans_switch.run_dead_mans_switch_check_3lvl()`.
O integridade checker é **complementar**: pode ser invocado pelo mesmo
job (ou separado) para emitir métrica Prometheus `audit_chain_integrity`
ou alerta Telegram via `AUDIT_ALERT_TELEGRAM_CHAT_ID`.

Snippet sugerido (a integrar no Wave 51+):

```python
from app.services.audit_integrity import verify_full_chain
from app.db import SessionLocal

with SessionLocal() as session:
    result = verify_full_chain(session)
    if not result["chain_intact"]:
        send_telegram_alert(
            f"[CRITICAL] audit_log chain quebrada: "
            f"{len(result['broken_indices'])}/{result['total_entries']} entries "
            f"(first_break_id={result['first_break_id']})"
        )
```

## Testes (12 cenários)

Localização: `backend/tests/test_audit_integrity_g8.py`

| Teste | Cobertura |
|-------|-----------|
| `test_chain_intact_returns_empty` | 5 entries canônicas → `[]` |
| `test_chain_break_detected_after_payload_edit` | tamper payload entry 3 → `[3, 4, ...]` |
| `test_hmac_break_detected_with_valid_hash` | HMAC fake → entry quebrada |
| `test_first_entry_no_prev_hash_is_ok` | chain head (`prev_hash=None`) → OK |
| `test_modify_in_middle_breaks_remaining` | mid-chain edit → `[2, 3, 4, 5]` (regressão t024) |
| `test_empty_chain_returns_empty` | 0 entries → `[]`, `integrity_score=1.0` |
| `test_verify_full_chain_intact` | summary OK 7 entries |
| `test_verify_full_chain_detects_tamper` | tamper direto no DB → broken_indices populado |
| `test_cli_exit_code_zero_when_intact` | CLI exit 0 quando intacto |
| `test_cli_exit_code_one_when_broken` | CLI exit 1 quando quebrado |
| `test_cli_json_output_format` | JSON mode emite chaves canônicas |
| `test_large_chain_streams_correctly` | 100 entries via `yield_per` → score 1.0 |

Rodar:
```bash
unset PYTHONPATH && cd backend && uv run pytest tests/test_audit_integrity_g8.py --no-cov -v
```

## LGPD-by-design

- **Não modifica `audit_log`** (READ-only, AGENTS.md regra P0).
- **Não expõe payload em logs de erro** — apenas `id`, `indices quebrados`,
  `first_break_id`. Mensagem de erro em caso de I/O é `io_error:{ClassName}`,
  sem PII.
- **HMAC verificado** garante que atacante sem a chave `AUDIT_HMAC_KEY`
  não consegue forjar assinatura válida.
- **Stream-based** (`yield_per(500)`) — não carrega 100k entries na memória
  (protege contra DoS acidental em produção).

## Não-objetivos

- **Não substitui** o `AuditService.verify_chain` original — ambos
  coexistem. O original é mais rápido (early exit) para healthchecks;
  este é mais completo (enumera tudo) para forense.
- **Não implementa rotação de chave HMAC** — mudança de `AUDIT_HMAC_KEY`
  invalida TODAS as assinaturas (use `lesson-181` Wave 35 procedure).
- **Não emite métrica Prometheus automaticamente** — fica para Wave 51+
  quando integrarmos com `app.jobs.cron_dead_mans_switch`.

## Referencias

- `app/services/audit.py` (chain builder intocável, AGENTS.md P0)
- `app/services/audit_query.py` (listagem paginada)
- `app/models/audit_log.py` (model SQLAlchemy 2.0)
- `docs/ARCHITECTURE.md` — seção "Audit chain (blockchain-style)"
- `docs/LGPD.md` — Art. 37 (registro de tratamento)
- ADR-027 (codebase analysis SOLID/DRY/KISS)
- `.harness/memory/lesson-257-g8-19-t1-audit-integrity-2026-07-18.md`
