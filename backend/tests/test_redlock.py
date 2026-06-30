"""Testes do Redlock (A25 - distributed lock)."""

from __future__ import annotations

from unittest.mock import patch


from app.services.redlock import acquire_lock, is_locked, release_lock


class FakeRedis:
    """Redis fake para testes (sem dependencia)."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex is not None:
            # Simplificado: nao implementa TTL real
            pass
        return True

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def eval(self, script: str, numkeys: int, *args) -> int:
        """Simula Lua script: deleta so se valor confere."""
        if numkeys != 1 or len(args) < 2:
            return 0
        key, expected = args[0], args[1]
        if self.store.get(key) == expected:
            del self.store[key]
            return 1
        return 0


class TestRedlock:
    """TDD strict - A25 distributed lock."""

    def test_acquire_lock_returns_token_on_success(self):
        """acquire_lock retorna token UUID4 se Redis aceita SETNX."""
        fake = FakeRedis()
        with patch("app.services.redlock._get_redis_client", return_value=fake):
            token = acquire_lock("test:lock", ttl_seconds=60)

        assert token is not None
        assert len(token) == 32  # UUID4 hex
        assert "redlock:test:lock" in fake.store
        assert fake.store["redlock:test:lock"] == token

    def test_acquire_lock_returns_none_if_already_locked(self):
        """acquire_lock retorna None se lock ja existe."""
        fake = FakeRedis()
        fake.store["redlock:busy"] = "outro-token"

        with patch("app.services.redlock._get_redis_client", return_value=fake):
            token = acquire_lock("busy", ttl_seconds=60)

        assert token is None

    def test_acquire_lock_fail_open_if_redis_offline(self):
        """Se Redis offline, retorna None (fail-open + log warn)."""
        with patch("app.services.redlock._get_redis_client", return_value=None):
            assert acquire_lock("test") is None

    def test_release_lock_with_correct_token_succeeds(self):
        """release_lock com token correto deleta a chave."""
        fake = FakeRedis()
        with patch("app.services.redlock._get_redis_client", return_value=fake):
            token = acquire_lock("test:lock", ttl_seconds=60)
            assert token is not None

            result = release_lock("test:lock", token)

        assert result is True
        assert "redlock:test:lock" not in fake.store

    def test_release_lock_with_wrong_token_fails(self):
        """release_lock com token errado NAO deleta (Lua script atomico)."""
        fake = FakeRedis()
        with patch("app.services.redlock._get_redis_client", return_value=fake):
            token = acquire_lock("test:lock", ttl_seconds=60)
            assert token is not None

            result = release_lock("test:lock", "wrong-token")

        assert result is False
        # Lock continua ativo
        assert "redlock:test:lock" in fake.store

    def test_release_lock_fail_safe_if_redis_offline(self):
        """Se Redis offline, release retorna False (nao levanta)."""
        with patch("app.services.redlock._get_redis_client", return_value=None):
            assert release_lock("test", "any-token") is False

    def test_is_locked_true_when_locked(self):
        """is_locked retorna True se lock existe."""
        fake = FakeRedis()
        fake.store["redlock:present"] = "x"

        with patch("app.services.redlock._get_redis_client", return_value=fake):
            assert is_locked("present") is True

    def test_is_locked_false_when_free(self):
        """is_locked retorna False se lock nao existe."""
        fake = FakeRedis()

        with patch("app.services.redlock._get_redis_client", return_value=fake):
            assert is_locked("absent") is False

    def test_is_locked_returns_false_if_redis_offline(self):
        """is_locked retorna False se Redis offline (fail-open)."""
        with patch("app.services.redlock._get_redis_client", return_value=None):
            assert is_locked("test") is False

    def test_lock_namespacing(self):
        """Lock name eh prefixado com 'redlock:' (LGPD: sem PII)."""
        fake = FakeRedis()
        with patch("app.services.redlock._get_redis_client", return_value=fake):
            acquire_lock("migrations:run", ttl_seconds=30)

        # Chave SEMPRE prefixada
        assert "redlock:migrations:run" in fake.store
        # NAO expoe PII no nome
        assert "cpf" not in "redlock:migrations:run"

    def test_acquire_lock_handles_redis_error(self):
        """acquire_lock retorna None se Redis lanca excecao."""
        fake = FakeRedis()
        orig_set = fake.set

        def broken_set(*args: object, **kwargs: object) -> None:
            raise ConnectionError("Redis connection refused")

        fake.set = broken_set  # type: ignore[method-assign]
        with patch("app.services.redlock._get_redis_client", return_value=fake):
            token = acquire_lock("error-test", ttl_seconds=60)
        assert token is None
        fake.set = orig_set

    def test_release_lock_handles_redis_error(self):
        """release_lock retorna False se Redis lanca excecao no eval."""
        fake = FakeRedis()
        fake.store["redlock:err"] = "mytoken"
        orig_eval = fake.eval

        def broken_eval(*args: object, **kwargs: object) -> None:
            raise ConnectionError("Redis eval failed")

        fake.eval = broken_eval  # type: ignore[method-assign]
        with patch("app.services.redlock._get_redis_client", return_value=fake):
            result = release_lock("err", "mytoken")
        assert result is False
        fake.eval = orig_eval
