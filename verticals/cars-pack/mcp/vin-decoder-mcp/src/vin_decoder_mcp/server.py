"""vin-decoder-mcp — ISO-3779 structural VIN decoder.

Stub server. Real WMI/VDS/year/plant decoding lands in Phase 2.

Threat model: bundled SAE WMI registry only. No outbound HTTP. No
vehicle-history lookup (commercial data, explicitly out of scope per
AGENTS.md rule 6).
"""

from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[vin-decoder-mcp] %(asctime)s %(levelname)s %(message)s",
)

NAME = "vin-decoder-mcp"
HOST = os.environ.get("VIN_DECODER_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("VIN_DECODER_MCP_PORT", "7620"))

log = logging.getLogger(NAME)
mcp = FastMCP(NAME, host=HOST, port=PORT)


@mcp.tool()
def decode_vin(vin: str) -> dict:
    """Decode a 17-character VIN's structural facts.

    Stub returns a placeholder; Phase 2 wires the bundled WMI
    registry, deterministic year codes, and mod-11 check.
    """
    return {
        "vin": vin,
        "decoded": {
            "wmi": None,
            "manufacturer": None,
            "country": None,
            "vds": None,
            "year": None,
            "plant": None,
            "check_digit_valid": None,
        },
        "contradictions": [],
        "warnings": [],
        "stub": True,
    }


if __name__ == "__main__":
    log.info("starting %s on %s:%d", NAME, HOST, PORT)
    mcp.run()
