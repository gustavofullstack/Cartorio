"""Wave Final P0 — regressao: trigger fn_auto_audit vs AuditService.verify_chain.

Root cause (prod, 2026-07-24): `POST /api/v1/audit/verify` retornava
chain_ok=false last_valid_position=667. Causa: entradas escritas pelo
trigger PL/pgSQL fn_auto_audit (migracao 0020) canonicalizam via
jsonb::text (ordem (len,bytewise), separadores com espaco), divergente do
json.dumps Python — 158 entradas sistematicas desde 2026-07-09.
prev_hash linkage provado 100% continuo (1130 entradas) => divergencia de
formato, NAO tampering.

Contratos testados aqui (falham se regredir):
1. _jsonb_text mimetiza jsonb::text (ordem (len,bytewise) + espacos).
2. _canonical_block_sql_trigger reproduz o template SQL da migracao.
3. verify_chain ACEITA entrada trigger-written com hash no formato SQL.
4. verify_chain REJEITA entrada trigger-written adulterada (fail-closed).
5. verify_chain REJEITA link quebrado mesmo em entrada trigger-written.
6. Migrations 0028/0029: o timestamp hasheado e o valor persistido usam o
   mesmo instante UTC, inclusive quando a sessao PostgreSQL nao esta em UTC.
7. Migration 0029 lineariza o grafo Alembic, falha fechado sem HMAC e grava
   o ``hmac_kid`` exigido pelo contrato de rotacao.

REVIEW cartorio-lgpd obrigatorio (superficie audit*).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.audit import AuditService

# ---------------------------------------------------------------------------
# 1. _jsonb_text: ordem (len, bytewise) + separadores com espaco
# ---------------------------------------------------------------------------


class TestJsonbText:
    def test_key_order_is_len_then_bytewise(self) -> None:
        # JSONB ordena por (comprimento, ordem binaria), NAO alfabetico.
        out = AuditService._jsonb_text({"zz": 1, "a": 2, "bb": 3})
        assert out == '{"a": 2, "bb": 3, "zz": 1}'

    def test_spaced_separators(self) -> None:
        out = AuditService._jsonb_text({"k": "v", "n": 1})
        assert out == '{"k": "v", "n": 1}'

    def test_nested_and_scalars(self) -> None:
        out = AuditService._jsonb_text({"obj": {"b": [1, None, True]}, "s": "x"})
        assert out == '{"s": "x", "obj": {"b": [1, null, true]}}'

    def test_utf8_raw_no_escape(self) -> None:
        # jsonb::text emite UTF-8 raw (diferente de json.dumps ensure_ascii=True)
        out = AuditService._jsonb_text({"nome": "José"})
        assert "José" in out
        assert "\\u" not in out


# ---------------------------------------------------------------------------
# 2. canonical SQL trigger == template da migracao
# ---------------------------------------------------------------------------


class TestCanonicalSqlTrigger:
    def test_matches_migration_template(self) -> None:
        payload = {"id": 4, "tipo": "duvida"}
        prev = "ab" * 32
        ts = "2026-07-09T16:19:12.022184"
        out = AuditService._canonical_block_sql_trigger(prev, payload, ts)
        expected = (
            '{"payload":'
            + AuditService._jsonb_text(payload)
            + ',"prev_hash":"'
            + prev
            + '","timestamp":"'
            + ts
            + '"}'
        )
        assert out == expected
        # ordem alfabetica das chaves do BLOCO (payload, prev_hash, timestamp)
        assert out.startswith('{"payload":')
        assert ',"prev_hash":"' in out
        assert out.endswith(f'"{ts}"' + "}")

    def test_genesis_prev_hash_zeros(self) -> None:
        out = AuditService._canonical_block_sql_trigger(None, {}, "2026-01-01T00:00:00.000000")
        assert '"prev_hash":"' + ("0" * 64) + '"' in out

    def test_hash_is_sha256_of_canonical(self) -> None:
        payload = {"a": 1}
        ts = "2026-07-24T00:00:00.000001"
        canonical = AuditService._canonical_block_sql_trigger("p" * 64, payload, ts)
        h = AuditService._compute_hash_sql_trigger("p" * 64, payload, ts)
        assert h == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 3-5. verify_chain com entradas trigger-written
# ---------------------------------------------------------------------------


def _entry(
    *,
    idx: int,
    prev_hash: str | None,
    payload: dict,
    ts: str,
    sql_style: bool,
    tamper: bool = False,
) -> SimpleNamespace:
    prev_for_hash = prev_hash if prev_hash else "0" * 64
    if sql_style:
        h = AuditService._compute_hash_sql_trigger(prev_for_hash, payload, ts)
    else:
        h = AuditService._compute_hash(prev_for_hash, payload, ts)
    if tamper:
        h = "0" * 64  # hash corrompido
    return SimpleNamespace(
        id=idx,
        timestamp=datetime.fromisoformat(ts),
        payload=payload,
        prev_hash=prev_hash,
        hash=h,
        user_agent="auto_audit_trigger" if sql_style else "pytest",
        actor_id="auto_audit" if sql_style else "pytest",
    )


def _db_with(entries: list[SimpleNamespace]) -> MagicMock:
    db = MagicMock()
    db.query.return_value.order_by.return_value.all.return_value = entries
    return db


class TestVerifyChainTriggerFallback:
    TS1 = "2026-07-09T16:19:12.022184"
    TS2 = "2026-07-09T16:19:22.387739"
    TS3 = "2026-07-09T16:19:38.852845"

    def _mixed_chain(self) -> list[SimpleNamespace]:
        e1 = _entry(idx=1, prev_hash=None, payload={"a": 1}, ts=self.TS1, sql_style=False)
        e2 = _entry(idx=2, prev_hash=e1.hash, payload={"b": 2}, ts=self.TS2, sql_style=True)
        e3 = _entry(idx=3, prev_hash=e2.hash, payload={"c": 3}, ts=self.TS3, sql_style=False)
        return [e1, e2, e3]

    def test_accepts_trigger_written_sql_hash(self) -> None:
        ok, last_valid = AuditService.verify_chain(_db_with(self._mixed_chain()))
        assert ok is True
        assert last_valid == 3

    def test_rejects_tampered_trigger_entry(self) -> None:
        entries = self._mixed_chain()
        entries[1] = _entry(
            idx=2,
            prev_hash=entries[0].hash,
            payload={"b": 2},
            ts=self.TS2,
            sql_style=True,
            tamper=True,
        )
        ok, last_valid = AuditService.verify_chain(_db_with(entries))
        assert ok is False
        assert last_valid == 1  # para ANTES da entrada adulterada

    def test_rejects_broken_link_even_for_trigger_entry(self) -> None:
        entries = self._mixed_chain()
        # prev_hash aponta para hash inexistente -> link quebrado: sem fallback
        entries[1] = _entry(
            idx=2,
            prev_hash="f" * 64,
            payload={"b": 2},
            ts=self.TS2,
            sql_style=True,
        )
        ok, last_valid = AuditService.verify_chain(_db_with(entries))
        assert ok is False
        assert last_valid == 1

    def test_non_trigger_entry_never_uses_sql_fallback(self) -> None:
        # Entrada Python-style adulterada para formato SQL NAO pode ser aceita
        e1 = _entry(idx=1, prev_hash=None, payload={"a": 1}, ts=self.TS1, sql_style=False)
        e2 = _entry(idx=2, prev_hash=e1.hash, payload={"b": 2}, ts=self.TS2, sql_style=True)
        e2.user_agent = "api"
        e2.actor_id = "escrevente"
        ok, last_valid = AuditService.verify_chain(_db_with([e1, e2]))
        assert ok is False
        assert last_valid == 1


# ---------------------------------------------------------------------------
# 6. Migracao 0028: ts hasheado == ts armazenado
#    (ex-0022; re-id 2026-07-24 para nao colidir com 0022 RLS)
# ---------------------------------------------------------------------------


class TestMigration0028:
    SQL = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_07_24_0028-fix-fn-auto-audit-ts-consistency.py"
    ).read_text()

    def test_ts_derived_from_now_not_clock_timestamp(self) -> None:
        # isola o corpo do UPGRADE_SQL (sem docstring, sem downgrade)
        upgrade = self.SQL.split('UPGRADE_SQL = r"""')[1].split('"""')[0]
        assert "v_now := NOW();" in upgrade
        assert "to_char(v_now AT TIME ZONE 'UTC'" in upgrade
        # clock_timestamp() so pode aparecer no DOWNGRADE (rollback da 0020).
        # O vetor de regressao real e o USO em to_char (nao comentarios).
        assert "to_char(clock_timestamp()" not in upgrade

    def test_same_now_goes_to_timestamp_column(self) -> None:
        upgrade = self.SQL.split('UPGRADE_SQL = r"""')[1].split('"""')[0]
        assert "v_hash, v_hmac, v_now" in upgrade

    def test_revision_chain(self) -> None:
        # Head linear: ...0027 (CNJ artifact) -> 0028 (fn_auto_audit ts fix)
        assert 'revision = "0028"' in self.SQL
        assert 'down_revision = "0027"' in self.SQL


class TestMigration0029:
    SQL = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_07_28_0029-fix-fn-auto-audit-utc-naive-session-timezone.py"
    ).read_text()

    def test_uses_one_utc_naive_value_for_hash_and_persistence(self) -> None:
        upgrade = self.SQL.split('UPGRADE_SQL = r"""')[1].split('"""')[0]
        assert "v_timestamp_utc TIMESTAMP WITHOUT TIME ZONE" in upgrade
        assert "v_timestamp_utc := NOW() AT TIME ZONE 'UTC';" in upgrade
        assert "to_char(v_timestamp_utc" in upgrade
        assert "v_hash, v_hmac, v_hmac_kid, v_timestamp_utc" in upgrade
        assert "v_now TIMESTAMPTZ" not in upgrade

    def test_revision_follows_emolumento_sibling_and_linearizes_head(self) -> None:
        assert 'revision = "0029"' in self.SQL
        assert 'down_revision = "df086899697e"' in self.SQL

    def test_hmac_configuration_is_required_without_known_fallback(self) -> None:
        upgrade = self.SQL.split('UPGRADE_SQL = r"""')[1].split('"""')[0]
        assert "v_key := NULLIF(current_setting('app.audit_hmac_key', true), '');" in upgrade
        assert (
            "v_hmac_kid := NULLIF(current_setting('app.audit_hmac_kid', true), '');" in upgrade
        )
        assert "IF v_key IS NULL OR length(v_key) < 32 THEN" in upgrade
        assert "IF v_hmac_kid IS NULL OR length(v_hmac_kid) > 64 THEN" in upgrade
        assert "RAISE EXCEPTION USING" in upgrade
        assert "auto_audit_local_key" not in upgrade

    def test_persists_hmac_kid_with_signature(self) -> None:
        upgrade = self.SQL.split('UPGRADE_SQL = r"""')[1].split('"""')[0]
        assert "prev_hash, hash, hmac_signature, hmac_kid, timestamp" in upgrade
        assert "v_hash, v_hmac, v_hmac_kid, v_timestamp_utc" in upgrade
