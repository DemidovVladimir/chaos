"""Sign and verify Nostr attestation events.

An attestation is a small Nostr event the seller signs to assert a
fact about a listing — for example "I have a recent inspection PDF
on file" or "the VIN I shared in the encrypted channel is correct".

Buyers' agents verify these signatures against the seller's pubkey
to weight evaluation. The buyer-cars SKILL.md uses this as a green
flag input.

We use ``kind: 30078`` (NIP-78 application-specific data) with a
namespacing ``["d", "chaos:attestation:<topic>"]`` tag so
relays can address them and the buyer can find them by topic.

CLAUDE.md rule 4 ("Trust signals layered, not centralized") — these
attestations are just one input among NIP-58 badges, PoW, and pubkey
reputation. They are NOT a gatekeeper.
"""
from __future__ import annotations

from dataclasses import dataclass

ATTESTATION_KIND = 30078


@dataclass(frozen=True, slots=True)
class Attestation:
    """A signed attestation about a listing.

    Attributes:
        item_id: The listing's ``d`` tag value.
        topic: Free-form topic
               (e.g. ``"inspection_report_present"`` or
               ``"vin_claimed"``).
        body: Short body text. Length-capped at 1 KB.
        seller_pubkey: Seller's pubkey hex.
        signed_event_id: Id of the published kind-30078 event.
    """

    item_id: str
    topic: str
    body: str
    seller_pubkey: str
    signed_event_id: str


def build(item_id: str, topic: str, body: str, *, seller_pubkey_hex: str) -> dict:
    """Assemble the unsigned attestation event dict.

    Args:
        item_id: The listing's ``d`` tag value.
        topic: Topic string.
        body: Plain-text body. Truncated to 1 KB.
        seller_pubkey_hex: Seller's pubkey hex.

    Returns:
        A kind-30078 event dict ready for signing and publishing.

    Raises:
        ValueError: if any field is empty or the body is binary.
    """
    raise NotImplementedError("attestation.build not implemented")


def verify(event: dict, *, expected_seller_pubkey: str) -> bool:
    """Verify a signed attestation.

    Args:
        event: A signed kind-30078 event dict.
        expected_seller_pubkey: Pubkey we expect to have signed
                                (usually the listing's pubkey).

    Returns:
        True if the Schnorr signature is valid AND the event's
        ``pubkey`` matches ``expected_seller_pubkey``.
    """
    raise NotImplementedError("attestation.verify not implemented")
