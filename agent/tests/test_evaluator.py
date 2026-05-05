"""Tests for ``chaos_agent.evaluator``.

Hard red flags MUST auto-suppress; the rubric here is the executable
form of the seeking-cars SKILL.md § "Evaluation rubric".
"""

from __future__ import annotations

import pytest


def test_hard_red_flag_overpriced() -> None:
    """A listing priced > 1.5× market median is auto-suppressed."""
    pytest.skip("not yet implemented")
def test_hard_red_flag_underpriced() -> None:
    """A listing priced < 0.6× median raises a HARD_RED flag (do not auto-suppress; price-bait)."""
    pytest.skip("not yet implemented")
def test_hard_red_flag_accident_contradiction() -> None:
    """Tag accident_history=none_known + description "front collision repair" is hard-flagged."""
    pytest.skip("not yet implemented")
def test_hard_red_flag_pubkey_under_seven_days() -> None:
    """A listing from a pubkey < 7 days old AND no prior listings AND no badge is hard-flagged."""
    pytest.skip("not yet implemented")
def test_soft_red_flag_short_description() -> None:
    """A description ≤ 100 chars produces a soft red flag."""
    pytest.skip("not yet implemented")
def test_soft_red_flag_owners_three_plus() -> None:
    """``owners`` tag ≥ 3 produces a soft red flag."""
    pytest.skip("not yet implemented")
def test_green_flag_verified_seller_badge() -> None:
    """A verified-offering agent badge on the listing produces a green flag."""
    pytest.skip("not yet implemented")
def test_inquiry_grant_policy_denies_vin_full_without_user() -> None:
    """The seeking agent never auto-shares the user's VIN-equivalent PII to a counterparty.

    This mirrors the offering agent test of the same name. Confirms the
    seeking agent side enforces the same hard rule from the other direction:
    no PII outbound without explicit user approval.
    """
    pytest.skip("not yet implemented")
def test_buyer_pii_never_in_outgoing_inquiry() -> None:
    """Seeking agent's name, phone, address never end up in the rumor content."""
    pytest.skip("not yet implemented")
def test_evaluator_skips_market_comp_when_offline() -> None:
    """When ``market_comp`` is None, price-related branches return no flag rather than crashing."""
    pytest.skip("not yet implemented")