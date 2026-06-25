"""Métricas de performance para agendamentos (A26 - Performance Monitoring).

Rastreia:
- Cache hit/miss rates
- Tempo de resposta
- Contagem de operações

Integra com Prometheus via MetricsStore."""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from app.services.metrics import store as metrics_store

T = TypeVar("T")


def track_cache_operation(operation_name: str, cache_key: str) -> Callable:
    """Decorator para rastrear operações de cache.
    
    Args:
        operation_name: Nome da operação (get_pendentes, get_proximos, etc.)
        cache_key: Chave de cache usada
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Rastreia métrica
            labels = {
                "operation": operation_name,
                "cache_key": cache_key,
                "hit": "true" if result is not None else "false"
            }
            
            metrics_store.observe_histogram(
                "agendamento_cache_operation_duration_ms",
                duration_ms,
                labels=labels
            )
            
            metrics_store.inc_counter(
                "agendamento_cache_operations_total",
                labels=labels
            )
            
            return result
        return wrapper
    return decorator


def track_agendamento_operation(operation_name: str) -> Callable:
    """Decorator para rastrear operações de agendamento.
    
    Args:
        operation_name: Nome da operação (criar, cancelar, confirmar, etc.)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                labels = {
                    "operation": operation_name,
                    "success": str(success)
                }
                
                metrics_store.observe_histogram(
                    "agendamento_operation_duration_ms",
                    duration_ms,
                    labels=labels
                )
                
                metrics_store.inc_counter(
                    "agendamento_operations_total",
                    labels=labels
                )
        return wrapper
    return decorator


def increment_cache_metric(metric_name: str, labels: dict | None = None) -> None:
    """Incrementa um contador de cache.
    
    Args:
        metric_name: Nome da métrica
        labels: Labels para o Prometheus
    """
    if labels is None:
        labels = {}
    metrics_store.inc_counter(metric_name, labels=labels)