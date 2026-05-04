"""Tests for ``chaos_buyer.inquiry``."""
from __future__ import annotations


def test_inquiry_payload_shape_matches_protocol() -> None:
    """The built payload exactly matches the shape in PROTOCOL.md § "1-to-1 messaging".

    Specifically: rumor type is ``mcp_inquiry_open``; payload carries
    ``item_id``, ``buyer_pubkey``, ``session_token``, and ``asks``;
    no seller MCP URL is embedded (that comes from the listing's
    ``["mcp", url]`` tag).
    """
    assert False, "TODO: implement"


def test_inquiry_pow_skipped() -> None:
    """The published gift-wrap (kind 1059) does NOT carry a NIP-13 nonce tag.

    Per PROTOCOL.md, encrypted DMs skip PoW because they're encrypted
    and rate-limited per-sender.
    """
    assert False, "TODO: implement"


def test_inquiry_payload_max_chars_capped() -> None:
    """``free_text`` longer than 1000 chars is truncated."""
    assert False, "TODO: implement"


def test_inquiry_session_token_minimum_entropy() -> None:
    """``build_payload`` raises on a ``session_token`` shorter than 16 bytes of entropy."""
    assert False, "TODO: implement"


def test_inquiry_does_not_carry_seller_mcp_url() -> None:
    """The rumor payload must NOT include the seller's MCP HTTP+SSE URL.

    The buyer learns it from the matched NIP-99 listing's
    ``["mcp", url]`` tag, never from the rumor itself.
    """
    assert False, "TODO: implement"
