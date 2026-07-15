"""Testes do LGPD Export Envelope (D24).

Cobre o envelope ZIP + manifest + README + integridade via SHA256 + HMAC.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.cliente import Cliente
from app.services.lgpd_export_envelope import (
    ENVELOPE_VERSION,
    build_export_envelope,
    verify_envelope,
)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def cliente(db: Session) -> Cliente:
    c = Cliente(
        nome="Maria Export",
        cpf_hash="hash_export_maria",
        email="maria@export.com",
        telefone_hash="hash_tel_maria",
        consentimento_lgpd=True,
        consentimento_em=datetime.now(tz=timezone.utc),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestLGPDExportEnvelopeShape:
    """D24 — Shape e metadata do envelope."""

    def test_build_retorna_bytes_e_manifest(self, db, cliente):
        """build_export_envelope retorna (bytes, dict)."""
        zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        assert isinstance(zip_bytes, bytes)
        assert isinstance(manifest, dict)
        assert len(zip_bytes) > 0

    def test_manifest_header_lgpd_export_v1(self, db, cliente):
        """Manifest tem header `LGPD-EXPORT-V1`."""
        _zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        assert manifest["envelope_version"] == ENVELOPE_VERSION
        assert manifest["envelope_version"] == "LGPD-EXPORT-V1"

    def test_manifest_tem_cliente_id_hash(self, db, cliente):
        """Manifest tem cliente_id_hash (SHA256, nao expor PK raw)."""
        _zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        assert "cliente_id_hash" in manifest
        # SHA256 hex = 64 chars
        assert len(manifest["cliente_id_hash"]) == 64
        # NAO expoe PK diretamente
        assert "cliente_id" not in manifest or str(cliente.id) not in str(
            manifest.get("cliente_id", "")
        )

    def test_manifest_tem_metadata(self, db, cliente):
        """Manifest tem emitido_em, formato, tamanho_bytes."""
        _zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        assert "emitido_em" in manifest
        assert "formato" in manifest
        assert "tamanho_bytes" in manifest
        assert manifest["formato"] == "zip+json"
        assert manifest["tamanho_bytes"] > 0

    def test_manifest_tem_sha256_content_hash(self, db, cliente):
        """Manifest tem content_hash_sha256 (64 chars hex)."""
        _zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        h = manifest["content_hash_sha256"]
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_manifest_tem_hmac_signature(self, db, cliente):
        """Manifest tem hmac_signature (mesma chave do audit)."""
        _zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        assert "hmac_signature" in manifest
        assert len(manifest["hmac_signature"]) == 64
        assert len(manifest["hmac_key_fingerprint"]) == 16

    def test_manifest_tem_envelope_hash(self, db, cliente):
        """Manifest inclui envelope_hash_sha256 (do ZIP inteiro)."""
        _zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        assert "envelope_hash_sha256" in manifest
        assert len(manifest["envelope_hash_sha256"]) == 64
        assert manifest["envelope_tamanho_bytes"] > 0


class TestLGPDExportEnvelopeContent:
    """D24 — Conteudo do ZIP."""

    def test_zip_contem_export_json(self, db, cliente):
        """ZIP tem export.json valido."""
        zip_bytes, _manifest = build_export_envelope(db, cliente_id=cliente.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "export.json" in zf.namelist()
            data = json.loads(zf.read("export.json").decode("utf-8"))
            assert "cliente" in data
            assert "export_hash" in data

    def test_zip_contem_manifest_json(self, db, cliente):
        """ZIP tem manifest.json (machine-readable)."""
        zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "manifest.json" in zf.namelist()
            m = json.loads(zf.read("manifest.json").decode("utf-8"))
            assert m["envelope_version"] == "LGPD-EXPORT-V1"
            assert m["content_hash_sha256"] == manifest["content_hash_sha256"]

    def test_zip_contem_manifest_txt(self, db, cliente):
        """ZIP tem manifest.txt (human-readable)."""
        zip_bytes, _manifest = build_export_envelope(db, cliente_id=cliente.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "manifest.txt" in zf.namelist()
            txt = zf.read("manifest.txt").decode("utf-8")
            assert "LGPD" in txt
            assert "INTEGRIDADE" in txt
            assert "sha256" in txt.lower()

    def test_zip_contem_readme_md(self, db, cliente):
        """ZIP tem README.md com orientacoes pro titular."""
        zip_bytes, _manifest = build_export_envelope(db, cliente_id=cliente.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "README.md" in zf.namelist()
            md = zf.read("README.md").decode("utf-8")
            assert "LGPD" in md
            assert "Gustavo Almeida" in md
            assert "6682284055" in md
            assert "direitos" in md.lower()


class TestLGPDExportEnvelopeIntegrity:
    """D24 — Integridade SHA256 + HMAC (LGPD art. 37)."""

    def test_verify_envelope_valido(self, db, cliente):
        """Verify retorna valid=True para envelope nao adulterado."""
        zip_bytes, manifest = build_export_envelope(
            db, cliente_id=cliente.id, actor_id="dpo:verify"
        )
        result = verify_envelope(
            zip_bytes,
            expected_content_hash=manifest["content_hash_sha256"],
            expected_hmac=manifest["hmac_signature"],
        )
        assert result["valid"] is True
        assert result["content_hash_match"] is True
        assert result["hmac_match"] is True
        assert result["errors"] == []

    def test_verify_detecta_conteudo_adulterado(self, db, cliente):
        """Modify export.json dentro do ZIP -> verify falha."""
        zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)

        # Reconstroi ZIP adulterado (modifica export.json)
        new_buf = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zin:
            with zipfile.ZipFile(new_buf, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.namelist():
                    data = zin.read(item)
                    if item == "export.json":
                        # Adultera: inverte um byte do JSON
                        data = data.replace(b'"exported_at"', b'"HACKED_at"', 1)
                    zout.writestr(item, data)
        tampered_zip = new_buf.getvalue()

        result = verify_envelope(
            tampered_zip,
            expected_content_hash=manifest["content_hash_sha256"],
            expected_hmac=manifest["hmac_signature"],
        )
        assert result["valid"] is False
        assert result["content_hash_match"] is False
        # HMAC tbm falha porque content_hash mudou
        assert result["hmac_match"] is False
        assert len(result["errors"]) >= 1

    def test_verify_detecta_hmac_errado(self, db, cliente):
        """HMAC incorreto (outra chave) -> verify falha."""
        zip_bytes, manifest = build_export_envelope(db, cliente_id=cliente.id)
        result = verify_envelope(
            zip_bytes,
            expected_content_hash=manifest["content_hash_sha256"],
            expected_hmac="0" * 64,  # HMAC fake
        )
        assert result["valid"] is False
        assert result["hmac_match"] is False

    def test_verify_zip_malformado(self):
        """ZIP malformado -> valid=False."""
        result = verify_envelope(
            b"not a real zip at all",
            expected_content_hash="0" * 64,
            expected_hmac="0" * 64,
        )
        assert result["valid"] is False
        assert "ZIP malformado" in str(result["errors"])


class TestLGPDExportEnvelopeAuditLog:
    """D24 — Audit log eh gerado (LGPD art. 37)."""

    def test_build_gera_audit_log(self, db, cliente):
        """build_export_envelope gera entry no audit log."""
        from app.models.audit_log import AuditLog

        _zip_bytes, _manifest = build_export_envelope(
            db, cliente_id=cliente.id, actor_id="dpo:audit_test"
        )
        entries = db.query(AuditLog).filter(AuditLog.action == "lgpd.export.envelope_v1").all()
        assert len(entries) >= 1
        entry = entries[-1]
        assert entry.actor_id == "dpo:audit_test"
        assert entry.resource == f"cliente:{cliente.id}"
        # Payload inclui hashes
        p = entry.payload or {}
        assert "content_hash_sha256" in p
        assert "hmac_signature" in p
        assert p["lgpd_article"] == "art. 18 V"
        assert p["envelope_version"] == "LGPD-EXPORT-V1"

    def test_build_cliente_inexistente_levanta(self, db):
        """Cliente inexistente -> ValueError."""
        with pytest.raises(ValueError, match="99999"):
            build_export_envelope(db, cliente_id=99999)


class TestLGPDExportEnvelopeLGPDCompliance:
    """D24 — Compliance LGPD-by-design."""

    def test_envelope_nao_expoe_cpf_plain(self, db, cliente):
        """LGPD-by-design: export.json dentro do ZIP nao expoe CPF plain."""
        zip_bytes, _manifest = build_export_envelope(db, cliente_id=cliente.id)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            export_data = zf.read("export.json").decode("utf-8")
        # CPF/plaintext nao presente (apenas hash)
        assert "123.456.789" not in export_data
        # cpf_hash eh exposto (LGPD-by-design)
        assert "cpf_hash" in export_data
        assert "hash_export_maria" in export_data

    def test_envelope_idempotente_em_tamanho(self, db, cliente):
        """2 envelopes do mesmo cliente tem conteudo de export similar (ignorando timestamp)."""
        zip1, _m1 = build_export_envelope(db, cliente_id=cliente.id)
        zip2, _m2 = build_export_envelope(db, cliente_id=cliente.id)

        # Conteudo binario difere (timestamp created), mas conteudo de export
        # (excluindo o campo exported_at) deve ser similar.
        with zipfile.ZipFile(io.BytesIO(zip1), "r") as zf1:
            e1 = zf1.read("export.json")
        with zipfile.ZipFile(io.BytesIO(zip2), "r") as zf2:
            e2 = zf2.read("export.json")

        # Tamanhos similares (so exported_at muda)
        assert abs(len(e1) - len(e2)) < 100, f"Diferenca grande: {len(e1)} vs {len(e2)}"
        # Conteudo eh similar (90%+ dos bytes identicos)
        common = sum(1 for a, b in zip(e1, e2) if a == b)
        assert common > 0.9 * min(len(e1), len(e2))

    def test_envelope_2_chamadas_geram_2_audit_entries(self, db, cliente):
        """2 envelopes = 2 audit entries (cada export eh evento distinto)."""
        from app.models.audit_log import AuditLog

        build_export_envelope(db, cliente_id=cliente.id, actor_id="dpo:audit1")
        build_export_envelope(db, cliente_id=cliente.id, actor_id="dpo:audit2")

        entries = db.query(AuditLog).filter(AuditLog.action == "lgpd.export.envelope_v1").all()
        assert len(entries) == 2
        actors = {e.actor_id for e in entries}
        assert actors == {"dpo:audit1", "dpo:audit2"}
