"""
buyer.py — weekend MVP buyer agent.

Subcommands:
  python buyer.py keygen           — generate / show your buyer identity
  python buyer.py watch            — subscribe to NIP-99 cars listings,
                                     prompt to DM the seller on each match,
                                     and print the seller's reply

Edit MATCH_FILTER below to change what you're looking for.
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

from shared import DEFAULT_RELAYS, Identity, render_listing


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

    seen = set()
    while True:
        rm.run_sync()
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


def _handle_listing(ev: Event, sk: PrivateKey, rm: RelayManager) -> None:
    render_listing(ev)
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
    rm.run_sync()
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
