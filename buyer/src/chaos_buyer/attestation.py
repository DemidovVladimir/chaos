"""Verify Nostr attestation events the seller sends.

Buyer-side counterpart to
``chaos_seller.attestation``. We only ever VERIFY (never
sign) — buyers don't issue attestations, sellers do.
"""
from __future__ import annotations

ATTESTATION_KIND = 30078


def verify(event: dict, *, expected_seller_pubkey: str) -> bool:
    """Verify a signed attestation came from the listed seller.

    Args:
        event: A signed kind-30078 event dict.
        expected_seller_pubkey: Pubkey we expect (usually the
                                listing's pubkey).

    Returns:
        True iff the BIP-340 Schnorr signature is valid AND the
        event's ``pubkey`` matches ``expected_seller_pubkey``.
    """
    raise NotImplementedError("attestation.verify not implemented")


def parse_topic(event: dict) -> str:
    """Extract the topic component from the ``["d", "..."]`` tag.

    The seller writes ``["d", "chaos:attestation:<topic>"]``.

    Args:
        event: A kind-30078 event dict.

    Returns:
        The topic string (everything after the second colon),
        or ``""`` if the d tag isn't shaped this way.
    """
    raise NotImplementedError("attestation.parse_topic not implemented")
