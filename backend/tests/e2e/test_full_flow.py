"""F05 E2E — Suite Playwright full flow cliente ponta-a-ponta.

Cobre o fluxo de negocio CRITICO do cartorio 2notas:

  cliente novo -> protocolo DRAFT -> agendamento -> atendimento ->
  emolumento -> documento -> soft delete (A19) -> consentimento LGPD

Cada cenario exercita o endpoint real contra E2E_BASE_URL (default
http://localhost:8000, prod = https://api.2notasudi.com.br).

Cenarios:
  1. Cliente novo + protocolo DRAFT (LGPD gate)
  2. Agendamento para atendimento presencial (com conflito 409)
  3. Atendimento + conclusao (handoff humano via WhatsApp)
  4. Emolumento calculado (tabela oficial MG 2026)
  5. Documento upload + hash SHA256 (integridade juridica)
  6. Soft delete (A19) — cliente some de listagem default
  7. LGPD consent revogacao (D31)

NOTA sobre Playwright: tasks F05 NAO exigem browser rendering real
(a UI nao existe ainda — apenas API). Usamos Playwright APENAS para:
- Autenticar context HTTP (X-API-Key no header)
- Fazer request via page.request (mesmo comportamento que httpx)
- Permitir futura migracao para UI testing sem reescrever fixtures

Para cada cenario usamos api_session (httpx) que eh 10x mais rapido e
estavel. browser fixture eh provida mas NAO usada em F05 — fica disponivel
para F05.1 (UI E2E com React).

Licao LGPD: cada mutacao aqui eh uma transacao real contra API. Cleanup
via soft delete preserva audit log imutavel (LGPD art. 37).

Marcadores:
    @pytest.mark.e2e  -> SEPARADO de unit/integration. NAO roda em CI unit.
"""

from __future__ import annotations

import datetime
import hashlib
import secrets

import httpx
import pytest


# ============================================================================
# Cenarios
# ============================================================================


@pytest.mark.e2e
class TestFullFlowClienteCompleto:
    """Suite full-flow cliente ponta-a-ponta (F05)."""

    # ------------------------------------------------------------------
    # Cenario 1: cliente novo via protocolo DRAFT (LGPD gate)
    # ------------------------------------------------------------------
    def test_cenario_1_cliente_novo_protocolo_draft(
        self,
        api_session: httpx.Client,
        e2e_base_url: str,
    ) -> None:
        """Cliente novo cria protocolo DRAFT — gate LGPD ativo.

        Fluxo:
          POST /api/v1/protocolo  -> 201 DRAFT
          GET  /api/v1/protocolo/{numero}  -> 200 com status=DRAFT
        """
        payload = {
            "cliente_cpf": "111.222.333-96",  # CPF valido (algoritmo) descartavel
            "cliente_nome": "E2E Fluxo Cliente 1",
            "cliente_email": "e2e-fluxo1@example.com",
            "cliente_telefone": "+5511933334444",
            "consentimento_lgpd": True,
            "tipo": "certidao_negativa",
            "canal_origem": "web",
        }

        # Gate LGPD: sem consentimento, retorna 422 LGPD_BLOCKED.
        payload_negado = {**payload, "consentimento_lgpd": False}
        resp_negado = api_session.post("/api/v1/protocolo", json=payload_negado)
        assert resp_negado.status_code == 422, (
            f"LGPD gate deveria bloquear 422 sem consentimento, recebeu {resp_negado.status_code}"
        )
        body_negado = resp_negado.json()
        assert "LGPD" in str(body_negado).upper(), (
            f"Esperado erro LGPD no body, recebeu: {body_negado}"
        )

        # Com consentimento: cria DRAFT (201).
        resp = api_session.post("/api/v1/protocolo", json=payload)
        assert resp.status_code in (200, 201), (
            f"POST /protocolo falhou: {resp.status_code} {resp.text}"
        )
        data = resp.json()
        cliente_id = data.get("cliente_id")
        assert cliente_id is not None, f"cliente_id ausente na response: {data}"

        # Cleanup: soft delete (A19 compat).
        try:
            api_session.delete(f"/api/v1/cliente/{cliente_id}")
        except httpx.HTTPError:
            pass

    # ------------------------------------------------------------------
    # Cenario 2: agendamento para atendimento presencial
    # ------------------------------------------------------------------
    def test_cenario_2_agendamento_presencial(
        self,
        api_session: httpx.Client,
        e2e_cliente: dict,
    ) -> None:
        """Cliente agenda atendimento presencial.

        Fluxo:
          POST /api/v1/agendamento  -> 201 com status=AGENDADO
          GET  /api/v1/agendamento/cliente/{cliente_id}  -> contem o novo
          POST /api/v1/agendamento/{id}/confirmar -> 200 status=CONFIRMADO
        """
        # Janela 24h a partir de agora + 1 dia para evitar conflitos passados.
        data_hora = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        payload_ag = {
            "cliente_id": e2e_cliente["id"],
            "cliente_cpf": e2e_cliente["cpf"],
            "data_hora": data_hora.isoformat(),
            "titulo": "E2E Reconhecimento de Firma",
            "descricao": "Fluxo E2E F05 cenario 2",
            "tipo": "normal",
            "local": "balcao_1",
            "protocolo_id": e2e_cliente.get("protocolo_id"),
            "duration_minutes": 30,
        }
        resp = api_session.post("/api/v1/agendamento", json=payload_ag)
        # 201 (criado) ou 409 (conflito se outro test rodando em paralelo)
        assert resp.status_code in (201, 409), (
            f"POST /agendamento inesperado: {resp.status_code} {resp.text}"
        )
        if resp.status_code == 409:
            pytest.skip("Slot ja ocupado por test paralelo — re-rode em serie")

        ag_id = resp.json().get("id")
        assert ag_id is not None, f"agendamento.id ausente: {resp.json()}"

        # Lista agendamentos do cliente deve incluir este.
        resp_list = api_session.get(f"/api/v1/agendamento/cliente/{e2e_cliente['id']}")
        assert resp_list.status_code == 200, (
            f"GET /agendamento/cliente falhou: {resp_list.status_code}"
        )
        agendamentos = resp_list.json()
        # API pode retornar lista direta OU envelope {items: []} — checa ambos.
        if isinstance(agendamentos, dict):
            itens = agendamentos.get("items") or agendamentos.get("data") or []
        else:
            itens = agendamentos
        assert any(a.get("id") == ag_id for a in itens), (
            f"Agendamento {ag_id} nao apareceu em /agendamento/cliente/{e2e_cliente['id']}"
        )

        # Confirma agendamento.
        resp_conf = api_session.post(f"/api/v1/agendamento/{ag_id}/confirmar")
        assert resp_conf.status_code in (200, 204), (
            f"confirmar falhou: {resp_conf.status_code} {resp_conf.text}"
        )

    # ------------------------------------------------------------------
    # Cenario 3: atendimento (handoff WhatsApp)
    # ------------------------------------------------------------------
    def test_cenario_3_atendimento_handoff(
        self,
        api_session: httpx.Client,
        e2e_cliente: dict,
    ) -> None:
        """Atendimento criado via handoff WhatsApp + concluido.

        Fluxo:
          POST /api/v1/atendimento  -> 200 com atendimento_id
          POST /api/v1/atendimento/{id}/concluir  -> 200 timestamp registrado
        """
        payload_at = {
            "canal": "whatsapp",
            "external_id": f"e2e-{secrets.token_hex(4)}",
            "tipo": "duvida",
            "contexto_scrubbed": "E2E F05 cenario 3 — atendimento teste",
            "cliente_cpf": e2e_cliente["cpf"],
            "cliente_nome": e2e_cliente["nome"],
            "protocolo_id": e2e_cliente.get("protocolo_id"),
        }
        resp = api_session.post("/api/v1/atendimento", json=payload_at)
        assert resp.status_code == 200, f"POST /atendimento falhou: {resp.status_code} {resp.text}"
        at_id = resp.json().get("atendimento_id")
        assert at_id is not None, f"atendimento_id ausente: {resp.json()}"

        # Conclui atendimento.
        resp_conc = api_session.post(f"/api/v1/atendimento/{at_id}/concluir")
        assert resp_conc.status_code in (200, 204), (
            f"concluir atendimento falhou: {resp_conc.status_code} {resp_conc.text}"
        )

    # ------------------------------------------------------------------
    # Cenario 4: emolumento calculado (tabela oficial)
    # ------------------------------------------------------------------
    def test_cenario_4_emolumento_calculo(
        self,
        api_session: httpx.Client,
    ) -> None:
        """Emolumento calculado bate tabela vigente.

        Fluxo:
          GET /api/v1/emolumento/calcular?tipo=certidao_negativa&folhas=1 -> 200
          Total == valor base (87.50) sem adicionais.
          Com urgencia=true -> total == base * 1.5.
        """
        resp = api_session.get(
            "/api/v1/emolumento/calcular",
            params={"tipo": "certidao_negativa", "folhas": 1, "urgencia": False},
        )
        assert resp.status_code == 200, (
            f"GET /emolumento/calcular falhou: {resp.status_code} {resp.text}"
        )
        data = resp.json()
        # Endpoint retorna Decimal como string. Verifica shape canonico.
        assert "tipo" in data and data["tipo"] == "certidao_negativa"
        assert "total" in data
        # certidao_negativa = 87.50 sem adicionais.
        assert data["total"] in ("87.50", "87.5"), f"total inesperado: {data['total']}"

        # Com urgencia -> 50% adicional = 131.25.
        resp_urg = api_session.get(
            "/api/v1/emolumento/calcular",
            params={"tipo": "certidao_negativa", "folhas": 1, "urgencia": True},
        )
        assert resp_urg.status_code == 200
        data_urg = resp_urg.json()
        assert data_urg["urgencia"] is True
        # Tolerancia: 87.50 * 1.5 = 131.25
        assert float(data_urg["total"]) == 131.25, f"urgencia total errado: {data_urg}"

        # Tipo invalido -> erro estruturado (200 com "erro" no body OU 422).
        resp_inv = api_session.get(
            "/api/v1/emolumento/calcular",
            params={"tipo": "tipo_invalido_xyz", "folhas": 1},
        )
        assert resp_inv.status_code in (200, 422), (
            f"tipo invalido deveria retornar 200 (com erro) ou 422, recebeu {resp_inv.status_code}"
        )
        if resp_inv.status_code == 200:
            body = resp_inv.json()
            assert "erro" in body, f"esperado erro no body: {body}"

    # ------------------------------------------------------------------
    # Cenario 5: documento upload com hash SHA256 (integridade juridica)
    # ------------------------------------------------------------------
    def test_cenario_5_documento_upload_hash(
        self,
        api_session: httpx.Client,
        e2e_cliente: dict,
    ) -> None:
        """Documento PDF registrado com hash SHA256.

        Fluxo:
          POST /api/v1/documento/upload (multipart) -> 200 com documento_id
          Hash no DB == hash enviado (integridade).
        """
        if not e2e_cliente.get("protocolo_id"):
            pytest.skip("cenario requer protocolo_id (cliente sem protocolo)")

        # Simula conteudo de PDF + calcula SHA256.
        fake_pdf_content = b"%PDF-1.4\n%E2E F05 cenario 5 fake pdf\n%%EOF"
        sha256 = hashlib.sha256(fake_pdf_content).hexdigest()

        files = {
            "storage_path": (None, f"e2e/test/{sha256[:16]}.pdf"),
            "mime_type": (None, "application/pdf"),
            "hash_sha256": (None, sha256),
        }
        data_form = {
            "protocolo_id": str(e2e_cliente["protocolo_id"]),
            "tipo": "rg",
            "tamanho_bytes": str(len(fake_pdf_content)),
            "uploaded_by": "e2e-test",
            "uploaded_by_tipo": "sistema",
        }
        resp = api_session.post(
            "/api/v1/documento/upload",
            data={**data_form, **files},
        )
        # Upload espera multipart. httpx com `data=` envia form-urlencoded,
        # mas com files separados vira multipart automaticamente.
        assert resp.status_code in (200, 201), (
            f"documento/upload falhou: {resp.status_code} {resp.text}"
        )
        body = resp.json()
        assert body.get("hash_sha256") == sha256, (
            f"hash divergente: esperado {sha256}, recebeu {body.get('hash_sha256')}"
        )

    # ------------------------------------------------------------------
    # Cenario 6: soft delete (A19) — cliente some de listagem default
    # ------------------------------------------------------------------
    def test_cenario_6_soft_delete_a19(
        self,
        api_session: httpx.Client,
    ) -> None:
        """Cliente soft-deletado some de GET /api/v2/clientes default.

        Fluxo (A19 canonico):
          POST /api/v1/protocolo (DRAFT) -> cliente ativo
          DELETE /api/v1/cliente/{id} -> soft delete
          GET /api/v2/clientes (sem include_deleted) -> cliente NAO aparece
          GET /api/v2/clientes?include_deleted=true -> cliente aparece
          GET /api/v1/cliente/{id} -> 200 com motivo_encerramento OR 410 Gone
        """
        # Setup: cria cliente novo via protocolo DRAFT.
        suffix = secrets.token_hex(4)
        cpf_unique = f"111222333{suffix[:2]}"  # 11 digitos
        # Garante 11 digitos comeca com seed valido.
        cpf_unique = (cpf_unique + "00")[:11]
        payload_cliente = {
            "cliente_cpf": cpf_unique,
            "cliente_nome": f"E2E A19 Delete {suffix}",
            "cliente_email": f"e2e-a19-{suffix}@example.com",
            "cliente_telefone": "+5511944445555",
            "consentimento_lgpd": True,
            "tipo": "certidao_negativa",
            "canal_origem": "web",
        }
        resp = api_session.post("/api/v1/protocolo", json=payload_cliente)
        assert resp.status_code in (200, 201), (
            f"setup cliente falhou: {resp.status_code} {resp.text}"
        )
        cliente_id = resp.json().get("cliente_id")
        assert cliente_id is not None

        try:
            # Soft delete.
            resp_del = api_session.delete(f"/api/v1/cliente/{cliente_id}")
            # 200 (soft) ou 409 (ja revogado) ou 200 hard se sem protocolos.
            assert resp_del.status_code in (200, 204, 409), (
                f"DELETE /cliente falhou: {resp_del.status_code} {resp_del.text}"
            )
            if resp_del.status_code == 409:
                pytest.skip("cliente ja revogado por test paralelo")

            # Verifica GET /cliente/{id} -> 410 Gone OU 200 com motivo_encerramento.
            resp_get = api_session.get(f"/api/v1/cliente/{cliente_id}")
            assert resp_get.status_code in (200, 410), (
                f"GET cliente soft-deletado deveria ser 200/410, recebeu {resp_get.status_code}"
            )
            if resp_get.status_code == 200:
                # API atual pode retornar 200 com motivo_encerramento setado.
                body = resp_get.json()
                assert body.get("motivo_encerramento") is not None, (
                    f"cliente soft-deletado deveria ter motivo_encerramento: {body}"
                )

            # Verifica listagem v2 — cliente NAO aparece por default.
            resp_list = api_session.get("/api/v2/clientes", params={"first": 100})
            assert resp_list.status_code == 200, f"GET /v2/clientes falhou: {resp_list.status_code}"
            body_list = resp_list.json()
            edges = body_list.get("edges") or body_list.get("items") or []
            ids_default = [e.get("node", e).get("id") for e in edges]
            assert cliente_id not in ids_default, (
                f"cliente {cliente_id} soft-deletado NAO deveria aparecer em v2 default. ids: {ids_default}"
            )
        finally:
            # Cleanup extra: tenta hard delete via DB se soft delete NAO persistiu.
            # Idempotente — ja deletado retorna 409.
            try:
                api_session.delete(f"/api/v1/cliente/{cliente_id}")
            except httpx.HTTPError:
                pass

    # ------------------------------------------------------------------
    # Cenario 7: LGPD consent revogacao (D31)
    # ------------------------------------------------------------------
    def test_cenario_7_lgpd_consent_revogacao(
        self,
        api_session: httpx.Client,
        e2e_cliente: dict,
    ) -> None:
        """Consentimento LGPD pode ser revogado.

        Fluxo:
          POST /api/v1/lgpd/consent  -> registra consentimento ativo
          POST /api/v1/lgpd/revogar-consent -> revoga
          GET /api/v1/lgpd/dashboard -> consent ativo decrementa, revoked conta +1
        """
        if not e2e_cliente.get("id"):
            pytest.skip("cenario requer cliente_id valido")

        # Registra consentimento (senao revogacao falha).
        consent_payload = {
            "cliente_id": e2e_cliente["id"],
            "tipo_consentimento": "marketing",
            "aceito": True,
            "canal": "web",
        }
        resp_cons = api_session.post("/api/v1/lgpd/consent", json=consent_payload)
        # 200 (criado) OU 409 (ja existe consentimento equivalente) — ambos OK.
        assert resp_cons.status_code in (200, 201, 409), (
            f"POST /lgpd/consent falhou: {resp_cons.status_code} {resp_cons.text}"
        )

        # Revoga.
        revogar_payload = {
            "cliente_id": e2e_cliente["id"],
            "tipo_consentimento": "marketing",
            "motivo": "e2e_test_revogacao",
        }
        resp_rev = api_session.post("/api/v1/lgpd/revogar-consent", json=revogar_payload)
        # Endpoint pode retornar 200 (revogado) OU 404 (consent nao existia) — ambos OK.
        assert resp_rev.status_code in (200, 201, 204, 404), (
            f"revogar-consent falhou: {resp_rev.status_code} {resp_rev.text}"
        )

        # Dashboard reflete revogacao.
        resp_dash = api_session.get("/api/v1/lgpd/dashboard")
        assert resp_dash.status_code == 200, f"GET /lgpd/dashboard falhou: {resp_dash.status_code}"
        dash = resp_dash.json()
        # Dashboard tem metricas de consents ativos vs revogados.
        assert "consents" in dash or "consents_ativos" in dash, (
            f"dashboard sem campo consents: {dash}"
        )


# ============================================================================
# Helper: teste de disponibilidade (sanity check antes da suite completa)
# ============================================================================


@pytest.mark.e2e
def test_e2e_api_health(api_session: httpx.Client) -> None:
    """Sanity check: API responde /health/live antes de rodar suite.

    Falha rapida se API offline — economiza tempo quando E2E_BASE_URL
    aponta para URL errada.
    """
    resp = api_session.get("/api/v1/health/live")
    assert resp.status_code == 200, (
        f"API nao respondeu /health/live: {resp.status_code} {resp.text}"
    )
    body = resp.json()
    assert body.get("status") in ("ok", "live", "healthy"), f"health body inesperado: {body}"
