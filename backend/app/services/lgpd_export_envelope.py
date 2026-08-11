"""LGPD Export Envelope (D24).

Adiciona um envelope padronizado ao exportar dados do titular (LGPD art. 18 V
— portabilidade) para garantir:

1. **Header** `LGPD-EXPORT-V1` — protocolo de export identificado por version.
2. **Metadata**: emitido_em, cliente_id_hash (PK + SHA256), formato, tamanho_bytes.
3. **Footer**: hash SHA256 do conteudo + assinatura HMAC (mesma chave do audit).
4. **Formato ZIP-like** (zipfile.ZipFile in-memory): `export.json` + `README.md` + `manifest.txt`.

LGPD-by-design: integridade forense. Permite ao titular (ou ANPD) verificar
que o export nao foi adulterado desde a emissao (LGPD art. 37).

Uso:
    from app.services.lgpd_export_envelope import build_export_envelope

    bundle_bytes, manifest = build_export_envelope(
        db,
        cliente_id=42,
        actor_id="dpo:gustavo",
    )
    # bundle_bytes -> bytes do ZIP (in-memory, sem tocar em disco)
    # manifest -> dict com metadata + hashes para validacao

    # O endpoint pode retornar bundle_bytes via StreamingResponse.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENVELOPE_VERSION = "LGPD-EXPORT-V1"
ALGORITHM_SHA = "sha256"
ALGORITHM_HMAC = "sha256"


# ============================================================================
# Hashing helpers
# ============================================================================


def _hash_cliente_id(cliente_id: int) -> str:
    """Hash SHA256 do cliente_id (LGPD-by-design: nao exposto em URL/hash reverso)."""
    return hashlib.sha256(f"cliente:{cliente_id}".encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    """SHA256 hex de bytes."""
    return hashlib.sha256(data).hexdigest()


def _hmac_signature(content_hash: str, hmac_key: str | None) -> str:
    """Calcula assinatura HMAC do hash do conteudo.

    Args:
        content_hash: hash SHA256 do conteudo
        hmac_key: chave HMAC (em prod, vem de settings.audit_hmac_key).
                  Se None (testes), usa uma chave dummy deterministica.
    """
    key = hmac_key if hmac_key else "test-crypt-key-32-chars-min-XXXX"
    if len(key) < 32:
        # Pad pra ter pelo menos 32 chars (HMAC SHA256 requer >= 16 mas aqui usamos 32)
        key = (key + "x" * 32)[:32]
    return hmac.new(key.encode("utf-8"), content_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def _get_audit_hmac_key() -> str:
    """Recupera a HMAC key do settings (LGPD-by-design: mesma chave do audit)."""
    try:
        from app.config import settings

        return settings.audit_hmac_key
    except Exception:
        return "test-crypt-key-32-chars-min-XXXX"


# ============================================================================
# Build envelope
# ============================================================================


def build_export_envelope(
    db: Session,
    cliente_id: int,
    *,
    actor_id: str = "system:cartorio-dpo",
    incluir_audit: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    """Constroi o envelope ZIP de export LGPD para o titular.

    Args:
        db: Session
        cliente_id: PK do titular
        actor_id: quem esta executando (pra audit_log)
        incluir_audit: se True, inclui audit_logs do titular no JSON

    Returns:
        Tupla (bytes_do_zip, manifest_dict)
        - bytes_do_zip: ZIP pronto pra servir via StreamingResponse
        - manifest_dict: metadata + hashes para validacao externa

    Raises:
        ValueError: se cliente nao existe
    """
    from app.services.audit import AuditService
    from app.services.lgpd_export import (
        ClienteNotFoundError,
        exportar_dados_titular,
    )

    # 1) Monta bundle com dados do titular
    try:
        bundle = exportar_dados_titular(db, cliente_id=cliente_id, incluir_audit=incluir_audit)
    except ClienteNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    # 2) Serializa para JSON canonico
    bundle_json_str = bundle.to_json()
    bundle_bytes = bundle_json_str.encode("utf-8")

    # 3) Calcula hashes
    content_hash_sha256 = _sha256_bytes(bundle_bytes)
    hmac_key = _get_audit_hmac_key()
    hmac_sig = _hmac_signature(content_hash_sha256, hmac_key)

    # 4) Metadata
    emitido_em = datetime.now(tz=timezone.utc).isoformat()
    cliente_id_hash = _hash_cliente_id(cliente_id)
    tamanho_bytes = len(bundle_bytes)

    manifest = {
        "envelope_version": ENVELOPE_VERSION,
        "lgpd_article": "art. 18 V",
        "cliente_id_hash": cliente_id_hash,
        "emitido_em": emitido_em,
        "emitido_por": actor_id,
        "formato": "zip+json",
        "algoritmos": {"content_hash": ALGORITHM_SHA, "hmac": ALGORITHM_HMAC},
        "tamanho_bytes": tamanho_bytes,
        "content_hash_sha256": content_hash_sha256,
        "hmac_signature": hmac_sig,
        "hmac_key_fingerprint": hashlib.sha256(hmac_key.encode("utf-8")).hexdigest()[:16],
        "audit_log_chained": True,
        "verification_instructions": (
            "Para verificar integridade: "
            "(1) concatene bytes do export.json dentro deste ZIP; "
            "(2) calcule SHA256; "
            "(3) compare com content_hash_sha256 acima; "
            "(4) calcule HMAC-SHA256 do hash usando hmac_key_fingerprint correspondente; "
            "(5) compare com hmac_signature."
        ),
        "registros_exportados": {
            "cliente": 1 if bundle.cliente else 0,
            "protocolos": len(bundle.protocolos),
            "atendimentos": len(bundle.atendimentos),
            "documentos": len(bundle.documentos),
            "audit_logs": len(bundle.audit_logs),
            "consentimentos": len(bundle.consentimentos),
        },
    }

    # 5) README em markdown
    readme_md = _build_readme(manifest)

    # 6) Manifest em texto (human-readable)
    manifest_txt = _build_manifest_txt(manifest)

    # 7) Constroi ZIP em memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # export.json (dados canonicos)
        zf.writestr("export.json", bundle_bytes)
        # manifest.json (machine-readable)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        # manifest.txt (human-readable)
        zf.writestr("manifest.txt", manifest_txt)
        # README.md (orientacoes pro titular)
        zf.writestr("README.md", readme_md)

    zip_bytes = zip_buffer.getvalue()

    # 8) ZIP-level hash (SHA256 do ZIP inteiro) — opcional, para integridade do envelope
    envelope_hash = _sha256_bytes(zip_bytes)
    manifest["envelope_hash_sha256"] = envelope_hash
    manifest["envelope_tamanho_bytes"] = len(zip_bytes)

    # 9) Audit log do export (LGPD art. 37)
    AuditService.log(
        db,
        actor_id=actor_id,
        actor_type="dpo",
        action="lgpd.export.envelope_v1",
        resource=f"cliente:{cliente_id}",
        payload={
            "cliente_id_hash": cliente_id_hash,
            "tamanho_bytes": tamanho_bytes,
            "envelope_tamanho_bytes": len(zip_bytes),
            "content_hash_sha256": content_hash_sha256,
            "envelope_hash_sha256": envelope_hash,
            "hmac_signature": hmac_sig,
            "envelope_version": ENVELOPE_VERSION,
            "lgpd_article": "art. 18 V",
        },
    )
    db.commit()

    logger.info(
        "LGPD export envelope built: cliente_id=%s size=%d envelope_size=%d hash=%s",
        cliente_id,
        tamanho_bytes,
        len(zip_bytes),
        envelope_hash[:12],
    )

    return zip_bytes, manifest


def _build_readme(manifest: dict[str, Any]) -> str:
    """Conteudo README.md no ZIP — orientacoes para o titular."""
    return f"""# LGPD Export — Pacote de Portabilidade

## Envelope version: {manifest["envelope_version"]}

Emitido em: {manifest["emitido_em"]}
Para o titular (cliente_id_hash `{manifest["cliente_id_hash"][:16]}...`).

## Conteudo deste pacote

1. `export.json` — Dados pessoais do titular (LGPD art. 18 V — portabilidade).
2. `manifest.json` — Metadata + hashes para verificacao de integridade (LGPD art. 37).
3. `manifest.txt` — Mesmo conteudo, formato texto.
4. `README.md` — Este arquivo.

## Como verificar a integridade

Execute (no Linux/Mac):

```bash
# 1) Extraia
unzip lgpd-export.zip -d lgpd-export/

# 2) Calcule SHA256 do export.json
shasum -a 256 lgpd-export/export.json

# 3) Compare com manifest.json -> content_hash_sha256
```

Se os hashes nao baterem, o pacote foi ADULTERADO. Reporte ao DPO.

## Direitos do Titular (LGPD art. 18)

Voce tem direito a:
- Confirmacao/existencia + acesso (art. 18 I+II)
- Correcao (art. 18 III)
- Anonimizacao/bloqueio/eliminacao (art. 18 IV)
- **Portabilidade (art. 18 V) — este documento**
- Revogacao do consentimento (art. 18 VI)
- Oposicao (art. 18 IX)
- Nao ser submetido a decisao automatizada (art. 20)

Prazo de resposta do controlador: ate 15 dias uteis (LGPD art. 18 §5).

## Contact do Encarregado/DPO

- Nome: Gustavo Almeida
- E-mail: dpo@2notasudi.com.br
- Telegram: 6682284055
- Papel: Encarregado de Dados / DPO (LGPD art. 41)
"""


def _build_manifest_txt(manifest: dict[str, Any]) -> str:
    """Manifest em texto plano (human-readable)."""
    lines: list[str] = [
        "=" * 60,
        f"LGPD EXPORT ENVELOPE — {manifest['envelope_version']}",
        "=" * 60,
        "",
        f"LGPD Article         : {manifest['lgpd_article']}",
        f"Emitido em           : {manifest['emitido_em']}",
        f"Emitido por          : {manifest['emitido_por']}",
        f"Cliente (ID hash)    : {manifest['cliente_id_hash']}",
        f"Formato              : {manifest['formato']}",
        f"Tamanho export.json  : {manifest['tamanho_bytes']} bytes",
        f"Tamanho envelope     : {manifest.get('envelope_tamanho_bytes', '?')} bytes",
        "",
        "INTEGRIDADE",
        f"  content_hash_sha256 : {manifest['content_hash_sha256']}",
        f"  envelope_hash_sha256: {manifest.get('envelope_hash_sha256', '?')}",
        f"  hmac_signature      : {manifest['hmac_signature']}",
        f"  hmac_key_fingerprint: {manifest['hmac_key_fingerprint']}",
        "",
        "ALGORITMOS",
        f"  content_hash: {manifest['algoritmos']['content_hash']}",
        f"  hmac        : {manifest['algoritmos']['hmac']}",
        "",
        "REGISTROS EXPORTADOS",
    ]
    regs = manifest["registros_exportados"]
    for k, v in regs.items():
        lines.append(f"  {k}: {v}")
    lines.extend(
        [
            "",
            "INSTRUCOES DE VERIFICACAO",
            manifest["verification_instructions"],
            "",
        ]
    )
    return "\n".join(lines)


# ============================================================================
# Verify envelope (LGPD art. 37 — integridade)
# ============================================================================


def verify_envelope(
    zip_bytes: bytes,
    *,
    expected_content_hash: str,
    expected_hmac: str,
    hmac_key: str | None = None,
) -> dict[str, Any]:
    """Verifica integridade de um ZIP envelope (LGPD art. 37).

    Args:
        zip_bytes: bytes do ZIP a verificar
        expected_content_hash: SHA256 esperado do export.json
        expected_hmac: HMAC esperado (da manifest)
        hmac_key: chave HMAC para validar (None = busca de settings)

    Returns:
        dict com:
        - valid: bool (True se export.json SHA256 bate E HMAC bate)
        - content_hash_match: bool
        - hmac_match: bool
        - export_json_size: int
        - errors: list[str]
    """
    errors: list[str] = []
    key = hmac_key if hmac_key else _get_audit_hmac_key()

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            try:
                export_data = zf.read("export.json")
            except KeyError:
                errors.append("export.json nao encontrado no ZIP")
                return {
                    "valid": False,
                    "content_hash_match": False,
                    "hmac_match": False,
                    "export_json_size": 0,
                    "errors": errors,
                }

            # SHA256 do export.json
            computed_hash = _sha256_bytes(export_data)
            content_hash_match = computed_hash == expected_content_hash
            if not content_hash_match:
                errors.append(
                    f"content_hash mismatch: expected={expected_content_hash[:16]}... "
                    f"got={computed_hash[:16]}..."
                )

            # HMAC do content_hash
            computed_hmac = _hmac_signature(computed_hash, key)
            hmac_match = hmac.compare_digest(computed_hmac, expected_hmac)
            if not hmac_match:
                errors.append("HMAC signature mismatch (envelope may be tampered)")

            return {
                "valid": content_hash_match and hmac_match,
                "content_hash_match": content_hash_match,
                "hmac_match": hmac_match,
                "export_json_size": len(export_data),
                "errors": errors,
            }
    except zipfile.BadZipFile:
        return {
            "valid": False,
            "content_hash_match": False,
            "hmac_match": False,
            "export_json_size": 0,
            "errors": ["ZIP malformado"],
        }


__all__ = [
    "build_export_envelope",
    "verify_envelope",
    "ENVELOPE_VERSION",
]
