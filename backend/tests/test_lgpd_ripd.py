"""Testes do endpoint RIPD (LGPD D21 — Relatorio de Impacto a Protecao de Dados).

Cobre:
- test_ripd_retorna_200_ok
- test_ripd_contem_todas_categorias_pii
- test_ripd_contem_bases_legais
- test_ripd_contem_retencao_por_categoria
- (edge cases adicionais)
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# X-API-Key canonico do conftest (TEST_CARTORIO_API_KEY = "a"*64)
AUTH_HEADERS = {"X-API-Key": "a" * 64}


class TestLGPDRipd:
    """D21 RIPD — Relatorio de Impacto a Protecao de Dados (LGPD art. 38)."""

    def test_ripd_retorna_200_ok(self) -> None:
        """Endpoint retorna 200 OK com auth X-API-Key."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "metadata" in body
        assert "categorias_dados_pessoais" in body
        assert "finalidades" in body
        assert "bases_legais" in body
        assert "riscos_identificados" in body
        assert "medidas_mitigacao" in body
        assert "politica_retencao" in body
        assert "direitos_titular_art_18" in body

    def test_ripd_retorna_401_sem_api_key(self) -> None:
        """Sem X-API-Key header -> 401."""
        resp = client.get("/api/v1/lgpd/ripd")
        assert resp.status_code == 401

    def test_ripd_retorna_401_com_chave_invalida(self) -> None:
        """X-API-Key invalida -> 401."""
        resp = client.get("/api/v1/lgpd/ripd", headers={"X-API-Key": "fake-key"})
        assert resp.status_code == 401

    def test_ripd_contem_todas_categorias_pii(self) -> None:
        """RIPD lista todas as 6 categorias PII tratadas."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        cats = {c["categoria"] for c in body["categorias_dados_pessoais"]}
        expected = {
            "dados_identificacao",
            "dados_contato",
            "dados_ato_juridico",
            "dados_documento",
            "dados_audit",
            "dados_lgpd",
        }
        assert expected.issubset(cats), f"Faltando categorias: {expected - cats}"

    def test_ripd_contem_cpf_e_rg_nas_categorias(self) -> None:
        """RIPD explicita tratamento de CPF e RG como categorias PII."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        concatenated = " ".join(
            c.get("descricao", "") for c in body["categorias_dados_pessoais"]
        ).lower()
        assert "cpf" in concatenated
        assert "rg" in concatenated

    def test_ripd_contem_bases_legais(self) -> None:
        """RIPD cita LGPD art. 6o (principios) E art. 7o (hipoteses de tratamento)."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        artigos = {bl["artigo_lgpd"] for bl in body["bases_legais"]}
        assert any("6o" in a for a in artigos), f"Sem citacao ao art. 6o: {artigos}"
        assert any("7o" in a for a in artigos), f"Sem citacao ao art. 7o: {artigos}"

    def test_ripd_contem_hipotese_obrigacao_legal(self) -> None:
        """RIPD cita obrigacao legal (Lei 8.935/94 notarios) como hipotese de tratamento."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        # Procura hipotese "obrigacao legal"
        hipotese_obrigacao = any(
            bl.get("hipotese") == "obrigacao legal" for bl in body["bases_legais"]
        )
        assert hipotese_obrigacao

    def test_ripd_contem_retencao_por_categoria(self) -> None:
        """RIPD tem politica de retencao para cliente, conversa e audit log."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        retencao = body["politica_retencao"]
        assert "categorias" in retencao
        cats = " ".join(c["categoria"].lower() for c in retencao["categorias"])
        assert "cliente" in cats
        assert "conversa" in cats
        assert "audit_log" in cats

    def test_ripd_retencao_cliente_5_anos(self) -> None:
        """Retencao de cliente = 5 anos (Provimento CNJ 74/2018)."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        cats = body["politica_retencao"]["categorias"]
        cliente_cat = next(
            (c for c in cats if "cliente" in c["categoria"].lower()),
            None,
        )
        assert cliente_cat is not None
        assert "5" in cliente_cat["prazo"]

    def test_ripd_contem_riscos_e_mitigacoes(self) -> None:
        """RIPD tem pelo menos 1 risco + 1 medida de mitigacao."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["riscos_identificados"]) >= 3
        assert len(body["medidas_mitigacao"]) >= 3

    def test_ripd_risco_audit_chain_mencoes(self) -> None:
        """RIPD menciona protecao contra tampering do audit log (LGPD-by-design)."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        # Pega o titulo + descricao de cada mitigacao
        mitigations_concat = " ".join(
            (m.get("descricao", "") + " " + m.get("controle", ""))
            for m in body["medidas_mitigacao"]
        ).lower()
        # Audit log + HMAC + SHA256 sao os 3 pilares
        assert "audit log" in mitigations_concat
        assert "hmac" in mitigations_concat
        assert "sha256" in mitigations_concat

    def test_ripd_contem_direitos_art_18(self) -> None:
        """RIPD lista 6 direitos do art. 18 (acesso, correcao, anonimizacao, portabilidade, revogacao, oposicao)."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        direitos_concat = " ".join(d["direito"].lower() for d in body["direitos_titular_art_18"])
        # Pelo menos 5 dos 6 direitos LGPD art. 18 mapeados
        for keyword in ("acesso", "correcao", "anonimizacao", "portabilidade", "oposicao"):
            assert keyword in direitos_concat, f"Direito '{keyword}' ausente"

    def test_ripd_contem_contact_dpo_gustavo(self) -> None:
        """RIPD cita o DPO Gustavo Almeida (chat_id 6682284055) para contato do titular."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        dpo_meta = body["metadata"]["agente_tratamento"]["encarregado_dpo"]
        assert "Gustavo Almeida" in dpo_meta["nome"]
        assert dpo_meta["telegram_chat_id"] == "6682284055"

    def test_ripd_nao_expoe_pii_individual(self) -> None:
        """LGPD-by-design: RIPD nao expoe PII de clientes especificos (apenas info agregada)."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body_str = str(resp.json())
        # Sem valores comuns de CPF/email/phone
        assert "123.456.789" not in body_str
        assert "@example.com" not in body_str
        # Sem ID de cliente especifico
        assert '"cliente_id":' not in body_str

    def test_ripd_formato_markdown(self) -> None:
        """?format=markdown retorna string markdown renderizado."""
        resp = client.get("/api/v1/lgpd/ripd?format=markdown", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        assert "ripd_markdown" in body
        md = body["ripd_markdown"]
        assert md.startswith("# ")
        assert "LGPD" in md
        assert "Direitos dos Titulares" in md
        # Markdown tem ao menos 7 secoes ##
        assert md.count("\n## ") >= 7

    def test_ripd_formato_invalido_retorna_422(self) -> None:
        """?format=html (invalido) -> 422 (validacao Pydantic/FastAPI)."""
        resp = client.get("/api/v1/lgpd/ripd?format=html", headers=AUTH_HEADERS)
        assert resp.status_code == 422

    def test_ripd_metadata_tem_timestamp_iso(self) -> None:
        """metadata.gerado_em eh timestamp ISO 8601 UTC."""
        resp = client.get("/api/v1/lgpd/ripd", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()
        gerado_em = body["metadata"]["gerado_em"]
        assert gerado_em.endswith("+00:00") or gerado_em.endswith("Z")
        # Contem data
        from datetime import datetime

        # parse OK
        datetime.fromisoformat(gerado_em.replace("Z", "+00:00"))
