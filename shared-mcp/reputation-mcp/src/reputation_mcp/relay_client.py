"""Minimal pynostr-based relay client used by reputation-mcp.

This wraps `pynostr.relay_manager.RelayManager` with synchronous
helpers tuned for short-lived REQ scans and one-shot publishes.
The aggregator queries are read-mostly; we open connections,
collect for a few seconds, and tear down.

We intentionally do not cache events across calls — per CLAUDE.md
Rule 5 (no data custody) reputation-mcp keeps no state between
queries beyond the in-flight request.
"""
from __future__ import annotations

# --- macOS / generic SSL preamble ----------------------------------------
# Python on macOS ships without a CA bundle wired into ssl, so wss://
# handshakes fail with CERTIFICATE_VERIFY_FAILED. Point Python at
# certifi's bundle if it's available. No-op on systems where the CA
# bundle is already wired in (most Linux distros).
import os
try:
    import certifi as _certifi  # noqa: WPS433
    _ca = _certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", _ca)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca)
    os.environ.setdefault("WEBSOCKET_CLIENT_CA_BUNDLE", _ca)
except ImportError:
    pass

import logging
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynostr.event import Event
    from pynostr.filters import Filters

log = logging.getLogger(__name__)


class ReputationRelayClient:
    """Tiny synchronous wrapper around pynostr's RelayManager.

    Construct with a list of `wss://...` relay URLs. The constructor
    opens connections eagerly so callers can fail fast when DNS or
    TLS is broken.
    """

    def __init__(
        self,
        relays: list[str],
        *,
        timeout_seconds: float = 6.0,
    ) -> None:
        from pynostr.relay_manager import RelayManager  # noqa: WPS433

        if not relays:
            raise ValueError("at least one relay URL required")
        self._relays: list[str] = list(relays)
        self._timeout: float = timeout_seconds
        self._rm = RelayManager(timeout=timeout_seconds)
        for r in self._relays:
            self._rm.add_relay(r)
        # Eager connect so DNS / TLS errors surface at construction.
        self._rm.run_sync()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query_events(
        self,
        filters: list["Filters"],
        timeout_seconds: float | None = None,
    ) -> list["Event"]:
        """Open a REQ subscription, collect for `timeout_seconds`, dedupe.

        Returns events in arrival order, deduplicated by `event.id`.
        """
        from pynostr.filters import FiltersList  # noqa: WPS433

        wait = self._timeout if timeout_seconds is None else timeout_seconds
        sub_id = uuid.uuid4().hex[:16]
        self._rm.add_subscription_on_all_relays(sub_id, FiltersList(filters))

        deadline = time.monotonic() + wait
        seen: set[str] = set()
        results: list["Event"] = []
        while time.monotonic() < deadline:
            self._rm.run_sync()
            while self._rm.message_pool.has_events():
                msg = self._rm.message_pool.get_event()
                ev = msg.event
                if ev.id in seen:
                    continue
                seen.add(ev.id)
                results.append(ev)
            time.sleep(0.1)

        return results

    def publish_event(self, event: "Event") -> None:
        """Publish a signed event and pump the relay manager briefly.

        We do not block on relay-side OK confirmations because pynostr
        0.6.2 doesn't expose a clean "wait for OK from N relays" API;
        instead we run two pump cycles to give the message a fair
        chance to land on every connected relay.
        """
        if not getattr(event, "sig", None):
            raise ValueError("event must be signed before publish")
        self._rm.publish_event(event)
        # Two pump cycles ~= 1.2s, enough for fast public relays.
        for _ in range(2):
            self._rm.run_sync()
            time.sleep(0.6)

    def close(self) -> None:
        """Close all connections.

        pynostr 0.6.2's `RelayManager.close_all_relay_connections()`
        is the canonical teardown; if that's missing on the installed
        version we fall back to closing each relay individually.
        """
        try:
            self._rm.close_all_relay_connections()
        except AttributeError:
            for relay in getattr(self._rm, "relays", {}).values():
                try:
                    relay.close()
                except Exception:  # noqa: BLE001
                    pass

    # Context-manager sugar for callers that want one-shot use.
    def __enter__(self) -> "ReputationRelayClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------


def filter_for_pubkey_tag(
    *,
    kinds: list[int],
    pubkey_hex: str,
    limit: int = 500,
) -> "Filters":
    """Build a Filters object that matches `kind in kinds` and `#p == pubkey`.

    pynostr 0.6.2's Filters has no first-class tag-filter helper; we
    use `add_arbitrary_tag` to set the `#p` filter (the one-character
    "p" is what NIP-01 uses on the wire).
    """
    from pynostr.filters import Filters  # noqa: WPS433

    f = Filters(kinds=kinds, limit=limit)
    f.add_arbitrary_tag("p", [pubkey_hex])
    return f


def filter_for_event_tag(
    *,
    kinds: list[int],
    event_id_hex: str,
    limit: int = 200,
) -> "Filters":
    """Build a Filters object matching `#e == event_id`."""
    from pynostr.filters import Filters  # noqa: WPS433

    f = Filters(kinds=kinds, limit=limit)
    f.add_arbitrary_tag("e", [event_id_hex])
    return f


def filter_for_authors(
    *,
    kinds: list[int],
    authors: list[str],
    limit: int = 200,
) -> "Filters":
    """Build a Filters object matching `kind in kinds` from `authors`."""
    from pynostr.filters import Filters  # noqa: WPS433

    return Filters(kinds=kinds, authors=authors, limit=limit)
