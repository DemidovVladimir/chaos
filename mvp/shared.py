"""
shared.py — minimal helpers for the weekend MVP.

Centralizes keypair I/O, NIP-99 event construction, and relay client
configuration so seller.py and buyer.py stay short.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib            # Python 3.11+
except ImportError:
    import tomli as tomllib   # type: ignore


# Public, low-friction relays for the MVP.
DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
]


KEYS_DIR = Path.home() / ".mvp"
KEYS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Identity:
    sk_hex: str
    pk_hex: str
    npub:   str

    @classmethod
    def load_or_create(cls, name: str) -> "Identity":
        """Load identity for `name` (e.g. 'seller', 'buyer') or generate one."""
        from pynostr.key import PrivateKey                         # noqa: WPS433

        path = KEYS_DIR / f"{name}.key"
        if path.exists():
            sk = PrivateKey.from_hex(path.read_text().strip())
        else:
            sk = PrivateKey()
            path.write_text(sk.hex())
            os.chmod(path, 0o600)
            print(f"[+] Generated new identity for {name!r} at {path}")

        pk = sk.public_key
        return cls(sk_hex=sk.hex(), pk_hex=pk.hex(), npub=pk.bech32())


def load_listing(toml_path: str | os.PathLike) -> dict:
    """Read a TOML car definition into a plain dict (string-typed)."""
    with open(toml_path, "rb") as f:
        return tomllib.load(f)


def build_nip99_listing(listing: dict, *, pubkey_hex: str) -> dict:
    """Build a kind-30402 NIP-99 event from a TOML listing dict."""
    item_id = listing.get("item_id") or str(uuid.uuid4())
    tags = [
        ["d", item_id],
        ["title", listing["title"]],
        ["summary", listing["summary"]],
        ["price", listing["price_amount"], listing["price_currency"], ""],
        ["location", listing["location"]],
        ["t", "cars"],
        ["t", listing["make"]],
        ["make", listing["make"]],
        ["model", listing["model"]],
        ["year", listing["year"]],
        ["body_type", listing["body_type"]],
        ["fuel_type", listing["fuel_type"]],
        ["transmission", listing["transmission"]],
        ["mileage_band", listing["mileage_band"]],
    ]
    return {
        "kind": 30402,
        "pubkey": pubkey_hex,
        "created_at": int(time.time()),
        "tags": tags,
        "content": listing.get("content", ""),
    }


def render_listing(event) -> None:
    """Print a NIP-99 event in a human-readable form."""
    facets = {tag[0]: tag[1] for tag in event.tags if len(tag) >= 2}
    title    = facets.get("title", "(untitled)")
    summary  = facets.get("summary", "")
    location = facets.get("location", "(unknown)")
    price    = next((t for t in event.tags if t and t[0] == "price"), None)

    price_s = f"{price[1]} {price[2]}" if price else "(no price)"
    print(f"\nMatch: {title}")
    print(f"  price:    {price_s}")
    print(f"  location: {location}")
    print(f"  seller:   {event.pubkey[:16]}…")
    print(f"  summary:  {summary}\n")
