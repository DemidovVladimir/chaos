# =====================================================================
# SUPERSEDED — historical A2A spike, kept for reference only.
# The project chose MCP after the MCP spike passed. See
# spike/MCP_SPIKE_REPORT.md for the verdict and spike/seller_mcp.py /
# spike/buyer_mcp.py for the live wire.
# Do NOT copy this code into seller/ or buyer/ — the production scaffold
# is built on FastMCP, not on ACP/A2A.
# =====================================================================
"""
buyer_a2a.py — A2A buyer spike.

Spawns seller_a2a.py as a subprocess (local HTTP server), waits for it
to be ready, then sends an A2A SendMessage call via the official
Python `Client`. Captures the streamed Task / Artifact events,
extracts the binary FileParts, and SHA-256-verifies the bytes against
the known-expected payloads.

Exit 0 = ACP round-trip works over A2A's HTTP+JSON-RPC transport.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

from a2a.client import ClientFactory, ClientConfig
from a2a.client.card_resolver import A2ACardResolver
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TaskState,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[buyer]  %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


HOST = "127.0.0.1"
PORT = int(os.environ.get("A2A_PORT", "7421"))
SELLER_BASE = f"http://{HOST}:{PORT}"

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

HERE = Path(__file__).parent
OUT_DIR = HERE / "received_a2a"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _wait_for_port(host: str, port: int, timeout_s: float = 8.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


async def _run_round_trip() -> int:
    async with httpx.AsyncClient(timeout=10.0) as http:
        # 1. Fetch + parse the agent card via the SDK's resolver, which
        # tolerates v0.3 compat fields ('preferredTransport', 'url').
        resolver = A2ACardResolver(http, SELLER_BASE)
        card = await resolver.get_agent_card()
        log.info("card.name=%s skills=%d ifaces=%s",
                 card.name, len(card.skills),
                 [(i.protocol_binding, i.url) for i in card.supported_interfaces])

        # 2. Build a Client against this card
        factory = ClientFactory(ClientConfig(httpx_client=http))
        client = factory.create(card)
        log.info("client created")

        # 3. Build a SendMessage request
        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[Part(text="Send me the photos and inspection report.")],
        )
        req = SendMessageRequest(message=msg)
        log.info("→ send_message")

        # 4. Iterate streamed events. Each StreamResponse carries one of
        #    {task, message, status_update, artifact_update}.
        image_blocks: list[bytes] = []
        report_blocks: list[tuple[str, bytes, str]] = []
        text_buf: list[str] = []
        final_state = None

        async for stream_resp in client.send_message(req):
            kind = stream_resp.WhichOneof("payload")
            log.info("← event payload=%s", kind)
            if kind == "task":
                final_state = stream_resp.task.status.state
                for art in stream_resp.task.artifacts:
                    _extract_parts(art.parts, image_blocks, report_blocks, text_buf)
            elif kind == "message":
                _extract_parts(stream_resp.message.parts, image_blocks, report_blocks, text_buf)
            elif kind == "artifact_update":
                _extract_parts(
                    stream_resp.artifact_update.artifact.parts,
                    image_blocks, report_blocks, text_buf,
                )
            elif kind == "status_update":
                final_state = stream_resp.status_update.status.state

        log.info("final task state = %s",
                 TaskState.Name(final_state) if final_state else "?")

    # 5. Verify
    ok = True
    if not image_blocks:
        log.error("FAIL no image FilePart received")
        ok = False
    else:
        got = image_blocks[0]
        if got == EXPECTED_PNG_BYTES:
            log.info("PASS image sha256 matches (%d bytes)", len(got))
            (OUT_DIR / "received_image.png").write_bytes(got)
        else:
            log.error("FAIL image bytes mismatch (%d vs %d)",
                      len(got), len(EXPECTED_PNG_BYTES))
            ok = False

    if not report_blocks:
        log.error("FAIL no report FilePart received")
        ok = False
    else:
        name, got, mime = report_blocks[0]
        if got == EXPECTED_REPORT_BYTES:
            log.info("PASS report sha256 matches (%d bytes, name=%s mime=%s)",
                     len(got), name, mime)
            (OUT_DIR / "received_report.txt").write_bytes(got)
        else:
            log.error("FAIL report bytes mismatch")
            ok = False

    if text_buf:
        log.info("text received: %r", "".join(text_buf)[:120])

    return 0 if ok else 2


def _extract_parts(parts, image_blocks, report_blocks, text_buf) -> None:
    """Pull bytes / text out of a list of A2A Parts and into the buckets."""
    for p in parts:
        # protobuf oneof — inspect WhichOneof('content')
        which = p.WhichOneof("content")
        if which == "text":
            text_buf.append(p.text)
        elif which == "raw":
            mime = p.media_type or "application/octet-stream"
            name = p.filename or "(unnamed)"
            sha = hashlib.sha256(p.raw).hexdigest()
            log.info("  raw  name=%s mime=%s bytes=%d sha=%s…",
                     name, mime, len(p.raw), sha[:12])
            if mime.startswith("image/"):
                image_blocks.append(p.raw)
            else:
                report_blocks.append((name, p.raw, mime))
        elif which == "url":
            log.info("  url part: %s (would fetch)", p.url)
        else:
            log.info("  other part kind: %s", which)


async def main() -> int:
    seller_script = str((HERE / "seller_a2a.py").resolve())
    log.info("Spawning seller: %s on port %d", seller_script, PORT)

    proc = subprocess.Popen(
        [sys.executable, seller_script],
        stdout=subprocess.DEVNULL,
        stderr=sys.stderr,
        env={**os.environ, "A2A_PORT": str(PORT)},
    )

    try:
        if not _wait_for_port(HOST, PORT, timeout_s=10):
            log.error("seller did not bind to %s:%d in 10s", HOST, PORT)
            return 1

        log.info("seller is up, running round-trip")
        rc = await asyncio.wait_for(_run_round_trip(), timeout=15.0)
    except asyncio.TimeoutError:
        log.error("FAIL spike timed out")
        rc = 3
    except Exception as e:
        log.error("FAIL exception: %s: %s", type(e).__name__, e)
        rc = 4
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    if rc == 0:
        print("\n=== A2A SPIKE PASS ===")
        print(f"Image  bytes saved to: {OUT_DIR / 'received_image.png'}")
        print(f"Report bytes saved to: {OUT_DIR / 'received_report.txt'}")
        print("A2A over HTTP+JSON-RPC carries FileParts (binary) end-to-end.")
        print("Cross-network transport unblocked. Hermes integration: see README.")
    else:
        print(f"\n=== A2A SPIKE FAIL (rc={rc}) ===")
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
