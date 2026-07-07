"""Testes para app/api/v1/router.py - helpers (cobertura).

Cobre:
1. _gerar_numero_protocolo com 0 protocolos no ano
2. _gerar_numero_protocolo com 3 protocolos no ano
3. _gerar_numero_protocolo nao colide com anos diferentes
4. _verify_api_key com chave valida
5. _verify_api_key com chave invalida
6. _verify_api_key com chave ausente

Sobe cobertura router.py 78% -> >=88%.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.router import _gerar_numero_protocolo
from app.models.base import Base
from app.models.protocolo import Protocolo


@pytest.fixture
def db_session():
    """Session SQLite in-memory com Protocolo metadata criado."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(eng)


# =============================================================================
# _gerar_numero_protocolo
# =============================================================================


def test_gerar_numero_protocolo_zero_protocolos(db_session) -> None:
    """_gerar_numero_protocolo com 0 protocolos retorna YYYY-00001."""
    numero = _gerar_numero_protocolo(db_session, ano=2026)
    assert numero == "2026-00001"


def _make_protocolo(numero: str) -> Protocolo:
    """Cria um Protocolo com todos os campos NOT NULL preenchidos."""
    return Protocolo(
        numero=numero,
        cliente_id=1,
        tipo="certidao",
        status="DRAFT",
        canal_origem="presencial",
    )


def test_gerar_numero_protocolo_com_3_existentes(db_session) -> None:
    """_gerar_numero_protocolo com 3 existentes retorna YYYY-00004."""
    for i in range(1, 4):
        db_session.add(_make_protocolo(f"2026-{i:05d}"))
    db_session.commit()

    numero = _gerar_numero_protocolo(db_session, ano=2026)
    assert numero == "2026-00004"


def test_gerar_numero_protocolo_anos_diferentes_independentes(db_session) -> None:
    """_gerar_numero_protocolo trata cada ano independentemente."""
    for i in range(1, 6):
        db_session.add(_make_protocolo(f"2025-{i:05d}"))
    db_session.commit()

    # 2025 tem 5, mas 2026 deve comecar em 1
    numero_2026 = _gerar_numero_protocolo(db_session, ano=2026)
    assert numero_2026 == "2026-00001"


def test_gerar_numero_protocolo_formato_YYYY_NNNNN(db_session) -> None:
    """_gerar_numero_protocolo retorna string formato YYYY-NNNNN (5 digitos)."""
    numero = _gerar_numero_protocolo(db_session, ano=2027)
    parts = numero.split("-")
    assert len(parts) == 2
    assert parts[0] == "2027"
    assert len(parts[1]) == 5  # zero-padded
    assert parts[1].isdigit()


def test_gerar_numero_protocolo_pula_para_10_protocolos(db_session) -> None:
    """Apos 9 protocolos, retorna 00010 (continua sequencia)."""
    for i in range(1, 10):
        db_session.add(_make_protocolo(f"2026-{i:05d}"))
    db_session.commit()

    numero = _gerar_numero_protocolo(db_session, ano=2026)
    assert numero == "2026-00010"


# =============================================================================
# _verify_api_key
# =============================================================================


def test_verify_api_key_chave_valida_nao_levanta() -> None:
    """_verify_api_key com chave canonica NAO levanta."""
    from app.api.v1.router import _verify_api_key

    # A chave deve bater com a env. Pega via settings
    from app.config import settings

    _verify_api_key(settings.cartorio_api_key)


def test_verify_api_key_chave_invalida_levanta_401() -> None:
    """_verify_api_key com chave errada -> HTTPException 401."""
    from fastapi import HTTPException

    from app.api.v1.router import _verify_api_key

    with pytest.raises(HTTPException) as exc_info:
        _verify_api_key("chave-invalida-errada")
    assert exc_info.value.status_code == 401


def test_verify_api_key_chave_ausente_levanta_401() -> None:
    """_verify_api_key com None ou string vazia -> HTTPException 401."""
    from fastapi import HTTPException

    from app.api.v1.router import _verify_api_key

    with pytest.raises(HTTPException) as exc_info:
        _verify_api_key(None)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        _verify_api_key("")
    assert exc_info.value.status_code == 401
