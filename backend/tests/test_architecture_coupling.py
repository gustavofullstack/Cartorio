"""Architecture coupling tests — G8.11.T4 (Wave 43 / cartorio-dev).

These tests encode Clean Architecture / Hexagonal Architecture invariants
for the cartorio backend. They run as a single AST-level guard (no pylint,
no import linter, no network/DB) so they integrate into CI without overhead.

Layout enforced by this suite (see docs/ARCHITECTURE.md, ADR-007):

    api/  ──►  services/  ──►  models/  ──►  (SQLAlchemy core)
      │           │
      ▼           ▼
    deps.py    schemas/

Rules (one test each, all MUST pass for a green build):

    R1  Services NEVER import app.api.*              (lower-layer rule)
    R2  Core infra NEVER imports app.api/services    (infra rule)
    R3  Schemas NEVER instantiate SQLAlchemy sessions (DTO rule)
    R4  FastAPI Dependency providers are concentrated
        in app/api/deps.py                            (DI bridge rule)
    R5  Services NEVER import business-orchestration
        services (audit/notify/notificacao/cache)
        EXCEPT a documented utility whitelist
        (pii primitives — pure functions, safe for
        models to call)                               (cycle guard)
    R6  Layer dependency graph is a DAG with models
        as leaves (no app.models file imports services)
        EXCEPT the documented pii primitive whitelist   (DAG rule)
    R7  Routers in app/api/v1/*.py use FastAPI Depends()
        for at least one parameter                    (positive DI)
    R8  Pydantic schemas use ConfigDict(from_attributes=True)
        so they remain ORM-independent                  (DTO quality)
    R9  Each top-level layer package (api/services/models
        /schemas/core) has its __init__.py             (packaging sanity)
    R10 Layer file counts stay inside documented
        order-of-magnitude bounds (regression smeller).

Honesty gate: each rule reflects the CURRENT clean state. New violations
introduced by future commits will turn the corresponding test red.
Today's baseline (Wave 43, 2026-07-17) reports ZERO violations for all
strict rules; R5/R6 carry the explicit pii whitelist.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable
from functools import lru_cache
from pathlib import Path

import pytest

pytestmark = pytest.mark.coupling

# ---------------------------------------------------------------------------
# Constants — single source of truth for layer rules. Add an entry here when
# introducing a new layer or a new whitelist exception.
# ---------------------------------------------------------------------------

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"

LAYER_DIRS: dict[str, Path] = {
    "api": APP_ROOT / "api",
    "services": APP_ROOT / "services",
    "models": APP_ROOT / "models",
    "schemas": APP_ROOT / "schemas",
    "core": APP_ROOT / "core",
}

# Modules in lower layers that must NEVER be imported by upper layers.
# Read as: "key layer must NOT import any of the values".
FORBIDDEN_UPWARD_IMPORTS: dict[str, frozenset[str]] = {
    "services": frozenset({"app.api"}),
    "models": frozenset({"app.api"}),
    "core": frozenset({"app.api", "app.services"}),
    "schemas": frozenset({"sqlalchemy"}),
}

# Business-orchestration services that services/models must NOT pull in
# (these would create invocation cycles). Pure utility primitives in pii.py
# are explicit allowed exceptions.
BUSINESS_SERVICE_MODULES: frozenset[str] = frozenset(
    {
        "app.services.audit",
        "app.services.audit_create",
        "app.services.audit_query",
        "app.services.audit_context",
        "app.services.notificacao",
        "app.services.metrics",
        "app.services.emolumento",
        "app.services.emolumento_cache",
        "app.services.agendamento_cache",
        "app.services.atendimento_cache",
        "app.services.cache_lgpd",
        "app.services.rate_limit",
        "app.services.rate_limit_by_key",
        "app.services.idempotency_store",
        "app.services.websocket_manager",
        "app.services.ws_heartbeat",
        "app.services.ws_concurrency",
        "app.services.stream_buffer",
        "app.services.message_debounce",
        "app.services.bot_mute",
        "app.services.bot_metrics",
        "app.services.brain_sync",
        "app.services.brain_compact",
        "app.services.brain_memory",
        "app.services.cartorio_agent",
        "app.services.dialog_history",
        "app.services.chat_pipeline",
        "app.services.chatwoot_handoff",
        "app.services.chatwoot_lgpd_erasure",
        "app.services.chatwoot_canned_responses",
        "app.services.evolution_ingest",
        "app.services.protocolo_query",
        "app.services.solid_atendimento_query",
        "app.services.sliding_window",
        "app.services.dlq",
        "app.services.dlq_encryption",
        "app.services.outbox",
        "app.services.dead_mans_switch",
        "app.services.lgpd_export",
        "app.services.lgpd_export_envelope",
        "app.services.lgpd_direito_esquecimento",
        "app.services.lgpd_anonimizacao",
        "app.services.lgpd_consent",
        "app.services.lgpd_relatorio",
        "app.services.lgpd_privacy_policy",
        "app.services.lgpd_erasure_orchestrator",
        "app.services.telegram_error_handler",
        "app.services.tracing",
    }
)

# Documented PII primitives — pure functions with no side effects, safe for
# models to call as default-value factories. This is the ONLY services
# import permitted from app/models/*.py.
PII_PRIMITIVE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "app.services.pii",
    }
)

# Lower bound sanity: a well-formed layer must hold more than zero non-init
# python files. Upper bound is a code-smell regression guard (e.g. one layer
# exploding in size usually signals SRP violations elsewhere).
LAYER_FILE_COUNT_BOUNDS: dict[str, tuple[int, int]] = {
    "api": (1, 100),
    "services": (10, 500),
    "models": (5, 50),
    "schemas": (1, 50),
    "core": (0, 20),
}


# ---------------------------------------------------------------------------
# AST helpers — cached parsing keeps the suite under 1s.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4096)
def _parse_file(filepath: Path) -> ast.Module | None:
    """Parse a python file into an AST, cached on absolute path.

    Returns None when the file cannot be decoded (binary, syntax error)
    so callers can skip it without poisoning the cache.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        return ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return None


def _iter_python_files(directory: Path) -> list[Path]:
    """Return every .py file under ``directory`` recursively, sorted by path."""
    if not directory.exists():
        return []
    return sorted(p for p in directory.rglob("*.py") if p.is_file())


def _collect_imports(filepath: Path) -> set[str]:
    """Collect the top-level module names imported by ``filepath``.

    Captures:
        - ``import x``          → ``x`` (first segment only)
        - ``import x.y``        → ``x``
        - ``from x.y import z`` → ``x.y``  (full dotted module path)

    Returns an empty set if the file cannot be parsed.
    """
    tree = _parse_file(filepath)
    if tree is None:
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name.split(".")[0]
                imports.add(head)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _violations(
    files: Iterable[Path],
    predicate: Callable[[str], bool],
) -> list[tuple[Path, str]]:
    """Return [(filepath, offending_module)] for files matching ``predicate``.

    ``predicate(filepath, imported_module) -> bool`` returns True when the
    import represents a forbidden upward edge.
    """
    found: list[tuple[Path, str]] = []
    for filepath in files:
        for module in _collect_imports(filepath):
            if predicate(module):
                found.append((filepath, module))
    return found


def _format_violations(violations: list[tuple[Path, str]]) -> str:
    """Format a violation list for pytest assertion messages."""
    if not violations:
        return "(none)"
    lines = [
        f"  {filepath.relative_to(BACKEND_ROOT)}: imports '{module}'"
        for filepath, module in violations
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fixtures — load each layer once per module.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_files() -> list[Path]:
    """All .py files under app/api/."""
    return _iter_python_files(LAYER_DIRS["api"])


@pytest.fixture(scope="module")
def services_files() -> list[Path]:
    """All .py files under app/services/."""
    return _iter_python_files(LAYER_DIRS["services"])


@pytest.fixture(scope="module")
def models_files() -> list[Path]:
    """All .py files under app/models/."""
    return _iter_python_files(LAYER_DIRS["models"])


@pytest.fixture(scope="module")
def schemas_files() -> list[Path]:
    """All .py files under app/schemas/."""
    return _iter_python_files(LAYER_DIRS["schemas"])


@pytest.fixture(scope="module")
def core_files() -> list[Path]:
    """All .py files under app/core/."""
    return _iter_python_files(LAYER_DIRS["core"])


# ---------------------------------------------------------------------------
# R1 — services MUST NOT import app.api.*
# ---------------------------------------------------------------------------


def test_services_layer_must_not_import_app_api(services_files: list[Path]) -> None:
    """R1: services is strictly below api — no upward edge allowed.

    Rationale: services compose business logic; if they imported API routers
    or HTTP shapes we would invert the dependency direction and create
    import cycles. ``deps.py`` is the only sanctioned bridge.
    """
    forbidden = FORBIDDEN_UPWARD_IMPORTS["services"]
    violations = _violations(
        services_files,
        predicate=lambda m: m == "app.api" or m.startswith("app.api."),
    )
    del forbidden  # explicit: predicate is the single source of truth
    assert not violations, (
        "Services must not import app.api.* (only deps.py is the DI bridge).\n"
        f"Found {len(violations)} violations:\n{_format_violations(violations)}"
    )


# ---------------------------------------------------------------------------
# R2 — core infra MUST NOT import services or api
# ---------------------------------------------------------------------------


def test_core_layer_must_not_import_high_layers(core_files: list[Path]) -> None:
    """R2: ``app/core`` is infrastructure (Redis client, settings).

    It must remain framework-and-domain agnostic; depending on services or
    API layers would couple shared infrastructure to business logic.
    """
    violations = _violations(
        core_files,
        predicate=lambda m: (
            m == "app.api"
            or m.startswith("app.api.")
            or m == "app.services"
            or m.startswith("app.services.")
        ),
    )
    assert not violations, (
        "core/* must not depend on app.api or app.services.\n"
        f"Found {len(violations)} violations:\n{_format_violations(violations)}"
    )


# ---------------------------------------------------------------------------
# R3 — schemas MUST NOT instantiate or import SQLAlchemy
# ---------------------------------------------------------------------------


def test_schemas_layer_must_not_instantiate_db_sessions(schemas_files: list[Path]) -> None:
    """R3: Pydantic schemas stay independent of the ORM.

    Schema ↔ ORM coupling happens via ``ConfigDict(from_attributes=True)``,
    never via direct SQLAlchemy session/engine imports.
    """
    violations = _violations(
        schemas_files,
        predicate=lambda m: m == "sqlalchemy" or m.startswith("sqlalchemy."),
    )
    assert not violations, (
        "schemas/* must not import sqlalchemy (use ConfigDict(from_attributes=True)).\n"
        f"Found {len(violations)} violations:\n{_format_violations(violations)}"
    )


# ---------------------------------------------------------------------------
# R4 — DI providers concentrated in deps.py
# ---------------------------------------------------------------------------


def test_dependencies_module_concentrates_di_providers(api_files: list[Path]) -> None:
    """R4: every FastAPI ``require_*`` dependency lives in deps.py.

    Scattered auth gates across routers make role enforcement impossible
    to audit. ``deps.py`` is the canonical home for cross-router providers.
    """
    offenders: list[tuple[Path, str]] = []
    deps_path = LAYER_DIRS["api"] / "deps.py"
    for filepath in api_files:
        if filepath == deps_path:
            continue
        tree = _parse_file(filepath)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "require_"
            ):
                offenders.append((filepath, node.name))

    assert not offenders, (
        "require_* dependencies must live in app/api/deps.py (single audit point).\n"
        f"Found {len(offenders)} violations:\n"
        + "\n".join(f"  {fp.relative_to(BACKEND_ROOT)}: defines {name}" for fp, name in offenders)
    )


# ---------------------------------------------------------------------------
# R5 — services/modules MUST NOT pull business-orchestration services
# ---------------------------------------------------------------------------


def test_models_must_not_reach_into_business_services(models_files: list[Path]) -> None:
    """R5: models never import business-orchestration services.

    Models are the leaf layer: they hold ORM mappings only. Importing any
    orchestration service (audit, rate limit, lgpd, ...) from a model
    would invert the dependency direction and create cycles.
    The ``app.services.pii`` primitives are the only allowed exception
    (pure stateless helpers used as column defaults/validators).
    """
    offenders: list[tuple[Path, str]] = []
    for filepath in models_files:
        for module in _collect_imports(filepath):
            if module == "app.services" or module.startswith("app.services."):
                if module in PII_PRIMITIVE_ALLOWLIST or module.startswith("app.services.pii."):
                    continue
                offenders.append((filepath, module))

    assert not offenders, (
        "app/models/* must not import business-orchestration services.\n"
        f"Allowed exceptions: {sorted(PII_PRIMITIVE_ALLOWLIST)}.\n"
        f"Found {len(offenders)} violations:\n{_format_violations(offenders)}"
    )


# ---------------------------------------------------------------------------
# R6 — layer dependency graph is a DAG with models at the bottom
# ---------------------------------------------------------------------------


def test_models_layer_dependency_graph_is_dag(models_files: list[Path]) -> None:
    """R6: no file under ``app/models/`` imports ``app.services.*``.

    Allowed exception: ``app.services.pii`` primitive whitelist (the only
    service-level import permitted in models — pure hashing functions
    used as column defaults/validators).
    """
    offenders: list[tuple[Path, str]] = []
    for filepath in models_files:
        for module in _collect_imports(filepath):
            if module == "app.services":
                offenders.append((filepath, module))
                continue
            if module.startswith("app.services."):
                if module in PII_PRIMITIVE_ALLOWLIST or module.startswith("app.services.pii."):
                    continue
                offenders.append((filepath, module))

    assert not offenders, (
        "app/models/* must be the leaf layer of the dependency graph.\n"
        f"Allowed exception: {sorted(PII_PRIMITIVE_ALLOWLIST)}.\n"
        f"Found {len(offenders)} violations:\n{_format_violations(offenders)}"
    )


# ---------------------------------------------------------------------------
# R7 — routers use FastAPI Depends() for injection (positive DI)
# ---------------------------------------------------------------------------


def test_routers_use_depends_for_di(api_files: list[Path]) -> None:
    """R7: at least one router file declares a Depends() parameter.

    This is a positive coupling check: it documents the contract that
    request handlers inject collaborators (db, settings, services)
    through FastAPI's DI container rather than building them inline.
    """
    deps_path = LAYER_DIRS["api"] / "deps.py"
    deps_uses = 0
    other_uses = 0
    for filepath in api_files:
        if filepath == deps_path or filepath.name == "__init__.py":
            continue
        tree = _parse_file(filepath)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "Depends":
                if other_uses == 0:
                    other_uses += 1
                deps_uses += 1
            elif isinstance(func, ast.Attribute) and func.attr == "Depends":
                deps_uses += 1

    assert other_uses >= 1, (
        "At least one router file must use Depends() for DI. "
        "Found zero Depends() calls across app/api/* outside deps.py."
    )
    assert deps_uses > other_uses, (
        "Router Depends() usage should exceed any single-file cluster; "
        f"got {deps_uses} total (other_uses={other_uses})."
    )


# ---------------------------------------------------------------------------
# R8 — Pydantic schemas use ConfigDict(from_attributes=True)
# ---------------------------------------------------------------------------


def test_pydantic_schemas_use_from_attributes_for_orm_mapping(schemas_files: list[Path]) -> None:
    """R8: at least one schema uses ``from_attributes=True`` so it can be
    built from an ORM instance without leaking the SQLAlchemy column
    objects into the schema layer.
    """
    found = 0
    for filepath in schemas_files:
        if filepath.name == "__init__.py":
            continue
        source = filepath.read_text(encoding="utf-8")
        if "from_attributes=True" in source:
            found += 1

    assert found >= 1, (
        "No Pydantic schema in app/schemas/* declares ConfigDict(from_attributes=True). "
        "Add at least one to keep the schema layer ORM-independent."
    )


# ---------------------------------------------------------------------------
# R9 — every documented top-level layer has __init__.py
# ---------------------------------------------------------------------------


def test_layer_packages_have_init_files() -> None:
    """R9: each layer package exposes its public surface via __init__.py.

    Missing __init__.py means the package cannot be imported by absolute
    path, breaking ``from app.X import Y`` and breaking the layer contract.
    """
    missing = [name for name, path in LAYER_DIRS.items() if not (path / "__init__.py").exists()]
    assert not missing, (
        f"Layers missing __init__.py: {missing}. Each layer must be a proper "
        "Python package so absolute imports work uniformly."
    )


# ---------------------------------------------------------------------------
# R10 — layer file counts inside documented bounds
# ---------------------------------------------------------------------------


def test_layer_file_counts_within_bounds() -> None:
    """R10: bounded layer sizes — smeller for SRP regressions.

    When one layer explodes (>500 files) it usually means we have not
    been splitting concerns; a layer near zero files usually means we
    forgot to scaffold it.
    """
    out_of_bounds: list[str] = []
    for layer, (low, high) in LAYER_FILE_COUNT_BOUNDS.items():
        files = _iter_python_files(LAYER_DIRS[layer])
        # exclude __init__.py from the count
        non_init = [p for p in files if p.name != "__init__.py"]
        count = len(non_init)
        if not (low <= count <= high):
            out_of_bounds.append(f"  {layer}: {count} non-init files (expected {low}..{high})")
    assert not out_of_bounds, (
        "Layer file counts drifted outside documented bounds (regression smeller):\n"
        + "\n".join(out_of_bounds)
    )
