from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_security_headers_present():
    """Testa se os headers de seguranca estao presentes na resposta."""
    # Fazer request para endpoint publico (health)
    response = client.get("/health")

    # Garantir que a requisicao foi bem sucedida
    assert response.status_code == 200

    # Verificar a presenca e valor dos headers de seguranca
    assert "Strict-Transport-Security" in response.headers
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"

    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"

    assert "Content-Security-Policy" in response.headers
    assert response.headers["Content-Security-Policy"] == "default-src 'self'"

    assert "Referrer-Policy" in response.headers
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
