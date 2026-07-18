"""Testes A20 v2 — Redlock distributed lock (cenarios canonicos do briefing).

Cobre os 6 cenarios:
    C1. Lock adquirido + release funciona
    C2. 2 callers competing — timeout=0 (fail-fast) vs timeout=10 (espera)
    C3. Lock auto-expira apos TTL (TTL via fakeredis)
    C4. Context manager propaga exception + lock release em finally
    C5. Mock Alembic env.py verifica acquire/release
    C6. Mock seed script idem

Usa fakeredis + lupa (lua support) para testes realistas.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import fakeredis
import pytest

from app.services.redlock import (
    EXIT_LOCK_BUSY,
    LockBusyError,
    _key,
    acquire_lock,
    is_locked,
    redlock,
    release_lock,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fake_redis():
    """fakeredis instance — suporta SET NX EX, EVAL, EXISTS, TTL."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def patched_redis(fake_redis):
    """Patch _get_redis_client para retornar fakeredis."""
    with patch("app.services.redlock._get_redis_client", return_value=fake_redis):
        yield fake_redis


# ============================================================================
# C1: Lock adquirido + release funciona
# ============================================================================


class TestCenario1AcquireRelease:
    """C1: fluxo canonico — acquire retorna token, release libera."""

    def test_acquire_retorna_token_e_release_libera(self, patched_redis):
        """C1.1: acquire_lock retorna token, release_lock remove do Redis."""
        token = acquire_lock("c1:test", ttl_seconds=60)
        assert token is not None
        assert len(token) == 32  # UUID4 hex

        # Lock esta presente no Redis
        key = _key("c1:test")
        assert patched_redis.exists(key) == 1
        assert patched_redis.get(key) == token

        # Release remove
        assert release_lock("c1:test", token) is True
        assert patched_redis.exists(key) == 0

    def test_redlock_context_manager_libera_no_exit(self, patched_redis):
        """C1.2: `with redlock(...):` adquire e libera no exit normal."""
        key = _key("c1:ctx")
        assert patched_redis.exists(key) == 0

        with redlock("c1:ctx", ttl_seconds=60) as token:
            assert token is not None
            assert patched_redis.exists(key) == 1

        # Apos exit normal: lock liberado
        assert patched_redis.exists(key) == 0

    def test_redlock_yields_token_correto(self, patched_redis):
        """C1.3: token yieldado pelo context manager == token no Redis."""
        with redlock("c1:yield", ttl_seconds=60) as token:
            assert patched_redis.get(_key("c1:yield")) == token


# ============================================================================
# C2: 2 callers competing — timeout=0 vs timeout=10
# ============================================================================


class TestCenario2CompetingCallers:
    """C2: caller 2 espera OU falha rapido dependendo do timeout."""

    def test_timeout_zero_falha_imediato_quando_ocupado(self, patched_redis):
        """C2.1: blocking=False/timeout=0 → caller 2 recebe LockBusyError."""
        # Caller 1 pega o lock
        token1 = acquire_lock("c2:busy", ttl_seconds=60)
        assert token1 is not None

        # Caller 2 tenta com blocking=False → levanta imediatamente
        start = time.monotonic()
        with pytest.raises(LockBusyError) as exc_info:
            with redlock("c2:busy", ttl_seconds=60, blocking=False, timeout=0):
                pass
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # fail-fast (sem espera)
        # Mensagem indica lock ocupado
        assert "ocupado" in str(exc_info.value) or "indisponivel" in str(exc_info.value)

        # Lock do caller 1 ainda ativo (caller 2 NAO sobrescreveu)
        assert patched_redis.get(_key("c2:busy")) == token1

    def test_timeout_positivo_espera_e_adquire(self, patched_redis):
        """C2.2: blocking=True/timeout=5 → caller 2 espera e adquire apos caller 1 liberar."""
        # Caller 1 pega o lock
        token1 = acquire_lock("c2:wait", ttl_seconds=60)
        assert token1 is not None

        # Caller 2 espera ate 5s. Liberamos caller 1 em 0.2s via thread.
        def release_after_delay() -> None:
            time.sleep(0.2)
            release_lock("c2:wait", token1)

        t = threading.Thread(target=release_after_delay, daemon=True)
        t.start()

        start = time.monotonic()
        with redlock("c2:wait", ttl_seconds=60, blocking=True, timeout=5, poll_interval=0.1):
            acquired_at = time.monotonic() - start
        elapsed = time.monotonic() - start

        # Esperou ate ~0.2s e conseguiu
        assert 0.15 < acquired_at < 1.0, f"adquirido em {acquired_at}s (esperado ~0.2s)"
        assert elapsed < 1.0

    def test_timeout_expirado_levanta_LockBusyError(self, patched_redis):
        """C2.3: blocking=True com timeout=0.5 e lock nunca liberado → LockBusyError."""
        token1 = acquire_lock("c2:expire", ttl_seconds=60)
        assert token1 is not None

        start = time.monotonic()
        with pytest.raises(LockBusyError):
            with redlock(
                "c2:expire", ttl_seconds=60, blocking=True, timeout=0.5, poll_interval=0.1
            ):
                pass
        elapsed = time.monotonic() - start

        # Esperou ~0.5s antes de desistir
        assert 0.4 < elapsed < 1.0, f"timeout em {elapsed}s (esperado ~0.5s)"


# ============================================================================
# C3: Lock auto-expira apos TTL (fakeredis TTL)
# ============================================================================


class TestCenario3TTLExpiration:
    """C3: TTL do Redis auto-libera lock se processo morrer."""

    def test_ttl_configurado_no_redis(self, patched_redis):
        """C3.1: SET NX EX aplica TTL correto no Redis."""
        acquire_lock("c3:ttl", ttl_seconds=42)

        # fakeredis implementa TTL — verifica via ttl() command
        ttl = patched_redis.ttl(_key("c3:ttl"))
        # ttl() retorna segundos restantes; pode ser 41 ou 42 dependendo de timing
        assert 39 <= ttl <= 42, f"TTL esperado ~42s, obtido {ttl}s"

    def test_lock_auto_expira_e_novo_caller_consegue(self, fake_redis):
        """C3.2: apos TTL expirar (simulado via delete), novo acquire_lock obtem sucesso."""
        # fakeredis respeita TTL mas NAO dispara expiracao sozinho; simulamos via delete.
        with patch("app.services.redlock._get_redis_client", return_value=fake_redis):
            token1 = acquire_lock("c3:auto", ttl_seconds=60)
            assert token1 is not None

            # Simula TTL expirar (Redis deleta a chave automaticamente)
            fake_redis.delete(_key("c3:auto"))

            # Novo caller consegue
            token2 = acquire_lock("c3:auto", ttl_seconds=60)
            assert token2 is not None
            assert token2 != token1

    def test_release_lock_apos_expiracao_retorna_False(self, patched_redis):
        """C3.3: se lock expirou (delete), release_lock retorna False (nao ha o que deletar)."""
        token = acquire_lock("c3:gone", ttl_seconds=60)
        assert token is not None

        # Simula expiracao
        patched_redis.delete(_key("c3:gone"))

        # Release nao encontra nada para deletar
        assert release_lock("c3:gone", token) is False


# ============================================================================
# C4: Context manager propaga exception + lock release em finally
# ============================================================================


class TestCenario4ExceptionPropagation:
    """C4: exception dentro do bloco NAO vaza lock (release em finally)."""

    def test_exception_propagada_e_lock_liberado(self, patched_redis):
        """C4.1: raise dentro do `with` propaga mas lock e liberado."""
        key = _key("c4:raise")

        class MinhaExcecao(RuntimeError):
            pass

        with pytest.raises(MinhaExcecao, match="boom"):
            with redlock("c4:raise", ttl_seconds=60):
                assert patched_redis.exists(key) == 1
                raise MinhaExcecao("boom")

        # Lock liberado apesar da exception
        assert patched_redis.exists(key) == 0

    def test_lock_nao_liberado_se_token_diferente(self, patched_redis):
        """C4.2: release NAO remove lock de outro caller (Lua script verifica token)."""
        # Caller 1 pega lock
        token1 = acquire_lock("c4:race", ttl_seconds=60)
        assert token1 is not None

        # Caller 2 rouba lock (race defensiva — impossivel com SET NX em prod)
        patched_redis.set(_key("c4:race"), "outro-token", ex=60)

        # Caller 1 tenta release com seu token — Lua script nao deleta
        assert release_lock("c4:race", token1) is False

        # Lock do caller 2 permanece
        assert patched_redis.get(_key("c4:race")) == "outro-token"

    def test_locked_check_pos_exception_mostra_liberado(self, patched_redis):
        """C4.3: apos exception, is_locked retorna False."""
        with pytest.raises(ValueError):
            with redlock("c4:check", ttl_seconds=60):
                assert is_locked("c4:check") is True
                raise ValueError("erro teste")

        assert is_locked("c4:check") is False

    def test_is_locked_retorna_false_quando_exists_levanta_excecao(self, patched_redis):
        """C4.4: is_locked retorna False se Redis lanca excecao no exists()."""
        # Quebra o metodo exists() do fake_redis para levantar ConnectionError
        orig_exists = patched_redis.exists

        def broken_exists(*args: object, **kwargs: object) -> int:
            raise ConnectionError("Redis exists failed")

        patched_redis.exists = broken_exists  # type: ignore[method-assign]
        assert is_locked("c4:exists-broken") is False
        patched_redis.exists = orig_exists  # type: ignore[method-assign]

    def test_redlock_mensagem_offline_quando_redis_indisponivel(self):
        """C4.5: redlock() levanta LockBusyError com mensagem 'indisponivel' se Redis offline."""
        # Simula Redis offline durante acquire (None) E is_locked (None)
        with patch("app.services.redlock._get_redis_client", return_value=None):
            with pytest.raises(LockBusyError) as exc_info:
                with redlock("c4:redis-offline", ttl_seconds=60, blocking=False, timeout=0):
                    pass
            # Mensagem deve indicar Redis indisponivel
            assert "indisponivel" in str(exc_info.value).lower()

    def test_redlock_log_warn_quando_release_falha(self, patched_redis, caplog):
        """C4.6: se release_lock retorna False dentro do context manager, loga warning.

        Cobre a branch `if not released: logger.warning(...)` (linha 201).
        """
        import logging

        from app.services import redlock as redlock_mod

        caplog.set_level(logging.WARNING, logger="app.services.redlock")

        def fake_release(name: str, t: str) -> bool:
            return False

        # Patch ANTES de entrar no context manager (senao acquire conflita)
        with patch.object(redlock_mod, "release_lock", fake_release):
            with redlock("c4:release-fail", ttl_seconds=42):
                # Dentro do context manager, lock foi adquirido
                assert patched_redis.exists(_key("c4:release-fail")) == 1

        # Apos exit: lock AINDA existe (release falhou)
        assert patched_redis.exists(_key("c4:release-fail")) == 1

        # Verifica que warning foi logado
        assert any("NAO foi liberado" in record.message for record in caplog.records), (
            f"Esperado warning de release falho, obtido: {[r.message for r in caplog.records]}"
        )
        assert any("42" in record.message for record in caplog.records), (
            "Warning deve mencionar TTL em segundos"
        )

        # Cleanup: libera o lock manualmente
        from app.services.redlock import _get_redis_client

        r = _get_redis_client()
        if r:
            r.delete(_key("c4:release-fail"))


# ============================================================================
# C5: Mock Alembic env.py verifica acquire/release
# ============================================================================


def _alembic_env_source() -> str:
    """Retorna o source code de backend/alembic/env.py."""
    env_path = Path(__file__).parent.parent / "alembic" / "env.py"
    return env_path.read_text(encoding="utf-8")


class TestCenario5AlembicIntegration:
    """C5: Alembic env.py chama redlock e exit 75 se ocupado.

    Como env.py e executado pelo Alembic CLI (que provê `alembic.context`
    configurado), nao carregamos ele como modulo. Em vez disso:
    - Verificamos o codigo fonte contem as primitivas corretas
    - Validamos a logica via analise do source (regex)
    - O comportamento end-to-end do redlock() e testado em C1-C4
    """

    def test_alembic_env_importa_redlock_context_manager(self):
        """C5.1: env.py importa redlock context manager e LockBusyError/EXIT_LOCK_BUSY."""
        source = _alembic_env_source()
        assert "from app.services.redlock import" in source
        assert "redlock" in source
        assert "LockBusyError" in source
        assert "EXIT_LOCK_BUSY" in source

    def test_alembic_env_define_lock_name_canonico(self):
        """C5.1b: env.py define ALEMBIC_LOCK_NAME = 'alembic:migration'."""
        source = _alembic_env_source()
        assert 'ALEMBIC_LOCK_NAME = "alembic:migration"' in source

    def test_alembic_env_chama_redlock_run_migrations_online(self):
        """C5.1c: env.py chama redlock() com blocking=False timeout=0 e run_migrations."""
        source = _alembic_env_source()
        assert "redlock(" in source
        assert "blocking=False" in source
        assert "timeout=0" in source
        assert "_run_migrations_online_locked" in source

    def test_alembic_env_exit_75_quando_lock_ocupado(self):
        """C5.2: env.py chama sys.exit(EXIT_LOCK_BUSY) em except LockBusyError."""
        source = _alembic_env_source()
        assert "except LockBusyError" in source
        assert "sys.exit(EXIT_LOCK_BUSY)" in source

    def test_alembic_lock_name_nao_expoe_pii(self):
        """C5.3: lock name 'alembic:migration' e LGPD-safe (sem dados pessoais)."""
        source = _alembic_env_source()

        # Extrai valor de ALEMBIC_LOCK_NAME
        import re

        m = re.search(r'ALEMBIC_LOCK_NAME\s*=\s*["\']([^"\']+)["\']', source)
        assert m is not None, "ALEMBIC_LOCK_NAME nao encontrado"
        lock_name = m.group(1)

        # LGPD: lock name NAO deve conter dados pessoais
        forbidden = ["cpf", "rg", "email", "telefone", "nome", "cliente", "pessoa"]
        for word in forbidden:
            assert word not in lock_name.lower(), (
                f"LGPD: lock name '{lock_name}' NAO deve conter '{word}'"
            )

        # Comentario LGPD-safe presente no env.py
        assert "LGPD" in source, "env.py deve documentar abordagem LGPD-safe"

    def test_alembic_offline_mode_nao_adquire_lock(self):
        """C5.4: run_migrations_offline NAO chama redlock (offline mode emite SQL)."""
        source = _alembic_env_source()
        offline_section_start = source.find("def run_migrations_offline")
        online_section_start = source.find("def run_migrations_online")
        offline_body = source[offline_section_start:online_section_start]
        assert "redlock" not in offline_body, (
            "run_migrations_offline NAO deve adquirir redlock (emite SQL, nao conecta)"
        )


# ============================================================================
# C6: Mock seed script verifica acquire/release
# ============================================================================


def _load_seed_module():
    """Carrega backend/scripts/seed_vault_secrets.py como modulo isolated."""
    seed_path = Path(__file__).parent.parent / "scripts" / "seed_vault_secrets.py"
    spec = importlib.util.spec_from_file_location("seed_vault_secrets_under_test", seed_path)
    seed_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_module)  # type: ignore[union-attr]

    # Injeta helper main_with_args para os testes
    def main_with_args(args: object) -> int:
        """Wrapper que injeta args pre-construidos (testes nao precisam de argv real)."""
        original_argv = sys.argv
        sys.argv = [
            "seed_vault_secrets.py",
            *(["--skip-lock"] if getattr(args, "skip_lock", False) else []),
            "--secrets-dir",
            str(getattr(args, "secrets_dir", "/tmp")),
        ]
        try:
            # Bypass argparse via monkeypatch
            orig_parse = seed_module.argparse.ArgumentParser.parse_args  # type: ignore[attr-defined]

            def fake_parse_args(self: object, *a: object, **k: object) -> object:
                return args

            seed_module.argparse.ArgumentParser.parse_args = fake_parse_args  # type: ignore[assignment,attr-defined]
            try:
                return seed_module.main()
            finally:
                seed_module.argparse.ArgumentParser.parse_args = orig_parse  # type: ignore[attr-defined]
        finally:
            sys.argv = original_argv

    seed_module.main_with_args = main_with_args  # type: ignore[attr-defined]
    return seed_module


class TestCenario6SeedIntegration:
    """C6: seed_vault_secrets.py chama redlock e retorna 75 se ocupado."""

    def test_seed_adquire_lock_e_libera(self, patched_redis, monkeypatch):
        """C6.1: seed main() adquire lock, executa seed, libera no exit."""
        seed_module = _load_seed_module()

        # Mocka _run_seed para apenas marcar que foi chamado
        called = {"ran": False}

        def fake_run_seed(args: object) -> int:
            called["ran"] = True
            return 0

        monkeypatch.setattr(seed_module, "_run_seed", fake_run_seed)

        import argparse

        args = argparse.Namespace(dry_run=False, secrets_dir="/tmp", skip_lock=False)
        result = seed_module.main_with_args(args)

        assert result == 0
        assert called["ran"] is True
        # Lock liberado apos execucao
        assert patched_redis.exists(_key("seed:vault_secrets")) == 0

    def test_seed_retorna_75_quando_lock_ocupado(self, patched_redis, monkeypatch):
        """C6.2: seed main() retorna EXIT_LOCK_BUSY (75) quando lock ja ocupado."""
        seed_module = _load_seed_module()

        # Pre-popula lock
        other_token = acquire_lock("seed:vault_secrets", ttl_seconds=60)
        assert other_token is not None

        # _run_seed NAO deve ser chamado
        called = {"ran": False}

        def fake_run_seed(args: object) -> int:
            called["ran"] = True
            return 0

        monkeypatch.setattr(seed_module, "_run_seed", fake_run_seed)

        import argparse

        args = argparse.Namespace(dry_run=False, secrets_dir="/tmp", skip_lock=False)
        result = seed_module.main_with_args(args)

        assert result == EXIT_LOCK_BUSY
        assert called["ran"] is False  # nunca executou seed

    def test_seed_skip_lock_flag_bypassa_lock(self, patched_redis, monkeypatch):
        """C6.3: --skip-lock permite rodar sem redlock (debug local)."""
        seed_module = _load_seed_module()

        # Mesmo com lock ocupado, --skip-lock deve permitir
        other_token = acquire_lock("seed:vault_secrets", ttl_seconds=60)
        assert other_token is not None

        called = {"ran": False}

        def fake_run_seed(args: object) -> int:
            called["ran"] = True
            return 0

        monkeypatch.setattr(seed_module, "_run_seed", fake_run_seed)

        import argparse

        args = argparse.Namespace(dry_run=False, secrets_dir="/tmp", skip_lock=True)
        result = seed_module.main_with_args(args)

        assert result == 0
        assert called["ran"] is True


# ============================================================================
# Testes de constantes/keys
# ============================================================================


class TestConstantesELGPD:
    """Testes das constantes publicas + LGPD safety."""

    def test_exit_code_75_conforme_sysv(self):
        """EXIT_LOCK_BUSY == 75 (EX_TEMPFAIL do BSD sysexits.h)."""
        assert EXIT_LOCK_BUSY == 75

    def test_default_ttl_eh_300_segundos(self, monkeypatch):
        """Default TTL canonico = 300s (5min) para migrations/seed."""
        monkeypatch.delenv("REDIS_LOCK_TTL_SECONDS", raising=False)
        # Reimport modulo para pegar env limpa
        reloaded = importlib.reload(importlib.import_module("app.services.redlock"))
        assert reloaded.DEFAULT_LOCK_TTL_SECONDS == 300

    def test_key_formato_canonico(self):
        """_key('X') == 'cartorio:lock:redlock:X' (formato canonico G8.12.T3)."""
        # safe_name converte : -> _
        assert _key("alembic:migration") == "cartorio:lock:redlock:alembic_migration"
        assert _key("seed:vault_secrets") == "cartorio:lock:redlock:seed_vault_secrets"
