"""Contratos HTTP das exportacoes CNJ com dupla autenticacao DPO."""

from __future__ import annotations

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
