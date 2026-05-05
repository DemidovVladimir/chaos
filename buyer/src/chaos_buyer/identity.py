"""Buyer-side Nostr identity: keypair load/save + signing.

The keypair lives at ``~/.chaos/keys/buyer.key`` mode 0600.
Same shape and rules as the seller's identity module, kept separate
so each plugin installs as a self-contained wheel.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path

KEYS_DIR = Path.home() / ".chaos" / "keys"
DEFAULT_KEY_PATH = KEYS_DIR / "buyer.key"


@dataclass(frozen=True, slots=True)
class Identity:
    """Buyer's secp256k1 keypair view.

    Attributes:
        sk_hex: 64-char lowercase secret-key hex.
        pk_hex: 64-char lowercase x-only pubkey hex.
        npub: Bech32 NIP-19 form for display.
    """

    sk_hex: str
    pk_hex: str
    npub: str


def load_or_create(path: Path | None = None) -> Identity:
    """Load identity at ``path`` or generate a new one if missing.

    Args:
        path: Optional override.

    Returns:
        ``Identity`` populated from disk.

    Raises:
        OSError, ValueError: as in seller's module.
    """
    raise NotImplementedError("identity.load_or_create not implemented")


def sign_event(ev_dict: dict, sk_hex: str) -> dict:
    """Sign a Nostr event dict in place and return it.

    Args:
        ev_dict: Event dict to sign.
        sk_hex: Buyer's secret key hex.

    Returns:
        The same dict with ``id`` and ``sig`` set.
    """
    raise NotImplementedError("identity.sign_event not implemented")


def ensure_keys_dir(path: Path = KEYS_DIR) -> Path:
    """Ensure the keys directory exists with mode 0700.

    Args:
        path: Directory path.

    Returns:
        The directory path.
    """
    path.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(path, 0o700)
    return path
