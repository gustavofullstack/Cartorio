"""Testes para serviço de notificações."""

import pytest
from sqlalchemy import create_engine

from app.models.base import Base
from app.models.cliente import Cliente
from app.services.notificacao import NotificationService, NotificationMethod
from app.services.pii import hash_pii


@pytest.fixture
def test_engine():
    # Force import de TODOS os models para popular Base.metadata
    from sqlalchemy.pool import StaticPool

    # StaticPool = 1 conexao compartilhada (evita "no such table" entre sessoes)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def test_session(test_session_factory):
    """Sessao para testes diretos do service."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cliente_completo(test_session):
    """Cria um cliente completo com dados de contato."""
    cliente = Cliente(
        cpf_hash=hash_pii("12345678909", salt="test-salt"),
        nome="Cliente Completo",
        email="cliente@example.com",
        telefone_hash=hash_pii("11999999999", salt="test-salt"),
        telegram_chat_id="123456789",
        whatsapp_number="5511999999999",
        email_notifications=True,
        sms_notifications=True,
        preferred_contact_method="telegram",
        consentimento_lgpd=True,
    )
    test_session.add(cliente)
    test_session.commit()
    test_session.refresh(cliente)
    return cliente


@pytest.fixture
def cliente_sem_contato(test_session):
    """Cria um cliente sem dados de contato."""
    cliente = Cliente(
        cpf_hash=hash_pii("98765432100", salt="test-salt"),
        nome="Cliente Sem Contato",
        email=None,
        telefone_hash=None,
        telegram_chat_id=None,
        whatsapp_number=None,
        email_notifications=False,
        sms_notifications=False,
        preferred_contact_method=None,
        consentimento_lgpd=True,
    )
    test_session.add(cliente)
    test_session.commit()
    test_session.refresh(cliente)
    return cliente


@pytest.fixture
def cliente_sem_consentimento(test_session):
    """Cria um cliente sem consentimento LGPD."""
    cliente = Cliente(
        cpf_hash=hash_pii("55566677788", salt="test-salt"),
        nome="Cliente Sem Consentimento",
        email="semconsentimento@example.com",
        telefone_hash=hash_pii("11888888888", salt="test-salt"),
        telegram_chat_id="987654321",
        whatsapp_number="5511888888888",
        email_notifications=True,
        sms_notifications=True,
        preferred_contact_method="whatsapp",
        consentimento_lgpd=False,  # Sem consentimento
    )
    test_session.add(cliente)
    test_session.commit()
    test_session.refresh(cliente)
    return cliente



async def test_enviar_notificacao_telegram(cliente_completo, test_session):
    """Testa envio de notificação via Telegram."""
    # Mock do método de envio para não chamar API real
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_telegram',
        return_value=True
    ) as mock_telegram:
        
        success = await NotificationService.enviar_notificacao(
            db=test_session,
            cliente_id=cliente_completo.id,
            mensagem="Teste de notificação Telegram",
            metodo=NotificationMethod.TELEGRAM,
        )
        
        assert success is True
        mock_telegram.assert_called_once_with(
            cliente_completo.telegram_chat_id, 
            "Teste de notificação Telegram"
        )


async def test_enviar_notificacao_whatsapp(cliente_completo, test_session):
    """Testa envio de notificação via WhatsApp."""
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_whatsapp',
        return_value=True
    ) as mock_whatsapp:
        
        success = await NotificationService.enviar_notificacao(
            db=test_session,
            cliente_id=cliente_completo.id,
            mensagem="Teste de notificação WhatsApp",
            metodo=NotificationMethod.WHATSAPP,
        )
        
        assert success is True
        mock_whatsapp.assert_called_once_with(
            cliente_completo.whatsapp_number, 
            "Teste de notificação WhatsApp"
        )


async def test_enviar_notificacao_metodo_preferido(cliente_completo, test_session):
    """Testa envio usando método preferido do cliente."""
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_telegram',
        return_value=True
    ) as mock_telegram:
        
        success = await NotificationService.enviar_notificacao(
            db=test_session,
            cliente_id=cliente_completo.id,
            mensagem="Teste método preferido",
            metodo=None,  # Usa preferido
        )
        
        assert success is True
        # Deve usar Telegram (método preferido do cliente)
        mock_telegram.assert_called_once()


async def test_enviar_notificacao_sem_contato(cliente_sem_contato, test_session):
    """Testa envio para cliente sem dados de contato."""
    with pytest.raises(ValueError, match="não tem método de contato"):
        await NotificationService.enviar_notificacao(
            db=test_session,
            cliente_id=cliente_sem_contato.id,
            mensagem="Teste sem contato",
        )


async def test_enviar_notificacao_sem_consentimento(cliente_sem_consentimento, test_session):
    """Testa envio para cliente sem consentimento LGPD."""
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_whatsapp',
        return_value=True
    ) as mock_whatsapp:
        
        success = await NotificationService.enviar_notificacao(
            db=test_session,
            cliente_id=cliente_sem_consentimento.id,
            mensagem="Teste sem consentimento",
            metodo=NotificationMethod.WHATSAPP,
        )
        
        # Deve retornar False por falta de consentimento
        assert success is False
        mock_whatsapp.assert_not_called()


async def test_notificar_agendamento_criado(cliente_completo, test_session):
    """Testa notificação de agendamento criado."""
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_telegram',
        return_value=True
    ) as mock_telegram:
        
        success = await NotificationService.notificar_agendamento_criado(
            db=test_session,
            cliente_id=cliente_completo.id,
            agendamento_id=123,
            titulo="Reconhecimento de Firma",
            data_hora="2026-07-01T14:30:00",
            local="balcao_1",
        )
        
        assert success is True
        # Verifica que a mensagem contém os dados do agendamento
        args, kwargs = mock_telegram.call_args
        assert "Reconhecimento de Firma" in args[1]
        assert "2026-07-01T14:30:00" in args[1]
        assert "balcao_1" in args[1]


async def test_notificar_agendamento_lembrete(cliente_completo, test_session):
    """Testa notificação de lembrete de agendamento."""
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_telegram',
        return_value=True
    ) as mock_telegram:
        
        success = await NotificationService.notificar_agendamento_lembrete(
            db=test_session,
            cliente_id=cliente_completo.id,
            agendamento_id=456,
            titulo="Autenticação de Documentos",
            data_hora="2026-07-02T10:00:00",
            local="balcao_2",
        )
        
        assert success is True
        # Verifica que a mensagem contém os dados do lembrete
        args, kwargs = mock_telegram.call_args
        assert "Lembrete" in args[1]
        assert "Autenticação de Documentos" in args[1]
        assert "2026-07-02T10:00:00" in args[1]


async def test_notificar_agendamento_cancelado(cliente_completo, test_session):
    """Testa notificação de cancelamento de agendamento."""
    import unittest.mock
    
    with unittest.mock.patch.object(
        NotificationService, 
        '_enviar_telegram',
        return_value=True
    ) as mock_telegram:
        
        success = await NotificationService.notificar_agendamento_cancelado(
            db=test_session,
            cliente_id=cliente_completo.id,
            agendamento_id=789,
            titulo="Escritura Pública",
        )
        
        assert success is True
        # Verifica que a mensagem contém os dados do cancelamento
        args, kwargs = mock_telegram.call_args
        assert "cancelado" in args[1]
        assert "Escritura Pública" in args[1]
        assert "789" in args[1]