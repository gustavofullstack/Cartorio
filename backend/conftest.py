"""Conftest root — pytest plugins + monkey-patches.

Workarounds para bugs Python 3.11.15 + pytest 9.1.1:
1. isinstance() TypeError em pytest warnings
2. Config.get_verbosity AssertionError (coerce global_level to int)
3. coverage 7.x sqlite lru_cache TypeError (NAO usar cov no terminal final)
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
    """Workaround 2: Config.get_verbosity coerce verbose + auto-set all sub verbosity."""
    from _pytest.config import Config

    _orig = Config.get_verbosity

    def _patched(self, verbosity_type=None):
        try:
            v = self.getoption("verbose", default=0)
            if not isinstance(v, int):
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    v = 0
            if verbosity_type is None:
                return v
            ini_name = Config._verbosity_ini_name(verbosity_type)
            if ini_name not in self._parser._inidict:
                return v
            level = self.getini(ini_name)
            if level == Config._VERBOSITY_INI_DEFAULT:
                return v
            try:
                return int(level)
            except (TypeError, ValueError):
                return v
        except AssertionError:
            return 0

    Config.get_verbosity = _patched
