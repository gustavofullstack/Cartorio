"""Testes do helper extract_audit_context."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from unittest.mock import MagicMock  # noqa: E402

from app.services.audit_context import extract_audit_context  # noqa: E402


def test_extrai_request_id_do_state() -> None:
    req = MagicMock()
    req.state.request_id = "trace-xyz"
    req.state.client_ip = None
    req.state.user_agent = None
    req.state.canal = None
    ctx = extract_audit_context(req)
    assert ctx["request_id"] == "trace-xyz"
    assert ctx["ip"] is None
    assert ctx["user_agent"] is None
    assert ctx["canal"] is None


def test_extrai_ip_user_agent_canal() -> None:
    req = MagicMock()
    req.state.request_id = "rid-1"
    req.state.client_ip = "203.0.113.7"
    req.state.user_agent = "Cartorio/0.5"
    req.state.canal = "whatsapp"
    ctx = extract_audit_context(req)
    assert ctx == {
        "request_id": "rid-1",
        "ip": "203.0.113.7",
        "user_agent": "Cartorio/0.5",
        "canal": "whatsapp",
    }


def test_request_none_retorna_tudo_none() -> None:
    """Jobs em background nao tem Request; nunca deve quebrar."""
    ctx = extract_audit_context(None)
    assert ctx == {
        "request_id": None,
        "ip": None,
        "user_agent": None,
        "canal": None,
    }


def test_state_sem_atributos_retorna_none_graceful() -> None:
    """Se middleware nao registrou, .state nao tem os atributos. Nunca quebra."""
    # spec=[] restringe atributos do mock principal, mas state precisa de
    # configuracao explicita. Usamos SimpleNamespace vazio.
    from types import SimpleNamespace

    req = MagicMock()
    req.state = SimpleNamespace()  # sem nenhum atributo
    ctx = extract_audit_context(req)
    assert ctx["request_id"] is None
    assert ctx["ip"] is None
    assert ctx["user_agent"] is None
    assert ctx["canal"] is None


def test_state_com_apenas_request_id() -> None:
    from types import SimpleNamespace

    req = MagicMock()
    req.state = SimpleNamespace(request_id="rid-2")  # so request_id
    ctx = extract_audit_context(req)
    assert ctx["request_id"] == "rid-2"
    assert ctx["ip"] is None
    assert ctx["user_agent"] is None
    assert ctx["canal"] is None


def test_retorna_dict_com_chaves_estaveis() -> None:
    """Contrato: sempre retorna as mesmas 4 chaves (backward compat)."""
    req = MagicMock()
    req.state.request_id = "x"
    ctx = extract_audit_context(req)
    assert set(ctx.keys()) == {"request_id", "ip", "user_agent", "canal"}
    assert None not in set(ctx.keys()) - {"ip", "user_agent", "canal", "request_id"}
    # Verifica que tem exatamente 4 chaves
    assert len(ctx) == 4
