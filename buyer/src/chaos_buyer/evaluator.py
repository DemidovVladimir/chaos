"""Apply the buyer-cars rubric to an incoming listing.

The full rubric lives in
``verticals/cars-pack/skills/buyer-cars/SKILL.md`` § "Evaluation rubric".
This module is its executable form. Phase 2 implements the hard red
flags that are computable from listing metadata alone; soft + green
flags + photo-derived flags wait until Phase 3 wires the MCP photo
path.

Photo bytes reach this module as inline ``ImageContent`` blocks
returned from ``mcp_call_tool("request_photos", ...)`` on the seller's
MCP server — never as a URL, never as a remote fetch. EXIF /
perceptual-hash / reverse-image-check operates on those decoded
bytes directly.

CLAUDE.md rule 6 forbids commercial vehicle-history providers — this
module never reaches out to any third-party data broker. All inputs
come from on-network listings (via ``market_comp``) or local files
(VIN structural decode, perceptual photo hash).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FlagSeverity(str, Enum):
    """Severity bucket for a single rubric finding."""

    HARD_RED = "hard_red"
    SOFT_RED = "soft_red"
    GREEN = "green"


@dataclass(frozen=True, slots=True)
class Flag:
    """One rubric finding.

    Attributes:
        severity: ``HARD_RED`` triggers auto-suppression.
        code: Short slug (e.g. ``"price_above_1.5x_median"``).
        message: One-line human-readable rationale.
    """

    severity: FlagSeverity
    code: str
    message: str


@dataclass(slots=True)
class Verdict:
    """Aggregate verdict for one listing.

    Attributes:
        flags: All flags raised, in evaluation order.
    """

    flags: list[Flag] = field(default_factory=list)

    def has_hard_red_flag(self) -> bool:
        """True if any flag is ``HARD_RED``.

        Returns:
            Boolean.
        """
        return any(f.severity is FlagSeverity.HARD_RED for f in self.flags)

    def soft_red_count(self) -> int:
        """Return the count of soft red flags."""
        return sum(1 for f in self.flags if f.severity is FlagSeverity.SOFT_RED)

    def green_count(self) -> int:
        """Return the count of green flags."""
        return sum(1 for f in self.flags if f.severity is FlagSeverity.GREEN)


def evaluate(event: object, *, market_comp: object | None = None,
             trust_graph: object | None = None) -> Verdict:
    """Run the rubric against one NIP-99 event.

    Args:
        event: A ``pynostr.event.Event`` (typed loosely so this
               module doesn't import pynostr at import time).
        market_comp: Optional ``market_comp`` MCP handle. When None,
                     price-related flags are skipped (soft-degrade).
        trust_graph: Optional trust-graph handle for badge / mute-list
                     checks.

    Returns:
        A populated ``Verdict``.
    """
    raise NotImplementedError("evaluator.evaluate not implemented")


def evaluate_text_signals(description: str, tags: dict[str, str]) -> list[Flag]:
    """Cheap text-only checks (no MCPs, no photos).

    Implements the subset of the rubric we can run before any photo
    bytes have arrived via MCP:

    - ``accident_history=none_known`` but description contains
      collision / repair language.
    - Description ≤ 100 chars (soft).
    - Owners ≥ 3 in the tags (soft).

    Args:
        description: The listing's ``content`` field, AFTER passing
                     through ``input_safety.sanitize``.
        tags: Flat ``key -> value`` mapping of the event's tags.

    Returns:
        List of flags raised.
    """
    raise NotImplementedError("evaluator.evaluate_text_signals not implemented")


def evaluate_seller_reputation(pubkey_hex: str, *, seen_cache_path: object) -> list[Flag]:
    """Reputation-from-history flags.

    Implements the rubric rules that depend on the local cache of
    previously-seen listings (seller's pubkey age, prior listing
    count, prior listings closing cleanly).

    Args:
        pubkey_hex: Seller's pubkey.
        seen_cache_path: Path to the seen-cache JSONL.

    Returns:
        List of flags raised.
    """
    raise NotImplementedError("evaluator.evaluate_seller_reputation not implemented")
