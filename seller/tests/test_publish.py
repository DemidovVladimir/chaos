"""Tests for ``chaos_seller.publish``.

Day-1 tests focus on the build + PoW + publish pipeline. Each test
is currently a stub that asserts ``False`` so a fresh checkout fails
loud — Week-2 fills them in.
"""

from __future__ import annotations

import pytest


def test_publish_signs_correctly() -> None:
    """A built kind-30402 event has a valid Schnorr signature.

    Validates: Schnorr signature against the seller's pubkey,
    presence of all required cars-pack tags, and the CRITICAL absence
    of any ``image`` tag (AGENTS.md rule 2).
    """
    pytest.skip("not yet implemented")
def test_pow_mine_meets_difficulty() -> None:
    """``mine_pow(raw, bits=20)`` produces an event id with ≥ 20 leading zeros.

    Also asserts the ``nonce`` tag is present and well-formed.
    """
    pytest.skip("not yet implemented")
def test_publish_no_image_tag_ever() -> None:
    """Property test: across many random Item fixtures, no event has an ``image`` tag.

    AGENTS.md rule 2 forbids image tags or public photo URLs. This is
    the single most important invariant of the seller plugin and
    deserves a property test, not just a happy-path test.
    """
    pytest.skip("not yet implemented")
def test_publish_mcp_and_pack_tags_present() -> None:
    """Every published event MUST include ``["mcp", <https url>]`` and ``["pack", "cars-pack@1"]``."""
    pytest.skip("not yet implemented")
def test_publish_pow_below_minimum_fails() -> None:
    """``publish.publish`` refuses an event whose PoW is < SellerConfig.publish.pow_min_bits."""
    pytest.skip("not yet implemented")
@pytest.mark.skip(reason="Requires live relay — promote to integration tests")
def test_publish_to_live_relay_round_trip() -> None:
    """Publish → re-fetch round-trip on a real relay (skipped by default)."""
    pytest.skip("not yet implemented")