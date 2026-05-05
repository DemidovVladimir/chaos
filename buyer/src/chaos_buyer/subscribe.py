"""REQ subscription, dedupe, persistent seen-cache.

The subscriber connects to the configured relays, sends the user's
filter set as a REQ message, drains the message pool for matching
events, and dedupes by ``event.id`` across relays. Already-seen
events are persisted at ``~/.chaos/buyer/seen.jsonl`` so a
process restart doesn't notify the user twice.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynostr.event import Event
    from pynostr.relay_manager import RelayManager

DEFAULT_SEEN_PATH = Path.home() / ".chaos" / "buyer" / "seen.jsonl"


def start(rm: RelayManager, sub_id: str, filters: list[dict]) -> None:
    """Open a REQ subscription on every relay in ``rm``.

    Args:
        rm: Live relay manager.
        sub_id: Caller-supplied subscription id.
        filters: List of filter dicts (will be wrapped in a
                 ``pynostr.filters.FiltersList``).
    """
    raise NotImplementedError("subscribe.start not implemented")


def iter_events(
    rm: RelayManager,
    sub_id: str,
    *,
    seen_cache: Path = DEFAULT_SEEN_PATH,
) -> Iterator[Event]:
    """Yield deduplicated events forever.

    Each event is checked against an in-memory LRU and the
    on-disk persistent cache. New events are appended to the
    cache before being yielded.

    Args:
        rm: Live relay manager.
        sub_id: The subscription id used in ``start()``.
        seen_cache: Persistent-cache path. Default
                    ``~/.chaos/buyer/seen.jsonl``.

    Yields:
        Unique ``pynostr.event.Event`` instances.
    """
    raise NotImplementedError("subscribe.iter_events not implemented")


def cache_seen(event_id: str, *, seen_cache: Path = DEFAULT_SEEN_PATH) -> None:
    """Mark ``event_id`` as seen (append to JSONL).

    Args:
        event_id: Hex event id.
        seen_cache: Path to the seen-cache file.
    """
    raise NotImplementedError("subscribe.cache_seen not implemented")


def has_seen(event_id: str, *, seen_cache: Path = DEFAULT_SEEN_PATH) -> bool:
    """Return True if ``event_id`` was previously cached.

    Args:
        event_id: Hex event id.
        seen_cache: Path to the seen-cache file.

    Returns:
        Boolean.
    """
    raise NotImplementedError("subscribe.has_seen not implemented")
