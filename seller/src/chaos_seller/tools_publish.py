"""Hermes tool handlers — publishing-side tools.

Each handler matches the Hermes plugin contract:

- Signature: ``def handler(args: dict, **kwargs) -> str``
- Returns: a JSON string, ALWAYS — success and error alike
- Never raises: catches everything, returns error JSON

See the build-a-plugin guide § "Step 4: Write the tool handlers".
"""

from __future__ import annotations

import json
from typing import Any


def publish_item(args: dict, **kwargs: Any) -> str:
    """Build, PoW-mine, sign and publish a NIP-99 listing.

    Args:
        args: ``{"item_id": "<uuid>"}``.
        **kwargs: Forward-compatible Hermes context.

    Returns:
        JSON string:
            ``{"event_id": "...", "relays_accepted": [...]}`` on success,
            ``{"error": "..."}`` on failure.
    """
    raise NotImplementedError("tools_publish.publish_item not implemented")


def archive_item(args: dict, **kwargs: Any) -> str:
    """Republish with ``status="archived"`` and emit a NIP-09 deletion.

    Args:
        args: ``{"item_id": "<uuid>", "reason": "<short>"}``.

    Returns:
        JSON string with the new event id on success or an error.
    """
    raise NotImplementedError("tools_publish.archive_item not implemented")


def update_item(args: dict, **kwargs: Any) -> str:
    """Apply a patch to a local item and republish.

    Args:
        args: ``{"item_id": "<uuid>", "patch": {<field>: <value>, ...}}``.

    Returns:
        JSON string with the new event id and the fields actually
        changed.
    """
    raise NotImplementedError("tools_publish.update_item not implemented")


def _ok(payload: dict) -> str:
    """Wrap a success payload as a JSON string.

    Args:
        payload: The success body.

    Returns:
        ``json.dumps(payload, default=str)``.
    """
    return json.dumps(payload, default=str)


def _err(message: str, **extra: Any) -> str:
    """Wrap an error message as a JSON string.

    Args:
        message: Human-readable error string.
        **extra: Optional fields to merge into the response.

    Returns:
        JSON-encoded error payload, e.g.
        ``{"error": "no such item", "item_id": "..."}``.
    """
    payload = {"error": message, **extra}
    return json.dumps(payload, default=str)
