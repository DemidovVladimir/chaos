"""Tests for ``chaos_seller.mcp_server``.

We test the seller-side FastMCP HTTP+SSE server with an in-process
fake MCP client (driven through ``mcp.client.session.ClientSession``
or a direct ``FastMCP`` invocation) so the suite stays fast and
offline. The proven shape lives in ``spike/seller_mcp.py``.
"""

from __future__ import annotations

import pytest


def test_mcp_server_view_listing_returns_summary() -> None:
    """``view_listing(item_id)`` returns a non-empty text summary.

    The first thing a buyer's agent calls after ``tools/list``; the
    cars-pack@1 contract requires a plain-text response.
    """
    pytest.skip("not yet implemented")
def test_mcp_server_request_photos_returns_image_content_blocks() -> None:
    """``request_photos`` returns ``ImageContent`` blocks, one per granted photo.

    Sets up an item with three exterior photos, drives
    ``request_photos(item_id, kinds=["exterior"])``, and asserts
    exactly three ``ImageContent`` blocks come back with valid
    base64 data and the right ``mimeType``.
    """
    pytest.skip("not yet implemented")
def test_mcp_server_request_inspection_report_returns_embedded_resource() -> None:
    """``request_inspection_report`` returns an ``EmbeddedResource`` (PDF bytes)."""
    pytest.skip("not yet implemented")
def test_mcp_server_rejects_unknown_session_token() -> None:
    """A handshake with an unbound ``session_token`` is refused.

    The buyer's agent must first send a NIP-17 ``mcp_inquiry_open``
    rumor; ``inquiry_listener`` binds the token in ``SessionRegistry``.
    Without a binding, the FastMCP server returns an auth error.
    """
    pytest.skip("not yet implemented")
def test_mcp_server_rejects_after_session_expiry() -> None:
    """A bound session past its ``expires_at`` is rejected on ``tools/call``."""
    pytest.skip("not yet implemented")
def test_mcp_server_only_emits_granted_photo_kinds() -> None:
    """``request_photos(kinds=["exterior"])`` MUST NOT return interior photos.

    Defends the per-tool grant policy against a regression where the
    handler ignores the ``kinds`` filter.
    """
    pytest.skip("not yet implemented")
def test_mcp_server_request_vin_blocks_until_user_confirm() -> None:
    """``request_vin`` always escalates to ASK_USER and never auto-grants.

    ``grant_policy.ALWAYS_USER_CONFIRM`` includes ``request_vin``;
    the FastMCP handler must surface it as a pending-user-confirm
    error rather than executing.
    """
    pytest.skip("not yet implemented")
def test_mcp_server_no_http_egress() -> None:
    """The seller's MCP path never makes an outbound HTTP call.

    Patches ``httpx.AsyncClient.send`` to raise; the test confirms
    nothing in the streaming path triggers it. Defends against a
    regression where someone wires an Imgur/Dropbox/S3 fallback.
    """
    pytest.skip("not yet implemented")
@pytest.mark.skip(reason="Requires live FastMCP transport — integration test")
def test_mcp_server_two_machine_round_trip() -> None:
    """Seller and buyer plugins on different processes exchange a 3-photo session."""
    pytest.skip("not yet implemented")