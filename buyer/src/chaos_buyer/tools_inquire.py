"""Hermes tool handlers — inquiry-side tools."""
from __future__ import annotations

import json
from typing import Any


def send_inquiry(args: dict, **kwargs: Any) -> str:
    """Send a NIP-17 gift-wrapped inquiry to the seller.

    The rumor type is ``mcp_inquiry_open``; the payload carries
    ``item_id``, ``buyer_pubkey``, a freshly-minted ``session_token``
    (24-byte url-safe base64), and the user's ``asks``. The seller's
    MCP HTTP+SSE URL is discovered from the matched listing's
    ``["mcp", url]`` tag and is NOT carried in the rumor.

    Args:
        args: ``{"item_id": "...", "asks": [...]}``.

    Returns:
        JSON string with ``{"event_id": "...", "session_token": "..."}``
        — the latter is what the buyer presents on every later
        ``mcp_call_tool`` so the seller can bind the call back to the
        inquiry's grant policy.
    """
    raise NotImplementedError("tools_inquire.send_inquiry not implemented")


def mcp_connect(args: dict, **kwargs: Any) -> str:
    """Open an MCP HTTP+SSE session to the seller's MCP URL.

    Looks up the matched listing's ``["mcp", url]`` tag, opens a
    FastMCP-style ``ClientSession`` over SSE, runs ``initialize``,
    then calls ``tools/list``. The session is held in a per-item
    pool so subsequent ``mcp_call_tool`` invocations reuse it.

    Args:
        args: ``{"item_id": "..."}``.

    Returns:
        JSON string with the advertised tool surface, e.g.::

            {
              "tools": ["view_listing", "request_photos",
                        "request_inspection_report", "request_vin",
                        "submit_offer", "cancel_inquiry"]
            }
    """
    raise NotImplementedError("tools_inquire.mcp_connect not implemented")


def mcp_call_tool(args: dict, **kwargs: Any) -> str:
    """Dispatch one ``tools/call`` on the open MCP session.

    Decodes the returned content blocks:

    - ``ImageContent`` blocks are size-capped per
      ``BuyerConfig.mcp.max_image_bytes_per_response`` and written
      to ``~/.chaos/buyer/inbox/<item_id>/photos/``.
    - ``EmbeddedResource`` blocks are written to
      ``~/.chaos/buyer/inbox/<item_id>/documents/``.
    - ``TextContent`` blocks are passed through ``input_safety.sanitize``
      and returned inline in the response payload.

    Per CLAUDE.md rule 2, the buyer NEVER fetches binary content
    from any URL — bytes are only ever decoded inline from the MCP
    response.

    Args:
        args: ``{"item_id": "...", "tool_name": "...",
                "arguments": {...}}``. The ``arguments`` dict MUST
               include the inquiry's ``session_token`` so the seller
               can bind the call to its grant policy.

    Returns:
        JSON string with one row per content block (text inline,
        image / resource as relative inbox paths plus byte counts
        and SHA-256).
    """
    raise NotImplementedError("tools_inquire.mcp_call_tool not implemented")


def list_inquiries(args: dict, **kwargs: Any) -> str:
    """List the user's open inquiries with status and last activity.

    Args:
        args: Empty.

    Returns:
        JSON string with one row per open inquiry.
    """
    raise NotImplementedError("tools_inquire.list_inquiries not implemented")


def _ok(payload: dict) -> str:
    """Wrap a success payload as a JSON string."""
    return json.dumps(payload, default=str)


def _err(message: str, **extra: Any) -> str:
    """Wrap an error as a JSON string."""
    return json.dumps({"error": message, **extra}, default=str)
