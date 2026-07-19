# Worker de retry do Outbox

`backend/app/jobs/outbox_retry.py` reprocessa, em lote limitado, somente registros
`outbox_messages` com `status=failed`, `attempts < 3` e `next_retry_at` vencido.
Ele usa o mesmo adaptador dos despachos primários e preserva o HITL: o canal
Chatwoot aceita exclusivamente contexto `incoming`.

O job não é iniciado pelo lifespan da API. Antes de agendá-lo em N8N, CronJob ou
systemd, a operação deve definir frequência, alerta para `PROCESSING` interrompido
e owner de incidentes. A chamada é assíncrona e recebe uma `Session`:

```python
with session_scope() as db:
    result = await run_due_outbox_retries(db, batch_limit=25)
```

Se o lock Redis não for adquirido — inclusive em indisponibilidade de Redis — o
resultado vem com `lock_acquired=False` e nada é enviado. Isso é intencional:
retries de integrações externas são at-least-once e devem privilegiar evitar envio
duplicado. Não são registrados payloads, respostas upstream ou detalhes de exceção.
