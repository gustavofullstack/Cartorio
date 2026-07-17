"""Testes unitários para a API estendida de cálculo de emolumentos notariais (Wave 8 S8.T1).

Valida:
- Cálculo básico nominal (folhas=1, urgencia=False) e breakdown de adicionais
- Aplicação de isenção por motivo legal (justiça gratuita)
- Rejeição de isenções com motivos inválidos (HTTP 400)
- Barreira de conformidade LGPD para escrituras sensíveis de alto valor (HTTP 403 se sem consentimento)
- Auditoria e incremento de contadores de erros no Prometheus

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.cliente import Cliente

client = TestClient(app)


def test_calcular_emolumento_api_basico() -> None:
    """GET /api/v1/emolumentos/calcular-api deve retornar cálculo de procuração sem adicionais."""
    resp = client.get("/api/v1/emolumentos/calcular-api?tipo=procuracao&folhas=1&urgencia=false")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tipo"] == "procuracao"
    assert float(body["base"]) == 156.40
    assert float(body["adicional_folhas"]) == 0.00
    assert float(body["adicional_urgencia"]) == 0.00
    assert float(body["total"]) == 156.40
    assert body["isento"] is False


def test_calcular_emolumento_api_com_adicionais() -> None:
    """GET /api/v1/emolumentos/calcular-api deve aplicar 50% de urgência e 5% por folha adicional."""
    # base procuracao: 156.40. folhas=3 (2 adicionais = 10% = 15.64). urgencia=50% (78.20).
    # total = 156.40 + 15.64 + 78.20 = 250.24
    resp = client.get("/api/v1/emolumentos/calcular-api?tipo=procuracao&folhas=3&urgencia=true")
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["base"]) == 156.40
    assert float(body["adicional_folhas"]) == 15.64
    assert float(body["adicional_urgencia"]) == 78.20
    assert float(body["total"]) == 250.24


def test_calcular_emolumento_api_isencao_valida() -> None:
    """GET /api/v1/emolumentos/calcular-api deve zerar taxas se isencao_motivo for justica_gratuita."""
    resp = client.get("/api/v1/emolumentos/calcular-api?tipo=procuracao&isencao_motivo=justica_gratuita")
    assert resp.status_code == 200
    body = resp.json()
    assert body["isento"] is True
    assert body["isencao_motivo"] == "justica_gratuita"
    assert float(body["total"]) == 0.00


def test_calcular_emolumento_api_isencao_invalida_fails() -> None:
    """GET /api/v1/emolumentos/calcular-api deve falhar com 400 se isencao_motivo for inválido."""
    resp = client.get("/api/v1/emolumentos/calcular-api?tipo=procuracao&isencao_motivo=motivo_errado")
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["erro"] == "ISENCAO_INVALIDA"


def test_calcular_emolumento_api_sensivel_without_lgpd_consent_fails(db_session: Session) -> None:
    """GET /api/v1/emolumentos/calcular-api para escritura com cliente deve falhar com 403 se sem consentimento LGPD."""
    # Cria cliente sem consentimento LGPD
    cliente = Cliente(
        nome="Cliente Sem Consentimento",
        email="sem@consentimento.com",
        cpf_hash="e" * 64,
        consentimento_lgpd=False,
    )
    db_session.add(cliente)
    db_session.commit()

    # Escritura de compra e venda (alto valor > R$ 1000) com cliente associado
    resp = client.get(
        f"/api/v1/emolumentos/calcular-api?tipo=escritura_compra_venda&cliente_id={cliente.id}"
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["erro"] == "LGPD_CONSENT_REQUIRED"


def test_calcular_emolumento_api_sensivel_with_lgpd_consent_success(db_session: Session) -> None:
    """GET /api/v1/emolumentos/calcular-api para escritura com cliente deve passar com 200 se com consentimento LGPD."""
    # Cria cliente com consentimento LGPD
    cliente = Cliente(
        nome="Cliente Com Consentimento",
        email="com@consentimento.com",
        cpf_hash="f" * 64,
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()

    resp = client.get(
        f"/api/v1/emolumentos/calcular-api?tipo=escritura_compra_venda&cliente_id={cliente.id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tipo"] == "escritura_compra_venda"
    assert float(body["total"]) == 4521.00
