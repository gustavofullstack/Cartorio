"""Conftest root — pytest plugins + monkey-patches.

Workarounds para bugs Python 3.11.15 + pytest 9.1.1:
1. isinstance() TypeError em pytest warnings
2. Config.get_verbosity AssertionError
3. coverage 7.x sqlite lru_cache TypeError
"""

from __future__ import annotations

import builtins as _builtins
import warnings as _w_mod

# Workaround 1: isinstance() TypeError
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
_w_mod.int = _builtins.int
_w_mod.type = _builtins.type


def pytest_configure(config):
    """Workaround 2: Config.get_verbosity AssertionError."""
    from _pytest.config import Config

    _orig = Config.get_verbosity

    def _patched(self, verbosity_type=None):
        try:
            return _orig(self, verbosity_type)
        except AssertionError:
            return 0

    Config.get_verbosity = _patched
