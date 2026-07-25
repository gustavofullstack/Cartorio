"""Service de metrics Prometheus (open source, sem vendor).

Endpoint: GET /api/v1/metrics/prometheus (formato text/plain, version 0.0.4).

Por que Prometheus e nao vendor:
- Open source (Apache 2.0)
- Formato text simples, sem SDK
- Funciona com Grafana/Mimir/Thanos/etc (ecosistema padrao)
- Sem lock-in (vendor migracao = 1 dia)
- Sem dados enviados pra terceiros

Metricas expostas (A1+A2 + G8.15.T1):
- cartorio_http_requests_total{endpoint, method, status} - counter
- cartorio_http_request_duration_seconds{endpoint, method} - histogram
- cartorio_protocolos_total{status} - gauge (snapshot)
- cartorio_clientes_total - gauge
- cartorio_audit_chain_length - gauge
- cartorio_pii_blocks_total{type} - counter (legacy)
- pii_blocked_total{tipo_scrub, channel} - counter (A2 LGPD)
- scrub_latency_ms{tipo_scrub, result} - summary (A2 LGPD)
- dlq_depth{queue} - gauge (A2 LGPD)
- cartorio_db_pool_checked_out - gauge (A15 connection pool)
- cartorio_db_pool_size - gauge (A15)
- cartorio_db_pool_overflow - gauge (A15)
- cartorio_db_pool_max_overflow - gauge (A15)
- cartorio_db_pool_total_capacity - gauge (A15)
- cartorio_db_pool_utilization_pct - gauge (A15)
- cartorio_uptime_seconds - gauge

G8.15.T1 — Prometheus AI/LLM instrumentation (LGPD-safe labels):
- cartorio_llm_call_seconds{model,operation} - histogram (latency por chamada)
- cartorio_llm_calls_total{model,operation,status} - counter (success|error|timeout)
- cartorio_llm_tokens_total{model,direction} - counter (input|output cumulativo)
- cartorio_llm_errors_total{model,operation,error_type} - counter (tipo do erro)
- cartorio_llm_degraded_total{reason} - counter (E2.02 S3: degraded reply servida)

LGPD: APENAS labels categoricos (model, operation, status, direction, error_type).
ZERO PII em labels. Ver app/services/metrics.py::instrument_llm.
E2.02 S3: os metodos inc_llm_*/observe_llm_call_seconds COERCIONAM qualquer
valor fora da whitelist canonica para um fallback ("unknown"/"UnknownError") —
fail-safe, nunca levanta, nunca grava label dinamico (cardinalidade + PII).
"""

from __future__ import annotations

import functools
import inspect
import time
from typing import Any, Callable, TypeVar, cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.models.agendamento import Agendamento, StatusAgendamento

F = TypeVar("F", bound=Callable[..., Any])


class MetricsStore:
    """Singleton in-memory para metrics (reset a cada restart do processo).

    Cardinalidade de labels eh controlada via enums:
    - tipo_scrub: cpf | rg | telefone | email | cns | cnh | none
    - channel:    whatsapp | telegram | web | api
    - result:     blocked | allowed
    - queue:      evolution | chatwoot | telegram | outbox
    SEM session_id / cpf_value / user_email / request_id (explodem cardinalidade
    OU vazam PII).
    """

    def __init__(self) -> None:
        # counters: {metric_name: {labels_key: value}}
        self.counters: dict[str, dict[str, int]] = {}
        # histograms: {metric_name: {labels_key: [observations]}}
        self.histograms: dict[str, dict[str, list[float]]] = {}
        # gauges: {metric_name: scalar OR {labels_key: value}}
        self.gauges: dict[str, Any] = {}
        # registry para idempotencia do factory (chave -> handle)
        self._metric_registry: dict[str, _MetricHandle] = {}
        self._started_at: float = time.time()

        # Inicializa contadores de cold-start (evita Grafana no-data)
        self.inc_counter("cartorio_emolumento_consultado_total", value=0)
        self.inc_counter("cartorio_emolumento_erros_total", value=0)
        self.inc_counter("cartorio_telegram_mensagens_total", labels={"direction": "in"}, value=0)
        self.inc_counter("cartorio_telegram_mensagens_total", labels={"direction": "out"}, value=0)
        self.inc_counter("cartorio_telegram_erros_total", value=0)
        self.inc_counter("cartorio_whatsapp_mensagens_total", labels={"direction": "in"}, value=0)
        self.inc_counter("cartorio_whatsapp_mensagens_total", labels={"direction": "out"}, value=0)
        self.inc_counter("cartorio_whatsapp_erros_total", value=0)
        self.inc_counter("cartorio_agendamentos_conflitos_total", value=0)
        # E3.06 — cold-start das series novas (evita Grafana no-data)
        self.inc_counter(
            "cartorio_webhook_auth_failures_total", labels={"channel": "telegram"}, value=0
        )
        self.inc_counter(
            "cartorio_webhook_auth_failures_total", labels={"channel": "whatsapp"}, value=0
        )
        # Heartbeat 0.0 = "nunca rodou" (fail-safe: alerta dispara se o
        # scheduler do dead-man's switch nunca executar — mesmo padrao de
        # `backup_last_success_timestamp_seconds`).
        self.set_gauge("cartorio_audit_dead_mans_switch_heartbeat", 0.0)
        # Saude WhatsApp desconhecida no boot -> 0 (down, fail-safe).
        self.set_gauge("cartorio_whatsapp_evolution_service_up", 0.0)
        self.set_gauge("cartorio_whatsapp_session_connected", 0.0)
        # E3.07 / G9.S2 — series Telegram (nomes canonicos do SUPER_PLANO).
        for result in ("200", "401", "5xx"):
            self.inc_counter("telegram_webhook_total", labels={"result": result}, value=0)
        self.inc_counter("telegram_debounce_scheduled_total", value=0)
        self.inc_counter("telegram_response_sent_total", value=0)

    def inc_counter(self, name: str, labels: dict[str, str] | None = None, value: int = 1) -> None:
        key = self._labels_key(labels)
        self.counters.setdefault(name, {}).setdefault(key, 0)
        self.counters[name][key] += value

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        key = self._labels_key(labels)
        self.histograms.setdefault(name, {}).setdefault(key, [])
        self.histograms[name][key].append(value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Store gauge. With labels -> dict[labels_key, value]. Without -> scalar."""
        if labels:
            key = self._labels_key(labels)
            existing = self.gauges.get(name)
            if not isinstance(existing, dict):
                old = existing
                self.gauges[name] = {}
                if old is not None:
                    self.gauges[name][""] = old
            self.gauges[name][key] = value
        else:
            self.gauges[name] = value

    def _make_metric_or_skip_test(self, name: str, metric_type: str) -> "_MetricHandle":
        """Factory idempotente (A2 best practice).

        - Mesmo nome+type -> retorna mesma referencia (idempotente).
        - Nome diferente -> retorna nova referencia (nao colapsa).
        """
        if metric_type not in ("counter", "histogram", "gauge"):
            raise ValueError(f"metric_type invalido: {metric_type!r}")
        registry_key = f"{metric_type}:{name}"
        existing = self._metric_registry.get(registry_key)
        if existing is None:
            handle = _MetricHandle(name=name, metric_type=metric_type, store=self)
            self._metric_registry[registry_key] = handle
            return handle
        return existing

    def track_scrub_latency(self, tipo_scrub: str, result: str, duration_ms: float) -> None:
        """Helper A2: histogram scrub_latency_ms{tipo_scrub,result}."""
        self._make_metric_or_skip_test("scrub_latency_ms", "histogram")
        self.observe_histogram(
            "scrub_latency_ms",
            duration_ms,
            labels={"tipo_scrub": tipo_scrub, "result": result},
        )

    def inc_pii_blocked(self, tipo_scrub: str, channel: str) -> None:
        """Helper A2: counter pii_blocked_total{tipo_scrub,channel}."""
        self._make_metric_or_skip_test("pii_blocked_total", "counter")
        self.inc_counter(
            "pii_blocked_total",
            labels={"tipo_scrub": tipo_scrub, "channel": channel},
        )

    def set_dlq_depth(self, queue: str, depth: int) -> None:
        """Helper A2: gauge dlq_depth{queue}."""
        self._make_metric_or_skip_test("dlq_depth", "gauge")
        self.set_gauge("dlq_depth", float(depth), labels={"queue": queue})

    def inc_dlq_expired(self, queue: str | None, count: int) -> None:
        """Helper G8.08.T1: counter dlq_expired_total{queue}.

        Chamado apos `dlq.expire_old_messages()` para observability de
        retencao LGPD Art.16 (quanto foi descartado por idade).

        Args:
            queue: enum queue (evolution|chatwoot|telegram|outbox) ou None
                para totais agregados.
            count: numero de mensagens expiradas (soma no counter).
        """
        self._make_metric_or_skip_test("dlq_expired_total", "counter")
        labels = {"queue": queue} if queue else {}
        key = self._labels_key(labels)
        current = self.counters.get("dlq_expired_total", {}).get(key, 0)
        self.counters.setdefault("dlq_expired_total", {})[key] = current + count

    def set_audit_dead_mans_status(self, status_code: int) -> None:
        """Helper A13: gauge `audit_dead_mans_status` (3 niveis).

        Args:
            status_code: 0=healthy, 1=warning, 2=critical. Outros valores caem em 2.
        """
        # Clamp para evitar valores fora do range (safety net)
        if status_code not in (0, 1, 2):
            status_code = 2  # treat unknown as critical (fail-safe)
        self._make_metric_or_skip_test("audit_dead_mans_status", "gauge")
        self.set_gauge("audit_dead_mans_status", float(status_code))

    def inc_n8n_wf_execution(self, wf_name: str, status: str) -> None:
        """Helper B10: counter n8n_wf_executions_total{wf_name,status}.

        Args:
            wf_name: nome canonico do workflow N8N (slug ex: 'consulta-emolumento')
            status: 'success' | 'error' | 'running' (use success/error para finalized)
        """
        self._make_metric_or_skip_test("n8n_wf_executions_total", "counter")
        self.inc_counter(
            "n8n_wf_executions_total",
            labels={"wf_name": wf_name, "status": status},
        )

    def observe_n8n_wf_duration(self, wf_name: str, duration_seconds: float) -> None:
        """Helper B10: histogram n8n_wf_duration_seconds{wf_name}.

        Args:
            wf_name: nome canonico do workflow N8N
            duration_seconds: duracao total da execucao (segundos)
        """
        self._make_metric_or_skip_test("n8n_wf_duration_seconds", "histogram")
        self.observe_histogram(
            "n8n_wf_duration_seconds",
            duration_seconds,
            labels={"wf_name": wf_name},
        )

    # -------------------------------------------------------------------
    # E07 — Agent/LLM metrics (tokens, latency, success)
    # -------------------------------------------------------------------

    def observe_agent_tokens(self, tokens_in: int, tokens_out: int, think_tokens: int = 0) -> None:
        """Helper E07: histogram agent_tokens_total.

        Args:
            tokens_in: tokens de prompt consumidos
            tokens_out: tokens de completion gerados
            think_tokens: tokens de thinking (se disponivel)
        """
        self._make_metric_or_skip_test("agent_tokens_in_total", "histogram")
        self.observe_histogram("agent_tokens_in_total", float(tokens_in))
        self._make_metric_or_skip_test("agent_tokens_out_total", "histogram")
        self.observe_histogram("agent_tokens_out_total", float(tokens_out))
        if think_tokens:
            self._make_metric_or_skip_test("agent_think_tokens_total", "histogram")
            self.observe_histogram("agent_think_tokens_total", float(think_tokens))

    def observe_agent_latency(self, latency_seconds: float) -> None:
        """Helper E07: histogram agent_latency_seconds.

        Args:
            latency_seconds: tempo total da chamada ao LLM (segundos)
        """
        self._make_metric_or_skip_test("agent_latency_seconds", "histogram")
        self.observe_histogram("agent_latency_seconds", latency_seconds)

    def inc_agent_requests_total(self, provider: str, status: str) -> None:
        """Helper E07: counter agent_requests_total{provider,status}.

        Args:
            provider: 'opencode_go' | 'openclaw' | 'openrouter'
            status: 'success' | 'error' | 'rate_limited' | 'timeout'
        """
        self._make_metric_or_skip_test("agent_requests_total", "counter")
        self.inc_counter(
            "agent_requests_total",
            labels={"provider": provider, "status": status},
        )

    def inc_rate_limit_total(self, layer: str, tier: str = "none") -> None:
        """G7.07.T3: counter cartorio_rate_limit_total{layer,tier}.

        Args:
            layer: 'ddos' | 'sliding' | 'tier' | 'ip'
            tier: 'n8n' | 'dpo' | 'padrao' | 'none' (when IP layers)
        """
        self._make_metric_or_skip_test("cartorio_rate_limit_total", "counter")
        self.inc_counter(
            "cartorio_rate_limit_total",
            labels={"layer": layer, "tier": tier},
        )

    def set_n8n_wf_error_rate(self, wf_name: str, error_rate: float) -> None:
        """Helper B10: gauge n8n_wf_error_rate{wf_name} (0.0-1.0).

        Args:
            wf_name: nome canonico do workflow N8N
            error_rate: errors / (success+errors), clamped [0.0, 1.0]
        """
        rate = max(0.0, min(1.0, float(error_rate)))
        self._make_metric_or_skip_test("n8n_wf_error_rate", "gauge")
        self.set_gauge("n8n_wf_error_rate", rate, labels={"wf_name": wf_name})

    def set_backup_last_success_timestamp(self, unix_ts: float | None) -> None:
        """Helper A14: gauge `backup_last_success_timestamp_seconds` (Unix epoch).

        Gauge padrao Prometheus para "ultima vez que algo aconteceu com sucesso".
        Valor 0 (epoch=1970) sinaliza cold-start (nunca houve backup). Quando
        `unix_ts` eh None, mantemos 0 como sinal de "nunca" (fail-safe para
        alertas Prometheus `time() - backup_last_success_timestamp_seconds > X`).

        Args:
            unix_ts: timestamp Unix (segundos) do ultimo backup com marker
                `.complete` no diretorio de backups pg_basebackup. None = sem
                backup (cold-start).
        """
        value = float(unix_ts) if unix_ts is not None else 0.0
        self._make_metric_or_skip_test("backup_last_success_timestamp_seconds", "gauge")
        self.set_gauge("backup_last_success_timestamp_seconds", value)

    # -------------------------------------------------------------------
    # G8.15.T1 — Prometheus AI/LLM instrumentation (LGPD-safe)
    # -------------------------------------------------------------------
    #
    # Cardinalidade controlada por enums canonicos:
    #   model:      opencode_go | MiniMax_direct | litellm | openclaw | cache
    #   operation:  chat | tool_use | embedding | tts | fast_path
    #   status:     success | error | timeout | rate_limited | circuit_open
    #   direction:  input | output
    #   error_type: TimeoutException | HTTPError | ChatError | ValueError | ...
    #
    # SEM cpf / rg / email / protocolo / escritura / session_id nos labels.

    def observe_llm_call_seconds(self, model: str, operation: str, duration_seconds: float) -> None:
        """G8.15.T1: histogram `cartorio_llm_call_seconds{model,operation}`.

        Args:
            model: nome canonico do modelo (enum restrito, ex: 'opencode_go').
            operation: tipo de chamada (enum restrito, ex: 'chat').
            duration_seconds: duracao da chamada em segundos.

        E2.02 S3: model/operation fora da whitelist viram 'unknown' (fail-safe).
        """
        self._make_metric_or_skip_test("cartorio_llm_call_seconds", "histogram")
        self.observe_histogram(
            "cartorio_llm_call_seconds",
            float(duration_seconds),
            labels={
                "model": _canonical_label(model, _ALLOWED_LLM_MODELS, "unknown"),
                "operation": _canonical_label(operation, _ALLOWED_LLM_OPERATIONS, "unknown"),
            },
        )

    def inc_llm_calls_total(self, model: str, operation: str, status: str) -> None:
        """G8.15.T1: counter `cartorio_llm_calls_total{model,operation,status}`.

        Args:
            model: enum (opencode_go | MiniMax_direct | litellm | openclaw | cache).
            operation: enum (chat | tool_use | embedding | tts | fast_path).
            status: enum (success | error | timeout | rate_limited | circuit_open).

        E2.02 S3: labels fora da whitelist viram 'unknown' (fail-safe).
        """
        self._make_metric_or_skip_test("cartorio_llm_calls_total", "counter")
        self.inc_counter(
            "cartorio_llm_calls_total",
            labels={
                "model": _canonical_label(model, _ALLOWED_LLM_MODELS, "unknown"),
                "operation": _canonical_label(operation, _ALLOWED_LLM_OPERATIONS, "unknown"),
                "status": _canonical_label(status, _ALLOWED_LLM_STATUS, "unknown"),
            },
        )

    def inc_llm_tokens_total(self, model: str, direction: str, count: int) -> None:
        """G8.15.T1: counter cumulativo `cartorio_llm_tokens_total{model,direction}`.

        Nota: tokens sao cumulativos no tempo (Counter) porque a taxa de
        consumo (`rate()` no PromQL) eh a metrica de negocio relevante
        (custo do provider). Gauge seria util apenas para "tokens em vôo"
        e nao para "tokens consumidos historicamente".

        Args:
            model: enum (opencode_go | MiniMax_direct | litellm | openclaw).
            direction: enum (input | output).
            count: quantidade de tokens a incrementar (>= 0).
        """
        if count <= 0:
            return
        self._make_metric_or_skip_test("cartorio_llm_tokens_total", "counter")
        self.inc_counter(
            "cartorio_llm_tokens_total",
            labels={
                "model": _canonical_label(model, _ALLOWED_LLM_MODELS, "unknown"),
                "direction": _canonical_label(direction, _ALLOWED_LLM_DIRECTIONS, "unknown"),
            },
            value=int(count),
        )

    def inc_llm_errors_total(self, model: str, operation: str, error_type: str) -> None:
        """G8.15.T1: counter `cartorio_llm_errors_total{model,operation,error_type}`.

        Args:
            model: enum (opencode_go | MiniMax_direct | litellm | openclaw | cache).
            operation: enum (chat | tool_use | embedding | tts | fast_path).
            error_type: nome canonico do tipo de erro (ex: 'TimeoutException',
                'HTTP_5XX', 'HTTP_4XX', 'ChatError', 'JSONDecodeError').
                Cardinalidade controlada via classe de excecao, NAO mensagem.

        E2.02 S3: error_type fora da whitelist vira 'UnknownError' (fail-safe).
        """
        self._make_metric_or_skip_test("cartorio_llm_errors_total", "counter")
        self.inc_counter(
            "cartorio_llm_errors_total",
            labels={
                "model": _canonical_label(model, _ALLOWED_LLM_MODELS, "unknown"),
                "operation": _canonical_label(operation, _ALLOWED_LLM_OPERATIONS, "unknown"),
                "error_type": _canonical_label(
                    error_type, _ALLOWED_LLM_ERROR_TYPES, "UnknownError"
                ),
            },
        )

    def inc_llm_degraded_total(self, reason: str) -> None:
        """E2.02 S3: counter `cartorio_llm_degraded_total{reason}`.

        Incrementado TODA vez que o usuario recebe a degraded reply (LLM
        indisponivel) — silencio nunca e resposta, e cada ocorrencia vira
        sinal observavel para alerta (rate() no PromQL).

        Args:
            reason: enum (timeout | all_providers_down). Valor fora da
                whitelist vira 'unknown' (fail-safe, cardinalidade controlada).
        """
        self._make_metric_or_skip_test("cartorio_llm_degraded_total", "counter")
        self.inc_counter(
            "cartorio_llm_degraded_total",
            labels={
                "reason": _canonical_label(reason, _ALLOWED_LLM_DEGRADED_REASONS, "unknown"),
            },
        )

    # -------------------------------------------------------------------
    # E3.06 — Observability gaps (CB gauge, webhook auth, WA health, DMS)
    # -------------------------------------------------------------------

    def set_llm_circuit_open(self, provider: str, is_open: bool) -> None:
        """E3.06: gauge `cartorio_llm_circuit_open{provider}` (0/1).

        Atualizado onde o circuit breaker abre/fecha
        (`app/integrations/fallback.py::_record_failure` abre -> 1,
        `_record_success` fecha -> 0; `_is_circuit_open` re-publica 1 quando
        confirma circuito aberto no Redis — cobre restart do processo, ja que
        o gauge eh in-memory e o estado do CB vive no Redis com TTL 300s).

        Args:
            provider: enum canonico (mesma whitelist de `model` LLM).
                Valor fora da whitelist vira 'unknown' (fail-safe).
            is_open: True = circuito aberto (provider bloqueado).
        """
        self._make_metric_or_skip_test("cartorio_llm_circuit_open", "gauge")
        self.set_gauge(
            "cartorio_llm_circuit_open",
            1.0 if is_open else 0.0,
            labels={"provider": _canonical_label(provider, _ALLOWED_LLM_MODELS, "unknown")},
        )

    def inc_webhook_auth_failures(self, channel: str) -> None:
        """E3.06: counter `cartorio_webhook_auth_failures_total{channel}`.

        Incrementado nos pontos de 401 dos webhooks:
        - Telegram: `_verify_telegram_secret` (secret token ausente/invalido)
        - WhatsApp: `whatsapp_webhook` (HMAC Evolution invalido)

        Args:
            channel: enum (telegram | whatsapp). Fora da whitelist vira
                'unknown' (fail-safe, cardinalidade controlada).
        """
        self._make_metric_or_skip_test("cartorio_webhook_auth_failures_total", "counter")
        self.inc_counter(
            "cartorio_webhook_auth_failures_total",
            labels={"channel": _canonical_label(channel, _ALLOWED_WEBHOOK_CHANNELS, "unknown")},
        )

    def set_whatsapp_health(self, evolution_up: bool, session_connected: bool) -> None:
        """E3.06: gauges de saude WhatsApp/Evolution (0/1), alimentados no
        health check E2.08 (`app/api/v1/whatsapp.py::whatsapp_health`).

        - `cartorio_whatsapp_evolution_service_up`: Evolution API respondeu 200.
        - `cartorio_whatsapp_session_connected`: connectionState == "open".
          Separado por design (Lesson 260): API online NAO implica sessao aberta.
        """
        self._make_metric_or_skip_test("cartorio_whatsapp_evolution_service_up", "gauge")
        self._make_metric_or_skip_test("cartorio_whatsapp_session_connected", "gauge")
        self.set_gauge("cartorio_whatsapp_evolution_service_up", 1.0 if evolution_up else 0.0)
        self.set_gauge("cartorio_whatsapp_session_connected", 1.0 if session_connected else 0.0)

    def set_audit_dead_mans_heartbeat(self, unix_ts: float | None = None) -> None:
        """E3.06: gauge `cartorio_audit_dead_mans_switch_heartbeat` (Unix epoch).

        Marca o timestamp da ultima execucao do check do dead-man's switch
        (`app/jobs/dead_mans_switch.py::check_audit_log_freshness_3lvl`).
        Alerta canonico: `time() - metric > 900` (scheduler inativo > 15min).
        Cold-start = 0.0 ("nunca rodou" — fail-safe, alerta dispara).

        Args:
            unix_ts: timestamp Unix da execucao. None = agora (time.time()).
        """
        value = float(unix_ts) if unix_ts is not None else time.time()
        self._make_metric_or_skip_test("cartorio_audit_dead_mans_switch_heartbeat", "gauge")
        self.set_gauge("cartorio_audit_dead_mans_switch_heartbeat", value)

    # -------------------------------------------------------------------
    # E3.07 / G9.S2 — Telegram webhook pipeline (T3/T4/T5)
    # -------------------------------------------------------------------
    # LGPD (S2.T5): labels sao APENAS enums canonicos (result). NUNCA
    # chat_id / username / user_id / nome — ver test_telegram_metrics_g9.py
    # (gate que falha se label proibida aparecer).

    def inc_telegram_webhook_total(self, result: str) -> None:
        """G9.S2.T3: counter `telegram_webhook_total{result}` (200|401|5xx).

        Incrementado no wrapper do webhook (`telegram_webhook`) pelo desfecho
        HTTP: 200 = resposta normal (inclui degraded/scheduled — regra do bot
        eh SEMPRE 200), 401 = secret invalido, 5xx = excecao nao tratada.

        Args:
            result: enum ("200" | "401" | "5xx"). Fora da whitelist vira
                'unknown' (fail-safe, cardinalidade controlada).
        """
        self._make_metric_or_skip_test("telegram_webhook_total", "counter")
        self.inc_counter(
            "telegram_webhook_total",
            labels={
                "result": _canonical_label(result, _ALLOWED_TELEGRAM_WEBHOOK_RESULTS, "unknown")
            },
        )

    def inc_telegram_debounce_scheduled(self) -> None:
        """G9.S2.T3: counter `telegram_debounce_scheduled_total`.

        Incrementado quando o webhook agenda a background task de debounce
        (janela DEBOUNCE_WINDOW=1.2s) — 1x por janela, nao por mensagem.
        """
        self._make_metric_or_skip_test("telegram_debounce_scheduled_total", "counter")
        self.inc_counter("telegram_debounce_scheduled_total")

    def inc_telegram_response_sent(self) -> None:
        """G9.S2.T3: counter `telegram_response_sent_total`.

        Incrementado em `_send_message` quando a API do Telegram confirma o
        envio (HTTP 200). Cobre respostas sincronas e as da task de debounce.
        """
        self._make_metric_or_skip_test("telegram_response_sent_total", "counter")
        self.inc_counter("telegram_response_sent_total")

    def observe_telegram_webhook_response_seconds(self, duration_seconds: float) -> None:
        """G9.S2.T4: histogram `telegram_webhook_response_seconds`.

        Latencia webhook -> resposta ao usuario, INCLUINDO a janela de
        debounce de 1.2s: o inicio eh marcado na PRIMEIRA mensagem da janela
        (percepcao do usuario) e a observacao ocorre no envio confirmado
        (`_send_message` 200). Sem labels (cardinalidade zero).

        Args:
            duration_seconds: latencia observada (>= 0). Valores negativos
                (clock skew) sao clampados para 0.0.
        """
        self._make_metric_or_skip_test("telegram_webhook_response_seconds", "histogram")
        self.observe_histogram(
            "telegram_webhook_response_seconds", max(0.0, float(duration_seconds))
        )

    def _labels_key(self, labels: dict[str, str] | None) -> str:
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _parse_labels_key(self, key: str) -> dict[str, str]:
        if not key:
            return {}
        return dict(item.split("=", 1) for item in key.split("|") if "=" in item)

    def _labels_render(self, labels: dict[str, str] | None) -> str:
        """Render labels no formato Prometheus text (key="value",...)."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    def render_prometheus(self) -> str:
        """Renderiza tudo no formato text/plain do Prometheus (version 0.0.4)."""
        lines: list[str] = []

        # Counters
        counters: dict[str, dict[str, int]] = cast("dict[str, dict[str, int]]", self.counters)
        for name, buckets in counters.items():  # type: ignore[assignment]
            lines.append(f"# TYPE {name} counter")
            for key, value in buckets.items():
                label_dict = self._parse_labels_key(key)
                label_str = "{" + self._labels_render(label_dict) + "}" if label_dict else ""
                lines.append(f"{name}{label_str} {int(value)}")

        # Histograms (formato simplificado: count + sum, suficiente p/ cartorio)
        histograms: dict[str, dict[str, list[float]]] = cast(
            "dict[str, dict[str, list[float]]]", self.histograms
        )
        for name, buckets in histograms.items():  # type: ignore[assignment]
            lines.append(f"# TYPE {name} summary")
            for key, values in buckets.items():  # type: ignore[assignment]
                label_dict = self._parse_labels_key(key)
                label_str = "{" + self._labels_render(label_dict) + "}" if label_dict else ""
                lines.append(f"{name}_count{label_str} {len(values)}")  # type: ignore[arg-type]
                lines.append(
                    f"{name}_sum{label_str} {sum(values):.6f}"  # type: ignore[call-overload,arg-type]
                )

        # Gauges (suporta escalar E dict-com-labels)
        for name, val_or_map in self.gauges.items():  # type: ignore[assignment]
            lines.append(f"# TYPE {name} gauge")
            if isinstance(val_or_map, dict):
                for key, value in val_or_map.items():  # type: ignore[union-attr]
                    label_dict = self._parse_labels_key(key)
                    label_str = "{" + self._labels_render(label_dict) + "}" if label_dict else ""
                    lines.append(f"{name}{label_str} {float(value):.6f}")
            else:
                lines.append(f"{name} {float(val_or_map):.6f}")  # type: ignore[arg-type]

        # Uptime sempre
        lines.append("# TYPE cartorio_uptime_seconds gauge")
        lines.append(f"cartorio_uptime_seconds {time.time() - self._started_at:.6f}")
        return "\n".join(lines) + "\n"


# Singleton global
store = MetricsStore()


# ============================================================================
# G8.15.T1 — Decorator @instrument_llm
# ============================================================================
#
# Helper reutilizavel para instrumentar QUALQUER chamada LLM/AI sem acoplar
# o codigo de chamada ao codigo de metricas. Funciona para funcoes sync e
# async. Captura latencia, status (success/error), e tipo de erro.
#
# Uso:
#     from app.services.metrics import instrument_llm
#
#     @instrument_llm(model="opencode_go", operation="chat")
#     async def my_chat(messages): ...
#
#     @instrument_llm(model="MiniMax_direct", operation="tool_use")
#     def my_tool_call(payload): ...
#
# LGPD: NAO ha parametros opcionais com PII. model+operation vem de enums
# restritos do projeto (ver validate_label abaixo).


def _validate_label(name: str, value: str, allowed: set[str]) -> None:
    """Valida que um label value eh canonico (LGPD-safe).

    Args:
        name: nome do label (apenas para log).
        value: valor a ser usado como label.
        allowed: set canonico de valores permitidos.

    Raises:
        ValueError: se value nao estiver em allowed.
    """
    if value not in allowed:
        raise ValueError(
            f"metric label {name}={value!r} nao esta em whitelist canonica "
            f"(LGPD: nunca use valores dinamicos como CPF/RG/email). "
            f"Permitidos: {sorted(allowed)}"
        )


def instrument_llm(
    model: str,
    operation: str,
    *,
    extract_tokens: Callable[[Any], tuple[int, int]] | None = None,
) -> Callable[[F], F]:
    """G8.15.T1: decorator para instrumentar chamadas LLM/AI.

    Captura automaticamente:
    - latencia (cartorio_llm_call_seconds{model,operation})
    - status (cartorio_llm_calls_total{model,operation,status})
    - erros (cartorio_llm_errors_total{model,operation,error_type})
    - tokens (cartorio_llm_tokens_total{model,direction}) via extract_tokens

    Args:
        model: enum canonico (ex: 'opencode_go', 'MiniMax_direct', 'openclaw').
        operation: enum canonico (ex: 'chat', 'tool_use', 'embedding', 'tts').
        extract_tokens: funcao opcional `(result) -> (tokens_in, tokens_out)`
            para extrair contagem de tokens de um response object. Se None,
            token counting eh pulado (decorator funciona sem).

    Returns:
        decorator que envolve a funcao preservando __name__/__doc__/__wrapped__
        via functools.wraps. Funciona para sync e async.

    Raises:
        ValueError: se model ou operation nao estiver em whitelist.

    Example:
        @instrument_llm(model="opencode_go", operation="chat")
        async def call_opencode(messages):
            ...

        @instrument_llm(
            model="MiniMax_direct",
            operation="chat",
            extract_tokens=lambda r: (r.usage.prompt_tokens, r.usage.completion_tokens),
        )
        def call_minimax(payload): ...
    """
    _validate_label("model", model, _ALLOWED_LLM_MODELS)
    _validate_label("operation", operation, _ALLOWED_LLM_OPERATIONS)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                store.observe_llm_call_seconds(model, operation, elapsed)
                store.inc_llm_calls_total(model, operation, "success")
                if extract_tokens is not None:
                    try:
                        tok_in, tok_out = extract_tokens(result)
                        store.inc_llm_tokens_total(model, "input", tok_in)
                        store.inc_llm_tokens_total(model, "output", tok_out)
                    except Exception:
                        pass
                return result
            except Exception as exc:
                elapsed = time.perf_counter() - start
                store.observe_llm_call_seconds(model, operation, elapsed)
                store.inc_llm_calls_total(model, operation, "error")
                store.inc_llm_errors_total(
                    model,
                    operation,
                    _classify_error(exc),
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                store.observe_llm_call_seconds(model, operation, elapsed)
                store.inc_llm_calls_total(model, operation, "success")
                if extract_tokens is not None:
                    try:
                        tok_in, tok_out = extract_tokens(result)
                        store.inc_llm_tokens_total(model, "input", tok_in)
                        store.inc_llm_tokens_total(model, "output", tok_out)
                    except Exception:
                        pass
                return result
            except Exception as exc:
                elapsed = time.perf_counter() - start
                store.observe_llm_call_seconds(model, operation, elapsed)
                store.inc_llm_calls_total(model, operation, "error")
                store.inc_llm_errors_total(
                    model,
                    operation,
                    _classify_error(exc),
                )
                raise

        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)

    return decorator


# Whitelist canonica (LGPD: cardinalidade controlada).
# Adicionar novo valor aqui APENAS via PR com justificativa.
_ALLOWED_LLM_MODELS: set[str] = {
    "opencode_go",
    "MiniMax_direct",
    "litellm",
    "openclaw",
    "cache",
    "multi_provider",  # chat_with_fallback: chain tenta varios ate um dar certo
    "test",  # usado apenas em testes
    "opencode_free_1",
    "opencode_free_2",
    "opencode_free_3",
}

_ALLOWED_LLM_OPERATIONS: set[str] = {
    "chat",
    "tool_use",
    "embedding",
    "tts",
    "fast_path",
    "test",  # usado apenas em testes
}

# Whitelists canonicas E2.02 S3 (coercion fail-safe nos store methods).
_ALLOWED_LLM_STATUS: set[str] = {
    "success",
    "error",
    "timeout",
    "rate_limited",
    "circuit_open",  # G9.S3.T4 — provider skipped by circuit breaker
}

_ALLOWED_LLM_DIRECTIONS: set[str] = {
    "input",
    "output",
}

_ALLOWED_LLM_DEGRADED_REASONS: set[str] = {
    "timeout",  # teto global LLM_GLOBAL_TIMEOUT_S estourou
    "all_providers_down",  # tools + fallback simples retornaram vazio
}

# E3.06 — canais de webhook com auth propria (401 fail-closed).
_ALLOWED_WEBHOOK_CHANNELS: set[str] = {
    "telegram",  # X-Telegram-Bot-Api-Secret-Token (_verify_telegram_secret)
    "whatsapp",  # HMAC X-Hub-Signature-256 Evolution (whatsapp_webhook)
}

# E3.07 / G9.S2.T3 — desfechos HTTP possiveis do webhook Telegram.
# O bot responde SEMPRE 200 por design (retry infinito do Telegram em 5xx);
# "5xx" so ocorre em excecao nao tratada (bug) — por isso vira metrica.
_ALLOWED_TELEGRAM_WEBHOOK_RESULTS: set[str] = {
    "200",
    "401",
    "5xx",
}


def _canonical_label(value: str, allowed: set[str], fallback: str) -> str:
    """Coerce fail-safe de label para a whitelist canonica (E2.02 S3).

    Diferente de `_validate_label` (que levanta ValueError no decorator em
    tempo de import), este helper NUNCA levanta: metrica nao pode derrubar
    o request path. Valor fora da whitelist vira `fallback` — garantindo
    cardinalidade controlada e zero PII em labels mesmo se um call site
    passar valor dinamico (ex: nome cru de excecao, input de usuario).
    """
    return value if value in allowed else fallback


# Whitelist canonica de tipos de erro (LGPD: cardinalidade controlada).
# Adicionar novo valor aqui APENAS via PR com justificativa.
_ALLOWED_LLM_ERROR_TYPES: set[str] = {
    "TimeoutException",
    "HTTP_4XX",
    "HTTP_5XX",
    "ChatError",
    "JSONDecodeError",
    "ValueError",
    "TypeError",
    "KeyError",
    "RuntimeError",
    "ConnectionError",
    "CIRCUIT_OPEN",  # G9.S3.T4 — provider skipped by circuit breaker
    "UnknownError",
}


def _classify_error(exc: BaseException) -> str:
    """Classifica um erro em uma categoria canonica (LGPD-safe).

    Usa SOMENTE o nome da classe de excecao (nao a mensagem), garantindo
    que nenhum PII apareca no label error_type. Mensagens vao para log
    estruturado (que ja passa pelo log_masker PII scrubber).

    Args:
        exc: a excecao capturada.

    Returns:
        Categoria canonica do erro. Se nao houver match exato, retorna
        'UnknownError' (nunca o nome cru da classe para evitar cardinalidade
        explosiva).
    """
    name = type(exc).__name__
    if name in _ALLOWED_LLM_ERROR_TYPES:
        return name
    return "UnknownError"


class _MetricHandle:
    """Handle leve retornado por _make_metric_or_skip_test.

    - Mesmo nome+type -> mesma instancia (idempotente via _metric_registry).
    - Nome diferente -> instancia nova (handles distintos).
    Usado apenas como token de identidade; metodos de fato ficam no store pai.
    """

    __slots__ = ("name", "metric_type", "store", "_id")

    _counter: int = 0

    def __init__(self, name: str, metric_type: str, store: MetricsStore) -> None:
        _MetricHandle._counter += 1
        self._id = _MetricHandle._counter
        self.name = name
        self.metric_type = metric_type
        self.store = store

    def __repr__(self) -> str:
        return f"_MetricHandle(name={self.name!r}, type={self.metric_type!r}, id={self._id})"


def collect_db_metrics(db: Session) -> dict[str, Any]:
    """Coleta metrics do DB (gauge snapshot). Chamado pelo endpoint /metrics/prometheus."""
    from app.models.outbox_message import OutboxMessage, OutboxStatus

    metrics: dict[str, Any] = {}
    metrics["clientes_total"] = db.query(func.count(Cliente.id)).scalar() or 0
    metrics["lgpd_consent_total"] = (
        db.query(func.count(Cliente.id)).filter(Cliente.consentimento_lgpd.is_(True)).scalar() or 0
    )
    metrics["audit_chain_length"] = db.query(func.count(AuditLog.id)).scalar() or 0
    metrics["audit_chain_size"] = metrics["audit_chain_length"]

    # DLQ/outbox pending
    metrics["dlq_pending"] = (
        db.query(func.count(OutboxMessage.id))
        .filter(OutboxMessage.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]))
        .scalar()
        or 0
    )

    rows = db.query(Protocolo.status, func.count(Protocolo.id)).group_by(Protocolo.status).all()
    for status, count in rows:
        metrics[f'protocolos_total{{status="{status}"}}'] = count
        metrics[f'protocolo_status_total{{status="{status}"}}'] = count

    metrics["protocolo_total_total"] = db.query(func.count(Protocolo.id)).scalar() or 0

    # Gauge de agendamentos ativos futuros (S7.T4)
    import datetime

    metrics["agendamentos_ativos_total"] = (
        db.query(func.count(Agendamento.id))
        .filter(
            Agendamento.status.in_([StatusAgendamento.AGENDADO, StatusAgendamento.CONFIRMADO]),
            Agendamento.data_hora >= datetime.datetime.now(),
        )
        .scalar()
        or 0
    )

    return metrics


def collect_pool_metrics() -> dict[str, Any]:
    """Coleta gauges do pool SQLAlchemy (A15).

    Retorna dict com chaves canonicas para o Prometheus exposition format:
    - cartorio_db_pool_checked_out: conexoes em uso agora (gauge)
    - cartorio_db_pool_size: tamanho base do pool (gauge)
    - cartorio_db_pool_overflow: conexoes alem do pool_size (gauge)
    - cartorio_db_pool_max_overflow: maximo permitido alem do pool_size (gauge)
    - cartorio_db_pool_total_capacity: pool_size + max_overflow (gauge)
    - cartorio_db_pool_utilization_pct: % uso atual (0-100) (gauge)

    Para SQLite: retorna gauges zerados com chave `_backend=sqlite`.
    """
    # Import lazy pra evitar circular (db.py nao importa metrics.py)
    from app.db import get_pool_stats

    stats = get_pool_stats()
    metrics: dict[str, Any] = {
        "cartorio_db_pool_checked_out": float(stats.get("checked_out", 0)),
        "cartorio_db_pool_size": float(stats.get("pool_size", 0)),
        "cartorio_db_pool_overflow": float(stats.get("overflow", 0)),
        "cartorio_db_pool_max_overflow": float(stats.get("max_overflow", 0)),
        "cartorio_db_pool_total_capacity": float(stats.get("total_capacity", 0)),
        "cartorio_db_pool_utilization_pct": float(stats.get("utilization_pct", 0.0)),
    }
    return metrics


def render_full_prometheus(db: Session | None = None) -> str:
    """Renderiza todos os metrics incluindo snapshot do DB + pool stats (A15)."""
    if db is not None:
        for name, value in collect_db_metrics(db).items():
            p_name = name
            if (
                not name.startswith("cartorio_")
                and not name.startswith("pii_blocked_total")
                and not name.startswith("dlq_depth")
            ):
                p_name = f"cartorio_{name}"
            # Força o prefixo no dlq_pending para cartorio_dlq_pending
            if name == "dlq_pending":
                p_name = "cartorio_dlq_pending"
            store.set_gauge(p_name, value)
    # Pool stats sao in-process (sem dependencia de db), sempre populados
    for name, value in collect_pool_metrics().items():
        store.set_gauge(name, value)
    return store.render_prometheus()


def render_metrics_json(db: Session | None = None) -> dict[str, Any]:
    """Renderiza metrics como dict JSON (consumivel por N8N workflows).

    Shape canonico (Sprint 4 STREAM 1 - 2026-06-24):
    - clientes_total: int
    - protocolos_total: dict[status, int] - separa prefixo 'protocolos_total{status="..."}'
      para dict puro
    - audit_chain_length: int
    - db_pool: dict (A15) - pool_checked_out/size/overflow/max_overflow/
      total_capacity/utilization_pct - snapshot in-process
    - uptime_seconds: float
    - counters: dict[str, dict[labels_key, int]] - contadores in-process
    - gauges: dict[str, dict | scalar] - gauges in-process

    LGPD: NAO expoe PII. Apenas contadores agregados.
    """
    # Snapshot do DB (gauge values)
    db_snapshot: dict[str, Any] = {}
    if db is not None:
        db_snapshot = collect_db_metrics(db)
        # Popula a store.gauges in-memory com as db metrics para consistência no JSON
        for name, value in db_snapshot.items():
            p_name = name
            if (
                not name.startswith("cartorio_")
                and not name.startswith("pii_blocked_total")
                and not name.startswith("dlq_depth")
            ):
                p_name = f"cartorio_{name}"
            if name == "dlq_pending":
                p_name = "cartorio_dlq_pending"
            store.set_gauge(p_name, value)

    # Popula a store.gauges in-memory com as pool metrics para consistência no JSON
    for name, value in collect_pool_metrics().items():
        store.set_gauge(name, value)

    # Processa db_snapshot -> campos canonicos
    clientes_total = int(db_snapshot.get("clientes_total", 0))
    audit_chain_length = int(db_snapshot.get("audit_chain_length", 0))

    # protocolos_total: prefix 'protocolos_total{status="..."}' -> dict puro
    protocolos_total: dict[str, int] = {}
    for key, value in db_snapshot.items():
        if key.startswith('protocolos_total{status="') and key.endswith('"}'):
            # Extrai status entre 'protocolos_total{status="' e '"}'
            status = key[len('protocolos_total{status="') : -len('"}')]
            protocolos_total[status] = int(value)

    # A15: pool metrics (in-process, sempre presente)
    pool_raw = collect_pool_metrics()
    db_pool: dict[str, float] = {
        "checked_out": pool_raw.get("cartorio_db_pool_checked_out", 0.0),
        "size": pool_raw.get("cartorio_db_pool_size", 0.0),
        "overflow": pool_raw.get("cartorio_db_pool_overflow", 0.0),
        "max_overflow": pool_raw.get("cartorio_db_pool_max_overflow", 0.0),
        "total_capacity": pool_raw.get("cartorio_db_pool_total_capacity", 0.0),
        "utilization_pct": pool_raw.get("cartorio_db_pool_utilization_pct", 0.0),
    }

    # In-process metrics (counters e gauges)
    # Counters: {name: {labels_key: int}} -> {name: {labels_key: int}}
    counters: dict[str, dict[str, int]] = {}
    for name, buckets in store.counters.items():
        counters[name] = dict(buckets)

    # Gauges: suporta scalar E dict-com-labels -> normaliza pra JSON
    gauges: dict[str, Any] = {}
    for name, val_or_map in store.gauges.items():
        if isinstance(val_or_map, dict):
            gauges[name] = dict(val_or_map)
        else:
            gauges[name] = float(val_or_map)

    # Uptime sempre presente (reusa logica do render_prometheus)
    uptime_seconds = float(time.time() - store._started_at)

    return {
        "clientes_total": clientes_total,
        "protocolos_total": protocolos_total,
        "audit_chain_length": audit_chain_length,
        "audit_chain_size": audit_chain_length,
        "lgpd_consent_total": int(db_snapshot.get("lgpd_consent_total", 0)),
        "dlq_pending": int(db_snapshot.get("dlq_pending", 0)),
        "db_pool": db_pool,
        "uptime_seconds": uptime_seconds,
        "counters": counters,
        "gauges": gauges,
    }
