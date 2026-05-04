"""Template FastMCP server for a chaos shared capability MCP.

Copy this folder, rename, and fill in the tool implementations. Stub
shape mirrors `spike/seller_mcp.py` so the wire model is identical.
"""
from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[template-mcp] %(asctime)s %(levelname)s %(message)s",
)

NAME = "template-mcp"
HOST = os.environ.get("TEMPLATE_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("TEMPLATE_MCP_PORT", "7600"))

log = logging.getLogger(NAME)
mcp = FastMCP(NAME, host=HOST, port=PORT)


@mcp.tool()
def example_tool(payload: str) -> dict:
    """Stub tool. Replace with your real surface."""
    return {"echo": payload, "stub": True}


if __name__ == "__main__":
    log.info("starting %s on %s:%d", NAME, HOST, PORT)
    mcp.run()
