"""MCP HTTP+SSE client — receives photos and PDFs from a seller's MCP server.

The buyer is purely an MCP CLIENT. Given a matched listing's
``["mcp", url]`` tag, this module dials the seller's MCP server over
HTTP+SSE, runs the standard ``initialize`` handshake, calls
``tools/list`` to bootstrap the seller's tool surface, then dispatches
``tools/call`` per ask. Returned ``ImageContent`` /
``EmbeddedResource`` / ``TextContent`` blocks are unwrapped, size-
capped, and persisted onto disk.

Reference shape (from the proven spike at ``spike/buyer_mcp.py`` and
the ``mcp`` Python SDK 1.27.0):

    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.types import (
        TextContent,
        ImageContent,
        EmbeddedResource,
    )

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(name, arguments)
            for block in result.content:
                if block.type == "image":
                    img_bytes = base64.b64decode(block.data)
                    ...

AGENTS.md rule 2: binary content moves over MCP only. This module
NEVER writes a URL into a fetch — its only inputs are the bytes
already-decoded from base64 inside an incoming content block.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp import ClientSession


_BLOCK_BYTES_HARD_CAP = 10 * 1024 * 1024  # 10 MiB per block


@dataclass(slots=True)
class InboxEntry:
    """Result of one fetched MCP session.

    Attributes:
        conversation_id: Item id (or session token) for this conversation.
        photos: Paths to saved image files, in arrival order.
        documents: Paths to saved document files.
        text_blocks: List of text strings received around the bytes.
    """

    conversation_id: str
    photos: list[Path] = field(default_factory=list)
    documents: list[Path] = field(default_factory=list)
    text_blocks: list[str] = field(default_factory=list)


async def connect(url: str) -> ClientSession:
    """Open an MCP HTTP+SSE session to the seller's MCP URL.

    Wraps ``mcp.client.sse.sse_client`` + ``mcp.ClientSession`` and
    runs the ``initialize`` handshake. Caller is expected to use this
    inside an ``async with`` block (or call ``close`` explicitly) so
    the underlying SSE transport is shut down cleanly.

    Args:
        url: HTTPS URL from the listing's ``["mcp", url]`` tag.

    Returns:
        An initialized ``mcp.ClientSession``.

    Raises:
        ValueError: if ``url`` is not ``https://``.
        RuntimeError: on transport / initialize failure.
    """
    raise NotImplementedError("mcp_client.connect not implemented")


async def list_tools(session: ClientSession) -> list[Any]:
    """Bootstrap discovery — call ``tools/list`` on an open session.

    Per the MCP spike, the buyer learns the seller's full tool
    surface (cars-pack@1: ``view_listing``, ``request_photos``,
    ``request_inspection_report``, ``request_vin``, ``submit_offer``,
    ``cancel_inquiry``) without prior knowledge.

    Args:
        session: An initialized ``ClientSession`` from ``connect``.

    Returns:
        The list of ``mcp.types.Tool`` objects the seller advertises.
    """
    raise NotImplementedError("mcp_client.list_tools not implemented")


async def call_tool(
    session: ClientSession,
    name: str,
    arguments: dict,
) -> list[Any]:
    """Dispatch a single ``tools/call`` and return the content blocks.

    The blocks are returned untouched; ``persist_blocks`` is the
    helper that decodes and writes bytes to disk with size caps.

    Args:
        session: An initialized ``ClientSession`` from ``connect``.
        name: Tool name (e.g. ``"request_photos"``).
        arguments: Tool-specific arguments. MUST include the
                  inquiry's ``session_token``.

    Returns:
        The list of content blocks (one of ``mcp.types.TextContent``,
        ``ImageContent``, or ``EmbeddedResource``).

    Raises:
        RuntimeError: if ``CallToolResult.isError`` is set.
    """
    raise NotImplementedError("mcp_client.call_tool not implemented")


def persist_blocks(
    blocks: list[Any],
    *,
    inbox_dir: Path,
    conversation_id: str,
    max_block_bytes: int = _BLOCK_BYTES_HARD_CAP,
) -> InboxEntry:
    """Decode and write content blocks to the inbox.

    Routes:

    - ``ImageContent(type="image", data=base64, mimeType=...)`` →
      ``inbox_dir/<conv>/photos/<idx>.<ext>``.
    - ``EmbeddedResource(type="resource", resource.blob=base64, ...)``
      → ``inbox_dir/<conv>/documents/<safe-name>``.
    - ``TextContent(type="text", text=...)`` → appended to
      ``InboxEntry.text_blocks`` (caller is expected to feed each
      string through ``input_safety.sanitize`` before showing it to
      the planner).

    Per AGENTS.md rule 2 the only input is the bytes already-decoded
    from the MCP response — there is no URL fetch here, ever.

    Args:
        blocks: Output of ``call_tool``.
        inbox_dir: Inbox root (typically
                   ``~/.chaos/buyer/inbox``).
        conversation_id: Subdirectory name under ``inbox_dir``.
        max_block_bytes: Hard cap on the size of any single
                         content block (refuses oversized blocks
                         with a logged warning).

    Returns:
        Populated ``InboxEntry``.

    Raises:
        ValueError: on oversized block or invalid base64.
    """
    raise NotImplementedError("mcp_client.persist_blocks not implemented")


def _ext_for_mime(mime_type: str) -> str:
    """Map a MIME type to a file extension.

    Args:
        mime_type: e.g. ``"image/jpeg"``, ``"image/png"``,
                   ``"application/pdf"``.

    Returns:
        Lowercase extension without the leading dot. Defaults to
        ``"bin"`` for unknown types.
    """
    table = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "application/pdf": "pdf",
    }
    return table.get(mime_type.lower(), "bin")


def _decode_b64(data: str, *, max_bytes: int) -> bytes:
    """Base64-decode an inline blob with a length cap.

    Args:
        data: Base64-encoded string.
        max_bytes: Cap before decode (a 10 MiB cap on bytes implies
                   ~13.4 MiB of base64).

    Returns:
        Decoded bytes.

    Raises:
        ValueError: if the cap is exceeded or the input is not
            valid base64.
    """
    if len(data) > max_bytes * 2:
        raise ValueError(f"mcp content block too large: {len(data)} chars > {max_bytes * 2}")
    return base64.b64decode(data, validate=True)
