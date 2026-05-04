"""Hermes tool handlers — inquiry-handling tools.

These are the seller-side Hermes tools the seller-cars skill calls
to surface incoming MCP tool-call requests to the user, grant or
deny them, and produce structured replies. They wrap
``inquiry_listener`` + ``grant_policy`` + ``mcp_server`` behind the
standard Hermes ``handler(args, **kwargs) -> str`` shape.

Conceptually:

- ``handle_inquiry`` walks every pending MCP tool call from a buyer's
  agent, runs the per-tool grant policy, and either approves the call
  (allowing the FastMCP server to execute it), escalates to the user
  (``ASK_USER``), or denies it (``DENY``).
- ``grant_asks`` is the explicit user-approval path for tool calls
  marked ``ASK_USER``.
- ``deny_ask`` denies one specific tool call with a reason.
"""
from __future__ import annotations

import json
from typing import Any


def handle_inquiry(args: dict, **kwargs: Any) -> str:
    """Process pending MCP tool calls through the per-tool grant policy.

    Pipeline:

    1. Look up the open MCP session by ``session_token`` (bound to a
       buyer pubkey by ``inquiry_listener``).
    2. Run ``grant_policy.evaluate(...)`` over the pending tool calls.
    3. For ``ASK_USER`` outcomes, surface to the user via
       ``notify_user`` (delegated through ``ctx.dispatch_tool``).
    4. Approve granted calls so the FastMCP server returns their
       results (``ImageContent`` / ``EmbeddedResource`` blocks).
    5. Send a NIP-17 ``mcp_inquiry_ack`` if any human-readable text
       needs to land outside the MCP session itself.

    Args:
        args: ``{"session_token": "...", "calls": [...]}``.

    Returns:
        JSON string summarizing what was granted, what was denied,
        and which calls are now pending user confirmation.
    """
    raise NotImplementedError("tools_inquire.handle_inquiry not implemented")


def grant_asks(args: dict, **kwargs: Any) -> str:
    """User-approval path: explicitly grant pending ``ASK_USER`` MCP tool calls.

    Args:
        args: ``{"session_token": "...", "calls": [<tool_name>, ...]}``.

    Returns:
        JSON string with the calls now granted and the updated reply
        payload (or an error).
    """
    raise NotImplementedError("tools_inquire.grant_asks not implemented")


def deny_ask(args: dict, **kwargs: Any) -> str:
    """Deny one specific MCP tool call with a short reason.

    Args:
        args: ``{"session_token": "...", "tool": "...", "reason": "..."}``.

    Returns:
        JSON string with the updated reply payload.
    """
    raise NotImplementedError("tools_inquire.deny_ask not implemented")


def _ok(payload: dict) -> str:
    """Wrap a success payload as a JSON string."""
    return json.dumps(payload, default=str)


def _err(message: str, **extra: Any) -> str:
    """Wrap an error as a JSON string."""
    return json.dumps({"error": message, **extra}, default=str)
