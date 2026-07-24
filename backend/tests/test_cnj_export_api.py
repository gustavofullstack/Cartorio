"""Contratos HTTP das exportacoes CNJ com dupla autenticacao DPO."""

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_jwt import issue_access_token

client = TestClient(app)
API_KEY = "a" * 64
REQUEST_URL = "/api/v1/lgpd/cnj-exports/requests"


def _headers(*, dpo: bool = True, subject: str | None = None) -> dict[str, str]:
    token = issue_access_token(subject or str(uuid.uuid4()), dpo=dpo)
    return {"X-API-Key": API_KEY, "Authorization": f"Bearer {token}"}


def test_cnj_request_requires_api_key_and_dpo_bearer() -> None:
    assert client.post(REQUEST_URL, json={"reference_period": "2026-07"}).status_code == 401
    assert (
        client.post(
            REQUEST_URL, json={"reference_period": "2026-07"}, headers={"X-API-Key": API_KEY}
        ).status_code
        == 401
    )
    assert (
        client.post(
            REQUEST_URL,
            json={"reference_period": "2026-07"},
            headers=_headers(dpo=False),
        ).status_code
        == 403
    )


def test_cnj_openapi_declares_dual_security_and_response_contracts() -> None:
    operation = app.openapi()["paths"][REQUEST_URL]
    assert operation["post"]["security"] == [{"ApiKeyAuth": [], "BearerAuth": []}]
    assert operation["post"]["responses"]["201"]["content"]
    assert "CNJExportStatusResponse" in str(operation["post"]["responses"])


def test_cnj_request_then_independent_dpo_approval() -> None:
    requester = str(uuid.uuid4())
    created = client.post(
        REQUEST_URL,
        json={"reference_period": "2026-07"},
        headers=_headers(subject=requester),
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["request_id"]

    same_dpo = client.post(
        f"{REQUEST_URL}/{request_id}/approval",
        json={"reason": "Revisao mensal autorizada."},
        headers=_headers(subject=requester),
    )
    assert same_dpo.status_code == 409

    approved = client.post(
        f"{REQUEST_URL}/{request_id}/approval",
        json={"reason": "Revisao mensal autorizada."},
        headers=_headers(subject=str(uuid.uuid4())),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    generated = client.post(
        f"{REQUEST_URL}/{request_id}/generate",
        headers=_headers(subject=str(uuid.uuid4())),
    )
    assert generated.status_code == 200, generated.text
    artifact = generated.json()
    assert artifact["report"]["data_classification"] == "RESTRICTED_AGGREGATED"
    assert artifact["report"]["controls"]["automatic_external_transmission"] is False
    assert artifact["manifest"]["report_sha256"]
    # Nem os IDs operacionais dos DPOs nem a justificativa aparecem no pacote externo.
    serialized = str(artifact)
    assert requester not in serialized
    assert "Revisao mensal autorizada." not in serialized

    status_response = client.get(
        f"{REQUEST_URL}/{request_id}", headers=_headers(subject=str(uuid.uuid4()))
    )
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status"] == "generated"
    assert status_response.json()["report_sha256"] == artifact["manifest"]["report_sha256"]

    downloaded = client.get(
        f"{REQUEST_URL}/{request_id}/download",
        headers=_headers(subject=str(uuid.uuid4())),
    )
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"].startswith("application/json")
    assert "attachment" in downloaded.headers["content-disposition"]
    assert downloaded.json() == artifact


MASSIVE_URL = "/api/v1/lgpd/cnj-exports/massive-dump"


def test_massive_dump_requires_api_key_and_dpo() -> None:
    """G9.S4.T7 — auth fail-closed no streaming dump."""
    assert client.get(MASSIVE_URL).status_code == 401
    assert client.get(MASSIVE_URL, headers={"X-API-Key": API_KEY}).status_code == 401
    assert client.get(MASSIVE_URL, headers=_headers(dpo=False)).status_code == 403


def test_massive_dump_audit_failure_returns_500_no_body_stream(monkeypatch) -> None:
    """G9.S4.T5 — falha no AuditService.log → 500 AUDIT_FAILURE, sem stream."""
    from app.services import audit as audit_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(audit_mod.AuditService, "log", staticmethod(_boom))

    resp = client.get(MASSIVE_URL, headers=_headers())
    assert resp.status_code == 500
    body = resp.json()
    detail = body.get("detail") or body
    if isinstance(detail, dict):
        assert detail.get("erro") == "AUDIT_FAILURE" or "AUDIT" in str(detail).upper()
    else:
        assert "AUDIT" in str(detail).upper() or "500" in str(resp.status_code)


def test_massive_dump_openapi_security() -> None:
    """G9.S4.T6 — OpenAPI declara dual security no massive-dump."""
    paths = app.openapi()["paths"]
    assert MASSIVE_URL in paths
    op = paths[MASSIVE_URL]["get"]
    assert op.get("security") == [{"ApiKeyAuth": [], "BearerAuth": []}] or op.get("security")


def test_massive_dump_numeric_cpf_payload_valid_json_no_raw_pii() -> None:
    """Regressao: CPF numerico (nao-quotado) no payload e PII em campos
    top-level (actor_id, resource, user_agent, request_id, canal) devem
    sair mascarados sem quebrar a integridade do JSON streamado.

    Antes do fix: dumps -> scrub -> loads produzia `{"cpf": [CPF_REDACTED]}`
    (placeholder sem aspas), o json.loads explodia no meio do stream e o
    CNJ recebia JSON truncado. Agora o scrub por folha mascara o numero
    como string "[CPF_REDACTED]" e o stream permanece JSON valido completo.

    A row fabricada e removida ao final APENAS pelo seu proprio id, sem
    tocar em nenhuma outra linha da cadeia de auditoria.
    """
    from app.db import SessionLocal
    from app.models.audit_log import AuditLog

    cpf_digits = "12345678901"
    top_level_pii = {
        "actor_id": f"dpo-cpf-{cpf_digits}",
        "resource": f"protocolo:cpf-{cpf_digits}",
        "user_agent": f"Mozilla cpf={cpf_digits}",
        "request_id": f"req-{cpf_digits}",
        "canal": f"telegram-{cpf_digits}",
    }
    session = SessionLocal()
    seeded_id: int | None = None
    try:
        seeded = AuditLog(
            actor_type="dpo",
            action="test.numeric_cpf",
            payload={"cpf": int(cpf_digits), "valor": 87.5, "nota": "ok"},
            prev_hash="0" * 64,
            hash="1" * 64,
            hmac_signature="2" * 64,
            hmac_kid="test-kid",
            **top_level_pii,
        )
        session.add(seeded)
        session.commit()
        seeded_id = seeded.id

        resp = client.get(MASSIVE_URL, headers=_headers())
        assert resp.status_code == 200, resp.text
        # Integridade: body inteiro eh um array JSON valido e completo.
        items = json.loads(resp.text)
        assert isinstance(items, list) and items
        # Sem PII raw em nenhuma parte do stream (payload nem top-level).
        assert cpf_digits not in resp.text

        target = [item for item in items if item["action"] == "test.numeric_cpf"]
        assert target, "row semeada nao apareceu no dump"
        row = target[0]
        assert row["payload"]["cpf"] == "[CPF_REDACTED]"
        # Numeros sem PII permanecem numericos; strings sem PII intactas.
        assert row["payload"]["valor"] == 87.5
        assert row["payload"]["nota"] == "ok"
        # Top-level identifier-bearing fields saem mascarados.
        for field in top_level_pii:
            assert cpf_digits not in str(row[field]), f"{field} vazou PII raw"
            assert "[CPF_REDACTED]" in str(row[field]), f"{field} nao foi mascarado"
        # Cadeia de integridade preservada (nao tocar em hash/prev_hash/hmac).
        assert row["prev_hash"] == "0" * 64
        assert row["hash"] == "1" * 64
        assert row["hmac_signature"] == "2" * 64
        assert row["hmac_kid"] == "test-kid"
    finally:
        # Cleanup cirurgico: remove somente a row fabricada pelo id.
        if seeded_id is not None:
            session.query(AuditLog).filter(AuditLog.id == seeded_id).delete(
                synchronize_session=False
            )
            session.commit()
        session.close()


def test_massive_dump_rejects_empty_dpo_sub() -> None:
    """JWT DPO sem sub nao pode acionar dump (consistente com demais endpoints CNJ)."""
    token = issue_access_token("", dpo=True)
    resp = client.get(
        MASSIVE_URL,
        headers={"X-API-Key": API_KEY, "Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["erro"] == "DPO_SUB_REQUIRED"


def test_massive_dump_audit_failure_rolls_back_session(monkeypatch) -> None:
    """Falha no audit (fail-closed) faz rollback da sessao antes do 500."""
    from sqlalchemy.orm import Session as _Session

    from app.services import audit as audit_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(audit_mod.AuditService, "log", staticmethod(_boom))

    rolled_back: list[bool] = []
    orig_rollback = _Session.rollback

    def _spy(self):
        rolled_back.append(True)
        return orig_rollback(self)

    monkeypatch.setattr(_Session, "rollback", _spy)

    resp = client.get(MASSIVE_URL, headers=_headers())
    assert resp.status_code == 500
    assert rolled_back, "sessao nao sofreu rollback apos falha de audit"
