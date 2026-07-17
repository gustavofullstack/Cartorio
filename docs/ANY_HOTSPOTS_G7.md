# G7.20.T3 — Hotspots de `Any` vs TypedDict / Protocol

**Data:** 2026-07-17  
**Autor:** cartorio-dev (Wave 25 slot A3)  
**Escopo:** `backend/app/**/*.py`  
**Método:** `rg '\bAny\b' backend/app --type py` + classificação por linha (import vs uso)  
**Política desta wave:** **somente inventário + recomendações**. Sem refactor em massa.

---

## 1. Totais

| Métrica | Valor |
|---|---:|
| Arquivos com `Any` | 70 |
| Ocorrências brutas (`rg -c`, incl. imports) | ~358 |
| Usos **não-import** | **284** |
| Linhas só `from typing import … Any` | ~70 |

### Distribuição por *kind* (usos não-import)

| Kind | Qtd | % aprox. | Interpretação |
|---|---:|---:|---|
| `dict[str, Any]` | 223 | 78% | Payloads JSON / snapshots / webhooks |
| param/var `: Any` | 40 | 14% | Duck-typing (`bus`, `request`, Redis client) |
| `-> Any` return | 13 | 5% | Wrappers genéricos / scrub recursivo |
| list/nested outros | 4 | 1% | Listas heterogêneas |
| Callable / other | 4 | 1% | Raro |

**Leitura:** o “problema” não é `Any` solto em todo lugar — é **`dict[str, Any]` como contrato de borda** (HTTP externo, LLM tools, export LGPD, health checks).

---

## 2. Ranking geral (usos não-import)

| # | Usos | Arquivo | Camada |
|---:|---:|---|---|
| 1 | 24 | `app/api/v1/health_radar_expanded.py` | API |
| 2 | 21 | `app/api/v1/telegram.py` | API / webhook |
| 3 | 17 | `app/integrations/supabase_client.py` | Integração |
| 4 | 11 | `app/services/lgpd_export.py` | **Service (prio)** |
| 5 | 11 | `app/api/v1/integrations.py` | API |
| 6 | 9 | `app/services/chatwoot_handoff.py` | **Service (prio)** |
| 7 | 9 | `app/services/cartorio_agent.py` | **Service (prio)** |
| 8 | 9 | `app/api/v1/lgpd_direitos_v2.py` | API LGPD |
| 9 | 8 | `app/services/metrics.py` | **Service (prio)** |
| 10 | 7 | `app/services/brain_sync.py` | **Service** |
| 11 | 7 | `app/api/v1/_helpers.py` | API helper (ADR-027) |
| 12 | 6 | `app/services/notificacao.py` | **Service** |
| 13 | 6 | `app/services/chat_pipeline.py` | **Service** |
| 14 | 5 | `app/services/lgpd_erasure_orchestrator.py` | **Service LGPD** |
| 15 | 5 | `app/api/v1/n8n_metrics.py` / `lgpd_ripd` / `lgpd_dpo_dashboard` | API |

---

## 3. Prioridade **services** (foco G7.20.T3)

| Service | Usos | Padrão dominante | Risco tipagem | Recomendação |
|---|---:|---|---|---|
| `lgpd_export.py` | 11 | `DataExportBundle` com 6× `dict[str, Any]` | Médio (LGPD art. 18 portabilidade) | **TypedDict** por entidade exportada |
| `chatwoot_handoff.py` | 9 | webhook `payload: dict[str, Any]` | Médio (CRM) | TypedDict eventos Chatwoot + Protocol HTTP |
| `cartorio_agent.py` | 9 | tools/messages OpenAI-style | Médio (LLM) | TypedDict `ChatMessage` / `ToolDef` |
| `metrics.py` | 8 | snapshots Prometheus/JSON | Baixo | TypedDict `MetricsSnapshot` |
| `brain_sync.py` | 7 | containers/snapshots dict | Baixo | TypedDict `ContainerState` |
| `notificacao.py` | 6 | `request: Any` + context dict | Médio | `Protocol` Request-like + TypedDict context |
| `chat_pipeline.py` | 6 | payload/metadata/extra | Médio | dataclass já parcial → fechar TypedDict |
| `lgpd_erasure_orchestrator.py` | 5 | result summaries | **Alto** (erasure) | TypedDict `ErasureStepResult` (review lgpd) |
| `sentry.py` | 4 | `scrub_pii(obj: Any) -> Any` + event dict | Aceitável | Manter `Any` no scrubber recursivo; tipar `event` via SDK types se disponível |
| `redis_bus.py` | 4 | publish/subscribe payload | Baixo | TypedDict envelope `{channel, data}` |
| `lgpd_export_envelope.py` | 4 | manifest dict | Médio LGPD | TypedDict `ExportManifest` |
| `idempotency_store.py` | 4 | **já tem Protocol**; value ainda `dict[str, Any]` | Baixo | `IdempotencyCachedResponse` TypedDict |
| `audit_helper.py` | 4 | payload + `request: Any` | Médio (audit) | `Protocol` com `.headers`/`.client`/`state`; payload tipado por action |

---

## 4. Detalhamento dos top services

### 4.1 `lgpd_export.py` (melhor ROI)

```text
@dataclass
class DataExportBundle:
    cliente: dict[str, Any]
    protocolos: list[dict[str, Any]]
    ...
```

**Proposta (sem implementar agora):**

```python
class ClienteExportTD(TypedDict):
    id: int
    nome: str
    email_masked: str
    # ...

class DataExportBundleTD(TypedDict):
    cliente: ClienteExportTD
    protocolos: list[ProtocoloExportTD]
    ...
```

Benefício: mypy pega campo faltando no ZIP de portabilidade (ANPD).  
**Review:** `cartorio-lgpd` se tocar shape de export.

### 4.2 `chatwoot_handoff.py`

- `payload: dict[str, Any]` em handlers de status/message.
- `conv_id: Any` em `_send_to_telegram`.

**Proposta:**

```python
class ChatwootWebhookPayload(TypedDict, total=False):
    event: str
    id: int
    content: str
    conversation: NotRequired[dict[str, object]]
```

`conv_id: int | str` em vez de `Any`.

### 4.3 `cartorio_agent.py`

- `AGENT_TOOLS: list[dict[str, Any]]`
- `messages: list[dict[str, Any]]`
- tool args `dict[str, Any]`

**Proposta:** alinhar a schemas OpenAI-compat:

```python
class ToolFunctionDef(TypedDict):
    name: str
    description: str
    parameters: dict[str, object]  # JSON Schema — object ok

class ChatMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: NotRequired[list[dict[str, object]]]
```

### 4.4 `telegram.py` (API, mas hotspot #2)

- `bus: Any` em ~10 helpers (Redis bus duck-typed).

**Proposta (Protocol — já há padrão em `idempotency_store.py`):**

```python
class TelegramBus(Protocol):
    client: Any  # ou Protocol Redis com get/set/delete
    async def publish(self, channel: str, payload: dict[str, object]) -> int: ...
```

Isso remove a maioria dos `: Any` sem casar implementação concreta.

### 4.5 `health_radar_expanded.py` (API, hotspot #1)

- 19× `dict[str, Any]` para status de check (dns/traefik/socket/disk).

**Proposta:** um único TypedDict:

```python
class HealthCheckResult(TypedDict, total=False):
    status: Literal["online", "offline", "degraded"]
    latency_ms: int
    status_code: int | None
    erro: str | None
    detail: str
```

Baixo risco, alto ganho de legibilidade no radar.

### 4.6 `supabase_client.py`

- CRUD genérico retorna `list[dict[str, Any]]` + `_with_retry(fn: Any, ...) -> Any`.

**Proposta:**  
- `TypeVar` + `Callable[..., Awaitable[T]]` no retry.  
- Para rows: `dict[str, object]` ou TypedDict por tabela só onde o call-site for estável.

---

## 5. Onde `Any` é **aceitável** (não caçar)

| Local | Motivo |
|---|---|
| `sentry.scrub_pii(obj: Any) -> Any` | Walk recursivo de estruturas arbitrárias do SDK |
| JSON Schema `parameters` de tools LLM | Schema aberto por design |
| `before_send` event dict se sem stubs do Sentry | Integração vendor |
| Fakes de teste | Fora de `app/` (não contado no ranking de services) |

Preferir `object` a `Any` quando só se precisa de “não-None opaco” sem atributos.

---

## 6. Plano de ataque recomendado (waves futuras)

| Wave | Escopo | Esforço | Risco | Gate |
|---|---|---|---|---|
| W26 | `HealthCheckResult` + `TelegramBus` Protocol | P | Baixo | mypy app/ |
| W26 | `DataExportBundle` TypedDicts | M | Médio LGPD | testes export + review lgpd |
| W27 | Chatwoot webhook TypedDicts | M | Médio | handoff tests |
| W27 | Agent `ChatMessage`/`ToolDef` | M | Médio n8n/LLM | agent unit |
| W28 | `log_mutation(request: RequestLike)` Protocol | P | Baixo-audit | audit_helper unit |
| — | Mass `Any` → `object` sem TypedDict | — | **Evitar** | — |

**Não fazer:** bot auto-replace de `Any` → quebra mypy e não melhora contratos.

---

## 7. Critérios de “done” para G7.20.T3 (esta task)

- [x] Ranking por arquivo gerado  
- [x] Services priorizados  
- [x] Recomendações TypedDict/Protocol por hotspot  
- [ ] Zero refactor de produção nesta wave (cumprido)  

---

## 8. Comandos de reprodução

```bash
# contagem bruta
rg -c '\bAny\b' backend/app --type py | sort -t: -k2 -nr | head -40

# só services
rg -c '\bAny\b' backend/app/services --type py | sort -t: -k2 -nr
```

---

Modified by Gustavo Almeida  
cartorio-dev · G7.20.T3 · Wave 25
