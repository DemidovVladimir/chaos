"""Build, PoW-mine, sign, and publish a NIP-99 listing event.

The four public functions form a pipeline:

    item -> build_event -> mine_pow -> sign -> publish

Per ``PROTOCOL.md`` § "Discovery — NIP-99 classified listings":

- ``kind: 30402`` (addressable + replaceable)
- Required tags: ``d``, ``title``, ``summary``, ``price``,
  ``location``, ``t`` (multiple), make/model/year/body_type/
  fuel_type/transmission/mileage_band, ``mcp``, ``pack``.
- **No** ``image`` tag, **no** public photo URL anywhere on the
  event (AGENTS.md rule 2).

PoW: NIP-13. Default difficulty 20 bits per AGENTS.md rule 10.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .catalog import Item

if TYPE_CHECKING:
    from pynostr.event import Event
    from pynostr.relay_manager import RelayManager

DEFAULT_POW_BITS = 20


def build_event(
    item: Item,
    *,
    pubkey_hex: str,
    mcp_url: str,
    pack: str = "cars-pack@1",
) -> dict[str, Any]:
    """Assemble a NIP-99 (kind-30402) event dict from an ``Item``.

    Emits the discovery tags required by ``PROTOCOL.md``:

    - ``["mcp", <https-url>]`` — public URL of the seller's FastMCP
      HTTP+SSE server. A buyer's agent will dial this endpoint after
      sending a NIP-17 ``mcp_inquiry_open`` rumor.
    - ``["pack", <name>@<version>]`` — vertical pack contract the
      seller implements (e.g. ``cars-pack@1``). The buyer's skill
      uses this to know which tools to call.

    Args:
        item: The local item to publish.
        pubkey_hex: Seller's x-only pubkey hex.
        mcp_url: Public URL of the seller's MCP server. Must be
                 ``https://`` for production; embedded as the
                 ``["mcp", <url>]`` tag.
        pack: Vertical pack identifier; embedded as the
              ``["pack", <pack>]`` tag. Defaults to ``cars-pack@1``.

    Returns:
        A dict with ``kind``, ``pubkey``, ``created_at``, ``tags``,
        ``content``. Suitable for ``mine_pow()`` followed by
        ``sign()``.

    Raises:
        ValueError: if any required ``Item`` field is missing or if
            ``mcp_url`` is not ``https://``.
    """
    raise NotImplementedError("publish.build_event not implemented")


def mine_pow(raw_event: dict[str, Any], *, bits: int = DEFAULT_POW_BITS) -> dict[str, Any]:
    """NIP-13 mine the event id to ``bits`` leading zero bits.

    Iterates a ``["nonce", "<n>", "<bits>"]`` tag (replacing the
    previous nonce in place), recomputes the canonical event id, and
    returns when the leading-zero count is ≥ ``bits``.

    Args:
        raw_event: Output of ``build_event()`` (mutated in place).
        bits: Difficulty target. Defaults to 20.

    Returns:
        The same dict with a ``nonce`` tag and an updated
        ``created_at`` if the miner restarted.

    Raises:
        ValueError: if ``bits < 1`` or ``bits > 32`` (anything above
            32 is unreasonable for cars-pack@1).
    """
    raise NotImplementedError("publish.mine_pow not implemented")


def publish(rm: RelayManager, sk_hex: str, raw_event: dict[str, Any]) -> Event:
    """Sign and publish ``raw_event`` to every relay in ``rm``.

    Args:
        rm: A live ``pynostr.relay_manager.RelayManager``.
        sk_hex: Seller's secret key hex.
        raw_event: A PoW-mined event dict.

    Returns:
        The signed ``pynostr.event.Event`` that was sent.

    Raises:
        RuntimeError: if no relay accepted the event within the
            relay manager's timeout.
    """
    raise NotImplementedError("publish.publish not implemented")


def deletion_request(
    event_id: str, *, pubkey_hex: str, addressable: str | None = None, reason: str = ""
) -> dict[str, Any]:
    """Build a NIP-09 deletion request.

    Per ``PROTOCOL.md`` § "Item updates and removal", we publish a
    kind-5 referencing both the event id and the addressable form
    ``30402:<pubkey>:<d-value>``.

    Args:
        event_id: The published event id to delete.
        pubkey_hex: Seller's pubkey.
        addressable: Optional ``30402:<pubkey>:<d-value>`` reference.
        reason: Optional human-readable reason.

    Returns:
        A kind-5 event dict ready to sign and publish.
    """
    raise NotImplementedError("publish.deletion_request not implemented")


def now_unix() -> int:
    """Return the current unix timestamp.

    Wrapped so tests can monkeypatch one place.

    Returns:
        Integer unix seconds.
    """
    return int(time.time())
