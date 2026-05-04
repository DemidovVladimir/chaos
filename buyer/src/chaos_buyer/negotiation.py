"""Buyer-side negotiation: market-comp-driven counter drafting.

Per ``verticals/cars-pack/skills/buyer-cars/SKILL.md`` § "Negotiation drafting":

- For a clean car, start at median - 5%.
- For a soft-red-flag car, start at median - 15%.
- Cap at 5 rounds per item.

Same protocol-level invariants as the seller side
(``PROTOCOL.md`` § "Negotiation rounds"): max 5 rounds, ≤ 1000
chars per offer, ≤ 50,000 chars per match.

The user's explicit confirmation is required for any acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

DEFAULT_MAX_ROUNDS = 5
DEFAULT_MAX_CHARS_PER_OFFER = 1_000
DEFAULT_MAX_CHARS_PER_MATCH = 50_000


class Stance(str, Enum):
    """How aggressive the suggested offer should be."""

    FAIR = "fair"        # median - 5%
    LOW = "low"          # median - 15% (used when soft red flags exist)
    HIGH = "high"        # median; used when seller has strong green flags


@dataclass(frozen=True, slots=True)
class Offer:
    """One offer.

    Attributes:
        actor: ``"buyer"`` or ``"seller"``.
        amount_cents: Integer cents in the listing's currency.
        currency: ISO 4217 currency code.
        conditions: Free-text conditions, sanitized via
                    ``input_safety`` if from seller.
        timestamp: Unix seconds.
    """

    actor: str
    amount_cents: int
    currency: str
    conditions: str
    timestamp: int


@dataclass(slots=True)
class Match:
    """All offers exchanged for a (item, seller) pair.

    Attributes:
        item_id: The listing.
        seller_pubkey: The seller's pubkey hex.
        offers: Time-ordered list of offers.
        closed: True after accept / reject ends the match.
    """

    item_id: str
    seller_pubkey: str
    offers: list[Offer] = field(default_factory=list)
    closed: bool = False

    def round(self) -> int:
        """Return the round number the next offer would be (1-indexed)."""
        return len(self.offers) + 1


def draft_counter(
    *,
    median_cents: int,
    soft_flags: int,
    stance: Stance | None = None,
) -> int:
    """Draft a counter-offer in cents.

    Args:
        median_cents: ``market_comp`` median for the item's bucket.
        soft_flags: Number of soft red flags raised by the evaluator.
        stance: Override stance. When ``None``, derived from
                ``soft_flags`` (≥ 1 → ``LOW``, else ``FAIR``).

    Returns:
        Suggested offer in cents. The user can adjust before sending.

    Raises:
        ValueError: if ``median_cents`` is non-positive.
    """
    raise NotImplementedError("negotiation.draft_counter not implemented")


def can_send_offer(
    match: Match,
    new_offer: Offer,
    *,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_chars_per_offer: int = DEFAULT_MAX_CHARS_PER_OFFER,
    max_chars_per_match: int = DEFAULT_MAX_CHARS_PER_MATCH,
) -> tuple[bool, str]:
    """Check protocol invariants before adding an offer.

    Args:
        match: Current match state.
        new_offer: Candidate offer.

    Returns:
        ``(ok, reason)``.
    """
    raise NotImplementedError("negotiation.can_send_offer not implemented")
