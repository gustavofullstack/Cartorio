"""G7.21.T2 — Pydantic strict future flags on KEY input schemas.

Covers extra=forbid, str_strip_whitespace, validate_assignment.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.auth_login import LoginRequest, RefreshRequest
from app.schemas.agendamento import AgendamentoCreateRequest
from app.schemas.audit import AuditLogCreate
from app.schemas.lgpd_consent import LGPDConsentRequest
from app.schemas.lgpd_dsar import DSARCreate, LGPDRight
from app.schemas.llm import LLMTestRequest
from app.schemas.protocolo import CanalOrigem, ProtocoloCreateRequest
from app.services.crypto import mask_email_display, mask_nome


def test_protocolo_create_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError) as exc:
        ProtocoloCreateRequest(
            cliente_cpf="12345678901",
            cliente_nome="Joao da Silva",
            tipo="certidao_negativa",
            canal_origem=CanalOrigem.WEB,
            consentimento_lgpd=True,
            unknown_injection=True,  # type: ignore[call-arg]
        )
    assert "unknown_injection" in str(exc.value)


def test_protocolo_create_strips_whitespace() -> None:
    p = ProtocoloCreateRequest(
        cliente_cpf="12345678901",
        cliente_nome="  Joao da Silva  ",
        tipo="  certidao_negativa  ",
        canal_origem=CanalOrigem.WEB,
        consentimento_lgpd=True,
    )
    assert p.cliente_nome == "Joao da Silva"
    assert p.tipo == "certidao_negativa"


def test_audit_log_create_forbids_extra_and_strips() -> None:
    entry = AuditLogCreate(
        action="  protocolo.create  ",
        resource="  protocolo:1  ",
    )
    assert entry.action == "protocolo.create"
    assert entry.resource == "protocolo:1"
    with pytest.raises(ValidationError):
        AuditLogCreate(
            action="x",
            resource="y",
            smuggled=1,  # type: ignore[call-arg]
        )


def test_audit_validate_assignment() -> None:
    entry = AuditLogCreate(action="a", resource="b")
    with pytest.raises(ValidationError):
        entry.action = ""  # min_length=1


def test_llm_test_request_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        LLMTestRequest(message="ping", rogue=True)  # type: ignore[call-arg]


def test_dsar_create_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        DSARCreate(
            cpf="12345678901",
            rights=[LGPDRight.ACESSO],
            not_a_field="x",  # type: ignore[call-arg]
        )


def test_lgpd_consent_forbids_extra_and_strips_session() -> None:
    c = LGPDConsentRequest(accepted=True, session_id="  abc  ")
    assert c.session_id == "abc"
    with pytest.raises(ValidationError):
        LGPDConsentRequest(accepted=True, tracking_pixel=1)  # type: ignore[call-arg]


def test_login_refresh_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(
            user_id="12345678-1234-1234-1234-123456789012",
            password="nope",  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="x" * 20, extra=1)  # type: ignore[call-arg]


def test_agendamento_create_forbids_extra() -> None:
    import datetime

    with pytest.raises(ValidationError):
        AgendamentoCreateRequest(
            titulo="Reconhecimento de firma",
            cliente_id=1,
            cliente_cpf="12345678901",
            data_hora=datetime.datetime(2026, 7, 1, 14, 30),
            secret_field=True,  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# G7.20.T2 — shared mask helpers (crypto DRY)
# ---------------------------------------------------------------------------


def test_mask_nome_shared_default_empty() -> None:
    assert mask_nome("Gustavo Almeida") == "G*** A***"
    assert mask_nome("") == "[nome indisponivel]"
    assert mask_nome(None) == "[nome indisponivel]"
    assert mask_nome("  ") == "[nome indisponivel]"


def test_mask_nome_custom_empty_privacy() -> None:
    assert mask_nome(None, empty="[titular anonimizado]") == "[titular anonimizado]"


def test_mask_email_display_full_and_tld() -> None:
    assert mask_email_display("joao@example.com") == "j***@example.com"
    assert mask_email_display("teste@sub.dominio.com", domain_mode="tld") == "t***@com"
    assert mask_email_display(None) == "[email indisponivel]"
    assert mask_email_display("sem-arroba") == "[email indisponivel]"
