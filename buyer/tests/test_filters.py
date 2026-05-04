"""Tests for ``chaos_buyer.filters``."""
from __future__ import annotations


def test_year_range_to_buckets() -> None:
    """``year_range_to_set(2015, 2020)`` returns the 6 discrete year strings."""
    assert False, "TODO: implement"


def test_price_band_inclusion() -> None:
    """A user-specified price range maps to the canonical band set."""
    assert False, "TODO: implement"


def test_no_filter_emits_full_relay_query() -> None:
    """An empty UserWant still produces a valid ``kinds=[30402]`` filter."""
    assert False, "TODO: implement"


def test_mileage_range_to_bands_overlap() -> None:
    """A range that crosses multiple bands returns every overlapping band."""
    assert False, "TODO: implement"


def test_filter_includes_t_cars() -> None:
    """Every filter MUST include ``"#t": ["cars"]`` so we don't subscribe to all NIP-99."""
    assert False, "TODO: implement"
