"""Tests for ``chaos_agent.subscribe``."""

from __future__ import annotations

import pytest


def test_dedupes_by_event_id_across_relays() -> None:
    """Two relays delivering the same event id surface only once."""
    pytest.skip("not yet implemented")
def test_seen_cache_survives_restart() -> None:
    """An id cached on disk is suppressed by ``has_seen`` after restart."""
    pytest.skip("not yet implemented")
def test_iter_events_drains_message_pool() -> None:
    """The iterator empties the message pool before blocking."""
    pytest.skip("not yet implemented")