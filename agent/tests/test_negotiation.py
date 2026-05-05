"""Tests for ``chaos_agent.negotiation``."""

from __future__ import annotations

import pytest


def test_round_cap_at_5() -> None:
    """A sixth offer is rejected by ``can_send_offer``."""
    pytest.skip("not yet implemented")
def test_offer_chars_capped_at_1000() -> None:
    """An offer with > 1000-char ``conditions`` is rejected."""
    pytest.skip("not yet implemented")
def test_match_total_chars_capped() -> None:
    """Cumulative ``conditions`` chars > 50,000 close the match."""
    pytest.skip("not yet implemented")
def test_draft_counter_uses_low_when_soft_flags() -> None:
    """``draft_counter`` defaults to ``LOW`` (median - 15%) when ``soft_flags >= 1``."""
    pytest.skip("not yet implemented")
def test_draft_counter_uses_fair_when_clean() -> None:
    """``draft_counter`` defaults to ``FAIR`` (median - 5%) when ``soft_flags == 0``."""
    pytest.skip("not yet implemented")