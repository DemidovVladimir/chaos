# (Historical -- written under the project's previous name "neuro-spati", now called "chaos".)
# =====================================================================
# SUPERSEDED — historical ACP spike, kept for reference only.
# The project chose MCP after the MCP spike passed. See
# spike/MCP_SPIKE_REPORT.md for the verdict and spike/seller_mcp.py /
# spike/buyer_mcp.py for the live wire.
# Do NOT copy this code into seller/ or buyer/ — the production scaffold
# is built on FastMCP, not on ACP/A2A.
# =====================================================================
"""
seller_acp.py — ACP agent that streams a real PNG to a buyer.

Run via stdio (the only transport ACP 0.9.0 ships):
  python3 seller_acp.py

Driven by `buyer_acp.py` which spawns this as a subprocess. When the
buyer sends an `acp.prompt(...)` call, this agent emits a sequence of
session updates carrying:
  1. A text content block ("here's the photo you asked for...")
  2. An ImageContentBlock with real PNG bytes (base64-encoded inline)
  3. An EmbeddedResourceContentBlock with a small "inspection report"
  4. A closing text block

The buyer's `session_update` callback receives each chunk, decodes the
base64 payloads, and saves the bytes to disk.

This spike answers ONE question: can ACP move binary content end-to-end
between two processes via the published `ImageContentBlock` /
`EmbeddedResourceContentBlock` types?

If yes (this script + buyer_acp.py round-trips successfully), the
neuro-spati architecture's "photos move agent-to-agent over ACP" claim
is unblocked at the API level. Cross-network transport (HTTP+SSE
instead of stdio) is a separate question for a follow-up spike.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import sys
import time

import acp
from acp.schema import (
    AgentCapabilities,
    Implementation,
    InitializeResponse,
    NewSessionResponse,
    PromptResponse,
    SessionCapabilities,
)


# Log to stderr so it doesn't interleave with the JSON-RPC traffic on stdout.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[seller] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


# A real, minimal valid PNG: 1x1 red pixel. 67 bytes. Generated with PIL once
# and embedded so the spike has zero external file dependencies.
TEST_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c63f8cfc0000000020001e22165"
    "850000000049454e44ae426082"
)

# A small "inspection report" — plain text wrapped in PDF-ish framing.
TEST_REPORT_BYTES = (
    b"INSPECTION REPORT (test)\n"
    b"Item: 2018 Mazda 6 hatchback\n"
    b"VIN ending: 8K2J\n"
    b"Mileage at inspection: 65,432 km\n"
    b"Tires: Continental PremiumContact, ~5000 km wear\n"
    b"Body: no rust, no panel repaint indicators\n"
    b"Mechanical: clean, no codes\n"
    b"Verdict: pass\n"
)


class SpikeSeller(acp.Agent):
    """Minimal ACP agent that streams text + image + resource on prompt."""

    def __init__(self) -> None:
        self._conn: acp.Client | None = None

    def on_connect(self, conn: acp.Client) -> None:
        self._conn = conn
        log.info("Connected to client.")

    async def initialize(self, protocol_version, **kwargs):
        log.info("initialize(protocol_version=%s)", protocol_version)
        return InitializeResponse(
            protocol_version=acp.PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(
                load_session=False,
                prompt_capabilities=None,
                mcp_capabilities=None,
            ),
            auth_methods=[],
            agent_info=Implementation(
                name="neuro-spati-spike-seller",
                version="0.0.1",
                title="Spike seller",
            ),
        )

    async def new_session(self, cwd, mcp_servers=None, **kwargs):
        sid = f"spike-{int(time.time() * 1000)}"
        log.info("new_session → %s", sid)
        return NewSessionResponse(
            session_id=sid,
            session_capabilities=SessionCapabilities(),
        )

    async def prompt(self, prompt, session_id, message_id=None, **kwargs):
        log.info("prompt() session_id=%s blocks=%d", session_id, len(prompt))
        if self._conn is None:
            raise RuntimeError("on_connect was never called")

        # 1. Opening text
        await self._conn.session_update(
            session_id=session_id,
            update=acp.update_agent_message_text(
                "Sending photo + inspection report for the 2018 Mazda 6.\n"
            ),
        )

        # 2. Image content block (real PNG)
        img_b64 = base64.b64encode(TEST_PNG_BYTES).decode("ascii")
        img_sha = hashlib.sha256(TEST_PNG_BYTES).hexdigest()
        log.info("emit image  bytes=%d sha256=%s…", len(TEST_PNG_BYTES), img_sha[:12])
        await self._conn.session_update(
            session_id=session_id,
            update=acp.update_agent_message(
                acp.image_block(data=img_b64, mime_type="image/png"),
            ),
        )

        # 3. Embedded resource block (inspection report as a "PDF")
        rep_b64 = base64.b64encode(TEST_REPORT_BYTES).decode("ascii")
        rep_sha = hashlib.sha256(TEST_REPORT_BYTES).hexdigest()
        log.info("emit report bytes=%d sha256=%s…", len(TEST_REPORT_BYTES), rep_sha[:12])
        await self._conn.session_update(
            session_id=session_id,
            update=acp.update_agent_message(
                acp.resource_block(
                    acp.embedded_blob_resource(
                        uri="local://inspection-report.txt",
                        blob=rep_b64,
                        mime_type="text/plain",
                    ),
                ),
            ),
        )

        # 4. Closing text
        await self._conn.session_update(
            session_id=session_id,
            update=acp.update_agent_message_text(
                "That's everything. Open an ACP session again if you need more photos.\n"
            ),
        )

        return PromptResponse(stop_reason="end_turn")


def main() -> None:
    asyncio.run(acp.run_agent(SpikeSeller()))


if __name__ == "__main__":
    main()
