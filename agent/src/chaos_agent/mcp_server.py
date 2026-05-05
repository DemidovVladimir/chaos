"""FastMCP HTTP+SSE server for the offering agent — exposes the cars-pack@1 tool surface.

This is the network-facing leaf where the offering agent's photos and
inspection PDFs cross from disk into the seeking agent's process. It is the
canonical wire for seeking agent↔offering agent dialogue and binary content
(AGENTS.md rule 2).

The server is a ``FastMCP`` instance running over the SSE transport on
``SellerConfig.mcp.bind``. The cars-pack@1 tool surface (the
"protocol contract" for this vertical) is:

- ``view_listing(item_id)`` → text summary
- ``request_photos(item_id, kinds=[...])`` →
  ``list[ImageContent]``
- ``request_inspection_report(item_id)`` → ``EmbeddedResource``
- ``request_vin(item_id)`` → text (always per-tool ``ASK_USER``)
- ``submit_offer(item_id, amount, currency, note)`` → ack text
- ``cancel_inquiry(item_id, reason)`` → ack text

Optional cars-pack@1 tools:

- ``request_test_drive_slots(item_id)``
- ``request_inspection_at_shop(item_id)``
- ``request_delivery_options(item_id, region)``

Every tool call is gated by ``grant_policy.decide(tool, arguments,
item)`` before the underlying ``catalog`` lookup runs. Calls marked
``ASK_USER`` block until ``tools_inquire.grant_asks`` resolves them.
Calls marked ``DENY`` raise an MCP tool error with the policy reason.

AGENTS.md rule 2 ("Binary content moves over MCP only") and rule 5
("No data custody") are *enforced here*, not just described. Every
byte streamed leaves through this module — no other path exists.

Reference: the proven spike in ``spike/seller_mcp.py`` which boots
two of these on different ports for multi-offering agent fanout testing.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import EmbeddedResource, ImageContent

    from .catalog import Catalog


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SessionBinding:
    """A seeking agent's MCP session bound by ``inquiry_listener``.

    The seeking agent's agent first sends a NIP-17 ``mcp_inquiry_open`` rumor
    carrying a ``session_token``. ``inquiry_listener`` decrypts that,
    binds ``session_token → from_pubkey`` here, and the FastMCP
    server consults this binding on the HTTP+SSE handshake before
    accepting any tool call.

    Attributes:
        session_token: Opaque token presented in the
            ``Authorization`` header on the seeking agent's MCP handshake.
        from_pubkey: Pubkey from the rumor signer; the policy keys
            user-confirm decisions off this.
        item_id: The listing the seeking agent asked about.
        expires_at: Unix seconds; reject after this.
    """

    session_token: str
    from_pubkey: str
    item_id: str
    expires_at: int


@dataclass(slots=True)
class SessionRegistry:
    """In-memory registry of bound MCP sessions.

    For Week 1 this is a process-local dict. If the offering agent process
    restarts, in-flight sessions are lost — that's acceptable because
    the seeking agent will retry with a fresh inquiry rumor.
    """

    _sessions: dict[str, SessionBinding] = field(default_factory=dict)

    def bind(self, binding: SessionBinding) -> None:
        """Store a session binding for later validation.

        Args:
            binding: The binding to register. Replaces any prior
                binding with the same ``session_token``.
        """
        raise NotImplementedError("mcp_server.SessionRegistry.bind not implemented")

    def take(self, session_token: str) -> SessionBinding | None:
        """Return the binding for ``session_token`` if not expired.

        Args:
            session_token: The token from the seeking agent's handshake.

        Returns:
            The ``SessionBinding`` or ``None`` if missing / expired.
        """
        raise NotImplementedError("mcp_server.SessionRegistry.take not implemented")


def build_server(
    *,
    name: str,
    host: str,
    port: int,
    catalog: Catalog,
    registry: SessionRegistry,
) -> FastMCP:
    """Construct the ``FastMCP`` instance and register cars-pack@1 tools.

    The resulting server is what ``serve()`` runs. Splitting it out
    lets tests instantiate a server against a fake catalog and a
    fake registry without binding a real socket.

    Args:
        name: Server name (e.g. ``"chaos-agent"``).
        host: Bind host.
        port: Bind port.
        catalog: Backing item catalog.
        registry: Session-token registry shared with
            ``inquiry_listener``.

    Returns:
        A ``FastMCP`` server with every cars-pack@1 tool registered.
    """
    raise NotImplementedError("mcp_server.build_server not implemented")


# ---------------------------------------------------------------------------
# Tool handlers — cars-pack@1 surface
#
# These are the function bodies registered with ``@mcp.tool()`` inside
# ``build_server()``. Each one:
#
# 1. Resolves ``ctx.session_token`` → ``SessionBinding`` via the
#    registry.
# 2. Calls ``grant_policy.decide(tool, arguments, item)``.
# 3. If GRANT → does the work and returns the MCP content.
# 4. If ASK_USER → raises a special "pending user confirmation" error
#    the seeking agent's client surfaces back to the seeking agent.
# 5. If DENY → raises an MCP tool error with the policy reason.
#
# The spike at ``spike/seller_mcp.py`` shows the proven shape; these
# scaffolds are stubs with the right signatures.
# ---------------------------------------------------------------------------


def view_listing_impl(item_id: str, *, catalog: Catalog) -> str:
    """Return a short textual summary of the item.

    Args:
        item_id: ``d`` tag of the listing.
        catalog: Backing catalog (injected by ``build_server``).

    Returns:
        Plain-text summary (title, year, mileage, asking price, etc.).
    """
    raise NotImplementedError("mcp_server.view_listing_impl not implemented")


def request_photos_impl(
    item_id: str,
    *,
    kinds: list[str] | None = None,
    catalog: Catalog,
) -> list[ImageContent]:
    """Return photos as inline ``ImageContent`` blocks.

    Args:
        item_id: ``d`` tag of the listing.
        kinds: Optional category filter (``exterior``, ``interior``,
            ``engine_bay``, ``undercarriage``,
            ``license_plate_blurred``).
        catalog: Backing catalog.

    Returns:
        A list of ``ImageContent`` blocks, one per photo file.
    """
    raise NotImplementedError("mcp_server.request_photos_impl not implemented")


def request_inspection_report_impl(
    item_id: str,
    *,
    catalog: Catalog,
) -> EmbeddedResource:
    """Return the inspection report as an ``EmbeddedResource``.

    Args:
        item_id: ``d`` tag of the listing.
        catalog: Backing catalog.

    Returns:
        An ``EmbeddedResource`` with the PDF bytes (base64).
    """
    raise NotImplementedError("mcp_server.request_inspection_report_impl not implemented")


def request_vin_impl(item_id: str, *, catalog: Catalog) -> str:
    """Return the full VIN as text (always gated by user confirmation).

    Args:
        item_id: ``d`` tag of the listing.
        catalog: Backing catalog.

    Returns:
        The VIN string. Raises if not yet user-approved.
    """
    raise NotImplementedError("mcp_server.request_vin_impl not implemented")


def submit_offer_impl(
    item_id: str,
    *,
    amount: int,
    currency: str,
    note: str = "",
) -> str:
    """Record a seeking agent's offer and surface it to the user.

    Args:
        item_id: ``d`` tag of the listing.
        amount: Offer amount in the smallest currency unit (e.g. cents).
        currency: ISO 4217 code (``"EUR"`` etc.).
        note: Optional seeking agent-supplied note (sanitized before display).

    Returns:
        Acknowledgement text the seeking agent's agent will read.
    """
    raise NotImplementedError("mcp_server.submit_offer_impl not implemented")


def cancel_inquiry_impl(item_id: str, *, reason: str = "") -> str:
    """Mark the seeking agent's session as withdrawn.

    Args:
        item_id: ``d`` tag of the listing.
        reason: Optional seeking agent-supplied reason (sanitized).

    Returns:
        Acknowledgement text.
    """
    raise NotImplementedError("mcp_server.cancel_inquiry_impl not implemented")


def _b64_image(path: Path, mime_type: str = "image/jpeg") -> ImageContent:
    """Helper: read a photo from disk and wrap in ``ImageContent``."""
    raise NotImplementedError("mcp_server._b64_image not implemented")


def _sha_log(name: str, blob: bytes) -> None:
    """Helper: log the size + first 12 hex chars of SHA-256(blob)."""
    sha = hashlib.sha256(blob).hexdigest()
    logger.info("  → %s bytes=%d sha=%s…", name, len(blob), sha[:12])


async def serve(
    bind: str,
    *,
    catalog: Catalog,
    registry: SessionRegistry,
    name: str = "chaos-agent",
    transport: str = "sse",
) -> None:
    """Run the offering agent's FastMCP server until cancelled.

    Wraps ``build_server(...).run(transport=transport)``. The caller
    is responsible for hosting this in an asyncio task alongside the
    inquiry listener (see ``main.cmd_serve``).

    Args:
        bind: ``host:port`` string from ``SellerConfig.mcp.bind``.
        catalog: Backing item catalog.
        registry: Session-token registry shared with
            ``inquiry_listener``.
        name: FastMCP server name.
        transport: Transport name; defaults to ``"sse"`` (HTTP+SSE).

    Raises:
        Never — runs until the surrounding task is cancelled.
    """
    raise NotImplementedError("mcp_server.serve not implemented")
