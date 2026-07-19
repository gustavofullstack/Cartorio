"""G8.04.T4 — Parse + validate Traefik routing: LobeChat → multi OpenClaw nodes.

Valida o artifact file-provider em
``infra/traefik/lobechat-openclaw-routing-g8.yaml`` (ou dict equivalente):

- routers obrigatórios: ``lobechat``, ``openclaw-pool``
- services obrigatórios: ``lobechat``, ``openclaw-pool``, ``openclaw-a``, ``openclaw-b``
- openclaw-pool deve ser weighted (a+b) **ou** primary/fallback explícito
- sem secrets (tokens, API keys, passwords, sk-*, bearer longos)

API:
- ``parse_yaml_or_dict(source)`` → dict normalizado
- ``validate_routing(config)`` → ``RoutingValidationResult``
- ``load_default_template()`` → dict do YAML versionado no monorepo

Modified by Gustavo Almeida — G8.04.T4 Wave 32.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover — PyYAML is a project dep via venv
    yaml = None  # type: ignore[assignment]

# Nomes canônicos exigidos pelo artifact G8.04.T4.
REQUIRED_ROUTERS: frozenset[str] = frozenset({"lobechat", "openclaw-pool"})
REQUIRED_SERVICES: frozenset[str] = frozenset(
    {"lobechat", "openclaw-pool", "openclaw-a", "openclaw-b"}
)
OPENCLAW_NODE_SERVICES: frozenset[str] = frozenset({"openclaw-a", "openclaw-b"})

# Caminho relativo à raiz do monorepo.
DEFAULT_TEMPLATE_REL = Path("infra/traefik/lobechat-openclaw-routing-g8.yaml")

# Padrões de secret — config Traefik NÃO deve carregar tokens/API keys.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(api[_-]?key|password|secret|token|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}"),
    re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

# Chaves YAML cujo valor nunca deve parecer secret (defesa em profundidade).
_SUSPICIOUS_KEY_RE = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|authorization|private[_-]?key|credential)"
)


@dataclass(frozen=True, slots=True)
class RoutingValidationResult:
    """Resultado de validação do routing Traefik (sem secrets)."""

    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    routers: tuple[str, ...] = field(default_factory=tuple)
    services: tuple[str, ...] = field(default_factory=tuple)
    openclaw_mode: str = ""  # weighted | failover | unknown | missing

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def find_repo_root(start: Path | None = None) -> Path:
    """Sobe diretórios até achar monorepo Cartorio (backend/ + infra/)."""
    cur = (start or Path(__file__).resolve()).resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if (candidate / "backend").is_dir() and (candidate / "infra").is_dir():
            return candidate
    # Fallback: backend/app/services → parents[3] = repo
    return Path(__file__).resolve().parents[3]


def parse_yaml_or_dict(source: str | Path | dict[str, Any] | bytes) -> dict[str, Any]:
    """Parse YAML string/path/bytes **ou** aceita dict já carregado.

    Args:
        source: path, YAML text, bytes, ou dict.

    Returns:
        dict com a árvore Traefik (tipicamente com chave top-level ``http``).

    Raises:
        TypeError: tipo não suportado.
        ValueError: YAML inválido, vazio, ou não-mapping.
        RuntimeError: PyYAML indisponível.
    """
    if isinstance(source, dict):
        return dict(source)

    text: str
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    elif isinstance(source, bytes):
        text = source.decode("utf-8")
    elif isinstance(source, str):
        # Path existente vs YAML inline.
        p = Path(source)
        if len(source) < 4096 and ("\n" not in source or source.endswith((".yaml", ".yml"))):
            if p.is_file():
                text = p.read_text(encoding="utf-8")
            else:
                text = source
        else:
            text = source
    else:
        raise TypeError(f"unsupported source type: {type(source)!r}")

    if not text.strip():
        raise ValueError("empty YAML / config source")

    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML is required to parse Traefik routing YAML")

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:  # type: ignore[union-attr]
        raise ValueError(f"invalid YAML: {exc}") from exc

    if data is None:
        raise ValueError("empty YAML document")
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping, got {type(data).__name__}")
    return data


def load_default_template(repo_root: Path | None = None) -> dict[str, Any]:
    """Carrega o YAML template versionado em infra/traefik/."""
    root = repo_root or find_repo_root()
    path = root / DEFAULT_TEMPLATE_REL
    if not path.is_file():
        raise FileNotFoundError(f"default template missing: {path}")
    return parse_yaml_or_dict(path)


def _http_section(config: dict[str, Any]) -> dict[str, Any]:
    http = config.get("http")
    if http is None:
        return {}
    if not isinstance(http, dict):
        return {}
    return http


def _mapping_keys(section: Any) -> list[str]:
    if not isinstance(section, dict):
        return []
    return [str(k) for k in section.keys()]


def _detect_openclaw_mode(services: dict[str, Any]) -> str:
    """Detecta weighted vs failover no service openclaw-pool."""
    pool = services.get("openclaw-pool")
    if not isinstance(pool, dict):
        return "missing"
    if "weighted" in pool and isinstance(pool["weighted"], dict):
        return "weighted"
    if "failover" in pool and isinstance(pool["failover"], dict):
        return "failover"
    # loadBalancer único não é multi-node
    if "loadBalancer" in pool:
        return "unknown"
    return "unknown"


def _weighted_refs(pool: dict[str, Any]) -> set[str]:
    weighted = pool.get("weighted")
    if not isinstance(weighted, dict):
        return set()
    entries = weighted.get("services") or []
    names: set[str] = set()
    if isinstance(entries, list):
        for item in entries:
            if isinstance(item, dict) and item.get("name"):
                names.add(str(item["name"]))
    return names


def _failover_refs(pool: dict[str, Any]) -> set[str]:
    fo = pool.get("failover")
    if not isinstance(fo, dict):
        return set()
    names: set[str] = set()
    for key in ("service", "fallback"):
        val = fo.get(key)
        if isinstance(val, str) and val:
            names.add(val)
    return names


def _service_has_server_url(svc: Any) -> bool:
    if not isinstance(svc, dict):
        return False
    lb = svc.get("loadBalancer")
    if not isinstance(lb, dict):
        return False
    servers = lb.get("servers")
    if not isinstance(servers, list) or not servers:
        return False
    for s in servers:
        if isinstance(s, dict) and isinstance(s.get("url"), str) and s["url"].strip():
            return True
    return False


def _collect_secret_hits(obj: Any, path: str = "") -> list[str]:
    """Varre árvore em busca de padrões de secret (valores e chaves suspeitas)."""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            child_path = f"{path}.{key}" if path else key
            if _SUSPICIOUS_KEY_RE.search(key):
                # Chave suspeita só é erro se o valor for string não-vazia "secreta".
                if isinstance(v, str) and v.strip() and not v.startswith("$"):
                    # Permitir referências @file / nomes de middleware sem valor secret.
                    if len(v) > 8 and not v.endswith("@file") and not v.endswith("@docker"):
                        hits.append(f"suspicious key with value at {child_path}")
            hits.extend(_collect_secret_hits(v, child_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            hits.extend(_collect_secret_hits(item, f"{path}[{i}]"))
    elif isinstance(obj, str):
        for pat in _SECRET_PATTERNS:
            if pat.search(obj):
                hits.append(f"secret-like value at {path or 'root'}")
                break
    return hits


def validate_routing(config: dict[str, Any] | str | Path) -> RoutingValidationResult:
    """Valida config Traefik LobeChat → multi OpenClaw.

    Checks:
    1. ``http.routers`` contém ``lobechat`` e ``openclaw-pool``
    2. ``http.services`` contém ``lobechat``, ``openclaw-pool``, ``openclaw-a``, ``openclaw-b``
    3. Cada router aponta para um service existente
    4. ``openclaw-pool`` é weighted (refs a+b) ou failover (primary+fallback)
    5. ``openclaw-a`` / ``openclaw-b`` têm loadBalancer.servers[].url
    6. Nenhum secret embutido

    Args:
        config: dict ou path/YAML parseável.

    Returns:
        RoutingValidationResult (ok + errors/warnings; sem secrets no payload).
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = parse_yaml_or_dict(config) if not isinstance(config, dict) else config
    except (TypeError, ValueError, RuntimeError, OSError) as exc:
        return RoutingValidationResult(
            ok=False,
            errors=(f"parse error: {exc}",),
            openclaw_mode="missing",
        )

    if not isinstance(data, dict):
        return RoutingValidationResult(
            ok=False,
            errors=("config must be a mapping",),
            openclaw_mode="missing",
        )

    http = _http_section(data)
    if not http:
        errors.append("missing http section")

    routers_raw = http.get("routers") if http else None
    services_raw = http.get("services") if http else None

    router_names = _mapping_keys(routers_raw)
    service_names = _mapping_keys(services_raw)
    routers_set = set(router_names)
    services_set = set(service_names)

    missing_routers = sorted(REQUIRED_ROUTERS - routers_set)
    if missing_routers:
        errors.append(f"missing required routers: {', '.join(missing_routers)}")

    missing_services = sorted(REQUIRED_SERVICES - services_set)
    if missing_services:
        errors.append(f"missing required services: {', '.join(missing_services)}")

    # Router → service binding
    if isinstance(routers_raw, dict):
        for rname, rcfg in routers_raw.items():
            if not isinstance(rcfg, dict):
                errors.append(f"router {rname!r} must be a mapping")
                continue
            if "rule" not in rcfg:
                errors.append(f"router {rname!r} missing rule")
            svc = rcfg.get("service")
            if not svc:
                errors.append(f"router {rname!r} missing service")
            elif isinstance(svc, str) and svc not in services_set:
                # Permitir @file / @docker externos sem exigir definição local.
                if "@" not in svc:
                    errors.append(f"router {rname!r} references unknown service {svc!r}")

    services_map: dict[str, Any] = services_raw if isinstance(services_raw, dict) else {}
    mode = _detect_openclaw_mode(services_map)

    if mode == "weighted":
        pool = services_map.get("openclaw-pool") or {}
        refs = _weighted_refs(pool if isinstance(pool, dict) else {})
        missing_nodes = OPENCLAW_NODE_SERVICES - refs
        if missing_nodes:
            errors.append(
                "openclaw-pool weighted must reference openclaw-a and openclaw-b; "
                f"missing: {', '.join(sorted(missing_nodes))}"
            )
        for name in refs:
            if name not in services_set:
                errors.append(f"weighted ref {name!r} not defined under http.services")
    elif mode == "failover":
        pool = services_map.get("openclaw-pool") or {}
        refs = _failover_refs(pool if isinstance(pool, dict) else {})
        if "openclaw-a" not in refs or "openclaw-b" not in refs:
            # Aceitar qualquer primary/fallback desde que ambos nós existam e
            # estejam referenciados — preferimos nomes canônicos.
            if not refs:
                errors.append("openclaw-pool failover missing service/fallback")
            else:
                warnings.append(
                    "openclaw-pool failover refs are non-canonical "
                    f"(expected openclaw-a/openclaw-b, got {sorted(refs)})"
                )
                if not OPENCLAW_NODE_SERVICES.issubset(services_set):
                    errors.append("failover mode still requires services openclaw-a and openclaw-b")
        for name in refs:
            if name not in services_set and "@" not in name:
                errors.append(f"failover ref {name!r} not defined under http.services")
    elif mode == "missing":
        if "openclaw-pool" in services_set or "openclaw-pool" in REQUIRED_SERVICES:
            errors.append("openclaw-pool service missing or empty")
    else:
        errors.append(
            "openclaw-pool must use weighted (openclaw-a/b) or failover (primary/fallback)"
        )

    for node in sorted(OPENCLAW_NODE_SERVICES):
        if node in services_map and not _service_has_server_url(services_map[node]):
            errors.append(f"service {node!r} missing loadBalancer.servers[].url")

    if "lobechat" in services_map and not _service_has_server_url(services_map["lobechat"]):
        # LobeChat pode ser só UI — ainda assim exigimos URL de backend.
        errors.append("service 'lobechat' missing loadBalancer.servers[].url")

    # Secret hygiene
    secret_hits = _collect_secret_hits(data)
    if secret_hits:
        # Não ecoar o valor — só path/classificação.
        errors.append(f"secret-like content forbidden ({len(secret_hits)} hit(s))")
        for h in secret_hits[:5]:
            warnings.append(h)

    ok = not errors
    return RoutingValidationResult(
        ok=ok,
        errors=tuple(errors),
        warnings=tuple(warnings),
        routers=tuple(sorted(router_names)),
        services=tuple(sorted(service_names)),
        openclaw_mode=mode if mode != "missing" or ok else mode,
    )


__all__ = [
    "DEFAULT_TEMPLATE_REL",
    "OPENCLAW_NODE_SERVICES",
    "REQUIRED_ROUTERS",
    "REQUIRED_SERVICES",
    "RoutingValidationResult",
    "find_repo_root",
    "load_default_template",
    "parse_yaml_or_dict",
    "validate_routing",
]
