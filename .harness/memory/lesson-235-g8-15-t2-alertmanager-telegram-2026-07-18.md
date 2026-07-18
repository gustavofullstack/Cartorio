# Lesson 235 — G8.15.T2 AlertManager → Telegram LGPD-safe pipeline (2026-07-18)

## Contexto

Wave 47 (Squad 15 — Radar, Metrics & Observability). G8.15.T2 do SUPER_PLANO_G8_100_TASKS:

> Habilitar alertas no AlertManager do Prometheus enviando logs formatados ao Telegram.

Implementação **OFFLINE-friendly** (sem VPS/AlertManager live nesta sessão):
- `infra/observability/alertmanager.yml` — config canônica (referência de produção).
- `scripts/alert_to_telegram.py` — script standalone (CLI dry-run + apply).
- `backend/app/api/v1/alertmanager.py` — endpoint FastAPI registrado em `api_router`.

## Decisões arquiteturais

### 1. LGPD-by-design em 3 camadas (defense-in-depth)

Já estabelecido em `app/services/pii.py` — repliquei no alertmanager receiver:

- **Camada 1 (input)**: Pydantic `extra="forbid"` rejeita payload com campos não documentados.
- **Camada 2 (formatação)**: `_scrub_pii()` aplica regex em summary/description antes de montar mensagem Telegram.
- **Camada 3 (output)**: `_safe_str()` trunca e aplica scrubber em qualquer label exposto.

Mesmo se uma camada falhar, as outras duas contêm o vazamento. **Zero persistência do payload bruto**.

### 2. BackgroundTasks + asyncio.run (FastAPI pattern)

```python
background_tasks.add_task(_runner_sync)  # NÃO asyncio.create_task

def _runner_sync() -> None:
    asyncio.run(_dispatch_or_send_all(...))  # cria loop novo no thread
```

**Por quê**: `BackgroundTasks` do FastAPI roda em threadpool (sem event loop ativo). `asyncio.create_task()` falha com `RuntimeError: no running event loop`. Solução: `asyncio.run()` cria loop novo no thread, encapsulado em try/except para isolar exceções.

### 3. Dedup em 2 níveis

- **AlertManager**: `group_interval: 5m` + `repeat_interval: 4h` no `route`.
- **Backend (defesa em profundidade)**: Redis SET NX TTL 60s por fingerprint de label canônica.

Se Redis cair, fail-open (passa). Se AlertManager repetir, dedup Redis segura. Se ambos falharem, mensagem duplicada — mas LGPD-safe, então risco zero.

### 4. Receivers granulares (não 1 receiver genérico)

5 receivers separados para routing fino:
- `default` → chat genérico (escrevente + GRUPO PIETRA)
- `critical` → sem dedup, repeat 1h
- `dlq` → sem `send_resolved` (DLQ é contador)
- `lgpd` → chat DPO + cartorio-lgpd
- `n8n` → chat operadores de workflow

Cada um aponta pra webhook dedicado no FastAPI (mesma lógica, distinto log prefix).

## Phone regex gotcha

PHONE_BR regex original (`\+?55?\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}`) falhava em `(34) 99876-1234` porque `+?55?` consumia `+5` greedy e depois não casava o `5?` opcional. Fix:

```python
# Duas alternativas (BR com ou sem código país):
re.compile(r"\+?55?\s?\(?\d{2}\)?\s?\d{4,5}-?\d{4}|\(?\d{2}\)?\s?\d{4,5}-?\d{4}")
```

Test que pegou: `test_email_phone_protocol_redacted` — assertion `"(34) 99876-1234" not in msg` falhou antes do fix.

## Trade-offs / O que NÃO foi feito

- **Sem MCP tool pro AlertManager**: fora de escopo desta task. Roadmap: G8.15.T5+ quando MCP para SRE for priorizado.
- **Sem templates Go custom (`templates/*.tmpl`)**: AlertManager nativo já cobre HTML formatting. Templates custom são nice-to-have.
- **Sem rate limit específico no webhook**: AlertManager já tem `group_wait: 30s` que limita naturalmente.
- **Sem persistência de histórico de alertas**: Prometheus + AlertManager já retém por `resolve_timeout: 5m`. Backend não precisa.

## Testes (22 PASS, 0 FAIL)

```
$ cd backend && uv run pytest tests/test_alert_to_telegram_g8.py --no-cov -v
============================== 22 passed in 0.48s ==============================
```

Cobertura:
- LGPD scrubber (3 testes): CPF, email+phone+protocol, payload vazio.
- Pydantic strict (4 testes): válido, extra forbidden, severity inválida, alerts vazio.
- Severity mapping (5 testes): critical/warning/info, fallback warning, resolved status.
- Dry-run (1 teste): CLI NÃO chama Telegram Bot API quando sem `--apply`.
- DedupCache (3 testes): mesmo fp dedup, fps distintos passam, janela expira.
- Endpoint HTTP (4 testes): 202 válido, 422 inválido, 422 extra, critical endpoint existe.
- YAML config (2 testes): válido, severity routing presente.

## Honesty gate (verde)

```bash
$ python3 -c "import yaml; yaml.safe_load(open('infra/observability/alertmanager.yml'))"
OK 5 top-level keys: ['global', 'route', 'inhibit_rules', 'receivers', 'templates']

$ cd backend && uv run ruff check app/   # 0 errors
$ uv run mypy app/                       # 0 errors
$ uv run pytest tests/test_alert_to_telegram_g8.py --no-cov -v  # 22 PASS
```

## Lesson reusable

1. **Pydantic `extra="forbid"` em qualquer webhook externo** — previne vetor de vazamento de PII via campos novos.
2. **`asyncio.run()` em `BackgroundTasks`** — padrão pra tasks que precisam de loop em threadpool.
3. **PHONE_BR regex com 2 alternativas** — `(XX) 9XXXX-XXXX` E `+55 XX 9XXXX-XXXX` precisam de regex separados.
4. **Dedup em 2 níveis (AlertManager + Redis)** — defesa em profundidade, fail-open no Redis.
5. **Config canônica em `infra/observability/`** (NÃO em `infra/alertmanager/` legado) — convenção do projeto pra observability tooling.

Modified by Gustavo Almeida — G8.15.T2.
