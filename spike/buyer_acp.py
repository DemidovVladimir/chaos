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
buyer_acp.py — ACP client that drives the seller spike and verifies
the round-trip.

Spawns `seller_acp.py` as an ACP subprocess (stdio transport — the only
one ACP 0.9.0 ships), opens a session, sends a prompt, captures the
content blocks emitted via session_update callbacks, decodes the
base64 payloads, saves them to ./received/, and asserts SHA-256 matches.

Exit code 0 = round-trip works. Non-zero = it doesn't, with a diagnostic.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import sys
from pathlib import Path

import acp
from acp.schema import (
    Implementation,
    ClientCapabilities,
)


# Same test bytes as the seller has — used for SHA-256 comparison.
EXPECTED_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c63f8cfc0000000020001e22165"
    "850000000049454e44ae426082"
)
EXPECTED_REPORT_BYTES = (
    b"INSPECTION REPORT (test)\n"
    b"Item: 2018 Mazda 6 hatchback\n"
    b"VIN ending: 8K2J\n"
    b"Mileage at inspection: 65,432 km\n"
    b"Tires: Continental PremiumContact, ~5000 km wear\n"
    b"Body: no rust, no panel repaint indicators\n"
    b"Mechanical: clean, no codes\n"
    b"Verdict: pass\n"
)


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[buyer]  %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


HERE = Path(__file__).parent
OUT_DIR = HERE / "received"
OUT_DIR.mkdir(parents=True, exist_ok=True)


class SpikeBuyer(acp.Client):
    """Minimal ACP client that records every session_update it sees."""

    def __init__(self) -> None:
        self.text_buf: list[str] = []
        self.image_blocks: list[bytes] = []
        self.resource_blocks: list[tuple[str, bytes, str]] = []  # (uri, bytes, mime)

    def on_connect(self, conn) -> None:
        log.info("Connected to seller.")

    async def session_update(self, session_id, update, **kwargs):
        # `update` is one of the SessionUpdate variants. For our spike, we
        # care about AgentMessageChunk (text + image + resource).
        kind = getattr(update, "session_update", "?")
        log.info("session_update kind=%s", kind)

        content = getattr(update, "content", None)
        if content is None:
            return

        ctype = getattr(content, "type", None)

        if ctype == "text":
            self.text_buf.append(content.text)
            log.info("  text len=%d", len(content.text))
        elif ctype == "image":
            data_b64 = content.data
            img_bytes = base64.b64decode(data_b64)
            self.image_blocks.append(img_bytes)
            sha = hashlib.sha256(img_bytes).hexdigest()
            log.info("  image bytes=%d mime=%s sha256=%s…",
                     len(img_bytes), content.mime_type, sha[:12])
        elif ctype == "resource":
            r = content.resource
            blob = getattr(r, "blob", None)
            uri = getattr(r, "uri", "<no-uri>")
            mime = getattr(r, "mime_type", None) or "application/octet-stream"
            if blob is None:
                # text resource
                payload = getattr(r, "text", "").encode("utf-8")
            else:
                payload = base64.b64decode(blob)
            self.resource_blocks.append((uri, payload, mime))
            sha = hashlib.sha256(payload).hexdigest()
            log.info("  resource uri=%s mime=%s bytes=%d sha256=%s…",
                     uri, mime, len(payload), sha[:12])

    # The Client protocol has many other methods; we accept defaults via
    # the Protocol base. Anything we don't override returns None.

    async def request_permission(self, *args, **kwargs):
        # Auto-allow for the spike. Real buyer would prompt the user.
        return None

    async def read_text_file(self, *args, **kwargs):
        return None

    async def write_text_file(self, *args, **kwargs):
        return None

    async def create_terminal(self, *args, **kwargs):
        return None


async def _drive(buyer: "SpikeBuyer") -> int:
    seller_script = str((HERE / "seller_acp.py").resolve())
    log.info("Spawning seller: %s", seller_script)

    async with acp.spawn_agent_process(
        buyer,
        sys.executable,
        seller_script,
    ) as (conn, proc):
        init = await conn.initialize(
            protocol_version=acp.PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
            client_info=Implementation(
                name="neuro-spati-spike-buyer",
                version="0.0.1",
                title="Spike buyer",
            ),
        )
        log.info("initialized; agent=%s", init.agent_info.name if init.agent_info else "?")

        sess = await conn.new_session(cwd=str(HERE))
        log.info("session=%s", sess.session_id)

        log.info("→ prompt")
        resp = await conn.prompt(
            prompt=[acp.text_block(text="Send me the photos and inspection report.")],
            session_id=sess.session_id,
        )
        log.info("← prompt stop=%s", resp.stop_reason)

        # Verify
        ok = True
        if not buyer.image_blocks:
            log.error("FAIL no image blocks received")
            ok = False
        else:
            got = buyer.image_blocks[0]
            if got == EXPECTED_PNG_BYTES:
                log.info("PASS image sha256 matches (%d bytes)", len(got))
                (OUT_DIR / "received_image.png").write_bytes(got)
            else:
                log.error("FAIL image bytes mismatch (%d vs %d)",
                          len(got), len(EXPECTED_PNG_BYTES))
                ok = False

        if not buyer.resource_blocks:
            log.error("FAIL no resource blocks received")
            ok = False
        else:
            uri, got, mime = buyer.resource_blocks[0]
            if got == EXPECTED_REPORT_BYTES:
                log.info("PASS resource sha256 matches (%d bytes)", len(got))
                (OUT_DIR / "received_report.txt").write_bytes(got)
            else:
                log.error("FAIL resource bytes mismatch")
                ok = False

        if buyer.text_buf:
            joined = "".join(buyer.text_buf).strip()
            log.info("text received: %r", joined[:120])

        rc = 0 if ok else 2

        # Best-effort tell the seller to stop. The context manager exit
        # also kills the subprocess.
        try:
            proc.terminate()
        except Exception:
            pass

    return rc


async def main() -> int:
    buyer = SpikeBuyer()
    try:
        rc = await asyncio.wait_for(_drive(buyer), timeout=15.0)
    except asyncio.TimeoutError:
        log.error("FAIL spike timed out after 15s")
        rc = 3

    if rc == 0:
        print("\n=== SPIKE PASS ===")
        print(f"Image  bytes saved to: {OUT_DIR / 'received_image.png'}")
        print(f"Report bytes saved to: {OUT_DIR / 'received_report.txt'}")
        print("ACP can stream ImageContentBlock + EmbeddedResourceContentBlock end-to-end.")
        print("Architecture decision in v5 (photos via ACP) is unblocked at the API level.")
    else:
        print(f"\n=== SPIKE FAIL (rc={rc}) ===")
        print("See [buyer] / [seller] log lines above for the failing check.")
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
