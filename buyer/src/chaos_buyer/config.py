"""Buyer-side configuration loaded from ``~/.chaos/buyer.yaml``.

Holds: relays, identity location, MCP client knobs (timeout, in-flight
call cap, per-response byte cap, allowed pack ids), default REQ filter,
evaluator thresholds, and trust-graph anchor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".chaos" / "buyer.yaml"


@dataclass(frozen=True, slots=True)
class McpConfig:
    """MCP-client knobs.

    The buyer is purely an MCP CLIENT — it dials the seller's
    ``["mcp", url]`` tag over HTTP+SSE, calls ``tools/list`` to
    bootstrap the seller's tool surface, then dispatches per-ask
    ``tools/call`` invocations. There is no buyer-side MCP server
    to bind.
    """

    client_timeout_seconds: float = 30.0
    max_inflight_calls: int = 4
    max_image_bytes_per_response: int = 10 * 1024 * 1024
    pack_whitelist: tuple[str, ...] = ("cars-pack@1",)


@dataclass(frozen=True, slots=True)
class HardRedFlagThresholds:
    """Hard red flag thresholds from buyer-cars SKILL.md."""

    stock_image_similarity: float = 0.92
    price_off_median: float = 0.5  # 50% off in either direction


@dataclass(frozen=True, slots=True)
class SoftRedFlagThresholds:
    """Soft red flag thresholds."""

    stock_image_similarity: float = 0.85


@dataclass(frozen=True, slots=True)
class EvaluatorConfig:
    """Evaluator knobs."""

    hard: HardRedFlagThresholds = field(default_factory=HardRedFlagThresholds)
    soft: SoftRedFlagThresholds = field(default_factory=SoftRedFlagThresholds)
    market_comp_window_days: int = 60


@dataclass(frozen=True, slots=True)
class TrustGraphConfig:
    """Trust graph configuration.

    Per AGENTS.md rule 4 ("Trust signals layered, not centralized"),
    no single signal is decisive. The badge is one input among
    several.
    """

    default_trust_root_pubkey: str = ""
    badge_required_for_evaluation: bool = False


@dataclass(frozen=True, slots=True)
class FiltersConfig:
    """Default filter shape."""

    default: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BuyerConfig:
    """Top-level buyer config."""

    relays: tuple[str, ...]
    mcp: McpConfig = field(default_factory=McpConfig)
    filters: FiltersConfig = field(default_factory=FiltersConfig)
    evaluator: EvaluatorConfig = field(default_factory=EvaluatorConfig)
    trust_graph: TrustGraphConfig = field(default_factory=TrustGraphConfig)
    inbox_dir: Path = Path.home() / ".chaos" / "buyer" / "inbox"

    @classmethod
    def load(cls, path: os.PathLike | None = None) -> BuyerConfig:
        """Load and validate the YAML config.

        Args:
            path: Optional override for the config path.

        Returns:
            A populated, frozen ``BuyerConfig``.

        Raises:
            FileNotFoundError: if no config file exists.
            ValueError: on invalid fields.
        """
        raise NotImplementedError("config.BuyerConfig.load not implemented")

    def assert_valid(self) -> None:
        """Self-check the config against architecture constraints.

        Raises:
            ValueError: e.g. on empty relays or a non-https seller
                MCP URL discovered later when consuming a listing.
        """
        raise NotImplementedError("config.assert_valid not implemented")
