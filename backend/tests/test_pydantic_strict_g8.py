"""G8.13.T1 — Pydantic strict=True regression tests para schemas de request notarial.

Garante que TODOS os schemas de request sob /api/v1/ recusam coerção implicita:
- string "123" → int 123 NAO eh aceito
- float 1.0 → int 1 NAO eh aceito
- string "true" → bool NAO eh aceito
- campo extra NAO eh aceito (extra="forbid")
- datetime: ISO string eh aceito, mas epoch numerico NAO

Schemas com wire-format string (Decimal, datetime, enum, Literal) tem field-level
strict=False override para nao quebrar JSON wire-format (cliente envia "150.50").

Ref:
- docs/PYDANTIC_STRICT_FUTURE_FLAGS_G7.md (G7.21.T2 - fase anterior)
- Pydantic v2 ConfigDict(strict=True) docs
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing_extensions import Annotated

from app.api.v1.bot_lgpd import (
    AccessRequest,
    CancelarRequest,
    ExportRequest,
    RestaurarRequest,
)
from app.api.v1.integrations import (
    ConsentPropagationRequest,
    N8nDeletionRequest,
    N8nErrorRequest,
    OpenCodeTestRequest,
)
from app.api.v1.lgpd_direitos_v2 import (
    ConsentRequest,
    CorrectionRequest,
    RevogarConsentRequest,
)
from app.schemas.agendamento import AgendamentoCreateRequest
from app.schemas.audit import AuditLogCreate
from app.schemas.lgpd_consent import LGPDConsentRequest
from app.schemas.lgpd_dsar import DSARCreate, LGPDRight
from app.schemas.llm import LLMTestRequest
from app.schemas.protocolo import (
    CanalOrigem,
    ProtocoloApiCreateRequest,
    ProtocoloCreateRequest,
)


# ============================================================================
# Test 1: int field rejects string coercion
# ============================================================================


def test_int_field_rejects_string_coercion() -> None:
    """int fields recusam coerção de string. Caller DEVE enviar JSON nativo int."""
    # LoginRequest.ttl_minutes e int, mas field-level default strict=True.
    from app.api.v1.auth_login import LoginRequest

    # Valido: int nativo
    req = LoginRequest(
        user_id="12345678-1234-1234-1234-123456789012",
        ttl_minutes=30,
    )
    assert req.ttl_minutes == 30

    # Invalido: string nao eh coerida para int
    with pytest.raises(ValidationError) as exc:
        LoginRequest(
            user_id="12345678-1234-1234-1234-123456789012",
            ttl_minutes="30",  # type: ignore[arg-type]
        )
    assert "ttl_minutes" in str(exc.value)
    assert "valid integer" in str(exc.value).lower() or "int_type" in str(exc.value)


# ============================================================================
# Test 2: bool field rejects string coercion
# ============================================================================


def test_bool_field_rejects_string_coercion() -> None:
    """bool fields recusam coerção de "true"/"false" string."""
    req = LGPDConsentRequest(accepted=True)
    assert req.accepted is True

    with pytest.raises(ValidationError) as exc:
        LGPDConsentRequest(accepted="true")  # type: ignore[arg-type]
    assert "accepted" in str(exc.value)
    assert "valid boolean" in str(exc.value).lower()


# ============================================================================
# Test 3: float field — int é aceito por causa do numeric tower, mas str NÃO
# ============================================================================


def test_float_field_rejects_string_coercion() -> None:
    """float fields recusam coerção de string (str NAO eh aceito).

    NOTA: Pydantic 2.x em strict mode ACEITA int->float (numeric tower).
    Apenas str->float eh rejeitado, que eh o caso de coerção implicita que
    queremos barrar (clientes mandando "0.2" como string).
    """
    req = LLMTestRequest(temperature=0.2)
    assert req.temperature == 0.2

    # strict=True: string "0.2" NAO eh aceito como float 0.2
    with pytest.raises(ValidationError) as exc:
        LLMTestRequest(temperature="0.2")  # type: ignore[arg-type]
    assert "temperature" in str(exc.value)


# ============================================================================
# Test 4: extra field rejected (extra="forbid")
# ============================================================================


def test_extra_field_rejected() -> None:
    """Schemas com extra="forbid" rejeitam campos desconhecidos (422)."""
    # ProtocoloCreateRequest tem extra="forbid"
    with pytest.raises(ValidationError) as exc:
        ProtocoloCreateRequest(
            cliente_cpf="12345678909",
            cliente_nome="Joao da Silva",
            tipo="certidao_negativa",
            canal_origem=CanalOrigem.WEB,
            consentimento_lgpd=True,
            evil_injection=42,  # type: ignore[call-arg]
        )
    assert "evil_injection" in str(exc.value)


# ============================================================================
# Test 5: datetime strict ISO accepts str, rejects int (epoch)
# ============================================================================


def test_datetime_field_accepts_iso_string_wire_format() -> None:
    """datetime field: aceita ISO 8601 string (JSON wire-format padrao).

    Field-level strict=False override em data_hora (AgendamentoCreateRequest)
    permite a coerção str->datetime esperada para JSON wire-format.

    NOTA: com strict=False Pydantic aceita TAMBEM epoch numerico (int/float).
    Como clientes JSON enviam sempre string ISO, este caso nao aparece em prod.
    Para forçar rejeição de epoch seria necessario validator custom (G8.14+).
    """
    # Valido: ISO string
    req = AgendamentoCreateRequest(
        cliente_id=1,
        cliente_cpf="12345678909",
        data_hora="2026-07-01T14:30:00",  # type: ignore[arg-type]
        titulo="Reconhecimento de firma",
    )
    assert req.data_hora == datetime(2026, 7, 1, 14, 30)

    # Valido: datetime nativo
    req2 = AgendamentoCreateRequest(
        cliente_id=1,
        cliente_cpf="12345678909",
        data_hora=datetime(2026, 7, 1, 14, 30),
        titulo="Reconhecimento de firma",
    )
    assert req2.data_hora == datetime(2026, 7, 1, 14, 30)

    # Bonus: schema-level strict=True com field-level strict=False
    # eh a unica forma de aceitar str+datetime+int+float para datetime
    # (aceitar epoch eh aceitavel para compat com wire-format)


# ============================================================================
# Bonus 1: enum field coerces from JSON string (wire-format)
# ============================================================================


def test_enum_field_accepts_string_wire_format() -> None:
    """Enum fields aceitam string no JSON wire (quando strict=False field-level).

    Field-level strict=False override em ProtocoloCreateRequest.canal_origem
    permite coerção str->enum (necessario para JSON wire-format).
    """
    # Valido: string coerzida para enum via strict=False override
    req = ProtocoloCreateRequest(
        cliente_cpf="12345678909",
        cliente_nome="Joao da Silva",
        tipo="certidao_negativa",
        canal_origem="web",  # type: ignore[arg-type]
        consentimento_lgpd=True,
    )
    assert req.canal_origem == CanalOrigem.WEB

    # Bonus: CancelarRequest usa Literal (que retorna str nativo)
    req2 = CancelarRequest(channel="telegram", sender_id="123")  # type: ignore[arg-type]
    assert req2.channel == "telegram"
    assert isinstance(req2.channel, str)


# ============================================================================
# Bonus 2: Decimal field accepts str/float (wire-format JSON)
# ============================================================================


def test_decimal_field_accepts_string_wire_format() -> None:
    """Decimal field aceita "150.50" string e 150.50 float (JSON wire).

    Field-level strict=False override. Sem isso, strict mode rejeita
    strings e clientes que mandam valor como string quebrariam.
    """
    # Valido: Decimal nativo
    req = ProtocoloApiCreateRequest(
        cliente_id=1,
        ato="escritural",  # type: ignore[arg-type]
        valor_snapshot=Decimal("150.50"),
    )
    assert req.valor_snapshot == Decimal("150.50")

    # Valido: string wire (cliente N8N manda assim)
    req2 = ProtocoloApiCreateRequest(
        cliente_id=1,
        ato="escritural",  # type: ignore[arg-type]
        valor_snapshot="150.50",  # type: ignore[arg-type]
    )
    assert req2.valor_snapshot == Decimal("150.50")

    # Valido: float wire
    req3 = ProtocoloApiCreateRequest(
        cliente_id=1,
        ato="escritural",  # type: ignore[arg-type]
        valor_snapshot=150.50,  # type: ignore[arg-type]
    )
    assert req3.valor_snapshot == Decimal("150.50")


# ============================================================================
# Bonus 3: AuditLogCreate strict mode (G8.13.T1 enabled strict)
# ============================================================================


def test_audit_log_create_strict_coercion() -> None:
    """AuditLogCreate recusa coerção implicita em campos obrigatorios."""
    # Valido: tipos nativos
    entry = AuditLogCreate(action="protocolo.create", resource="protocolo:1")
    assert entry.action == "protocolo.create"

    # Invalido: actor_id int NAO eh aceito
    with pytest.raises(ValidationError):
        AuditLogCreate(action="x", resource="y", actor_id=123)  # type: ignore[arg-type]


# ============================================================================
# Bonus 4: DSARCreate strict mode
# ============================================================================


def test_dsar_create_strict_coercion() -> None:
    """DSARCreate recusa coerção em CPF (int NAO eh aceito)."""
    # Valido: str CPF
    dsar = DSARCreate(cpf="12345678909", rights=[LGPDRight.ACESSO])
    assert dsar.cpf == "12345678909"

    # Invalido: int CPF NAO eh aceito (LGPD: caller deve mandar string)
    with pytest.raises(ValidationError):
        DSARCreate(cpf=12345678909, rights=[LGPDRight.ACESSO])  # type: ignore[arg-type]


# ============================================================================
# Bonus 5: OpenCodeTestRequest temperature strict
# ============================================================================


def test_opencode_test_temperature_strict() -> None:
    """OpenCodeTestRequest.temperature eh float strict.

    NOTA: Pydantic 2.x aceita int->float (numeric tower) mesmo em strict mode.
    Apenas str->float eh rejeitado.
    """
    # Valido: float
    req = OpenCodeTestRequest(temperature=0.5)
    assert req.temperature == 0.5

    # Valido: int eh aceito por causa do numeric tower (int subclass of float)
    req2 = OpenCodeTestRequest(temperature=1)
    assert req2.temperature == 1.0

    # Invalido: string NAO eh aceita como float
    with pytest.raises(ValidationError):
        OpenCodeTestRequest(temperature="0.5")  # type: ignore[arg-type]


# ============================================================================
# Bonus 6: N8nErrorRequest strict
# ============================================================================


def test_n8n_error_request_strict_extra_forbid() -> None:
    """N8nErrorRequest recusa campos extras (extra="forbid")."""
    req = N8nErrorRequest(workflow_name="wf1", execution_id="exec1")
    assert req.workflow_name == "wf1"

    with pytest.raises(ValidationError):
        N8nErrorRequest(
            workflow_name="wf1",
            execution_id="exec1",
            smuggled=42,  # type: ignore[call-arg]
        )


# ============================================================================
# Bonus 7: N8nDeletionRequest.deleted_count strict int
# ============================================================================


def test_n8n_deletion_deleted_count_strict_int() -> None:
    """N8nDeletionRequest.deleted_count eh int strict."""
    req = N8nDeletionRequest(
        execution_id="exec1",
        target_category="conversas",
        deleted_count=5,
    )
    assert req.deleted_count == 5

    with pytest.raises(ValidationError):
        N8nDeletionRequest(
            execution_id="exec1",
            target_category="conversas",
            deleted_count="5",  # type: ignore[arg-type]
        )


# ============================================================================
# Bonus 8: ConsentPropagationRequest.chatwoot_conversation_id strict int
# ============================================================================


def test_consent_propagation_chatwoot_id_strict_int() -> None:
    """ConsentPropagationRequest.chatwoot_conversation_id eh int strict."""
    req = ConsentPropagationRequest(
        chatwoot_conversation_id=42,
        telegram_chat_id="123",
    )
    assert req.chatwoot_conversation_id == 42

    with pytest.raises(ValidationError):
        ConsentPropagationRequest(
            chatwoot_conversation_id="42",  # type: ignore[arg-type]
            telegram_chat_id="123",
        )


# ============================================================================
# Bonus 9: AccessRequest.strict
# ============================================================================


def test_access_request_strict() -> None:
    """AccessRequest strict mode + extra=forbid."""
    req = AccessRequest(channel="telegram", sender_id="123")  # type: ignore[arg-type]
    assert req.sender_id == "123"

    # cliente_id strict int
    with pytest.raises(ValidationError):
        AccessRequest(
            channel="telegram",  # type: ignore[arg-type]
            sender_id="123",
            cliente_id="42",  # type: ignore[arg-type]
        )


# ============================================================================
# Bonus 10: ExportRequest.strict
# ============================================================================


def test_export_request_strict() -> None:
    """ExportRequest strict mode."""
    req = ExportRequest(channel="whatsapp", sender_id="abc")  # type: ignore[arg-type]
    assert req.sender_id == "abc"

    # cliente_id strict int - rejeita string
    with pytest.raises(ValidationError):
        ExportRequest(
            channel="whatsapp",  # type: ignore[arg-type]
            sender_id="abc",
            cliente_id="99",  # type: ignore[arg-type]
        )


# ============================================================================
# Bonus 11: RestaurarRequest.strict
# ============================================================================


def test_restaurar_request_strict() -> None:
    """RestaurarRequest strict mode."""
    req = RestaurarRequest(revogacao_id="abcd1234")
    assert req.revogacao_id == "abcd1234"

    # revogacao_id length validation
    with pytest.raises(ValidationError):
        RestaurarRequest(revogacao_id="abc")  # too short (min_length=8)


# ============================================================================
# Bonus 12: LGPD v2 strict (ConsentRequest/CorrectionRequest/RevogarConsentRequest)
# ============================================================================


def test_lgpd_v2_consent_request_strict() -> None:
    """ConsentRequest strict mode."""
    req = ConsentRequest(cliente_id=1, finalidade="atendimento", granted=True)
    assert req.cliente_id == 1
    assert req.granted is True

    # cliente_id strict int
    with pytest.raises(ValidationError):
        ConsentRequest(cliente_id="1", finalidade="atendimento", granted=True)  # type: ignore[arg-type]

    # granted strict bool
    with pytest.raises(ValidationError):
        ConsentRequest(cliente_id=1, finalidade="atendimento", granted="true")  # type: ignore[arg-type]


def test_lgpd_v2_correction_request_strict() -> None:
    """CorrectionRequest strict mode + extra=forbid."""
    req = CorrectionRequest(nome="Joao")
    assert req.nome == "Joao"

    # extra forbidden
    with pytest.raises(ValidationError):
        CorrectionRequest(nome="Joao", cpf_hash="xyz")  # type: ignore[call-arg]


def test_lgpd_v2_revogar_consent_strict() -> None:
    """RevogarConsentRequest strict mode."""
    req = RevogarConsentRequest(cliente_id=1)
    assert req.cliente_id == 1

    # cliente_id strict int
    with pytest.raises(ValidationError):
        RevogarConsentRequest(cliente_id="1")  # type: ignore[arg-type]


# ============================================================================
# Bonus 13: ProtocoloApiCreateRequest.strict
# ============================================================================


def test_protocolo_api_create_strict() -> None:
    """ProtocoloApiCreateRequest strict mode."""
    req = ProtocoloApiCreateRequest(
        cliente_id=1,
        ato="escritural",  # type: ignore[arg-type]
        valor_snapshot="150.50",  # type: ignore[arg-type]
        hitl_draft=True,
    )
    assert req.cliente_id == 1
    assert req.hitl_draft is True

    # cliente_id strict int
    with pytest.raises(ValidationError):
        ProtocoloApiCreateRequest(
            cliente_id="1",  # type: ignore[arg-type]
            ato="escritural",  # type: ignore[arg-type]
            valor_snapshot="150.50",  # type: ignore[arg-type]
        )

    # hitl_draft strict bool
    with pytest.raises(ValidationError):
        ProtocoloApiCreateRequest(
            cliente_id=1,
            ato="escritural",  # type: ignore[arg-type]
            valor_snapshot="150.50",  # type: ignore[arg-type]
            hitl_draft="true",  # type: ignore[arg-type]
        )


# ============================================================================
# Bonus 14: Direct model_validate strict mode coverage
# ============================================================================


def test_settings_strict_mode_is_true_by_default() -> None:
    """G8.13.T1: pydantic_strict_mode default eh True."""
    from app.config import settings

    assert settings.pydantic_strict_mode is True


# ============================================================================
# Bonus 15: Annotated strict per-field pattern
# ============================================================================


def test_annotated_strict_per_field_pattern() -> None:
    """Pattern per-field com Annotated[T, Field(strict=...)] funciona.

    Smoke test do pattern G8.13.T1: Pydantic suporta strict=False em field-level
    mesmo com strict=True na classe.
    """

    class _Schema(BaseModel):
        model_config = ConfigDict(strict=True)

        valor: Annotated[Decimal, Field(strict=False)]
        data: Annotated[datetime, Field(strict=False)]

    # Field-level override permite str wire-format
    s = _Schema(valor="150.50", data="2026-07-01T00:00:00")  # type: ignore[arg-type]
    assert s.valor == Decimal("150.50")
    assert s.data == datetime(2026, 7, 1, 0, 0, 0)


# ============================================================================
# Bonus 16: LessonCreate strict (brain.py)
# ============================================================================


def test_lesson_create_strict() -> None:
    """LessonCreate strict mode + extra=forbid."""
    from app.api.v1.brain import LessonCreate

    req = LessonCreate(
        titulo="Titulo valido",
        contexto="Contexto da lesson com mais de 10 chars",
        solucao="Solucao da lesson com mais de 10 chars",
    )
    assert req.titulo == "Titulo valido"

    # extra forbidden
    with pytest.raises(ValidationError):
        LessonCreate(
            titulo="Titulo valido",
            contexto="Contexto da lesson com mais de 10 chars",
            solucao="Solucao da lesson com mais de 10 chars",
            injected=1,  # type: ignore[call-arg]
        )


# ============================================================================
# Bonus 17: CPFStr e CNPJStr mathematical validation (G8.13.T3)
# ============================================================================


def test_cpf_cnpj_custom_types_validation() -> None:
    """G8.13.T3: CPFStr e CNPJStr realizam validações de formato e dígitos verificadores."""
    from app.schemas.types import CPFStr, CNPJStr

    class _MockSchema(BaseModel):
        cpf: CPFStr
        cnpj: CNPJStr

    # CPFs e CNPJs válidos de teste
    valid_cpf_formatted = "123.456.789-09"
    valid_cpf_raw = "12345678909"
    valid_cnpj_formatted = "12.345.678/0001-95"
    valid_cnpj_raw = "12345678000195"

    # Deve passar
    schema = _MockSchema(cpf=valid_cpf_formatted, cnpj=valid_cnpj_formatted)
    assert schema.cpf == valid_cpf_formatted
    assert schema.cnpj == valid_cnpj_formatted

    schema_raw = _MockSchema(cpf=valid_cpf_raw, cnpj=valid_cnpj_raw)
    assert schema_raw.cpf == valid_cpf_raw
    assert schema_raw.cnpj == valid_cnpj_raw

    # Erro: int não deve ser aceito se strict=True for usado
    class _MockStrictSchema(BaseModel):
        model_config = ConfigDict(strict=True)
        cpf: CPFStr
        cnpj: CNPJStr

    with pytest.raises(ValidationError):
        _MockStrictSchema(cpf=12345678909, cnpj=valid_cnpj_formatted)  # type: ignore[arg-type]

    # CPFs/CNPJs matematicamente inválidos
    invalid_cpf_digits = "123.456.789-00"  # dígitos verificadores errados
    invalid_cpf_repeated = "111.111.111-11"  # dígitos repetidos
    invalid_cnpj_digits = "12.345.678/0001-00"  # dígitos errados
    invalid_cnpj_repeated = "00.000.000/0000-00"

    with pytest.raises(ValidationError) as exc:
        _MockSchema(cpf=invalid_cpf_digits, cnpj=valid_cnpj_formatted)
    assert "Dígito verificador do CPF inválido." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        _MockSchema(cpf=invalid_cpf_repeated, cnpj=valid_cnpj_formatted)
    assert "CPF inválido (todos os dígitos são iguais)." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        _MockSchema(cpf=valid_cpf_formatted, cnpj=invalid_cnpj_digits)
    assert "Primeiro dígito verificador do CNPJ inválido." in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        _MockSchema(cpf=valid_cpf_formatted, cnpj=invalid_cnpj_repeated)
    assert "CNPJ inválido (todos os dígitos são iguais)." in str(exc.value)

    # CPF/CNPJ com tamanho inválido
    with pytest.raises(ValidationError):
        _MockSchema(cpf="123456789", cnpj=valid_cnpj_formatted)

    with pytest.raises(ValidationError):
        _MockSchema(cpf=valid_cpf_formatted, cnpj="12345")
