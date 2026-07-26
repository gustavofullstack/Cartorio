"""Channel capability contracts for multichannel gateways (Cartório OS Stage 4 / R3).

Provider truth rules:
- Shared/test Spectrum lines remain allowlisted (LIMITED_INBOUND) even if a
  flag like ALLOW_ALL_INBOUND / PHOTON_ALLOW_ALL_USERS is set — those flags
  only expand access among registered provider users, never open the line to
  the public internet.
- PUBLIC_INBOUND requires a dedicated business line + provider plan that
  documents open inbound.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["imessage", "telegram", "whatsapp", "web"]
InboundScope = Literal["allowlist", "public", "unknown"]
LineType = Literal["shared", "test", "limited", "dedicated", "public", "unknown"]


class ChannelCapabilities(BaseModel):
    """Capability snapshot for a messaging channel/line."""

    platform: Platform
    can_send_text: bool = True
    can_send_media: bool = False
    can_send_poll: bool = False
    inbound_scope: InboundScope
    requires_pairing: bool = False
    public_inbound: bool = False
    line_type: LineType = "unknown"
    notes: str = ""


def resolve_inbound_scope(
    *,
    line_type: str,
    allow_all_inbound: bool = False,
    provider_supports_public: bool = False,
) -> InboundScope:
    """Map line + flags to inbound_scope without inventing public access.

    ALLOW_ALL_INBOUND never upgrades a shared/test line to public.
    """
    normalized = (line_type or "unknown").strip().lower()
    if normalized in {"shared", "test", "limited"}:
        return "allowlist"
    if normalized in {"dedicated", "public"}:
        if allow_all_inbound and provider_supports_public:
            return "public"
        # Dedicated line without explicit provider support stays unknown/allowlist.
        return "allowlist" if not provider_supports_public else "public"
    return "unknown"


def get_channel_capabilities(
    platform: Platform,
    *,
    line_type: str = "shared",
    allow_all_inbound: bool = False,
    provider_supports_public: bool = False,
) -> ChannelCapabilities:
    """Build ChannelCapabilities for a platform/line combination."""
    scope = resolve_inbound_scope(
        line_type=line_type,
        allow_all_inbound=allow_all_inbound,
        provider_supports_public=provider_supports_public,
    )
    normalized_line: LineType
    lt = (line_type or "unknown").strip().lower()
    if lt in {"shared", "test", "limited", "dedicated", "public"}:
        normalized_line = lt  # type: ignore[assignment]
    else:
        normalized_line = "unknown"

    return ChannelCapabilities(
        platform=platform,
        can_send_text=True,
        can_send_media=platform in {"telegram", "whatsapp", "web"},
        can_send_poll=platform in {"telegram", "whatsapp"},
        inbound_scope=scope,
        requires_pairing=platform == "whatsapp",
        public_inbound=scope == "public",
        line_type=normalized_line,
        notes=(
            "shared/test Spectrum lines are LIMITED_INBOUND (provider allowlist)"
            if scope == "allowlist"
            else "public inbound only with dedicated business line + provider support"
        ),
    )


class GatewayHealthContract(BaseModel):
    """Health contract for channel gateways (process ≠ operational)."""

    process_up: bool
    provider_connected: bool
    channel_capability_known: bool
    last_inbound_at: str | None = None
    last_outbound_at: str | None = None
    last_error: str | None = Field(default=None, description="Scrubbed error detail")
    operational: bool = False
    real_e2e: Literal[
        "UNVERIFIED",
        "SYNTHETIC_E2E_PASS",
        "REAL_E2E_PASS",
        "FAILED",
        "BLOCKED_SUI",
    ] = "UNVERIFIED"
