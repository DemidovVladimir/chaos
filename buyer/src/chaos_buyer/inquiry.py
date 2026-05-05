"""Build, encrypt, and publish NIP-17 inquiries to a seller.

Per ``PROTOCOL.md`` § "1-to-1 messaging — NIP-17 sealed gift-wraps":

    Rumor (kind 14, sender-signed)
      -> Seal (kind 13, NIP-44 to recipient, sender-signed)
        -> Gift wrap (kind 1059, NIP-44 from ephemeral, ephemeral-signed,
                       tagged ["p", recipient_pubkey])

Inquiry payload shape (inside the rumor):

    {
        "type": "mcp_inquiry_open",
        "item_id": "<seller's d tag value>",
        "buyer_pubkey": "<buyer's pubkey hex>",
        "session_token": "<opaque token the seller binds to its grant>",
        "asks": [...]
    }

The buyer learns the seller's MCP HTTP+SSE URL from the matched
NIP-99 listing's ``["mcp", url]`` tag — it is NOT carried inside
the rumor. The ``session_token`` is what binds an open MCP session
back to this inquiry on the seller side.

AGENTS.md rule 7 forbids NIP-04 in production paths. The production
buyer package only emits NIP-17 inquiries; the MVP shortcut remains
isolated under ``mvp/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynostr.relay_manager import RelayManager


@dataclass(frozen=True, slots=True)
class InquiryReply:
    """Decrypted reply rumor parsed into a typed shape.

    Attributes:
        item_id: Subject listing.
        granted: Asks the seller granted.
        denied: Asks the seller denied.
        denial_reason: Optional one-line reason.
        inline: Map of ask -> inline payload (e.g. service_history
                text). Photos NEVER appear here — photos arrive only
                as MCP ``ImageContent`` blocks from a ``tools/call``
                response on the seller's MCP server.
        session_token: Echoed back by the seller; the buyer passes it
                       on every subsequent ``mcp_call_tool`` so the
                       seller can bind the call to this inquiry's
                       grant policy.
    """

    item_id: str
    granted: tuple[str, ...]
    denied: tuple[str, ...]
    denial_reason: str
    inline: dict[str, str]
    session_token: str


def build_payload(
    item_id: str,
    asks: list[str],
    *,
    buyer_pubkey_hex: str,
    session_token: str,
    free_text: str = "",
) -> dict:
    """Assemble the JSON inquiry payload that goes inside a rumor.

    Args:
        item_id: The seller's listing ``d`` tag value.
        asks: List of ask field names.
        buyer_pubkey_hex: Buyer's pubkey hex; the seller uses it to
                         scope the grant policy and to authenticate
                         subsequent MCP ``tools/call`` invocations
                         that present the same ``session_token``.
        session_token: Opaque high-entropy token (e.g. 24 bytes
                       url-safe base64) the buyer mints once per
                       inquiry. Required on every later
                       ``mcp_call_tool`` against the seller's MCP
                       server so the seller can bind the call back
                       to this inquiry.
        free_text: Optional free-form text. Will be length-capped at
                   1000 chars to match ``max_chars_per_offer``.

    Returns:
        A JSON-serializable dict.

    Raises:
        ValueError: if ``asks`` is empty or ``session_token`` is too
            short to be safe.
    """
    raise NotImplementedError("inquiry.build_payload not implemented")


def send(
    rm: RelayManager,
    *,
    my_sk_hex: str,
    seller_pubkey_hex: str,
    payload: dict,
) -> str:
    """Wrap, seal, gift-wrap and publish the inquiry.

    Args:
        rm: Live relay manager.
        my_sk_hex: Buyer's secret key hex (signs the rumor).
        seller_pubkey_hex: Seller's pubkey hex (NIP-44 ECDH peer for
                           the seal layer; ``["p", ...]`` tag for the
                           gift wrap).
        payload: As produced by ``build_payload``.
    Returns:
        The id of the published gift-wrap event.

    Raises:
        RuntimeError: if no relay accepted the wrap within the
            relay manager's timeout.
    """
    raise NotImplementedError("inquiry.send not implemented")


def await_reply(
    rm: RelayManager,
    *,
    my_sk_hex: str,
    sub_id: str,
    timeout_sec: float = 120.0,
) -> InquiryReply:
    """Block until a NIP-17 reply rumor for our inquiry arrives.

    Args:
        rm: Live relay manager.
        my_sk_hex: Buyer's secret key hex (decrypts incoming wraps).
        sub_id: Subscription id used to filter relevant events.
        timeout_sec: Max wall-clock seconds to wait.

    Returns:
        A populated ``InquiryReply``.

    Raises:
        TimeoutError: if no reply arrived in time.
    """
    raise NotImplementedError("inquiry.await_reply not implemented")
