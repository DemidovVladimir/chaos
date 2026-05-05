# (Historical -- written under the project's previous name "neuro-spati", now called "chaos".)
"""
buyer_mcp.py — neuro-spati MCP seeking agent spike.

Spawns TWO seller_mcp.py instances on different ports (alice@7501,
bob@7502), then for each offering agent in parallel:

  1. Opens an MCP HTTP+SSE session
  2. Calls `tools/list` (BOOTSTRAP — seeking agent learns what offering agent can do
     without prior knowledge)
  3. Calls `request_photos(...)` and `request_inspection_report(...)`
  4. Decodes the binary content blocks and SHA-256-verifies them

This proves three things at once:

  • bootstrap discovery (tools/list)
  • binary content (ImageContent + EmbeddedResource over SSE)
  • multi-offering agent fanout (one seeking agent, two offering agents, asyncio.gather)

Exit 0 = all three succeed. Non-zero = one failed; check stderr.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[seeking agent]   %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("seeking agent")


# Same bytes the offering agents carry — used for SHA verification.
EXPECTED_PNG_RED = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c63f8cfc0000000020001e22165"
    "850000000049454e44ae426082"
)
EXPECTED_PNG_BLUE = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c6360606000000000050001e201"
    "ed230000000049454e44ae426082"
)
EXPECTED_PNGS = {"alice": EXPECTED_PNG_RED, "bob": EXPECTED_PNG_BLUE}

HERE = Path(__file__).parent
OUT_DIR = HERE / "received_mcp"
OUT_DIR.mkdir(parents=True, exist_ok=True)


SELLERS = [
    {"name": "alice", "port": 7501},
    {"name": "bob",   "port": 7502},
]


def _wait_for_port(host: str, port: int, timeout_s: float = 8.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


async def _query_one_seller(name: str, port: int) -> dict:
    """Open MCP session, bootstrap, request photos + report, verify."""
    out: dict = {"name": name, "port": port, "ok": False, "errors": []}

    url = f"http://127.0.0.1:{port}/sse"
    log.info("[%s] connecting to %s", name, url)

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            log.info("[%s] initialized; server=%s v=%s",
                     name, init.serverInfo.name, init.serverInfo.version)

            # ── BOOTSTRAP — the seeking agent doesn't know in advance what tools
            # this offering agent exposes. tools/list is the discovery primitive.
            tools_resp = await session.list_tools()
            tool_names = [t.name for t in tools_resp.tools]
            log.info("[%s] tools/list → %s", name, tool_names)
            out["tools_advertised"] = tool_names

            if "request_photos" not in tool_names:
                out["errors"].append("offering agent doesn't expose request_photos")
                return out

            # ── BINARY — call request_photos, expect ImageContent
            photos = await session.call_tool(
                "request_photos",
                {"item_id": "8f4a2b1e", "kinds": ["exterior"]},
            )

            if photos.isError:
                out["errors"].append(f"request_photos returned error: {photos}")
                return out

            for block in photos.content:
                kind = getattr(block, "type", "?")
                log.info("[%s]   block.type=%s", name, kind)
                if kind == "image":
                    img_bytes = base64.b64decode(block.data)
                    sha = hashlib.sha256(img_bytes).hexdigest()
                    log.info("[%s]   image bytes=%d mime=%s sha=%s…",
                             name, len(img_bytes), block.mimeType, sha[:12])
                    out["image_bytes"] = img_bytes
                    out["image_sha"] = sha

            # ── BINARY (resource) — call request_inspection_report
            report = await session.call_tool("request_inspection_report",
                                              {"item_id": "8f4a2b1e"})
            if report.isError:
                out["errors"].append(f"request_inspection_report error: {report}")
                return out

            for block in report.content:
                kind = getattr(block, "type", "?")
                if kind == "resource":
                    blob_b64 = block.resource.blob
                    blob_bytes = base64.b64decode(blob_b64)
                    sha = hashlib.sha256(blob_bytes).hexdigest()
                    log.info("[%s]   report uri=%s mime=%s bytes=%d sha=%s…",
                             name, block.resource.uri, block.resource.mimeType,
                             len(blob_bytes), sha[:12])
                    out["report_bytes"] = blob_bytes
                    out["report_sha"] = sha

    out["ok"] = True
    return out


async def main() -> int:
    # 1. Spawn both offering agents in parallel
    procs: list[subprocess.Popen] = []
    for s in SELLERS:
        env = {**os.environ, "SELLER_NAME": s["name"], "MCP_PORT": str(s["port"])}
        p = subprocess.Popen(
            [sys.executable, str(HERE / "seller_mcp.py")],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=sys.stderr,
        )
        procs.append(p)

    try:
        # Wait for both ports to bind
        for s in SELLERS:
            if not _wait_for_port("127.0.0.1", s["port"], timeout_s=10):
                log.error("offering agent %s did not bind to port %d", s["name"], s["port"])
                return 1
        log.info("both offering agents up — running parallel queries")

        # 2. Query both in parallel — the fanout demo
        results = await asyncio.wait_for(
            asyncio.gather(*[
                _query_one_seller(s["name"], s["port"]) for s in SELLERS
            ], return_exceptions=True),
            timeout=15.0,
        )

        # 3. Verify each
        rc = 0
        for r in results:
            if isinstance(r, Exception):
                log.error("FAIL exception in fanout: %s", r)
                rc = 2
                continue

            name = r["name"]
            if not r["ok"]:
                log.error("[%s] FAIL %s", name, r.get("errors"))
                rc = 2
                continue

            expected = EXPECTED_PNGS[name]
            got = r.get("image_bytes")
            if got == expected:
                log.info("[%s] PASS image sha matches (%d bytes)", name, len(got))
                (OUT_DIR / f"{name}_image.png").write_bytes(got)
            else:
                log.error("[%s] FAIL image bytes mismatch (got %d, want %d)",
                          name, len(got or b""), len(expected))
                rc = 2

            rep = r.get("report_bytes")
            if rep and rep.startswith(b"INSPECTION REPORT"):
                log.info("[%s] PASS report received (%d bytes)", name, len(rep))
                (OUT_DIR / f"{name}_report.txt").write_bytes(rep)
            else:
                log.error("[%s] FAIL report missing or wrong shape", name)
                rc = 2

        return rc

    finally:
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                p.kill()


def cli() -> None:
    rc = asyncio.run(main())
    if rc == 0:
        print("\n=== MCP SPIKE PASS ===")
        print(f"Two offering agents, one seeking agent, parallel fanout, binary verified.")
        print(f"Bootstrap (tools/list) worked: seeking agent learned tool surface dynamically.")
        print(f"Outputs in: {OUT_DIR}")
    else:
        print(f"\n=== MCP SPIKE FAIL (rc={rc}) ===")
    sys.exit(rc)


if __name__ == "__main__":
    cli()
