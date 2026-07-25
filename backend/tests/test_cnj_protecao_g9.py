"""G9.S4.T9 (E3.08) — Testes do serviço puro cnj_protecao (relatório offline).

Sem DB: consome listas de dicts de audit entries (shape AuditLog
serializado) e valida agregação, tolerância a malformados, formato
CNJ-shaped (JSON-serializável) e renderização markdown.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.services.cnj_protecao import (
    build_protecao_report,
    render_protecao_markdown,
)

GEN_AT = datetime(2026, 7, 25, 15, 0, 0, tzinfo=UTC)


def _entry(
    action: str,
    *,
    timestamp: str | None = "2026-07-01T10:00:00+00:00",
    payload: dict | None = None,
) -> dict:
    return {
        "id": 1,
        "actor_id": "dpo-x",
        "actor_type": "dpo",
        "action": action,
        "resource": "res:x",
        "payload": payload or {},
        "timestamp": timestamp,
    }


class TestAgregacaoCorreta:
    def test_totais_e_quebra_por_acao(self) -> None:
        entries = [
            _entry("protocolo.create", timestamp="2026-07-01T10:00:00+00:00"),
            _entry("protocolo.create", timestamp="2026-07-02T10:00:00+00:00"),
            _entry("conversa.handoff", timestamp="2026-07-03T10:00:00+00:00"),
            _entry("cnj.export.massive_dump", timestamp="2026-07-04T10:00:00+00:00"),
            _entry("cnj.export.generated", timestamp="2026-07-05T10:00:00+00:00"),
            _entry("auth.failed", timestamp="2026-07-06T10:00:00+00:00"),
            _entry("pii.scrub", payload={"redaction_count": 2}),
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)

        assert report["schema"] == "cnj.protecao_dados/v1"
        assert report["data_classification"] == "RESTRICTED_AGGREGATED"
        assert report["gerado_em"] == GEN_AT.isoformat()
        totais = report["totais"]
        assert totais["acessos"] == 7
        assert totais["exportacoes"] == 2
        assert totais["mascaramentos"] == 1
        assert totais["falhas_auth"] == 1
        assert totais["entradas_malformadas"] == 0
        assert report["acessos_por_acao"]["protocolo.create"] == 2
        assert report["acessos_por_acao"]["conversa.handoff"] == 1
        assert report["exportacoes_por_acao"] == {
            "cnj.export.generated": 1,
            "cnj.export.massive_dump": 1,
        }

    def test_janela_temporal_min_max(self) -> None:
        entries = [
            _entry("a.b", timestamp="2026-07-10T08:00:00+00:00"),
            _entry("a.b", timestamp="2026-07-01T08:00:00+00:00"),
            _entry("a.b", timestamp="2026-07-05T08:00:00+00:00"),
            _entry("a.b", timestamp=None),  # sem timestamp não quebra janela
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)
        assert report["janela_temporal"]["inicio"] == "2026-07-01T08:00:00+00:00"
        assert report["janela_temporal"]["fim"] == "2026-07-10T08:00:00+00:00"

    def test_timestamp_z_suffix_e_datetime_obj(self) -> None:
        entries = [
            _entry("a.b", timestamp="2026-07-01T08:00:00Z"),
            {**_entry("a.b"), "timestamp": datetime(2026, 7, 2, 8, 0, 0)},  # naive
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)
        assert report["janela_temporal"]["inicio"].startswith("2026-07-01")
        assert report["janela_temporal"]["fim"].startswith("2026-07-02")

    def test_heuristicas_export_mask_auth(self) -> None:
        entries = [
            _entry("lgpd.exportacao.portabilidade"),  # export por nome
            _entry("documento.download"),  # export por 'download'
            _entry("cliente.anonimizacao"),  # mask por nome
            _entry("conversa.create", payload={"cpf": "[CPF_REDACTED]"}),  # mask por marker
            _entry("api.request", payload={"status": 401}),  # auth fail por status
            _entry("api.request", payload={"status_code": 403}),  # auth fail por status_code
            _entry("api.request", payload={"status": 200}),  # não é falha
        ]
        totais = build_protecao_report(entries, generated_at=GEN_AT)["totais"]
        assert totais["exportacoes"] == 2
        assert totais["mascaramentos"] == 2
        assert totais["falhas_auth"] == 2

    def test_report_e_json_serializavel(self) -> None:
        entries = [_entry("cnj.export.massive_dump"), _entry("auth.denied")]
        report = build_protecao_report(entries, generated_at=GEN_AT)
        blob = json.dumps(report, ensure_ascii=False)
        assert "cnj.protecao_dados/v1" in blob

    def test_minimizacao_sem_dados_pessoais(self) -> None:
        """Relatório nunca serializa actor/payload/IP das entradas."""
        entries = [
            {
                **_entry("cnj.export.massive_dump"),
                "actor_id": "dpo-cpf-529.982.247-25",
                "ip_truncated": "10.0.0.0/24",
                "payload": {"segredo": "nao-pode-vazar-XYZ"},
            }
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)
        blob = json.dumps(report, ensure_ascii=False)
        assert "529.982.247-25" not in blob
        assert "10.0.0.0/24" not in blob
        assert "nao-pode-vazar-XYZ" not in blob
        assert report["minimizacao"]["contem_dados_pessoais"] is False


class TestEntradasVazias:
    def test_lista_vazia(self) -> None:
        report = build_protecao_report([], generated_at=GEN_AT)
        assert report["totais"] == {
            "acessos": 0,
            "exportacoes": 0,
            "mascaramentos": 0,
            "falhas_auth": 0,
            "entradas_malformadas": 0,
        }
        assert report["acessos_por_acao"] == {}
        assert report["janela_temporal"] == {"inicio": None, "fim": None}
        md = render_protecao_markdown(report)
        assert "nenhuma entrada válida" in md
        assert "nenhuma exportação" in md


class TestEntradasMalformadasToleradas:
    def test_malformadas_contabilizadas_e_ignoradas(self) -> None:
        entries = [
            "nao-e-dict",
            None,
            42,
            {},  # sem action
            {"action": ""},  # action vazia
            {"action": 123},  # action não-string
            _entry("protocolo.create"),  # 1 válida
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)  # type: ignore[arg-type]
        assert report["totais"]["acessos"] == 1
        assert report["totais"]["entradas_malformadas"] == 6

    def test_timestamp_invalido_tolerado(self) -> None:
        entries = [
            _entry("a.b", timestamp="25/07/2026"),  # formato BR não-ISO
            _entry("a.b", timestamp="nunca"),
            _entry("a.b", timestamp="2026-07-25T00:00:00+00:00"),
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)
        assert report["totais"]["acessos"] == 3
        assert report["totais"]["entradas_malformadas"] == 0
        assert report["janela_temporal"]["inicio"] == "2026-07-25T00:00:00+00:00"

    def test_payload_exotico_nao_derruba(self) -> None:
        class Explosivo:
            def __repr__(self) -> str:
                raise RuntimeError("boom")

        entries = [
            _entry("conversa.create", payload={"obj": Explosivo()}),
            _entry("conversa.create", payload={"obj": Explosivo()}),
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)  # type: ignore[arg-type]
        assert report["totais"]["acessos"] == 2


class TestMarkdown:
    def test_markdown_renderiza_secoes(self) -> None:
        entries = [
            _entry("cnj.export.massive_dump"),
            _entry("auth.failed"),
            _entry("protocolo.create"),
        ]
        report = build_protecao_report(entries, generated_at=GEN_AT)
        md = render_protecao_markdown(report)
        assert md.startswith("# Relatório de Proteção de Dados")
        assert "## Janela temporal" in md
        assert "## Totais" in md
        assert "## Acessos por ação" in md
        assert "## Exportações por ação" in md
        assert "`cnj.export.massive_dump`" in md
        assert "minimização" in md
