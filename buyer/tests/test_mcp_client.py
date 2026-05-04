"""Tests for ``chaos_buyer.mcp_client``.

Use an in-process FastMCP server to drive the client.
"""
from __future__ import annotations

import pytest


def test_mcp_session_streams_image_blocks() -> None:
    """A FastMCP server returns 3 ImageContent blocks; client writes 3 files into the inbox."""
    assert False, "TODO: implement"


def test_mcp_session_streams_embedded_resource() -> None:
    """An EmbeddedResource is decoded and saved under documents/."""
    assert False, "TODO: implement"


def test_mcp_session_rejects_oversized_block() -> None:
    """A 50 MiB inline image is refused (cap to ~10 MiB per block)."""
    assert False, "TODO: implement"


def test_mcp_client_no_url_fetch_anywhere() -> None:
    """The client never makes an outbound HTTP fetch for content bytes.

    Patch ``httpx.AsyncClient.get`` to raise; the test confirms the
    streaming path doesn't trigger it. Defends against a regression
    where someone wires a URL fallback for binary content.
    """
    assert False, "TODO: implement"


def test_list_tools_advertises_cars_pack_surface() -> None:
    """``list_tools`` against a cars-pack@1 seller returns the documented tool names."""
    assert False, "TODO: implement"


@pytest.mark.skip(reason="Requires a live MCP HTTP+SSE seller — integration test")
def test_mcp_client_two_machine_round_trip() -> None:
    """Buyer client + seller MCP server on different processes complete a full ask."""
    assert False, "TODO: implement"
