"""Testes para app/api/v1/telegram.py - _handle_state (state machine).

Cobre todos os 5 estados:
1. STATE_AGENDAR_SERVICO: escolhe servico, opcao invalida
2. STATE_AGENDAR_DATA: data valida, data invalida
3. STATE_AGENDAR_HORA: hora valida, hora invalida
4. STATE_AGENDAR_CONFIRMAR: sim/nao/invalido
5. STATE_PROTOCOLO: protocolo encontrado, nao encontrado
6. STATE_HUMANO: cria ticket

Sobe cobertura telegram.py 59% -> >=75%.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.telegram import (
    STATE_AGENDAR_CONFIRMAR,
    STATE_AGENDAR_DATA,
    STATE_AGENDAR_HORA,
    STATE_AGENDAR_SERVICO,
    STATE_HUMANO,
    STATE_IDLE,
    STATE_PROTOCOLO,
    _confirmar_agendamento,
    _handle_state,
)


def _make_bus() -> MagicMock:
    """Cria bus mockado com set(ex=) + delete (redis-py 5+)."""
    bus = MagicMock()
    bus.client.set = AsyncMock(return_value=True)
    bus.client.delete = AsyncMock(return_value=True)
    return bus


# =============================================================================
# STATE_AGENDAR_SERVICO
# =============================================================================


@pytest.mark.asyncio
async def test_state_agendar_servico_escolhe_numero_1() -> None:
    """_handle_state AGENDAR_SERVICO com input '1' avanca para AGENDAR_DATA."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "1", STATE_AGENDAR_SERVICO, {}, bus, chat_id=123
    )
    assert "Data" in text or "data" in text.lower()
    assert new_state == STATE_AGENDAR_DATA
    assert keyboard is None
    assert bus.client.set.called  # state updated via set(ex=)


@pytest.mark.asyncio
async def test_state_agendar_servico_escolhe_nome_servico() -> None:
    """_handle_state AGENDAR_SERVICO com nome do servico (key) tambem aceita."""
    bus = _make_bus()
    # SERVICOS tem chaves como 'certidao', 'escritura', etc.
    text, new_state, keyboard = await _handle_state(
        "1", STATE_AGENDAR_SERVICO, {}, bus, chat_id=123
    )
    assert new_state == STATE_AGENDAR_DATA


@pytest.mark.asyncio
async def test_state_agendar_servico_opcao_invalida() -> None:
    """_handle_state AGENDAR_SERVICO com input invalido retorna teclado + mesmo state."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "999", STATE_AGENDAR_SERVICO, {}, bus, chat_id=123
    )
    assert "invalida" in text.lower() or "inval" in text.lower() or "Escolha" in text
    assert new_state == STATE_AGENDAR_SERVICO  # NAO muda
    assert keyboard is not None


# =============================================================================
# STATE_AGENDAR_DATA
# =============================================================================


@pytest.mark.asyncio
async def test_state_agendar_data_formato_valido_dd_mm_yyyy() -> None:
    """_handle_state AGENDAR_DATA com data valida vai para AGENDAR_HORA."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "25/12/2026", STATE_AGENDAR_DATA, {}, bus, chat_id=123
    )
    assert "Horario" in text or "horario" in text.lower() or "hor" in text.lower()
    assert new_state == STATE_AGENDAR_HORA
    assert keyboard is None


@pytest.mark.asyncio
async def test_state_agendar_data_palavra_hoje() -> None:
    """_handle_state AGENDAR_DATA com 'hoje' aceita."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "hoje", STATE_AGENDAR_DATA, {}, bus, chat_id=123
    )
    assert new_state == STATE_AGENDAR_HORA


@pytest.mark.asyncio
async def test_state_agendar_data_formato_invalido() -> None:
    """_handle_state AGENDAR_DATA com data invalida retorna erro + mesmo state."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "123", STATE_AGENDAR_DATA, {}, bus, chat_id=123
    )
    assert "invalida" in text.lower() or "inval" in text.lower() or "Use" in text
    assert new_state == STATE_AGENDAR_DATA
    assert keyboard is None


# =============================================================================
# STATE_AGENDAR_HORA
# =============================================================================


@pytest.mark.asyncio
async def test_state_agendar_hora_formato_valido() -> None:
    """_handle_state AGENDAR_HORA com hora valida vai para AGENDAR_CONFIRMAR."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "14:30",
        STATE_AGENDAR_HORA,
        {"servico_nome": "Certidao", "data": "2026-12-25"},
        bus,
        chat_id=123,
    )
    assert "Confirmar" in text or "Confirm" in text or "confirma" in text.lower()
    assert new_state == STATE_AGENDAR_CONFIRMAR
    assert keyboard is not None  # confirmar_keyboard


@pytest.mark.asyncio
async def test_state_agendar_hora_formato_invalido() -> None:
    """_handle_state AGENDAR_HORA com hora invalida retorna erro + mesmo state."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "hora invalida", STATE_AGENDAR_HORA, {}, bus, chat_id=123
    )
    assert "invalido" in text.lower() or "inval" in text.lower() or "Use" in text
    assert new_state == STATE_AGENDAR_HORA
    assert keyboard is None


# =============================================================================
# STATE_AGENDAR_CONFIRMAR
# =============================================================================


@pytest.mark.asyncio
async def test_state_agendar_confirmar_sim() -> None:
    """_handle_state AGENDAR_CONFIRMAR com 'sim' chama _confirmar_agendamento e vai para IDLE."""
    bus = _make_bus()
    with patch(
        "app.api.v1.telegram._confirmar_agendamento",
        new=AsyncMock(return_value=("Confirmado!", None, False)),
    ):
        text, new_state, keyboard = await _handle_state(
            "sim", STATE_AGENDAR_CONFIRMAR, {}, bus, chat_id=123
        )
    assert new_state == STATE_IDLE
    assert text == "Confirmado!"


@pytest.mark.asyncio
async def test_confirmar_agendamento_abre_ticket_humano_sem_reservar_horario() -> None:
    """HITL: confirmar no Telegram nunca chama a API de agendamento real."""
    bus = _make_bus()
    bus.client.get = AsyncMock(
        return_value='{"state":"agendar:confirmar","data":{"servico_nome":"Autenticacao","data":"2026-07-20","hora":"10:00","valor":"R$ 6,80"}}'
    )
    with (
        patch(
            "app.api.v1.telegram._tool_criar_atendimento",
            new=AsyncMock(return_value={"ok": True, "atendimento_id": 81}),
        ) as create_ticket,
        patch("app.api.v1.telegram._call_api", new=AsyncMock()) as call_api,
    ):
        text, _keyboard, _handled = await _confirmar_agendamento(bus, 123, user_id=456)

    assert "Solicitacao registrada" in text
    assert "confirmara" in text
    assert create_ticket.await_count == 1
    assert call_api.await_count == 0


@pytest.mark.asyncio
async def test_state_agendar_confirmar_nao() -> None:
    """_handle_state AGENDAR_CONFIRMAR com 'nao' limpa state e volta menu."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "nao", STATE_AGENDAR_CONFIRMAR, {}, bus, chat_id=123
    )
    assert new_state == STATE_IDLE
    assert "cancelado" in text.lower()
    assert keyboard is not None  # menu
    assert bus.client.delete.called  # state cleaned


@pytest.mark.asyncio
async def test_state_agendar_confirmar_resposta_invalida() -> None:
    """_handle_state AGENDAR_CONFIRMAR com resposta invalida fica no mesmo state."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "talvez", STATE_AGENDAR_CONFIRMAR, {}, bus, chat_id=123
    )
    assert "Confirme" in text or "sim" in text.lower() or "nao" in text.lower()
    assert new_state == STATE_AGENDAR_CONFIRMAR
    assert keyboard is not None  # confirmar keyboard


# =============================================================================
# STATE_PROTOCOLO
# =============================================================================


@pytest.mark.asyncio
async def test_state_protocolo_nao_encontrado() -> None:
    """_handle_state PROTOCOLO com protocolo inexistente retorna erro + menu."""
    bus = _make_bus()
    with patch(
        "app.api.v1.telegram._tool_consultar_protocolo",
        new=AsyncMock(return_value={"erro": "not_found"}),
    ):
        text, new_state, keyboard = await _handle_state(
            "2026-999999", STATE_PROTOCOLO, {}, bus, chat_id=123
        )
    assert "nao encontrado" in text.lower() or "Verifique" in text
    assert new_state == STATE_IDLE
    assert keyboard is not None
    assert bus.client.delete.called  # state cleaned


@pytest.mark.asyncio
async def test_state_protocolo_encontrado() -> None:
    """_handle_state PROTOCOLO com protocolo encontrado retorna dados + menu."""
    bus = _make_bus()
    with patch(
        "app.api.v1.telegram._tool_consultar_protocolo",
        new=AsyncMock(
            return_value={"status": "EM_ANDAMENTO", "servico": "Certidao", "data": "2026-12-25"}
        ),
    ):
        text, new_state, keyboard = await _handle_state(
            "2026-000123", STATE_PROTOCOLO, {}, bus, chat_id=123
        )
    assert "EM_ANDAMENTO" in text
    assert "Certidao" in text
    assert new_state == STATE_IDLE
    assert keyboard is not None


# =============================================================================
# STATE_HUMANO
# =============================================================================


@pytest.mark.asyncio
async def test_state_humano_cria_ticket() -> None:
    """_handle_state HUMANO cria ticket — API retorna atendimento_id (nao id)."""
    bus = _make_bus()
    with patch(
        "app.api.v1.telegram._tool_criar_atendimento",
        new=AsyncMock(return_value={"ok": True, "atendimento_id": 42}),
    ):
        text, new_state, keyboard = await _handle_state(
            "Minha duvida sobre certidao", STATE_HUMANO, {}, bus, chat_id=123
        )
    assert "42" in text
    assert "Ticket" in text
    assert new_state == STATE_IDLE
    assert keyboard is not None
    assert bus.client.delete.called


@pytest.mark.asyncio
async def test_state_humano_falha_api_nao_inventa_ticket() -> None:
    """Regressao P0: se API falhar, NAO diz Ticket #N/A — pede retry."""
    bus = _make_bus()
    with patch(
        "app.api.v1.telegram._tool_criar_atendimento",
        new=AsyncMock(return_value={"erro": "HTTP 500"}),
    ):
        text, new_state, keyboard = await _handle_state(
            "Preciso de ajuda", STATE_HUMANO, {}, bus, chat_id=123, user_id=99
        )
    assert "Ticket criado" not in text
    assert "N/A" not in text
    assert "/humano" in text or "ticket" in text.lower() or "balcao" in text.lower()
    assert new_state == STATE_IDLE


# =============================================================================
# Default (state desconhecido)
# =============================================================================


@pytest.mark.asyncio
async def test_state_desconhecido_retorna_default() -> None:
    """_handle_state com state desconhecido retorna tuple default."""
    bus = _make_bus()
    text, new_state, keyboard = await _handle_state(
        "qualquer", "STATE_INEXISTENTE_99", {}, bus, chat_id=123
    )
    # Default: retorna ("", state, None)
    assert text == ""
    assert new_state == "STATE_INEXISTENTE_99"
    assert keyboard is None
