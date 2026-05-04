"""market-comp-mcp — pricing comparables from on-network listings.

Stub server. Real relay query + percentile logic lands in Phase 2.

Threat model: queries Nostr relays the user has configured (read-
only). No outbound HTTP. No external comp data sources. No PII.
"""
from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[market-comp-mcp] %(asctime)s %(levelname)s %(message)s",
)

NAME = "market-comp-mcp"
HOST = os.environ.get("MARKET_COMP_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MARKET_COMP_MCP_PORT", "7611"))

log = logging.getLogger(NAME)
mcp = FastMCP(NAME, host=HOST, port=PORT)


@mcp.tool()
def query_comps(pack: str, filter_tags: dict, window_days: int = 60) -> dict:
    """Return pricing comparables for the given (pack, filter_tags).

    Args:
        pack: vertical pack id, e.g. "cars-pack@1".
        filter_tags: pack-specific filter dict, e.g.
            {"make": "mazda", "model": "6", "year_min": 2017, "year_max": 2019}.
        window_days: how far back to look (60 = fast tier default,
            180 = pro/thorough tier default).

    Returns:
        CompResult-shaped dict.
    """
    return {
        "median_cents": 0,
        "sample_size": 0,
        "stub": True,
        "pack": pack,
        "window_days": window_days,
    }


if __name__ == "__main__":
    log.info("starting %s on %s:%d", NAME, HOST, PORT)
    mcp.run()
