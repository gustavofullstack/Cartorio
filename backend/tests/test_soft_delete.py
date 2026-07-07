"""Testes de soft delete + restore (LGPD Art. 18 VI — direito ao esquecimento).

Usa a interface real de DeleteResult: tipo="hard"|"soft".
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest

from app.services.lgpd.direito_esquecimento import (
    direito_esquecimento,
    DeleteResult,
    ClienteNotFoundError,
    ClienteJaRevogadoError,
)


def test_direito_esquecimento_cliente_nao_existente() -> None:
    """Levanta ClienteNotFoundError se cliente não existe."""
    db = MagicMock()
    db.execute.return_value.scalar.return_value = 0  # count_protocolos = 0

    # Cliente não existe no DB
    db.get.return_value = None
    with pytest.raises(ClienteNotFoundError):
        direito_esquecimento(db, cliente_id=999, motivo="test")  # type: ignore[arg-type]


def test_direito_esquecimento_cliente_ja_revogado() -> None:
    """Levanta ClienteJaRevogadoError se já soft-deleted."""
    db = MagicMock()
    cliente = MagicMock()
    cliente.deleted_at = datetime.datetime(2026, 1, 1)
    db.get.return_value = cliente

    with pytest.raises(ClienteJaRevogadoError):
        direito_esquecimento(db, cliente_id=1, motivo="test")  # type: ignore[arg-type]


def test_direito_esquecimento_sem_protocolos_hard_delete() -> None:
    """Hard delete (tipo='hard') quando cliente não tem protocolos."""
    db = MagicMock()
    # _count_protocolos executa SELECT COUNT — retorna 0
    db.execute.return_value.scalar.return_value = 0

    cliente = MagicMock()
    cliente.deleted_at = None
    cliente.nome = "Test"
    cliente.cpf_hash = "a" * 64
    db.get.return_value = cliente
    # Protocolos órfãos query (cancelado/expirado) retorna lista vazia
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = []

    result = direito_esquecimento(db, cliente_id=1)

    # Interface real usa .tipo (não .action)
    assert result.tipo == "hard"
    assert result.protocolos_ativos == 0
    db.delete.assert_called_with(cliente)
    db.commit.assert_called()


def test_direito_esquecimento_com_protocolos_soft_delete() -> None:
    """Soft delete (tipo='soft', anonimiza PII) quando cliente tem protocolos."""
    db = MagicMock()
    # _count_protocolos retorna 3
    db.execute.return_value.scalar.return_value = 3

    cliente = MagicMock()
    cliente.deleted_at = None  # não está soft-deletado ainda
    cliente.cpf_hash = "abcdef0123456789abcdef0123456789"
    cliente.telefone_hash = "def"
    cliente.email = "test@x.com"
    db.get.return_value = cliente

    result = direito_esquecimento(db, cliente_id=1, motivo="solicitacao_titular")

    assert result.tipo == "soft"
    assert cliente.deleted_at is not None
    assert cliente.email is None  # anonimizado
    assert cliente.nome.startswith("TITULAR_REVOGADO_")  # anonimizado
    db.commit.assert_called()


def test_delete_result_e_dataclass() -> None:
    """DeleteResult é um dataclass frozen com os campos corretos."""
    now = datetime.datetime(2026, 7, 6, 12, 0, 0, tzinfo=datetime.timezone.utc)
    from app.models.cliente import MotivoEncerramento

    result = DeleteResult(
        cliente_id=1,
        tipo="hard",
        protocolos_ativos=0,
        data_encerramento=now,
        motivo=MotivoEncerramento.REVOGACAO_CONSENTIMENTO,
    )
    assert result.cliente_id == 1
    assert result.tipo == "hard"
    assert result.data_encerramento == now

    # Frozen: não pode modificar
    with pytest.raises(Exception):
        result.tipo = "soft"  # type: ignore[misc]


def test_soft_delete_servico_existe() -> None:
    """Serviço de direito ao esquecimento deve existir e ser callable."""
    from app.services.lgpd.direito_esquecimento import (
        direito_esquecimento as fn,
    )

    assert callable(fn)
