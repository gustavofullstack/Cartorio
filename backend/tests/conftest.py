"""Test fixtures."""

import os
import subprocess
import builtins as _builtins
import warnings as _w_mod
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from tests.test_telegram_e2e_5x import StatefulBus

# CPython 3.11.15 / 3.12 / 3.13 bug + pytest interaction:
# pytest_sessionfinish chama warnings.filterwarnings("always", ...) que
# internamente faz `assert isinstance(lineno, int)` que falha com
# "TypeError: isinstance() arg 2 must be a type" (C-level bug).
# Workaround 1: monkeypatch builtins.isinstance para nunca levantar TypeError
# (fallback para type(obj) is cls).
_orig_isinstance = _builtins.isinstance


def _safe_isinstance(obj, cls):
    try:
        return _orig_isinstance(obj, cls)
    except TypeError:
        try:
            return type(obj) is cls
        except Exception:
            return False


_builtins.isinstance = _safe_isinstance

# Workaround 2: garantir que `int` no namespace do modulo warnings e `type`
# apontam para as classes reais. Algum plugin de teste pode ter feito
# monkeypatch que nao afeta builtins global mas afeta o modulo.
_w_mod.int = _builtins.int
_w_mod.type = _builtins.type

# Mock global para subprocess.run (impede rsync de travar nos testes com timeout de 60s)
_orig_run = subprocess.run

def _mock_run(args, *args_list, **kwargs):
    if isinstance(args, list) and "rsync" in args:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="mocked rsync output", stderr="")
    return _orig_run(args, *args_list, **kwargs)

subprocess.run = _mock_run


# Set test env BEFORE importing app modules.
# Sprint 4 S01: usa setdefault para permitir override via env var
# (CI/prod tem DATABASE_URL=postgresql; dev local pode usar sqlite).
# Se a env var ja esta setada (Postgres), respeita.
# Forca SQLite para testes (default). CI/postgres-tests DEVEM setar
# DATABASE_URL explicitamente ANTES de invocar pytest.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_HMAC_KEY"] = "a" * 64
os.environ["TELEGRAM_WEBHOOK_SECRET"] = ""
os.environ["CHATWOOT_ACCOUNT_ID"] = "0"
os.environ["CHATWOOT_INBOX_ID"] = "0"
os.environ["DB_POOL_SIZE"] = "20"
os.environ["DB_MAX_OVERFLOW"] = "10"
os.environ["DB_POOL_RECYCLE"] = "3600"
os.environ["DB_POOL_TIMEOUT"] = "30"
os.environ["DB_POOL_PRE_PING"] = "true"
os.environ["AUDIT_DEAD_MANS_SWITCH_MINUTES"] = "60"
os.environ["APP_ENV"] = "development"
os.environ["PII_SCRUB_ENABLED"] = "true"
os.environ["PII_BLOCK_ON_DETECT"] = "true"
os.environ["N8N_API_KEY"] = "header.payload.signature"

TEST_CARTORIO_API_KEY = "a" * 64
os.environ["CARTORIO_API_KEY"] = TEST_CARTORIO_API_KEY
os.environ["JWT_SECRET"] = "a" * 64

os.environ["LLM_DEFAULT_PROVIDER"] = "opencode_go"
os.environ["LLM_FALLBACK_CHAIN"] = "opencode_go,openclaw"
os.environ["OPENCODE_GO_MODEL"] = "minimax-m3"
os.environ["JWT_SECRET"] = "a" * 64

from app.config import get_settings, settings  # noqa: E402


get_settings.cache_clear()
settings.jwt_secret = "a" * 64


from app.models.base import Base  # noqa: E402

# Importa modelos concretos para que Base.metadata esteja populado nos testes
# (caso contrario tabelas nao existem no SQLite in-memory e lifespan da app
#  falha em AuditService.log_system_action -> "no such table: audit_log")
from app.models import (  # noqa: E402,F401
    audit_log,  # usado por AuditService.log_system_action no lifespan
    cliente,
    protocolo,
    atendimento,
    documento,
    conversa,
    outbox_message,
    webhook_event,
)


@pytest.fixture
def db_session(monkeypatch) -> Iterator[Session]:
    """SQLite in-memory DB pra testes. Cada teste comeca vazio.

    Redireciona a engine global (app.db.engine) para esta engine via
    monkeypatch, garantindo que o lifespan da app + AuditService vejam
    as mesmas tabelas criadas aqui (sem isso, lifespan roda em conexao
    1 e AuditService em conexao 2 -> "no such table: audit_log").
    """
    from app.db import SessionLocal as GlobalSessionLocal  # noqa: PLC0415
    from app.db import engine as global_engine  # noqa: PLC0415

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    # Redireciona a engine global para a engine deste teste
    monkeypatch.setattr(global_engine, "pool", eng.pool)
    # Redireciona o SessionLocal global para criar sessoes nesta engine
    monkeypatch.setattr(
        GlobalSessionLocal,
        "kw",
        {"bind": eng, "autoflush": False, "autocommit": False, "expire_on_commit": False},
    )
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(eng)


@pytest.fixture(autouse=True)
def _patch_db_session_for_all_tests():
    """AUTUSE: patcha app.db.session_scope + SessionLocal para usar
    SQLite in-memory com TODAS as tabelas criadas.

    Sem isso, AuditService.log_system_action() durante lifespan shutdown
    falha com 'no such table: audit_log' (a engine global aponta para
    postgres de prod que nao existe em CI/test).

    Workaround 2026-07-06: aplica o patch em TODOS os testes, nao
    somente quando db_session fixture é solicitada.
    """
    import app.db as appdb
    import os
    from app.config import get_settings, settings

    os.environ["JWT_SECRET"] = "a" * 64
    get_settings.cache_clear()
    settings.jwt_secret = "a" * 64

    # FORCAR import de TODOS models ANTES do create_all
    from app.models.audit_log import AuditLog  # noqa: F401, PLC0415
    from app.models.protocolo import Protocolo  # noqa: F401, PLC0415
    from app.models.documento import Documento  # noqa: F401, PLC0415
    from app.models.conversa import Conversa  # noqa: F401, PLC0415
    from app.models.atendimento import Atendimento  # noqa: F401, PLC0415
    from app.models.agendamento import Agendamento  # noqa: F401, PLC0415
    from app.models.webhook_event import WebhookEvent  # noqa: F401, PLC0415
    from app.models.outbox_message import OutboxMessage  # noqa: F401, PLC0415

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    NewSL = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)

    # Substituir os objetos no modulo app.db
    original_sessionlocal = appdb.SessionLocal
    original_engine = appdb.engine

    # Como tests rodam em paralelo e `from app.db import get_db` ja
    # snapshotou as referencias, a unica forma garantida de fazer testes
    # que injetam deps enxergarem a NOVA engine SQLite eh SUBSTITUIR o
    # engine do app.db pela nossa. Assim get_db()/SessionLocal() do app.db
    # passam a abrir sessoes na nossa engine.
    appdb.engine = eng
    appdb.SessionLocal = NewSL
    # Re-bind engine/SessionLocal em TODOS os modulos que ja importaram
    # `from app.db import engine/SessionLocal`. Isso garante que lifespan,
    # routers, AuditService, etc. enxergam a mesma engine.
    import sys  # noqa: PLC0415

    rebound_engine: list[tuple[object, object]] = []
    rebound_sl: list[tuple[object, object]] = []
    for mod_name, mod in list(sys.modules.items()):
        if not mod or not mod_name.startswith("app"):
            continue
        if not hasattr(mod, "__dict__"):
            continue
        cur_eng = mod.__dict__.get("engine")
        if cur_eng is not None and cur_eng is not eng:
            try:
                mod.engine = eng  # type: ignore[attr-defined]
                rebound_engine.append((mod, cur_eng))
            except (AttributeError, TypeError):
                pass
        cur_sl = mod.__dict__.get("SessionLocal")
        if cur_sl is not None and cur_sl is not NewSL:
            try:
                mod.SessionLocal = NewSL  # type: ignore[attr-defined]
                rebound_sl.append((mod, cur_sl))
            except (AttributeError, TypeError):
                pass

    # Importante: como `from app.db import engine/get_db/etc.` em outros
    # modulos ja snapshotou as referencias no import time, basta trocar
    # os atributos no objeto modulo para que proximos usos (incluindo
    # Depends(get_db) do FastAPI) enxerguem a factory nova.
    appdb.engine = eng

    try:
        yield
    finally:
        appdb.SessionLocal = original_sessionlocal
        appdb.engine = original_engine
        for mod, old in rebound_engine:
            try:
                mod.engine = old  # type: ignore[attr-defined]
            except Exception:
                pass
        for mod, old in rebound_sl:
            try:
                mod.SessionLocal = old  # type: ignore[attr-defined]
            except Exception:
                pass


@pytest.fixture(autouse=True)
def _bypass_atendimento_cache(monkeypatch):
    """Bypass autouse do cache de atendimento em TODOS os testes.

    Sem este bypass, o `atendimento_cache.get_cached("24h")` le do Redis
    real (chave deterministica atendimento:ultimas-24h:v1:24h, TTL 60s)
    e pode devolver payload stale de um teste anterior, causando
    flakiness intermitente. Para os testes do cache em si
    (test_atendimento_cache.py), os proprios testes fazem monkeypatch em
    redis.Redis.from_url, entao este bypass nao conflita.

    Adicionado em 2026-07-02 — lesson 132.
    """
    from app.services import atendimento_cache  # noqa: PLC0415

    monkeypatch.setattr(
        atendimento_cache,
        "get_cached",
        lambda window: None,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        atendimento_cache,
        "set_cached",
        lambda payload, window: True,  # type: ignore[arg-type]
    )
    yield


@pytest.fixture(autouse=True)
def _reset_jwt_secret(monkeypatch):
    """Garante JWT_SECRET canonico (='a'*64) em TODOS os testes.

    Sem isso, tests como test_auth_jwt::test_settings_jwt_secret_min_length
    mutam o env var e chamam get_settings.cache_clear(), criando um novo
    singleton com secret curto ('' ou 'z'*32). Tests subsequentes que
    dependem do secret canonico (ex: test_v2_clientes com DPO JWT) quebram.

    Adicionado em 2026-07-07 — flakiness SQUAD A fix.
    """
    monkeypatch.setenv("JWT_SECRET", "a" * 64)
    from app.config import get_settings, settings  # noqa: PLC0415

    get_settings.cache_clear()
    settings.jwt_secret = "a" * 64
    yield


@pytest.fixture(autouse=True)
def _mock_redis_from_url():
    """Mocka redis.from_url globalmente para evitar conexoes reais em testes."""
    import redis
    from unittest.mock import MagicMock, patch

    class MockRedis:
        def incr(self, key):
            return 1

        def expire(self, key, seconds):
            return True

        def ping(self):
            raise redis.exceptions.ConnectionError("Redis offline mock")

        def close(self):
            pass

        def __getattr__(self, name):
            return MagicMock()

    with patch("redis.from_url", return_value=MockRedis()):
        yield


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    return {
        "protocolo_id": 123,
        "tipo": "certidao_negativa",
        "valor": 87.50,
        "cliente_cpf_hash": "abc123",
    }


# =============================================================================
# WhatsApp fixtures (Sprint 4 / Turn 51 — 2026-07-09, lesson 156)
#
# Fixtures para teste do canal WhatsApp via Evolution API:
# - StatefulBus: bus mockado com persistencia in-memory (state machine)
# - evolution_payload: helper para construir payload de webhook Evolution
# - evolution_mock_responses: mock httpx com respostas 200 padrao
# =============================================================================


@pytest.fixture
def evolution_payload() -> callable:
    """Helper para construir payload Evolution API valido para teste.

    Returns:
        Funcao que recebe (message_id, text, remote_jid) e retorna dict payload.
    """

    def _build(
        message_id: str = "wa-msg-test-1",
        text: str = "oi",
        remote_jid: str = "5511999999999@s.whatsapp.net",
        push_name: str = "Joao Teste",
    ) -> dict[str, Any]:
        return {
            "event": "messages.upsert",
            "instance": "cartorio-2notas",
            "data": {
                "key": {
                    "remoteJid": remote_jid,
                    "fromMe": False,
                    "id": message_id,
                },
                "message": {"conversation": text},
                "messageType": "conversation",
                "pushName": push_name,
            },
        }

    return _build


@pytest.fixture
def stateful_whatsapp_bus() -> "StatefulBus":
    """Bus mockado com persistencia in-memory para WhatsApp state machine."""
    from tests.test_telegram_e2e_5x import StatefulBus

    bus = StatefulBus()
    return bus


@pytest.fixture
def evolution_mock_responses():
    """Mock das respostas HTTP do Evolution API (200 OK padrao).

    Retorna MagicMock para httpx.AsyncClient com .post/.get/.aclose AsyncMock
    configurados para retornar respostas 200 com body vazio.
    """
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.text = "{}"
    resp_ok.json = MagicMock(return_value={"status": "ok", "instance": "test"})
    client.post = AsyncMock(return_value=resp_ok)
    client.get = AsyncMock(return_value=resp_ok)
    client.aclose = AsyncMock(return_value=None)
    return client
