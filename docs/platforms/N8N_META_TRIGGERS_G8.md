# G8.06.T4 — Supabase/Postgres NOTIFY → n8n (metadados críticos)

Triggers Postgres que alertam o n8n quando **status** de protocolo ou
atendimento muda (ou no INSERT). Canal único: **`cartorio_meta`**.

Sem live DB obrigatório para validar o artefato (SQL + parse Python offline).

## Artefatos

| Path | Papel |
|------|--------|
| `infra/supabase/triggers_n8n_notify_g8.sql` | `notify_cartorio_meta()` + triggers |
| `backend/app/services/n8n_meta_triggers.py` | parse / channel / SQL gate |
| `backend/tests/test_n8n_meta_triggers_g8.py` | testes offline |
| `docs/N8N_META_TRIGGERS_G8.md` | este doc |

## Canal e payload

- **LISTEN/NOTIFY channel:** `cartorio_meta`
- **Tabelas:** `public.protocolos`, `public.atendimentos`
- **Eventos:** `AFTER INSERT OR UPDATE OF status`
- **Filtro UPDATE:** só notifica se `NEW.status IS DISTINCT FROM OLD.status`

Payload JSON (LGPD-safe — sem CPF/PII raw):

```json
{
  "channel": "cartorio_meta",
  "table": "protocolos",
  "op": "UPDATE",
  "id": 42,
  "status": "em_andamento",
  "old_status": "aberto",
  "protocolo_id": null,
  "numero": "2026-00042",
  "ts": "2026-07-17T12:00:00.000Z"
}
```

## Aplicar SQL (ops)

```bash
# Exemplo (psql / Supabase SQL editor)
psql "$DATABASE_URL" -f infra/supabase/triggers_n8n_notify_g8.sql

# Verificar
psql "$DATABASE_URL" -c \
  "SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE tgname LIKE 'trg_cartorio_meta%';"
```

## n8n consumer (desenho)

1. **Opção A — Postgres Trigger node / LISTEN bridge**  
   Worker ou n8n community node faz `LISTEN cartorio_meta` e, a cada
   notificação, inicia o workflow.

2. **Opção B — HTTP bridge**  
   Serviço leve (API ou edge function) escuta `cartorio_meta` e faz
   `POST` no webhook n8n (ex.: `/webhook/cartorio-meta`).

3. **Workflow mínimo**
   - Trigger: webhook ou Postgres notify
   - Node Function: validar JSON com o mesmo contrato de
     `parse_notify_payload` (`table` ∈ {protocolos, atendimentos},
     `op` ∈ {INSERT, UPDATE}, `status` presente)
   - Branches por `table` + `status` (ex.: `concluido` → pesquisa
     satisfação; `cancelado` → notificar escrevente)
   - Idempotência: chave `cartorio_meta:{table}:{id}:{status}:{ts}`
     (Redis / n8n static data)

## Python API (backend)

```python
from app.services.n8n_meta_triggers import (
    expected_channel,
    parse_notify_payload,
    validate_sql_file_exists,
    sql_structure_ok,
)

assert expected_channel() == "cartorio_meta"
payload = parse_notify_payload(notify_payload_text)
validate_sql_file_exists()  # Path do SQL no repo
ok, missing = sql_structure_ok()
```

## Testes

```bash
cd backend
env -u PYTHONPATH .venv312/bin/pytest tests/test_n8n_meta_triggers_g8.py -q
```

## Notas

- Complementa (não substitui) o webhook HTTP `protocolo_status_webhook`
  já presente em `infra/supabase/migrations/2026_06_24_0003-…`.
  NOTIFY é barato e local; HTTP webhook depende de rede/Vault.
- Fail-open no trigger: falha de `pg_notify` vira `WARNING`, não aborta DML.
- Não tick de SUPER_PLANO neste task unitário (honesty gate no orquestrador).
