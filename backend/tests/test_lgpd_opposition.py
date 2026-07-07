"""Testes para direito de oposição (LGPD Art. 18 §2º)."""

from app.services.lgpd.opposition import register_opposition, check_opposition


def test_register_opposition_marketing():
    result = register_opposition(cliente_id=42, scope="marketing")
    assert result["cliente_id"] == 42
    assert result["scope"] == "marketing"
    assert result["registered"] is True


def test_register_opposition_all():
    result = register_opposition(cliente_id=1, scope="all")
    assert result["effect"] == "tratamento_suspenso"
    assert "Art. 18" in result["lgpd_article"]


def test_check_opposition_sem_db():
    assert check_opposition(cliente_id=1, scope="marketing") is False
