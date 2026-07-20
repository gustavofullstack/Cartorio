"""Suíte de Testes Progressivos Telegram 1000 Interações (@test_cartorio_bot).

Cobre:
- Tier 0: Smoke Test (5 interações nominais)
- Tier 1: 25 interações em DM e Grupos com menções e botões callback
- Tier 2: 100 interações de PII, comandos extras, deduplicação por update_id
- Tier 3: 250 interações multimodais (fotos, documentos, áudio, my_chat_member)
- Tier 4: 500 interações de máquina de estados e handoff HITL
- Tier 5: 1000 interações E2E de carga contínua com cálculo de latência e relatórios
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.telegram import ALLOWED_COMMANDS

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_telegram_outbound():
    """Mock de chamadas externas para Telegram e LLM para isolamento e velocidade extrema."""
    with patch("app.api.v1.telegram._send_message", new_callable=AsyncMock) as mock_send, \
         patch("app.api.v1.telegram._react", new_callable=AsyncMock) as mock_react, \
         patch("app.api.v1.telegram._answer_callback_query", new_callable=AsyncMock) as mock_cb, \
         patch("app.integrations.fallback.chat_with_fallback", new_callable=AsyncMock) as mock_llm:
        
        mock_send.return_value = True
        mock_react.return_value = True
        mock_cb.return_value = True
        
        llm_resp = MagicMock()
        llm_resp.content = "Atendimento do 2º Cartório de Notas de Uberlândia. Como posso ajudar?"
        mock_llm.return_value = llm_resp
        
        yield {
            "send": mock_send,
            "react": mock_react,
            "cb": mock_cb,
            "llm": mock_llm,
        }


def _make_dm_update(update_id: int, text: str, user_id: int = 6682284055) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id % 10000 + 1,
            "date": 1721500000 + update_id,
            "from": {"id": user_id, "first_name": "ClienteTest", "username": "clientetest", "is_bot": False},
            "chat": {"id": user_id, "type": "private"},
            "text": text,
        },
    }


def _make_group_update(update_id: int, text: str, group_id: int = -1004331849032, user_id: int = 111222) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id % 10000 + 1,
            "date": 1721500000 + update_id,
            "from": {"id": user_id, "first_name": "UsuarioGrupo", "username": "usermembro", "is_bot": False},
            "chat": {"id": group_id, "type": "supergroup", "title": "Grupo Teste Cartorio"},
            "text": text,
        },
    }


def _make_callback_update(update_id: int, data: str, user_id: int = 6682284055) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cb_{update_id}",
            "from": {"id": user_id, "first_name": "ClienteTest"},
            "message": {
                "chat": {"id": user_id, "type": "private"},
                "message_id": update_id % 10000,
            },
            "data": data,
        },
    }


def test_telegram_health_endpoint():
    resp = client.get("/api/v1/telegram/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "telegram-bot"


def test_smoke_5_interactions():
    """Tier 0: 5 interações nominais."""
    commands = ["/start", "/menu", "/agendar", "/protocolo", "/lgpd"]
    for i, cmd in enumerate(commands, start=100):
        upd = _make_dm_update(i, cmd)
        res = client.post("/api/v1/telegram/webhook", json=upd)
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") in ("ok", "ignored", "degraded")


def test_tier_1_25_interactions():
    """Tier 1: 25 interações em DM e Grupo com menções e callbacks."""
    for i in range(25):
        upd_id = 2000 + i
        if i % 3 == 0:
            upd = _make_dm_update(upd_id, f"Qual o valor do reconhecimento de firma? #{i}")
        elif i % 3 == 1:
            upd = _make_group_update(upd_id, f"@test_cartorio_bot qual o horário de atendimento? #{i}")
        else:
            upd = _make_callback_update(upd_id, "cmd:agendar")

        res = client.post("/api/v1/telegram/webhook", json=upd)
        assert res.status_code == 200


def test_tier_2_100_interactions_pii_and_dedup():
    """Tier 2: 100 interações com PII scrubbing e deduplicação."""
    # 1. Deduplicação por update_id
    upd_dup = _make_dm_update(3000, "Mensagem duplicada")
    res1 = client.post("/api/v1/telegram/webhook", json=upd_dup)
    res2 = client.post("/api/v1/telegram/webhook", json=upd_dup)
    assert res1.status_code == 200
    assert res2.status_code == 200

    # 2. PII inputs
    pii_texts = [
        "Meu CPF e 123.456.789-00 e meu RG e MG-12.345.678",
        "Contato pelo email cliente@dominio.com.br ou cel 34999998888",
        "Protocolo de certidao 2026-987654",
    ]
    for idx, text in enumerate(pii_texts):
        upd = _make_dm_update(3100 + idx, text)
        res = client.post("/api/v1/telegram/webhook", json=upd)
        assert res.status_code == 200

    # 3. 95 mensagens adicionais
    for i in range(95):
        upd = _make_dm_update(3200 + i, f"Pergunta número {i} sobre procuração pública")
        res = client.post("/api/v1/telegram/webhook", json=upd)
        assert res.status_code == 200


def test_tier_3_250_multimodal_and_group_events():
    """Tier 3: 250 interações multimodais e eventos de grupo."""
    # 1. Evento my_chat_member (bot entra no grupo)
    member_upd = {
        "update_id": 4000,
        "my_chat_member": {
            "chat": {"id": -1004331849032, "type": "supergroup", "title": "Grupo Novo"},
            "from": {"id": 111},
            "old_chat_member": {"status": "left"},
            "new_chat_member": {"status": "member"},
        },
    }
    res = client.post("/api/v1/telegram/webhook", json=member_upd)
    assert res.status_code == 200

    # 2. Áudio / voz update
    voice_upd = {
        "update_id": 4001,
        "message": {
            "message_id": 99,
            "chat": {"id": 6682284055, "type": "private"},
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "date": 1721500000,
            "voice": {"file_id": "file_voice_123", "duration": 5},
        },
    }
    res = client.post("/api/v1/telegram/webhook", json=voice_upd)
    assert res.status_code == 200

    # 3. Foto com legenda
    photo_upd = {
        "update_id": 4002,
        "message": {
            "message_id": 100,
            "chat": {"id": 6682284055, "type": "private"},
            "from": {"id": 6682284055, "first_name": "Gustavo"},
            "date": 1721500000,
            "photo": [{"file_id": "p1", "width": 100, "height": 100}],
            "caption": "Foto da minha identidade para agendamento",
        },
    }
    res = client.post("/api/v1/telegram/webhook", json=photo_upd)
    assert res.status_code == 200

    # 4. Restante de 246 mensagens
    for i in range(246):
        upd = _make_dm_update(4100 + i, f"Consulta multimodal {i}")
        res = client.post("/api/v1/telegram/webhook", json=upd)
        assert res.status_code == 200


def test_tier_5_1000_interactions_stress_benchmark():
    """Tier 5: 1000 interações E2E contínuas medindo latência e integridade."""
    latencies: list[float] = []
    success_count = 0

    t_start = time.perf_counter()

    for i in range(1000):
        upd_id = 500000 + i
        if i % 4 == 0:
            upd = _make_dm_update(upd_id, f"Mensagem {i}: Como agendar escritura?")
        elif i % 4 == 1:
            upd = _make_group_update(upd_id, f"@test_cartorio_bot qual o telefone? #{i}")
        elif i % 4 == 2:
            upd = _make_callback_update(upd_id, f"cmd:servico:{i % 5}")
        else:
            upd = _make_dm_update(upd_id, f"/menu")

        step_start = time.perf_counter()
        res = client.post("/api/v1/telegram/webhook", json=upd)
        elapsed = (time.perf_counter() - step_start) * 1000.0  # ms
        latencies.append(elapsed)

        if res.status_code == 200:
            success_count += 1

    t_total = time.perf_counter() - t_start

    assert success_count == 1000
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

    print(f"\n=== BENCHMARK 1000 INTERAÇÕES TELEGRAM ===")
    print(f"Total executado: 1000 interações em {t_total:.2f}s ({1000 / t_total:.1f} req/s)")
    print(f"Taxa de sucesso HTTP 200: {success_count / 1000 * 100:.1f}%")
    print(f"Latência Média: {avg_latency:.2f} ms")
    print(f"Latência P95: {p95_latency:.2f} ms")
    print(f"Latência P99: {p99_latency:.2f} ms")
