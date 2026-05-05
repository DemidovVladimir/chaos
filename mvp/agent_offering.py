"""
agent_offering.py — weekend MVP offering agent.

Subcommands:
  python agent_offering.py keygen                — generate / show your offering agent identity
  python agent_offering.py publish FILE          — publish a NIP-99 listing from a TOML file
  python agent_offering.py listen                — listen for incoming NIP-04 DM inquiries
  python agent_offering.py serve FILE            — publish a listing, start the FastMCP
                                           HTTP+SSE server in a background
                                           thread, and listen for inquiries in
                                           the foreground.
  python agent_offering.py serve-multi DIR       — publish every *.toml in DIR as its
                                           own NIP-99 event, share one MCP
                                           server (port 8765) across all of
                                           them (resolution by item_id at
                                           call time), and listen.

`publish` and `listen` can run together: `publish` returns immediately
after the relay confirms the event; `listen` keeps the WebSocket open
and prompts you to reply when an inquiry arrives.

`serve` is the one-terminal shortcut: it publishes the listing,
brings up the cars-pack@1 MCP tool surface (view_listing,
request_photos, request_inspection_report, request_vin, submit_offer,
cancel_inquiry) on http://127.0.0.1:8765/sse in a background thread,
and then transitions directly into the same listen loop without
closing the relay connections. The MCP URL must match the `mcp_url`
field in the listing TOML so seeking agents know where to reach it.

`serve-multi` is the multi-car variant: drop several listings into
`mvp/listings/` and run `python agent_offering.py serve-multi listings/`.
Each `.toml` is published as its own NIP-99 event. The same MCP
server (one port, one tool surface) serves all of them — the catalog
is built from the same directory at server boot. Per-item assets
live at `sample_photos/<item_id>/` and `sample_inspection_<item_id>.{pdf,txt,md}`;
missing items fall back to the global `sample_photos/cover.png` +
`sample_inspection.txt` defaults.
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
    build_nip99_listing,
    load_listing,
)


def _start_mcp_in_background() -> threading.Thread:
    """Boot the FastMCP HTTP+SSE server in a daemon thread.

    Imported lazily so `keygen`, `publish`, and `listen` (which don't
    need MCP) don't pay the import cost or fail if the `mcp` package
    isn't installed yet. `serve` requires `mcp==1.27.0` per
    `requirements.txt`.
    """
    from mcp_server import serve_blocking, HOST, PORT  # noqa: WPS433

    def _run() -> None:
        try:
            serve_blocking()
        except Exception as e:  # noqa: BLE001 — log + die quietly in MVP
            print(f"[mcp-srv] crashed: {e}", file=sys.stderr)

    t = threading.Thread(target=_run, name="mvp-mcp-server", daemon=True)
    t.start()
    # Brief sleep so the SSE bind happens before we print confirmation.
    time.sleep(0.6)
    print(f"[+] FastMCP server up on http://{HOST}:{PORT}/sse")
    return t


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
    pumping (because it's blocked in `input("Reply: ")` or in a 5s
    async MCP fetch) the relays drop us, DMs go nowhere, and
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


def _publish_listing(rm: RelayManager, me: Identity, sk: PrivateKey, toml_path: str) -> Event:
    listing = load_listing(toml_path)
    raw = build_nip99_listing(listing, pubkey_hex=me.pk_hex)

    ev = Event(
        kind=raw["kind"],
        content=raw["content"],
        tags=raw["tags"],
        created_at=raw["created_at"],
        pubkey=raw["pubkey"],
    )
    ev.sign(sk.hex())

    rm.publish_event(ev)
    rm.run_sync()
    time.sleep(2)

    item_id = next((t[1] for t in ev.tags if t and t[0] == "d"), "?")
    print(f"Published listing {item_id} (event id {ev.id[:12]}…) "
          f"to {len(DEFAULT_RELAYS)} relay(s).")
    return ev


def _listen_loop(rm: RelayManager, sk: PrivateKey, me: Identity) -> None:
    flt = Filters(kinds=[EventKind.ENCRYPTED_DIRECT_MESSAGE], pubkey_refs=[me.pk_hex])
    sub_id = "inbox"
    rm.add_subscription_on_all_relays(sub_id, FiltersList([flt]))

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

                try:
                    dm = EncryptedDirectMessage.from_event(ev)
                    dm.decrypt(sk.hex(), public_key_hex=ev.pubkey)
                    text = dm.cleartext_content
                except Exception as e:
                    print(f"[!] Could not decrypt DM from {ev.pubkey[:12]}…: {e}")
                    continue

                print(f"\nInquiry from {ev.pubkey[:16]}…:")
                print(f"  > {text}")
                reply = input("Reply (blank to skip): ").strip()
                if not reply:
                    continue

                outgoing = EncryptedDirectMessage()
                outgoing.encrypt(
                    private_key_hex=sk.hex(),
                    cleartext_content=reply,
                    recipient_pubkey=ev.pubkey,
                )
                out_ev = outgoing.to_event()
                out_ev.sign(sk.hex())
                rm.publish_event(out_ev)
                # Pump thread will flush this on its next tick (~0.3s).
                # Brief sleep so the publish gets a chance to go out
                # before the prompt redraws.
                time.sleep(1)
                print(f"[+] Reply sent.\n")

            time.sleep(0.5)
    finally:
        stop.set()


def cmd_keygen() -> None:
    me = Identity.load_or_create("offering")
    print(f"Offering agent identity:")
    print(f"  npub:    {me.npub}")
    print(f"  pubkey:  {me.pk_hex}")


def cmd_publish(toml_path: str) -> None:
    me = Identity.load_or_create("offering")
    sk = PrivateKey.from_hex(me.sk_hex)

    rm = _connect()
    try:
        _publish_listing(rm, me, sk, toml_path)
    finally:
        rm.close_all_relay_connections()


def cmd_listen() -> None:
    me = Identity.load_or_create("offering")
    sk = PrivateKey.from_hex(me.sk_hex)

    print(f"Listening as {me.npub} for NIP-04 DMs (Ctrl-C to stop).\n")

    rm = _connect()
    try:
        _listen_loop(rm, sk, me)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        rm.close_all_relay_connections()


def cmd_serve(toml_path: str) -> None:
    me = Identity.load_or_create("offering")
    sk = PrivateKey.from_hex(me.sk_hex)

    # Bring up MCP first so seeking agents calling immediately after seeing the
    # listing don't get connection refused.
    _start_mcp_in_background()

    rm = _connect()
    try:
        _publish_listing(rm, me, sk, toml_path)
        print("Listening for inquiries; Ctrl-C to stop.\n")
        _listen_loop(rm, sk, me)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        rm.close_all_relay_connections()


def cmd_serve_multi(dir_path: str) -> None:
    """Publish every *.toml in `dir_path` as its own NIP-99 event,
    boot one shared MCP server, then enter the listen loop.

    The MCP server (started below) reads the same directory at boot
    via `MVP_LISTINGS_DIR`, builds an in-memory catalog keyed by
    item_id, and resolves item_id at call time. One process, one
    port, many listings.
    """
    from pathlib import Path

    tomls = sorted(Path(dir_path).glob("*.toml"))
    if not tomls:
        print(f"No .toml in {dir_path}")
        sys.exit(2)

    me = Identity.load_or_create("offering")
    sk = PrivateKey.from_hex(me.sk_hex)

    # Tell the MCP server which directory to load its catalog from.
    # Set BEFORE _start_mcp_in_background() so module import sees it.
    os.environ["MVP_LISTINGS_DIR"] = str(Path(dir_path).resolve())
    _start_mcp_in_background()

    rm = _connect()
    try:
        for toml_path in tomls:
            _publish_listing(rm, me, sk, str(toml_path))
        print(
            f"Published {len(tomls)} listing(s). "
            f"Listening for inquiries; Ctrl-C to stop.\n"
        )
        _listen_loop(rm, sk, me)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        rm.close_all_relay_connections()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "keygen":
        cmd_keygen()
    elif cmd == "publish":
        if len(sys.argv) < 3:
            print("Usage: agent_offering.py publish FILE.toml")
            sys.exit(2)
        cmd_publish(sys.argv[2])
    elif cmd == "listen":
        cmd_listen()
    elif cmd == "serve":
        if len(sys.argv) < 3:
            print("Usage: agent_offering.py serve FILE.toml")
            sys.exit(2)
        cmd_serve(sys.argv[2])
    elif cmd == "serve-multi":
        if len(sys.argv) < 3:
            print("Usage: agent_offering.py serve-multi DIR")
            sys.exit(2)
        cmd_serve_multi(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
