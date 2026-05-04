"""Seller-side Nostr identity: keypair load/save + Schnorr signing.

The keypair lives at ``~/.chaos/keys/seller.key`` mode 0600.
Per CLAUDE.md rule 3 ("Identity is sovereign") and rule 5 ("No data
custody"), the platform never holds, escrows, or recovers user keys
— if the file is lost, the user loses their pubkey.

Mirrors the structure of ``mvp/shared.py::Identity`` but typed and
without side-effects at module load time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

KEYS_DIR = Path.home() / ".chaos" / "keys"
DEFAULT_KEY_PATH = KEYS_DIR / "seller.key"


@dataclass(frozen=True, slots=True)
class Identity:
    """Holds an immutable view of the seller's secp256k1 keypair.

    Attributes:
        sk_hex: 64-char lowercase hex of the secret key. Sensitive.
        pk_hex: 64-char lowercase x-only pubkey hex.
        npub: Bech32 NIP-19 ``npub1...`` form for display.
    """

    sk_hex: str
    pk_hex: str
    npub: str


def load_or_create(path: Path | None = None) -> Identity:
    """Load identity at ``path`` or generate a new one if missing.

    Permissions on a new file are set to 0600. If an existing file's
    permissions are looser than 0600, this function rewrites them.

    Args:
        path: Optional override for the key file. Defaults to
              ``~/.chaos/keys/seller.key``.

    Returns:
        An ``Identity`` populated from the on-disk key.

    Raises:
        OSError: if the key file cannot be read or written.
        ValueError: if the on-disk content is not a 64-char hex string.
    """
    raise NotImplementedError("identity.load_or_create not implemented")


def sign_event(ev_dict: dict, sk_hex: str) -> dict:
    """Sign a Nostr event dict in place and return it.

    Args:
        ev_dict: A dict with ``kind``, ``pubkey``, ``created_at``,
                 ``tags``, ``content``. Mutated in place; ``id`` and
                 ``sig`` fields are added.
        sk_hex: Secret key hex used for the BIP-340 Schnorr signature.

    Returns:
        The same dict with ``id`` and ``sig`` set.

    Raises:
        ValueError: if ``ev_dict`` is missing required fields.
    """
    raise NotImplementedError("identity.sign_event not implemented")


def ensure_keys_dir(path: Path = KEYS_DIR) -> Path:
    """Create the keys directory with mode 0700 if needed.

    Args:
        path: Directory to create. Default ``~/.chaos/keys``.

    Returns:
        The directory path.
    """
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        # On some filesystems chmod is a no-op; we tolerate that.
        pass
    return path
