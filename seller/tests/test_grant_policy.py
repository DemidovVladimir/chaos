"""Tests for ``chaos_seller.grant_policy``.

The default decision table MUST stay aligned with
``verticals/cars-pack/skills/seller-cars/SKILL.md`` § "Inquiry-handling
policy". These tests are the executable spec.

The grant policy is now keyed per MCP tool (one entry per
cars-pack@1 tool name, with optional per-argument overrides), not
per-ask. See ``grant_policy.DEFAULT_TOOL_TABLE`` and
``grant_policy.PER_ARG_OVERRIDES``.
"""
from __future__ import annotations


def test_default_grants_match_skill_md() -> None:
    """Every cars-pack@1 tool in seller-cars SKILL.md is reflected in DEFAULT_TOOL_TABLE."""
    assert False, "TODO: implement"


def test_request_vin_always_asks_user() -> None:
    """``decide("request_vin", {}, item)`` returns ASK_USER, never GRANT.

    Hard rule from seller-cars SKILL.md: never auto-share full VIN.
    Only after explicit user approval per buyer.
    """
    assert False, "TODO: implement"


def test_request_pickup_address_requires_user_confirm() -> None:
    """``decide("request_pickup_address", {}, item)`` returns ASK_USER."""
    assert False, "TODO: implement"


def test_request_phone_number_always_denied() -> None:
    """``decide("request_phone_number", {}, item)`` returns DENY regardless of item state."""
    assert False, "TODO: implement"


def test_unknown_tool_denied_with_reason() -> None:
    """A tool not in DEFAULT_TOOL_TABLE returns DENY with reason ``"unknown_tool"``."""
    assert False, "TODO: implement"


def test_request_photos_license_plate_kind_escalates() -> None:
    """``request_photos(kinds=["license_plate"])`` triggers the per-arg override.

    PER_ARG_OVERRIDES escalates this combination to ASK_USER even
    though ``request_photos`` is GRANT by default.
    """
    assert False, "TODO: implement"


def test_request_inspection_report_only_granted_when_pdf_exists() -> None:
    """If ``item.documents`` is empty, ``request_inspection_report`` falls back to DENY."""
    assert False, "TODO: implement"
