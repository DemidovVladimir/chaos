"""Hermes tool handlers — negotiation-side tools.

``accept_offer`` is the safety-sensitive tool on the buyer side and
MUST refuse to act without explicit user confirmation in the same
session, per AGENTS.md and the buyer-cars SKILL.md hard rule "Never
auto-commit to a purchase."
"""

from __future__ import annotations

import json
from typing import Any


def draft_offer(args: dict, **kwargs: Any) -> str:
    """Suggest a counter-offer via market_comp + soft-flag count.

    Args:
        args: ``{"item_id": "...", "stance": "fair|low|high"?}``.

    Returns:
        JSON with ``amount_cents``, ``currency``, ``rationale``,
        ``median_cents``, ``soft_flag_count``.
    """
    raise NotImplementedError("tools_negotiate.draft_offer not implemented")


def counter_offer(args: dict, **kwargs: Any) -> str:
    """Send a buyer-side counter-offer to the seller.

    Args:
        args: ``{"item_id": "...", "amount_cents": int,
                 "currency": "...", "conditions": "..."}``.

    Returns:
        JSON with the new round number and the published wrap id.
    """
    raise NotImplementedError("tools_negotiate.counter_offer not implemented")


def accept_offer(args: dict, **kwargs: Any) -> str:
    """Accept the seller's most recent offer.

    Refuses to send unless the user has explicitly confirmed in
    this same Hermes session.

    Args:
        args: ``{"item_id": "..."}``.

    Returns:
        JSON with the published acceptance event id, or an error.
    """
    raise NotImplementedError("tools_negotiate.accept_offer not implemented")


def reject_offer(args: dict, **kwargs: Any) -> str:
    """Reject the seller's most recent offer.

    Args:
        args: ``{"item_id": "...", "reason": "..."}``.

    Returns:
        JSON with the published reject event id.
    """
    raise NotImplementedError("tools_negotiate.reject_offer not implemented")


def _ok(payload: dict) -> str:
    """Wrap a success payload as a JSON string."""
    return json.dumps(payload, default=str)


def _err(message: str, **extra: Any) -> str:
    """Wrap an error as a JSON string."""
    return json.dumps({"error": message, **extra}, default=str)
