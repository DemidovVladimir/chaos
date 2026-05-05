"""NIP-17 gift-wrapped inquiry listener.

Listens on the configured relays for kind-1059 events tagged
``["p", <our_pubkey>]``, decrypts the gift wrap → seal → rumor stack,
parses the inner JSON inquiry payload, sanitizes any free-form text,
validates the embedded ``session_token``, and binds it to the calling
buyer pubkey for the upcoming MCP session.

The rumor type is ``mcp_inquiry_open``; it carries:

- ``session_token`` — opaque opaque token the buyer's agent will
  present in the ``Authorization`` header on the MCP HTTP+SSE handshake.
- ``item_id`` — the listing the buyer is interested in.
- ``buyer_pubkey`` — derived from the rumor signer; the MCP server
  binds the session_token → buyer_pubkey before accepting any tool
  call on that session.
- ``free_text`` (optional) — anything the buyer wrote; passed through
  ``input_safety.sanitize`` before any LLM-facing surface sees it.

Per ``PROTOCOL.md`` § "1-to-1 messaging":

    Gift wrap (kind 1059, NIP-44 from ephemeral key)
        -> Seal (kind 13, NIP-44 from sender)
            -> Rumor (kind 14, sender-signed structured payload)

The MVP path (`mvp/seller.py`) uses NIP-04 plaintext DMs as an
isolated demo shortcut. AGENTS.md rule 7 forbids NIP-04 in production,
so this production package accepts NIP-17 gift wraps only.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynostr.event import Event
    from pynostr.relay_manager import RelayManager


@dataclass(frozen=True, slots=True)
class Inquiry:
    """Decrypted, sanitized ``mcp_inquiry_open`` rumor from a buyer.

    Attributes:
        event_id: Id of the gift-wrap event we decrypted.
        sender_pubkey: Pubkey of the original sender (from the rumor,
                       NOT the ephemeral wrap key).
        item_id: ``d`` tag of the listing being asked about.
        session_token: Opaque token the buyer's agent will present on
                       the MCP HTTP+SSE handshake. The seller's MCP
                       server binds this token → ``sender_pubkey``
                       before accepting any tool call.
        free_text: Optional free-form text from the buyer; sanitized.
                   Empty string if no free text was provided.
    """

    event_id: str
    sender_pubkey: str
    item_id: str
    session_token: str
    free_text: str = ""


def listen(
    rm: RelayManager,
    *,
    my_sk_hex: str,
    my_pk_hex: str,
) -> Iterator[Inquiry]:
    """Yield decrypted ``Inquiry`` objects forever.

    Subscribes to the configured relays via a REQ filter for
    kind-1059 events tagged with our pubkey. Decrypts each, sanitizes free text,
    validates the rumor type is ``mcp_inquiry_open``, and yields a
    frozen ``Inquiry``.

    Args:
        rm: Live relay manager.
        my_sk_hex: Seller's secret key hex.
        my_pk_hex: Seller's pubkey hex.
    Yields:
        ``Inquiry`` instances. Generator never returns.

    Raises:
        Never — decryption failures and malformed payloads are
        logged and skipped.
    """
    raise NotImplementedError("inquiry_listener.listen not implemented")


def unwrap_gift(ev: Event, *, my_sk_hex: str) -> tuple[str, str]:
    """Decrypt a kind-1059 gift wrap → seal → rumor.

    Args:
        ev: A kind-1059 event tagged ``["p", <our_pubkey>]``.
        my_sk_hex: Seller's secret key hex (used for NIP-44 ECDH).

    Returns:
        A tuple of (sender_pubkey_hex, rumor_content_json_string).
        The caller MUST validate the JSON's ``type`` field equals
        ``"mcp_inquiry_open"`` before binding the session token.

    Raises:
        ValueError: if any decryption layer fails or the inner rumor
            has the wrong shape.
    """
    raise NotImplementedError("inquiry_listener.unwrap_gift not implemented")


def send_reply(
    rm: RelayManager,
    *,
    my_sk_hex: str,
    recipient_pubkey_hex: str,
    payload: dict,
) -> str:
    """Wrap, seal, gift-wrap and publish a structured reply.

    The reply rumor is typed ``mcp_inquiry_ack`` and carries a status
    field plus any user-facing text we want to deliver outside the
    MCP session (e.g. an explicit denial when no MCP session will be
    opened).

    Args:
        rm: Live relay manager.
        my_sk_hex: Seller's secret key hex (signs the rumor).
        recipient_pubkey_hex: Buyer's pubkey from the original
                              inquiry's sender field (NOT the wrap
                              key).
        payload: Dict matching the ``mcp_inquiry_ack`` shape in
                 ``PROTOCOL.md`` § "1-to-1 messaging".
    Returns:
        The id of the published gift-wrap event.

    Raises:
        RuntimeError: if no relay accepts the published wrap.
    """
    raise NotImplementedError("inquiry_listener.send_reply not implemented")
