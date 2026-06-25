"""Testes para o cache de agendamentos (A26)."""
import json
from unittest.mock import MagicMock, patch



def test_cache_key_functions():
    """Testa funções de geração de chaves de cache."""
    from app.services.agendamento_cache import (
        _cache_key_pendentes,
        _cache_key_proximos,
        _cache_key_cliente,
    )
    
    # Test keys are deterministic
    assert _cache_key_pendentes() == "agendamento:v1:pendentes"
    assert _cache_key_proximos() == "agendamento:v1:proximos"
    
    # Test cliente key uses hashing
    with patch("app.services.pii.hash_pii") as mock_hash:
        mock_hash.return_value = "hashed_123"
        assert _cache_key_cliente(123) == "agendamento:v1:cliente:hashed_123"
        mock_hash.assert_called_once()


def test_cache_operations_with_mock_redis():
    """Testa operações de cache com Redis mock."""
    from app.services.agendamento_cache import (
        get_agendamentos_pendentes_cached,
        set_agendamentos_pendentes_cached,
        get_agendamentos_proximos_cached,
        set_agendamentos_proximos_cached,
        get_cliente_cached,
        set_cliente_cached,
        invalidate_agendamento_cache,
    )
    
    # Mock Redis client
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps([{"id": 1, "titulo": "Test"}])
    mock_redis.set.return_value = True
    mock_redis.scan_iter.return_value = ["key1", "key2"]
    mock_redis.delete.return_value = 2
    
    with patch("app.services.agendamento_cache._get_redis_client") as mock_get_client:
        mock_get_client.return_value = mock_redis
        
        # Test get/set pendentes
        result = get_agendamentos_pendentes_cached()
        assert result == [{"id": 1, "titulo": "Test"}]
        
        success = set_agendamentos_pendentes_cached([{"id": 2, "titulo": "Test2"}])
        assert success is True
        
        # Test get/set proximos
        result = get_agendamentos_proximos_cached()
        assert result == [{"id": 1, "titulo": "Test"}]
        
        success = set_agendamentos_proximos_cached([{"id": 3, "titulo": "Test3"}])
        assert success is True
        
        # Test get/set cliente
        result = get_cliente_cached(123)
        assert result == [{"id": 1, "titulo": "Test"}]
        
        success = set_cliente_cached(123, {"nome": "Test Client"})
        assert success is True
        
        # Test invalidate
        count = invalidate_agendamento_cache()
        assert count == 2


def test_cache_fallback_when_redis_unavailable():
    """Testa comportamento de fallback quando Redis está indisponível."""
    from app.services.agendamento_cache import (
        get_agendamentos_pendentes_cached,
        set_agendamentos_pendentes_cached,
        get_agendamentos_proximos_cached,
        set_agendamentos_proximos_cached,
        get_cliente_cached,
        set_cliente_cached,
        invalidate_agendamento_cache,
    )
    
    with patch("app.services.agendamento_cache._get_redis_client") as mock_get_client:
        mock_get_client.return_value = None  # Redis unavailable
        
        # All operations should return None/False/0 without raising exceptions
        assert get_agendamentos_pendentes_cached() is None
        assert set_agendamentos_pendentes_cached([{"id": 1}]) is False
        assert get_agendamentos_proximos_cached() is None
        assert set_agendamentos_proximos_cached([{"id": 1}]) is False
        assert get_cliente_cached(123) is None
        assert set_cliente_cached(123, {"nome": "Test"}) is False
        assert invalidate_agendamento_cache() == 0


def test_cache_exception_handling():
    """Testa que exceções são tratadas corretamente."""
    from app.services.agendamento_cache import (
        get_agendamentos_pendentes_cached,
        set_agendamentos_pendentes_cached,
    )
    
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis error")
    mock_redis.set.side_effect = Exception("Redis error")
    
    with patch("app.services.agendamento_cache._get_redis_client") as mock_get_client:
        mock_get_client.return_value = mock_redis
        
        # Should return None/False without raising exceptions
        assert get_agendamentos_pendentes_cached() is None
        assert set_agendamentos_pendentes_cached([{"id": 1}]) is False