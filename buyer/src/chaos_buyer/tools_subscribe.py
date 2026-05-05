"""Hermes tool handlers — subscription-side tools."""

from __future__ import annotations

import json
from typing import Any


def create_filter(args: dict, **kwargs: Any) -> str:
    """Translate a UserWant into a REQ filter and start a subscription.

    Args:
        args: ``{"name": "...", "want": {...}}``.

    Returns:
        JSON string with the filter's REQ shape on success.
    """
    raise NotImplementedError("tools_subscribe.create_filter not implemented")


def list_filters(args: dict, **kwargs: Any) -> str:
    """List saved filters and their state.

    Args:
        args: Empty.

    Returns:
        JSON string with the list of filters.
    """
    raise NotImplementedError("tools_subscribe.list_filters not implemented")


def pause_filter(args: dict, **kwargs: Any) -> str:
    """Pause a saved filter.

    Args:
        args: ``{"name": "..."}``.

    Returns:
        JSON status.
    """
    raise NotImplementedError("tools_subscribe.pause_filter not implemented")


def delete_filter(args: dict, **kwargs: Any) -> str:
    """Delete a saved filter and stop its subscription.

    Args:
        args: ``{"name": "..."}``.

    Returns:
        JSON status.
    """
    raise NotImplementedError("tools_subscribe.delete_filter not implemented")


def _ok(payload: dict) -> str:
    """Wrap a success payload as a JSON string."""
    return json.dumps(payload, default=str)


def _err(message: str, **extra: Any) -> str:
    """Wrap an error as a JSON string."""
    return json.dumps({"error": message, **extra}, default=str)
