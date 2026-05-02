"""
seller.py — weekend MVP seller agent.

Subcommands:
  python seller.py keygen           — generate / show your seller identity
  python seller.py publish FILE     — publish a NIP-99 listing from a TOML file
  python seller.py listen           — listen for incoming NIP-04 DM inquiries

`publish` and `listen` can run together: `publish` returns immediately
after the relay confirms the event; `listen` keeps the WebSocket open
and prompts you to reply when an inquiry arrives.
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

import sys
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


def _connect(relays=DEFAULT_RELAYS) -> RelayManager:
    rm = RelayManager(timeout=6)
    for r in relays:
        rm.add_relay(r)
    rm.run_sync()
    return rm


def cmd_keygen() -> None:
    me = Identity.load_or_create("seller")
    print(f"Seller identity:")
    print(f"  npub:    {me.npub}")
    print(f"  pubkey:  {me.pk_hex}")


def cmd_publish(toml_path: str) -> None:
    me = Identity.load_or_create("seller")
    listing = load_listing(toml_path)
    raw = build_nip99_listing(listing, pubkey_hex=me.pk_hex)

    ev = Event(
        kind=raw["kind"],
        content=raw["content"],
        tags=raw["tags"],
        created_at=raw["created_at"],
        pubkey=raw["pubkey"],
    )
    sk = PrivateKey.from_hex(me.sk_hex)
    ev.sign(sk.hex())

    rm = _connect()
    rm.publish_event(ev)
    rm.run_sync()
    time.sleep(2)
    rm.close_all_relay_connections()

    item_id = next((t[1] for t in ev.tags if t and t[0] == "d"), "?")
    print(f"Published listing {item_id} (event id {ev.id[:12]}…) "
          f"to {len(DEFAULT_RELAYS)} relay(s).")


def cmd_listen() -> None:
    me = Identity.load_or_create("seller")
    sk = PrivateKey.from_hex(me.sk_hex)

    print(f"Listening as {me.npub} for NIP-04 DMs (Ctrl-C to stop).\n")

    rm = _connect()
    flt = Filters(kinds=[EventKind.ENCRYPTED_DIRECT_MESSAGE], pubkey_refs=[me.pk_hex])
    sub_id = "inbox"
    rm.add_subscription_on_all_relays(sub_id, FiltersList([flt]))

    seen = set()
    while True:
        rm.run_sync()
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
            rm.run_sync()
            time.sleep(1)
            print(f"[+] Reply sent.\n")

        time.sleep(0.5)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "keygen":
        cmd_keygen()
    elif cmd == "publish":
        if len(sys.argv) < 3:
            print("Usage: seller.py publish FILE.toml")
            sys.exit(2)
        cmd_publish(sys.argv[2])
    elif cmd == "listen":
        cmd_listen()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
