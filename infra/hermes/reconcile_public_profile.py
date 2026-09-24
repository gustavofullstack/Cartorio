"""Reconcile persisted Hermes config to the canonical Cartorio profile.

The data volume outlives Swarm tasks. Merely updating the image/template does
not correct old verbose display flags or missing platform toolsets, so every
boot merges the required public-channel policy while preserving unrelated
pairing, provider and channel state.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

PLUGIN_NAME = "pietra-public-output"


def _merge_required(
    persisted: dict[str, Any],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    """Overlay canonical mappings recursively while retaining unrelated keys."""
    for key, canonical_value in canonical.items():
        persisted_value = persisted.get(key)
        if isinstance(canonical_value, dict) and isinstance(persisted_value, dict):
            _merge_required(persisted_value, canonical_value)
        elif isinstance(canonical_value, dict):
            persisted[key] = _merge_required({}, canonical_value)
        else:
            persisted[key] = canonical_value
    return persisted


def reconcile_public_profile(
    config: dict[str, Any],
    canonical: dict[str, Any] | None = None,
    installed_skills: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return canonical required keys plus preserved unrelated persisted state."""
    if canonical is not None:
        _merge_required(config, canonical)

    display = config.setdefault("display", {})
    display.update(
        {
            "tool_progress": "off",
            "tool_progress_command": False,
            "interim_assistant_messages": False,
            "show_commentary": False,
            "show_reasoning": False,
            "busy_input_mode": "queue",
            "busy_text_mode": "queue",
            "busy_ack_enabled": False,
            "busy_steer_ack_enabled": False,
            "long_running_notifications": False,
            "background_process_notifications": "off",
        }
    )
    display.setdefault("runtime_footer", {})["enabled"] = False
    feishu = display.setdefault("platforms", {}).setdefault("feishu", {})
    feishu.update(
        {
            "tool_progress": "off",
            "streaming": False,
            "interim_assistant_messages": False,
            "long_running_notifications": False,
            "busy_ack_detail": False,
            "busy_steer_ack_enabled": False,
            "background_process_notifications": "off",
        }
    )

    config.setdefault("streaming", {}).update({"enabled": False, "transport": "off"})
    config["platform_toolsets"] = {"feishu": ["mcp-cartorio"]}

    # Public runtime topology is an allowlist, not a merge target. Otherwise a
    # stale volume can silently revive API Server, Photon or an arbitrary MCP
    # definition even though the canonical profile removed it.
    canonical_gateway = (canonical or {}).get("gateway", {})
    canonical_platforms = (
        canonical_gateway.get("platforms", {})
        if isinstance(canonical_gateway, dict)
        else {}
    )
    config.setdefault("gateway", {})["platforms"] = {
        "feishu": dict(canonical_platforms.get("feishu", {"enabled": True}))
    }
    canonical_mcp = (canonical or {}).get("mcp_servers", {})
    if isinstance(canonical_mcp, dict) and isinstance(
        canonical_mcp.get("cartorio"), dict
    ):
        config["mcp_servers"] = {"cartorio": dict(canonical_mcp["cartorio"])}

    # Enabled plugins are executable policy, not benign persisted metadata.
    # Fail closed on the public channel instead of reviving old user plugins
    # from the durable volume after an image or config migration.
    config.setdefault("plugins", {})["enabled"] = [PLUGIN_NAME]

    # Feishu is a customer surface: enumerate actual installed skills instead
    # of relying on a wildcard that Hermes may not understand.
    platform_disabled = config.setdefault("skills", {}).setdefault(
        "platform_disabled", {}
    )
    feishu_disabled = platform_disabled.setdefault("feishu", [])
    if not isinstance(feishu_disabled, list):
        feishu_disabled = []
    platform_disabled["feishu"] = sorted(
        {str(name) for name in (*feishu_disabled, *installed_skills) if str(name)}
    )
    return config


def reconcile_file(
    path: Path,
    canonical_path: Path | None = None,
    skills_dir: Path | None = None,
) -> None:
    """Atomically reconcile YAML without broadening file permissions."""
    current = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(current, dict):
        raise ValueError("Hermes config root must be a mapping")
    canonical = None
    if canonical_path is not None:
        canonical = yaml.safe_load(canonical_path.read_text(encoding="utf-8")) or {}
        if not isinstance(canonical, dict):
            raise ValueError("Canonical Hermes config root must be a mapping")
    skills_dir = skills_dir or path.parent / "skills"
    installed_skills = (
        tuple(sorted(child.name for child in skills_dir.iterdir() if child.is_dir()))
        if skills_dir.is_dir()
        else ()
    )
    reconciled = reconcile_public_profile(current, canonical, installed_skills)

    mode = path.stat().st_mode & 0o777
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temporary:
            yaml.safe_dump(reconciled, temporary, allow_unicode=True, sort_keys=False)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: reconcile_public_profile.py PERSISTED_CONFIG CANONICAL_CONFIG SKILLS_DIR"
        )
    reconcile_file(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
