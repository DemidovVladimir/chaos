"""
shared.py — minimal helpers for the weekend MVP.

Centralizes keypair I/O, NIP-99 event construction, and relay client
configuration so agent_offering.py and agent_seeking.py stay short.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import tomllib  # Python 3.11+ stdlib


# Public, low-friction relays for the MVP. Five relays for redundancy
# — public relays return transient HTTP 503s under load, so a single
# pair (damus + nos.lol) leaves us offline whenever both flap. Five
# gives the connection pool enough headroom that at least one stays
# up while the others reconnect.
DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.snort.social",
    "wss://nostr-pub.wellorder.net",
    "wss://relay.nostr.band",
]


KEYS_DIR = Path.home() / ".mvp"
KEYS_DIR.mkdir(parents=True, exist_ok=True)


# Allow overriding via env var so users can point at their own
# Mode-A relay (e.g. wss://localhost:7777). Comma-separated.
_env_relays = os.environ.get("MVP_RELAYS", "").strip()
if _env_relays:
    DEFAULT_RELAYS = [r.strip() for r in _env_relays.split(",") if r.strip()]


@dataclass
class Identity:
    sk_hex: str
    pk_hex: str
    npub:   str

    @classmethod
    def load_or_create(cls, name: str) -> "Identity":
        """Load identity for `name` (e.g. 'offering', 'seeking') or generate one."""
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
    """Build a kind-30402 NIP-99 event from a TOML listing dict.

    If the TOML carries `mcp_url`, an `["mcp", url]` tag is added so
    seeking agents know where to open an MCP HTTP+SSE session for photos and
    inspection reports. If `pack` is present, a `["pack", name]` tag
    is added so seeking agents know which vertical-pack contract to expect.
    """
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
    if listing.get("mcp_url"):
        tags.append(["mcp", listing["mcp_url"]])
    if listing.get("pack"):
        tags.append(["pack", listing["pack"]])
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
    mcp_url  = facets.get("mcp")
    pack     = facets.get("pack")

    price_s = f"{price[1]} {price[2]}" if price else "(no price)"
    print(f"\nMatch: {title}")
    print(f"  price:    {price_s}")
    print(f"  location: {location}")
    print(f"  offering:   {event.pubkey[:16]}…")
    print(f"  summary:  {summary}")
    if pack:
        print(f"  pack:     {pack}")
    if mcp_url:
        print(f"  mcp:      {mcp_url}")
    print()


def extract_mcp_url(event) -> str | None:
    """Return the `mcp` tag value from a NIP-99 event, or None."""
    for tag in event.tags:
        if tag and len(tag) >= 2 and tag[0] == "mcp":
            return tag[1]
    return None


def extract_item_id(event) -> str:
    """Return the `d` tag value from a NIP-99 event, or '?' if missing."""
    for tag in event.tags:
        if tag and len(tag) >= 2 and tag[0] == "d":
            return tag[1]
    return "?"
