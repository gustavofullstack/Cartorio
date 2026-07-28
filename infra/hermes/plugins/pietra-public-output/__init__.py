"""Hermes hook registration for Pietra's public-output policy."""

from __future__ import annotations

from typing import Any

from .public_output_guard import sanitize_public_reply


def _transform_public_output(
    response_text: str = "",
    platform: Any = "",
    **_: Any,
) -> str | None:
    """Replace contaminated Feishu finals; leave private/programmatic surfaces alone."""
    platform_name = str(getattr(platform, "value", platform) or "").strip().lower()
    if platform_name != "feishu":
        return None
    sanitized = sanitize_public_reply(response_text).text
    return sanitized if sanitized != response_text else None


def register(ctx: Any) -> None:
    """Register the official final-output hook exposed by Hermes."""
    ctx.register_hook("transform_llm_output", _transform_public_output)
