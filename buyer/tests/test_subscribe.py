"""Tests for ``chaos_buyer.subscribe``."""
from __future__ import annotations


def test_dedupes_by_event_id_across_relays() -> None:
    """Two relays delivering the same event id surface only once."""
    assert False, "TODO: implement"


def test_seen_cache_survives_restart() -> None:
    """An id cached on disk is suppressed by ``has_seen`` after restart."""
    assert False, "TODO: implement"


def test_iter_events_drains_message_pool() -> None:
    """The iterator empties the message pool before blocking."""
    assert False, "TODO: implement"
