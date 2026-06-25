import pytest
from app.main import app, SWAGGER_UI_HTML

def test_custom_swagger_ui():
    assert "<header class=\"header-cartorio\">" in SWAGGER_UI_HTML
    assert "<nav class=\"links\" aria-label=\"Navegação da API\">" in SWAGGER_UI_HTML
    assert "outline: 2px solid white; outline-offset: 2px; border-radius: 2px;" in SWAGGER_UI_HTML
    assert "<main id=\"swagger-ui\"></main>" in SWAGGER_UI_HTML
