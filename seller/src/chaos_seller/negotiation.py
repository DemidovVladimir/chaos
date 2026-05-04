"""Negotiation state machine for the seller side.

Per ``PROTOCOL.md`` § "Negotiation rounds":

- Max 5 rounds per (item, counterparty)
- Max 1000 chars per offer message
- Max 50,000 chars total per match
- Acceptance always requires explicit user confirmation in the same
  session.

Per ``verticals/cars-pack/skills/seller-cars/SKILL.md`` § "Negotiation flow",
the seller compares the buyer's offer against the user's
``bid_min_cents``, escalates to the user, and replies with one of
``accept`` / ``counter`` / ``reject``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

DEFAULT_MAX_ROUNDS = 5
DEFAULT_MAX_CHARS_PER_OFFER = 1_000
DEFAULT_MAX_CHARS_PER_MATCH = 50_000


class Action(str, Enum):
    """Reply actions for a negotiation step."""

    ACCEPT = "accept"
    COUNTER = "counter"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class Offer:
    """One offer (incoming or outgoing).

    Attributes:
        actor: ``"buyer"`` or ``"seller"``.
        amount_cents: Integer cents in the listing's currency.
        currency: ISO 4217 currency code.
        conditions: Free-text conditions (e.g.
                    ``"subject to inspection at <shop>"``); sanitized
                    via input_safety on incoming offers.
        timestamp: Unix seconds.
    """

    actor: str
    amount_cents: int
    currency: str
    conditions: str
    timestamp: int


@dataclass(slots=True)
class Match:
    """All offers exchanged for one (item, counterparty) pair.

    Attributes:
        item_id: The listing.
        counterparty_pubkey: The buyer's pubkey hex.
        offers: Time-ordered list of offers.
        closed: True when accept / reject ends the match.
    """

    item_id: str
    counterparty_pubkey: str
    offers: list[Offer] = field(default_factory=list)
    closed: bool = False

    def round(self) -> int:
        """Return the round number (1-indexed) the next offer would be.

        Returns:
            Integer round count.
        """
        return len(self.offers) + 1

    def total_chars(self) -> int:
        """Return the total chars across all offer ``conditions`` fields.

        Returns:
            Integer character count.
        """
        return sum(len(o.conditions) for o in self.offers)


def can_accept_offer(
    match: Match,
    new_offer: Offer,
    *,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_chars_per_offer: int = DEFAULT_MAX_CHARS_PER_OFFER,
    max_chars_per_match: int = DEFAULT_MAX_CHARS_PER_MATCH,
) -> tuple[bool, str]:
    """Check the protocol invariants before adding a new offer.

    Args:
        match: The current match state.
        new_offer: The candidate offer.
        max_rounds: Hard round cap.
        max_chars_per_offer: Per-offer char cap.
        max_chars_per_match: Cumulative char cap for the match.

    Returns:
        ``(ok, reason)``: ``ok`` is True if the offer is admissible.
        ``reason`` carries the rejection reason when not admissible.
    """
    raise NotImplementedError("negotiation.can_accept_offer not implemented")


def evaluate_buyer_offer(
    match: Match,
    new_offer: Offer,
    *,
    bid_min_cents: int | None,
) -> Action:
    """Suggest an action given a new buyer offer.

    Per the seller-cars SKILL.md flow:

    - If ``new_offer.amount_cents >= bid_min_cents``: prompt the
      user to accept / counter / reject.
    - Else: notify the user; default reply on inaction is to counter
      at the listed price.
    - If round limit is reached: must be ``REJECT``.

    Args:
        match: The current match state.
        new_offer: A buyer-actor offer to evaluate.
        bid_min_cents: The user's hard floor; ``None`` means no floor
                       was set and EVERYTHING must escalate.

    Returns:
        The suggested ``Action``. The actual reply still requires
        explicit user confirmation downstream.
    """
    raise NotImplementedError("negotiation.evaluate_buyer_offer not implemented")
