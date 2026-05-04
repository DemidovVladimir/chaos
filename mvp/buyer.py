"""
buyer.py — weekend MVP buyer agent.

Subcommands:
  python buyer.py keygen           — generate / show your buyer identity
  python buyer.py watch            — subscribe to NIP-99 cars listings,
                                     prompt to DM the seller on each match,
                                     and after the seller's reply offer
                                     to fetch photos + inspection report
                                     via the seller's MCP HTTP+SSE server.

Edit MATCH_FILTER below to change what you're looking for.

After a NIP-99 match the buyer caches the listing's `["mcp", url]`
tag (if present) keyed by seller pubkey. When the seller replies, we
prompt: "fetch photos + inspection now via MCP?" — answering `y`
opens an HTTP+SSE session, runs `tools/list`, calls `view_listing`,
`request_photos`, and `request_inspection_report`, and saves the
returned bytes into `mvp/received/` with SHA-256 verification logging.
"""
from __future__ import annotations

# --- macOS / generic SSL fix --------------------------------------------
# Python on macOS (python.org installer) ships without a CA bundle wired
# into the SSL module, so wss:// handshakes fail with
# "CERTIFICATE_VERIFY_FAILED". Point Python at certifi's bundle (pulled
# in by pynostr already). Safe on Linux too — same root CAs.
import os
try:
    import certifi as _certifi
    _ca = _certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", _ca)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca)
    os.environ.setdefault("WEBSOCKET_CLIENT_CA_BUNDLE", _ca)
except ImportError:
    pass

import queue  # noqa: F401  — documented thread-safety guarantee for rm.message_pool / rm.publish_event; relied on by the pump-thread fix below
import sys
import threading
import time

from pynostr.event import Event, EventKind
from pynostr.encrypted_dm import EncryptedDirectMessage
from pynostr.filters import Filters, FiltersList
from pynostr.key import PrivateKey
from pynostr.relay_manager import RelayManager

from shared import (
    DEFAULT_RELAYS,
    Identity,
    extract_item_id,
    extract_mcp_url,
    render_listing,
)


# Per-seller MCP context cached when we see a NIP-99 listing, so that
# when the seller replies we can prompt the user to MCP-fetch from the
# correct URL + item_id without round-tripping the relay again.
# Map: seller_pubkey_hex → {"mcp_url": str, "item_id": str}
_MCP_CONTEXT: dict[str, dict[str, str]] = {}

# Tracks (seller_pubkey, item_id) pairs we've already MCP-fetched in
# this session, so subsequent replies don't re-prompt. To force a
# refetch (e.g. seller said they uploaded new photos) the buyer can
# run `python mcp_client.py <mcp-url> <item_id>` directly.
_FETCHED: set[tuple[str, str]] = set()


# Hardcode for the MVP. Edit to taste before running.
MATCH_FILTER = Filters(
    kinds=[30402],
    limit=50,
)
# pynostr's Filters doesn't expose tag-filter helpers directly in 0.6.x;
# we add them manually below for cars-pack discovery.
MATCH_FILTER.add_arbitrary_tag("t", ["cars", "mazda"])
# To filter by year, mileage band, etc., add more arbitrary_tags here.


def _connect(relays=DEFAULT_RELAYS) -> RelayManager:
    rm = RelayManager(timeout=6)
    for r in relays:
        rm.add_relay(r)
    rm.run_sync()
    return rm


def _start_relay_pump(rm: RelayManager) -> tuple[threading.Thread, threading.Event]:
    """Background thread that calls rm.run_sync() continuously so
    WebSocket pings keep flowing while the main thread is blocked
    in input() or any other long-running synchronous work.

    Why this exists: pynostr's RelayManager owns a tornado IOLoop that
    only advances when run_sync() is invoked. Public relays close idle
    WebSocket connections after ~30-60s. If the main thread stops
    pumping (because it's blocked in `input("Fetch via MCP?")` or in
    a 5s async MCP fetch) the relays drop us, DMs go nowhere, and
    pynostr's auto-reconnect path stumbles into transient HTTP 503s.

    Concurrency note: tornado.ioloop.IOLoop.current() is thread-local,
    so ONLY this pump thread may call rm.run_sync(). The main thread
    must not call run_sync() once the pump is running — they would use
    different IOLoops and behave incoherently. rm.publish_event() is
    fine from the main thread: it just appends to per-relay publish
    queues that this pump's next run_sync() flushes.
    Same for rm.message_pool: backed by a thread-safe queue.Queue.

    Returns the thread and a stop event for graceful shutdown.
    """
    stop = threading.Event()

    def _pump() -> None:
        while not stop.is_set():
            try:
                rm.run_sync()
            except Exception:  # noqa: BLE001 — MVP: swallow + retry
                pass
            time.sleep(0.3)

    t = threading.Thread(target=_pump, daemon=True, name="relay-pump")
    t.start()
    return t, stop


def cmd_keygen() -> None:
    me = Identity.load_or_create("buyer")
    print(f"Buyer identity:")
    print(f"  npub:    {me.npub}")
    print(f"  pubkey:  {me.pk_hex}")


def cmd_watch() -> None:
    me = Identity.load_or_create("buyer")
    sk = PrivateKey.from_hex(me.sk_hex)

    rm = _connect()

    rm.add_subscription_on_all_relays("listings", FiltersList([MATCH_FILTER]))
    inbox_filter = Filters(
        kinds=[EventKind.ENCRYPTED_DIRECT_MESSAGE],
        pubkey_refs=[me.pk_hex],
    )
    rm.add_subscription_on_all_relays("inbox", FiltersList([inbox_filter]))

    print(f"Watching as {me.npub}.")
    print(f"Listing filter: kinds=[30402] #t=cars,mazda")
    print(f"Press Ctrl-C to stop.\n")

    # Start the background pump BEFORE entering the input()-blocking
    # loop. From here on, the main thread MUST NOT call rm.run_sync():
    # only the pump thread does. The main thread only consumes from
    # rm.message_pool (thread-safe queue.Queue) and calls
    # rm.publish_event() (thread-safe per-relay queue.put), which the
    # pump thread's next run_sync() flushes.
    _, stop = _start_relay_pump(rm)
    try:
        seen = set()
        while True:
            while rm.message_pool.has_events():
                msg = rm.message_pool.get_event()
                ev: Event = msg.event
                if ev.id in seen:
                    continue
                seen.add(ev.id)

                if ev.kind == 30402:
                    _handle_listing(ev, sk, rm)
                elif ev.kind == EventKind.ENCRYPTED_DIRECT_MESSAGE:
                    _handle_reply(ev, sk)

            time.sleep(0.5)
    finally:
        stop.set()


def _handle_listing(ev: Event, sk: PrivateKey, rm: RelayManager) -> None:
    render_listing(ev)

    # Cache the seller's MCP URL + item_id keyed by pubkey, so that
    # when their NIP-04 reply arrives we know where to MCP-fetch from.
    mcp_url = extract_mcp_url(ev)
    item_id = extract_item_id(ev)
    if mcp_url:
        _MCP_CONTEXT[ev.pubkey] = {"mcp_url": mcp_url, "item_id": item_id}

    text = input("Send the seller a DM? Type a message (blank to skip):\n> ").strip()
    if not text:
        return
    dm = EncryptedDirectMessage()
    dm.encrypt(
        private_key_hex=sk.hex(),
        cleartext_content=text,
        recipient_pubkey=ev.pubkey,
    )
    out_ev = dm.to_event()
    out_ev.sign(sk.hex())
    rm.publish_event(out_ev)
    # Pump thread will flush this on its next tick (~0.3s).
    time.sleep(1)
    print(f"[+] Sent. Listening for reply...\n")


def _handle_reply(ev: Event, sk: PrivateKey) -> None:
    try:
        dm = EncryptedDirectMessage.from_event(ev)
        dm.decrypt(sk.hex(), public_key_hex=ev.pubkey)
        text = dm.cleartext_content
    except Exception as e:
        print(f"[!] Could not decrypt DM from {ev.pubkey[:12]}…: {e}")
        return
    print(f"\nReply from {ev.pubkey[:16]}…:\n> {text}\n")

    ctx = _MCP_CONTEXT.get(ev.pubkey)
    if not ctx:
        return

    fetch_key = (ev.pubkey, ctx["item_id"])
    if fetch_key in _FETCHED:
        # Already pulled photos + inspection from this seller for this
        # item earlier in the session — don't re-prompt on every reply.
        # Run `python mcp_client.py <url> <item_id>` manually to refetch.
        return

    answer = input(
        f"This seller's listing advertised an MCP endpoint:\n"
        f"  {ctx['mcp_url']}  (item {ctx['item_id'][:8]}…)\n"
        f"Fetch cover photo + inspection report via MCP now? [y/N] "
    ).strip().lower()
    if answer != "y":
        return

    try:
        # Lazy import — `mcp` is only required if the user opts into
        # the MCP fetch step. Keeps `keygen`/text-only `watch` working
        # without the optional dependency.
        from mcp_client import fetch_listing_assets  # noqa: WPS433
    except ImportError as e:
        print(f"[!] mcp_client unavailable ({e}); skipping fetch.")
        return

    try:
        result = fetch_listing_assets(ctx["mcp_url"], ctx["item_id"])
    except Exception as e:  # noqa: BLE001 — print + continue in MVP
        print(f"[!] MCP fetch failed: {e}")
        return

    print("\n=== MCP fetch complete ===")
    print(f"  tools advertised: {result['tools_advertised']}")
    if result["summary"]:
        print(f"  summary:    {result['summary']}")
    if result["image_info"]:
        n, sha, path = result["image_info"]
        print(f"  cover:      {n} bytes → {path}")
        print(f"              sha256 {sha[:16]}…")
    if result["report_info"]:
        n, sha, path = result["report_info"]
        print(f"  inspection: {n} bytes → {path}")
        print(f"              sha256 {sha[:16]}…")
    print()

    _FETCHED.add(fetch_key)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "keygen":
        cmd_keygen()
    elif cmd == "watch":
        cmd_watch()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
