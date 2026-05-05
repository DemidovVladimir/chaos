"""Hermes tool handlers — negotiation-side tools.

Wraps ``negotiation`` behind the standard Hermes handler shape.
``accept_offer`` is the most safety-sensitive tool in the offering agent
plugin: it MUST refuse to act without an explicit user confirmation
in the same Hermes session, per AGENTS.md and the offering-cars
SKILL.md hard rule "Never auto-accept an offer."
"""

from __future__ import annotations

import json
from typing import Any


def counter_offer(args: dict, **kwargs: Any) -> str:
    """Send a counter-offer in an ongoing negotiation.

    Args:
        args: ``{"item_id": "...", "from_pubkey": "...",
                 "amount_cents": int, "currency": "...",
                 "conditions": "..."}``.

    Returns:
        JSON string with the new round number and the published
        gift-wrap event id, or an error JSON when round / char
        invariants are violated.
    """
    raise NotImplementedError("tools_negotiate.counter_offer not implemented")


def accept_offer(args: dict, **kwargs: Any) -> str:
    """Accept the seeking agent's most recent offer.

    Refuses to send unless the user has explicitly confirmed in
    this same Hermes session. Returns an error if the most recent
    counterparty offer is older than the protocol's expiry rule
    (currently informally: 7 days).

    Args:
        args: ``{"item_id": "...", "from_pubkey": "..."}``.

    Returns:
        JSON string with the published acceptance event id, or an
        error.
    """
    raise NotImplementedError("tools_negotiate.accept_offer not implemented")


def reject_offer(args: dict, **kwargs: Any) -> str:
    """Reject the seeking agent's most recent offer.

    Args:
        args: ``{"item_id": "...", "from_pubkey": "...", "reason": "..."}``.

    Returns:
        JSON string with the published reject event id.
    """
    raise NotImplementedError("tools_negotiate.reject_offer not implemented")


def _ok(payload: dict) -> str:
    """Wrap a success payload as a JSON string."""
    return json.dumps(payload, default=str)


def _err(message: str, **extra: Any) -> str:
    """Wrap an error as a JSON string."""
    return json.dumps({"error": message, **extra}, default=str)
