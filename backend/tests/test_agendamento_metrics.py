"""Testes A26 — agendamento_metrics: decorators de performance monitoring.

Cobertura:
- track_cache_operation decorator (hit/miss, duration, metrics)
- track_agendamento_operation decorator (sucesso/falha, duration)
- increment_cache_metric helper
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.agendamento_metrics import (
    increment_cache_metric,
    track_agendamento_operation,
    track_cache_operation,
)


# ─── track_cache_operation ─────────────────────────────────────────────

def test_track_cache_operation_hit():
    """track_cache_operation registra métricas de cache hit."""
    mock_store = MagicMock()

    @track_cache_operation("get_pendentes", "agendamento:v1:pendentes")
    def my_func():
        return [{"id": 1}]

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        result = my_func()

    assert result == [{"id": 1}]
    # Deve ter chamado observe_histogram + inc_counter
    assert mock_store.observe_histogram.called
    assert mock_store.inc_counter.called
    # Verifica label hit=true (passado como keyword arg)
    _, kwargs = mock_store.inc_counter.call_args
    labels = kwargs.get("labels", {})
    assert labels.get("hit") == "true"


def test_track_cache_operation_miss():
    """track_cache_operation registra métricas de cache miss."""
    mock_store = MagicMock()

    @track_cache_operation("get_pendentes", "agendamento:v1:pendentes")
    def my_func():
        return None  # Miss

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        result = my_func()

    assert result is None
    _, kwargs = mock_store.inc_counter.call_args
    labels = kwargs.get("labels", {})
    assert labels.get("hit") == "false"


def test_track_cache_operation_duration_recorded():
    """track_cache_operation registra duration no histograma."""
    mock_store = MagicMock()

    @track_cache_operation("slow_op", "some_key")
    def slow_func():
        import time
        time.sleep(0.01)  # 10ms
        return "done"

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        slow_func()

    hist_call = mock_store.observe_histogram.call_args
    assert hist_call is not None
    metric_name = hist_call[0][0]
    duration_ms = hist_call[0][1]
    assert metric_name == "agendamento_cache_operation_duration_ms"
    assert duration_ms >= 10


# ─── track_agendamento_operation ───────────────────────────────────────

def test_track_agendamento_operation_success():
    """track_agendamento_operation registra métricas de operação bem-sucedida."""
    mock_store = MagicMock()

    @track_agendamento_operation("criar")
    def create_agendamento():
        return {"id": 42}

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        result = create_agendamento()

    assert result == {"id": 42}
    assert mock_store.observe_histogram.called
    assert mock_store.inc_counter.called
    _, kwargs = mock_store.inc_counter.call_args
    labels = kwargs.get("labels", {})
    assert labels.get("operation") == "criar"
    assert labels.get("success") == "True"


def test_track_agendamento_operation_failure():
    """track_agendamento_operation registra métricas mesmo em falha."""
    mock_store = MagicMock()

    @track_agendamento_operation("cancelar")
    def cancel_agendamento():
        raise ValueError("falha na operação")

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        with pytest.raises(ValueError):
            cancel_agendamento()

    # Deve ter chamado métricas mesmo com exceção (finally block)
    assert mock_store.observe_histogram.called
    assert mock_store.inc_counter.called
    _, kwargs = mock_store.inc_counter.call_args
    labels = kwargs.get("labels", {})
    assert labels.get("success") == "False"


# ─── increment_cache_metric ────────────────────────────────────────────

def test_increment_cache_metric_sem_labels():
    """increment_cache_metric funciona sem labels."""
    mock_store = MagicMock()

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        increment_cache_metric("agendamento_cache_hits_total")

    mock_store.inc_counter.assert_called_once_with(
        "agendamento_cache_hits_total",
        labels={},
    )


def test_increment_cache_metric_com_labels():
    """increment_cache_metric funciona com labels."""
    mock_store = MagicMock()

    with patch("app.services.agendamento_metrics.metrics_store", mock_store):
        increment_cache_metric(
            "agendamento_cache_misses_total",
            labels={"operation": "get_pendentes", "reason": "cache_miss"},
        )

    mock_store.inc_counter.assert_called_once_with(
        "agendamento_cache_misses_total",
        labels={"operation": "get_pendentes", "reason": "cache_miss"},
    )
