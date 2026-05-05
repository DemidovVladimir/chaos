"""reverse-image-mcp — perceptual-hash photo fraud detection.

Stub server. Real perceptual-hash logic lands in Phase 2.

Threat model: this server NEVER makes outbound HTTP. All hashing is
local. Image bytes are received as base64 from the calling agent
(typically passed through from `ImageContent` blocks the seeking agent's
agent received from the offering agent's MCP server) and are NOT retained.
"""

from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[reverse-image-mcp] %(asctime)s %(levelname)s %(message)s",
)

NAME = "reverse-image-mcp"
HOST = os.environ.get("REVERSE_IMAGE_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("REVERSE_IMAGE_MCP_PORT", "7610"))

log = logging.getLogger(NAME)
mcp = FastMCP(NAME, host=HOST, port=PORT)


@mcp.tool()
def check_image(image_bytes_b64: str, tier: str = "fast") -> dict:
    """Check an image against the local perceptual-hash DB.

    Args:
        image_bytes_b64: base64-encoded image bytes (max ~10 MB).
            Bytes received from a `request_photos` MCP tool call,
            never a URL.
        tier: "fast" (pHash+dHash, free) or "thorough"
            (adds EXIF + federated registry + optional CLIP, paid
            via x402; flipped on by `chaos-pro`).

    Returns:
        SimilarityScore-shaped dict.
    """
    return {
        "score": 0.0,
        "tier": tier,
        "matched": False,
        "note": "stub — implement in Phase 2",
    }


if __name__ == "__main__":
    log.info("starting %s on %s:%d", NAME, HOST, PORT)
    mcp.run()
