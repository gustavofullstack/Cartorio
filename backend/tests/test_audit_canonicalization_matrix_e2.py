"""E2.10 (2026-07-24) — matriz de canonicalização audit. LOCAL_ONLY.

Especifica o algoritmo esperado dos DOIS formatos de canonical block e suas
divergências controladas. Complementa test_audit_trigger_canonical_p0.py com
os edges exigidos pelo plano Etapa 2 (unicode, key ordering divergente real,
null/bool/números, timestamp, linkage mista). NÃO toca produção nem legacy.

Propriedade central provada aqui: os dois formatos NUNCA produzem o mesmo
hash para o mesmo payload (separadores divergem sempre) — logo não existe
falso positivo cruzado: entrada Python só valida no formato Python, entrada
trigger só no formato trigger. Fail-closed preservado nos dois sentidos.

LIMITE DOCUMENTADO DO MIRROR (risco residual aceito): Postgres jsonb::text
preserva lexema numeric com trailing zeros ('1.50'), enquanto o mirror
Python emite json.dumps(1.5) -> '1.5'. UNVERIFIED sem PG real. Mitigação:
payloads de audit_log usam strings/ints/bools/None (nunca float formatado);
se um dia usarem, ampliar o mirror com preservação de lexema.

REVIEW cartorio-lgpd (superficie audit*). Modified by Gustavo Almeida.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.audit import AuditService


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
        h = "0" * 64
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


class TestKeyOrderingDivergente:
    def test_python_sort_keys_vs_jsonb_len_bytewise_divergem(self) -> None:
        # {"zz":..., "aaa":...}: Python sort_keys -> aaa primeiro;
        # JSONB (len,bytewise) -> zz (len 2) antes de aaa (len 3). DIVERGE.
        payload = {"zz": 1, "aaa": 2}
        py = AuditService._canonical_block(None, payload, "2026-07-24T00:00:00.000001")
        sql = AuditService._canonical_block_sql_trigger(None, payload, "2026-07-24T00:00:00.000001")
        assert py.index('"aaa"') < py.index('"zz"')
        assert sql.index('"zz"') < sql.index('"aaa"')
        assert py != sql


class TestUnicodeDivergente:
    def test_python_escapa_jsonb_emite_raw(self) -> None:
        payload = {"nome": "José Ação"}
        py = AuditService._canonical_block(None, payload, "2026-07-24T00:00:00.000001")
        sql = AuditService._canonical_block_sql_trigger(None, payload, "2026-07-24T00:00:00.000001")
        # json.dumps (ensure_ascii=True) escapa; jsonb::text e UTF-8 raw.
        assert "Jos\\u00e9" in py
        assert "José" in sql
        assert "\\u" not in sql


class TestFormatosNuncaColidem:
    PAYLOADS = (
        {"a": 1},
        {"n": None, "b": True},
        {"s": "texto"},
        {"lista": [1, 2, 3]},
        {"aninhado": {"x": {"y": None}}},
    )

    def test_hash_python_nunca_igual_hash_trigger(self) -> None:
        # Mesmo quando os valores convergem, os separadores divergem:
        # nao existe falso positivo cruzado entre os dois verificadores.
        ts = "2026-07-24T10:00:00.123456"
        for payload in self.PAYLOADS:
            h_py = AuditService._compute_hash(None, payload, ts)
            h_sql = AuditService._compute_hash_sql_trigger(None, payload, ts)
            assert h_py != h_sql, payload


class TestLexemasEscalares:
    def test_null_bool_int_float_no_jsonb_text(self) -> None:
        # Chaves len=1 -> ordem bytewise pura: d < f < i < n < t.
        out = AuditService._jsonb_text({"n": None, "t": True, "f": False, "i": 10, "d": 1.5})
        assert out == '{"d": 1.5, "f": false, "i": 10, "n": null, "t": true}'

    def test_limite_mirror_numeric_trailing_zero_documentado(self) -> None:
        # Mirror emite '1.5' (json.dumps); Postgres jsonb::text preservaria
        # '1.50' se o literal tivesse zeros. Risco aceito — ver docstring.
        assert AuditService._jsonb_text({"v": 1.5}) == '{"v": 1.5}'


class TestTimestampVerbatim:
    def test_mesmo_ts_nos_dois_formatos(self) -> None:
        ts = "2026-07-24T03:00:00.999999"
        py = AuditService._canonical_block(None, {"a": 1}, ts)
        sql = AuditService._canonical_block_sql_trigger(None, {"a": 1}, ts)
        assert f'"timestamp":"{ts}"' in py
        assert f'"timestamp":"{ts}"' in sql


class TestGenesisELinkageMista:
    TS1 = "2026-07-24T10:00:00.000001"
    TS2 = "2026-07-24T10:00:01.000002"
    TS3 = "2026-07-24T10:00:02.000003"

    def test_genesis_prev_hash_zero64_ambos(self) -> None:
        for canonical in (
            AuditService._canonical_block(None, {}, self.TS1),
            AuditService._canonical_block_sql_trigger(None, {}, self.TS1),
        ):
            assert '"prev_hash":"' + "0" * 64 + '"' in canonical

    def test_chain_mista_unicode_verifica_ponta_a_ponta(self) -> None:
        e1 = _entry(idx=1, prev_hash=None, payload={"nome": "José"}, ts=self.TS1, sql_style=False)
        e2 = _entry(
            idx=2,
            prev_hash=e1.hash,
            payload={"ação": "cadastro", "n": 2},
            ts=self.TS2,
            sql_style=True,
        )
        e3 = _entry(idx=3, prev_hash=e2.hash, payload={"fim": True}, ts=self.TS3, sql_style=False)
        ok, last_valid = AuditService.verify_chain(_db_with([e1, e2, e3]))
        assert ok is True
        assert last_valid == 3

    def test_chain_mista_unicode_tamper_fail_closed(self) -> None:
        e1 = _entry(idx=1, prev_hash=None, payload={"nome": "José"}, ts=self.TS1, sql_style=False)
        e2 = _entry(
            idx=2,
            prev_hash=e1.hash,
            payload={"ação": "adulterada"},
            ts=self.TS2,
            sql_style=True,
            tamper=True,
        )
        ok, last_valid = AuditService.verify_chain(_db_with([e1, e2]))
        assert ok is False
        assert last_valid == 1
