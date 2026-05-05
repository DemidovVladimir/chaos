"""Seller-side configuration loaded from ``~/.chaos/seller.yaml``.

The seller config tells the plugin which relays to talk to, where its
own MCP server lives (so it can include the public URL in NIP-99
``mcp`` tags), what PoW floor to mine, and which tools always need
explicit user confirmation regardless of the default policy.

The file is plain YAML so non-engineers can edit it. Secrets stay in
``~/.chaos/.env`` per AGENTS.md § "Code conventions".
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".chaos" / "seller.yaml"


@dataclass(frozen=True, slots=True)
class McpConfig:
    """MCP-server transport, bind, and public-facing URL.

    ``transport`` is the FastMCP transport (``"sse"`` for HTTP+SSE in
    v1; ``"streamable-http"`` is a future option).
    ``bind`` is what we listen on (e.g. ``0.0.0.0:7501``).
    ``public_url`` is the address peers reach us at (often a tunnel
    such as Cloudflare Tunnel, Tailscale Funnel, or ngrok). We embed
    ``public_url`` in the NIP-99 ``mcp`` tag.
    """

    bind: str
    public_url: str
    transport: str = "sse"


@dataclass(frozen=True, slots=True)
class PublishConfig:
    """Publishing knobs."""

    pow_min_bits: int = 20
    default_currency: str = "EUR"
    default_region: str = ""


@dataclass(frozen=True, slots=True)
class GrantPolicyConfig:
    """Per-tool policy overrides."""

    defaults_from: str = "verticals/cars-pack/skills/seller-cars/SKILL.md"
    always_user_confirm: tuple[str, ...] = (
        "request_vin",
        "request_pickup_address",
        "request_phone_number",
    )


@dataclass(frozen=True, slots=True)
class NegotiationConfig:
    """Negotiation hard limits — enforced both in policy and in code."""

    max_rounds: int = 5
    max_chars_per_offer: int = 1000
    max_chars_per_match: int = 50_000


@dataclass(frozen=True, slots=True)
class SellerConfig:
    """Top-level seller config.

    Use ``SellerConfig.load()`` to parse from YAML. The frozen-
    dataclass shape means downstream code can pass it around without
    worrying about mutation.
    """

    relays: tuple[str, ...]
    mcp: McpConfig
    mcp_url: str
    pack: str = "cars-pack@1"
    publish: PublishConfig = field(default_factory=PublishConfig)
    grant_policy: GrantPolicyConfig = field(default_factory=GrantPolicyConfig)
    negotiation: NegotiationConfig = field(default_factory=NegotiationConfig)
    items_dir: Path = Path.home() / ".chaos" / "items"

    @classmethod
    def load(cls, path: os.PathLike | None = None) -> SellerConfig:
        """Parse the YAML file at ``path`` (default: standard location).

        Args:
            path: Optional override path. Defaults to
                  ``~/.chaos/seller.yaml``.

        Returns:
            A populated, frozen ``SellerConfig``.

        Raises:
            FileNotFoundError: if no config file exists.
            ValueError: if required fields (``relays``, ``mcp``,
                ``mcp_url``) are empty or missing.
        """
        raise NotImplementedError("config.SellerConfig.load not implemented yet")

    def assert_valid(self) -> None:
        """Self-check that values pass the architecture constraints.

        Raises:
            ValueError: if any constraint is violated (empty relays,
                ``pow_min_bits < 16``, public_url is http:// not https://,
                ``pack`` not matching the ``<name>@<version>`` shape).
        """
        raise NotImplementedError("config.assert_valid not implemented yet")
