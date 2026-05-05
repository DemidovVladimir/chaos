"""
mcp_client.py — weekend MVP FastMCP client.

Helper used by `agent_seeking.py` after a NIP-04 reply arrives carrying an
`mcp` URL: opens an HTTP+SSE session against the offering agent's MCP server,
runs `tools/list` (bootstrap), then exercises view_listing,
request_photos, and request_inspection_report. Saves received bytes
to `mvp/received/` with SHA-256 verification logging.

MVP scope cuts vs production:
  • No session_token binding — we connect to whatever URL the
    offering agent's listing tag advertised. Production seeking agent plugins bind
    a session_token established via NIP-17 to the MCP session.
  • URL whitelist is permissive (localhost + https only). Production
    plugins SSRF-defend (no private IP unless explicitly opted-in,
    block redirects to other hosts, enforce pack_whitelist).
  • All returned text content is logged verbatim. Production wraps
    every TextContent / ImageContent.mimeType / EmbeddedResource.uri
    string in `<untrusted>` and runs it through input_safety before
    surfacing to the LLM planner.

Security notes (project-wide "always check prompt injection" rule):
  • _safe_url_for_mvp() rejects URLs that aren't localhost or https,
    preventing the seeking agent from being tricked into connecting to a
    malicious public host via a crafted listing tag during the demo.
  • Image bytes are written to disk and SHA-logged — never decoded
    as text and never fed to the LLM directly.
  • Tool-result text is bounded by MAX_TEXT_PRINT below before being
    printed; we don't dump unbounded server-controlled strings to
    the user's terminal.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.sse import sse_client


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[mcp-cli] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("mvp-mcp-client")


HERE = Path(__file__).resolve().parent
RECEIVED_DIR = HERE / "received"

MAX_TEXT_PRINT = 500            # cap server-controlled text echoed to user
CONNECT_TIMEOUT_SECONDS = 10.0
CALL_TIMEOUT_SECONDS = 30.0
MAX_IMAGE_BYTES = 25_000_000    # mirror production seeking agent config cap


def _safe_url_for_mvp(url: str) -> str:
    """Validate a URL is OK to connect to in the MVP demo.

    Rejects non-http(s), and rejects http:// hosts other than localhost
    / 127.0.0.1. This is a minimal SSRF / scam-listing defense for the
    weekend demo. Production plugins must be far stricter (private IP
    blocklists, redirect blocking, host pinning to the listing's
    declared tag, pack_whitelist enforcement).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"refusing non-http(s) MCP URL: {url!r}")
    if parsed.scheme == "http":
        host = (parsed.hostname or "").lower()
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(
                f"refusing http:// MCP URL with non-local host {host!r}; "
                f"production should require https for non-local."
            )
    return url


def _truncate_for_print(text: str) -> str:
    if len(text) <= MAX_TEXT_PRINT:
        return text
    return text[:MAX_TEXT_PRINT] + f"… [truncated; total {len(text)} chars]"


def _save_image_block(block: Any, item_id: str) -> tuple[int, str, Path]:
    img_bytes = base64.b64decode(block.data)
    if len(img_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"image block exceeds MVP cap "
            f"({len(img_bytes)} > {MAX_IMAGE_BYTES} bytes)"
        )
    sha = hashlib.sha256(img_bytes).hexdigest()
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
    out = RECEIVED_DIR / f"{item_id}_cover.png"
    out.write_bytes(img_bytes)
    return len(img_bytes), sha, out


def _save_resource_block(block: Any, item_id: str) -> tuple[int, str, Path]:
    blob_bytes = base64.b64decode(block.resource.blob)
    if len(blob_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"resource block exceeds MVP cap "
            f"({len(blob_bytes)} > {MAX_IMAGE_BYTES} bytes)"
        )
    sha = hashlib.sha256(blob_bytes).hexdigest()
    RECEIVED_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".pdf" if block.resource.mimeType == "application/pdf" else ".txt"
    out = RECEIVED_DIR / f"{item_id}_inspection{suffix}"
    out.write_bytes(blob_bytes)
    return len(blob_bytes), sha, out


async def _query(url: str, item_id: str) -> dict:
    """Open MCP session against `url` and exercise the cars-pack tool surface."""
    safe = _safe_url_for_mvp(url)
    log.info("connecting to %s", safe)

    summary = ""
    image_info: tuple[int, str, Path] | None = None
    report_info: tuple[int, str, Path] | None = None
    tools_advertised: list[str] = []

    async with sse_client(safe) as (read, write):
        async with ClientSession(read, write) as session:
            init = await asyncio.wait_for(
                session.initialize(),
                timeout=CONNECT_TIMEOUT_SECONDS,
            )
            log.info(
                "initialized; server=%s v=%s",
                init.serverInfo.name, init.serverInfo.version,
            )

            tools_resp = await asyncio.wait_for(
                session.list_tools(),
                timeout=CALL_TIMEOUT_SECONDS,
            )
            tools_advertised = [t.name for t in tools_resp.tools]
            log.info("tools/list → %s", tools_advertised)

            if "view_listing" in tools_advertised:
                resp = await asyncio.wait_for(
                    session.call_tool("view_listing", {"item_id": item_id}),
                    timeout=CALL_TIMEOUT_SECONDS,
                )
                if not resp.isError:
                    for block in resp.content:
                        if getattr(block, "type", None) == "text":
                            summary = block.text
                            log.info(
                                "view_listing → %s",
                                _truncate_for_print(summary),
                            )

            if "request_photos" in tools_advertised:
                resp = await asyncio.wait_for(
                    session.call_tool(
                        "request_photos",
                        {"item_id": item_id, "kinds": ["cover", "exterior"]},
                    ),
                    timeout=CALL_TIMEOUT_SECONDS,
                )
                if resp.isError:
                    log.warning("request_photos returned error: %s", resp)
                else:
                    for block in resp.content:
                        if getattr(block, "type", None) == "image":
                            image_info = _save_image_block(block, item_id)
                            n, sha, path = image_info
                            log.info(
                                "image bytes=%d sha=%s… → %s",
                                n, sha[:12], path,
                            )

            if "request_inspection_report" in tools_advertised:
                resp = await asyncio.wait_for(
                    session.call_tool(
                        "request_inspection_report",
                        {"item_id": item_id},
                    ),
                    timeout=CALL_TIMEOUT_SECONDS,
                )
                if resp.isError:
                    log.warning("request_inspection_report error: %s", resp)
                else:
                    for block in resp.content:
                        if getattr(block, "type", None) == "resource":
                            report_info = _save_resource_block(block, item_id)
                            n, sha, path = report_info
                            log.info(
                                "report bytes=%d sha=%s… → %s",
                                n, sha[:12], path,
                            )

    return {
        "url": safe,
        "tools_advertised": tools_advertised,
        "summary": summary,
        "image_info": image_info,
        "report_info": report_info,
    }


def fetch_listing_assets(url: str, item_id: str = "8f4a2b1e") -> dict:
    """Synchronous entry point — agent_seeking.py calls this from its main loop."""
    return asyncio.run(_query(url, item_id))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mcp_client.py <mcp-sse-url> [item_id]")
        sys.exit(1)
    url = sys.argv[1]
    item_id = sys.argv[2] if len(sys.argv) > 2 else "8f4a2b1e"
    result = fetch_listing_assets(url, item_id)
    print("\n=== MCP fetch summary ===")
    print(f"  url:        {result['url']}")
    print(f"  tools:      {result['tools_advertised']}")
    if result["summary"]:
        print(f"  summary:    {_truncate_for_print(result['summary'])}")
    if result["image_info"]:
        n, sha, path = result["image_info"]
        print(f"  cover:      {n} bytes → {path} (sha {sha[:16]}…)")
    if result["report_info"]:
        n, sha, path = result["report_info"]
        print(f"  inspection: {n} bytes → {path} (sha {sha[:16]}…)")
