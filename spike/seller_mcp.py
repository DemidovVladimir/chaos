# (Historical -- written under the project's previous name "neuro-spati", now called "chaos".)
"""
seller_mcp.py — neuro-spati MCP seller spike.

A FastMCP server (HTTP + SSE transport) exposing a small cars-pack
tool surface:

  • view_listing(item_id) → text summary
  • request_photos(item_id, kinds=["exterior",..]) → list of ImageContent
  • request_inspection_report(item_id) → EmbeddedResource (PDF-shaped binary)

Run two of these on different ports to exercise multi-seller fanout:
    MCP_PORT=7501 SELLER_NAME=alice python3 seller_mcp.py
    MCP_PORT=7502 SELLER_NAME=bob   python3 seller_mcp.py
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    BlobResourceContents,
    EmbeddedResource,
    ImageContent,
    TextContent,
)


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[seller-%(name)s] %(asctime)s %(levelname)s %(message)s",
)

NAME = os.environ.get("SELLER_NAME", "seller")
PORT = int(os.environ.get("MCP_PORT", "7501"))
HOST = os.environ.get("MCP_HOST", "127.0.0.1")

log = logging.getLogger(NAME)

# --- "Catalog" — one fictional car per seller, each with distinct bytes -------
# Distinct PNG per seller so the buyer can tell them apart by SHA.
TEST_PNG_RED = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c63f8cfc0000000020001e22165"
    "850000000049454e44ae426082"
)
TEST_PNG_BLUE = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c6360606000000000050001e201"
    "ed230000000049454e44ae426082"
)

PNG_BY_SELLER = {"alice": TEST_PNG_RED, "bob": TEST_PNG_BLUE}
TEST_PNG = PNG_BY_SELLER.get(NAME, TEST_PNG_RED)

TEST_REPORT = (
    f"INSPECTION REPORT (test, seller={NAME})\n"
    f"Item: 2018 Mazda 6 hatchback\n"
    f"VIN ending: 8K2J\n"
    f"Mileage at inspection: 65,432 km\n"
    f"Verdict: pass\n"
).encode("utf-8")

LISTING_TEXT = (
    f"2018 Mazda 6 hatchback — {NAME}'s listing.\n"
    f"65,000 km, 1 owner, full Mazda service history. No accidents. 15,000 EUR."
)


# --- MCP server ---------------------------------------------------------------
mcp = FastMCP(NAME, host=HOST, port=PORT)


@mcp.tool()
def view_listing(item_id: str = "8f4a2b1e") -> str:
    """Return a short textual summary of the item.

    The first thing a buyer's agent calls after `tools/list` to confirm
    the item exists and grab the human-readable description.
    """
    log.info("view_listing(item_id=%s) called", item_id)
    return LISTING_TEXT


@mcp.tool()
def request_photos(
    item_id: str = "8f4a2b1e",
    kinds: list[str] | None = None,
) -> list[ImageContent]:
    """Return photos of the item as inline ImageContent blocks.

    The seller's agent decides per-buyer (out of band, via grant policy)
    whether to grant photos. For the spike, all photos are auto-granted.

    `kinds` filters which photo categories to return (exterior, interior,
    engine_bay, …). For the spike we ignore it and return one cover image.
    """
    log.info("request_photos(item_id=%s, kinds=%s) called", item_id, kinds)
    img = ImageContent(
        type="image",
        data=base64.b64encode(TEST_PNG).decode("ascii"),
        mimeType="image/png",
    )
    sha = hashlib.sha256(TEST_PNG).hexdigest()
    log.info("  → 1 photo bytes=%d sha=%s…", len(TEST_PNG), sha[:12])
    return [img]


@mcp.tool()
def request_inspection_report(item_id: str = "8f4a2b1e") -> EmbeddedResource:
    """Return the inspection report as an embedded binary resource.

    Used for PDFs / DOCs / non-image binary content that doesn't fit
    the ImageContent shape.
    """
    log.info("request_inspection_report(item_id=%s) called", item_id)
    res = EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri=f"local://inspection/{item_id}",
            mimeType="text/plain",
            blob=base64.b64encode(TEST_REPORT).decode("ascii"),
        ),
    )
    sha = hashlib.sha256(TEST_REPORT).hexdigest()
    log.info("  → report bytes=%d sha=%s…", len(TEST_REPORT), sha[:12])
    return res


def main() -> None:
    log.info("Starting MCP seller %r on http://%s:%d/", NAME, HOST, PORT)
    log.info("  SSE endpoint:  http://%s:%d/sse", HOST, PORT)
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
