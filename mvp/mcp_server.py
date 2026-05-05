"""
mcp_server.py — weekend MVP FastMCP server.

A minimal HTTP+SSE MCP server exposing the cars-pack@1 tool surface
for one or many local listings. Designed to be started in a
background thread from `seller.py serve` (single listing) or
`seller.py serve-multi` (multi listing — same process, one port,
catalog keyed by item_id).

Tools exposed (cars-pack@1 minimum):
  • view_listing(item_id)            → TextContent  — short summary
  • request_photos(item_id, kinds)   → list[ImageContent] — inline bytes
  • request_inspection_report(id)    → EmbeddedResource — typed blob
                                        (auto-detects mime from file
                                        extension: .pdf → application/pdf,
                                        .txt → text/plain, .md →
                                        text/markdown, else octet-stream)
  • request_vin(item_id)             → TextContent — denied stub
  • cancel_inquiry(conversation_id)  → TextContent — ack stub
  • submit_offer(...)                → TextContent — denied stub

Catalog model:
  • Single-listing path (seller.py serve sample_car.toml) — no
    catalog needed; ITEM_ID_DEFAULT + the global asset paths are used.
  • Multi-listing path (seller.py serve-multi listings/) — at boot,
    we read every *.toml in `MVP_LISTINGS_DIR` and build CATALOG:
    item_id → {title, summary, photos_dir, inspection_path}. Tool
    calls that pass a known item_id resolve to that listing's
    assets; unknown item_ids fall back to the global defaults so
    the single-listing demo keeps working.

  Per-item asset layout for multi-listing:
    sample_photos/<item_id>/*.png            — listing-specific photos
    sample_inspection_<item_id>.{pdf,txt,md} — listing-specific report
  Missing → global fallback (sample_photos/cover.png +
  sample_inspection.txt).

MVP scope cuts vs production:
  • Binds to 127.0.0.1 only (no public URL, no tunnel).
  • No grant policy: every call auto-grants. Production wires the
    per-tool grant policy from cars-pack/skills/seller-cars/SKILL.md.
  • No session_token binding to buyer pubkey — we trust whoever
    reaches localhost. Production binds session_token established
    over NIP-17 to the calling buyer's pubkey.
  • request_vin returns a hard-coded "user-confirm-required" denial.
  • request_photos serves the per-item dir if present, otherwise the
    fixture cover image; ignores `kinds` filter.

Security review notes (project-wide rule "always check prompt
injection"):
  • Tool args are typed (str / list[str]) — no eval, no shell.
  • Returned text content is from the seller's own files
    (sample_inspection.txt, fixture summary). No buyer-controlled
    content is ever echoed back inside a tool response.
  • Returned image bytes are read from disk (sample_photos/cover.png)
    and base64-encoded — opaque to the LLM; cannot carry instructions.
  • No filesystem traversal: we resolve fixture paths against
    `Path(__file__).parent` and the catalog dir at module load;
    `item_id` from caller is used only as a dict key into the
    pre-loaded CATALOG, never spliced into a path.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import sys
from pathlib import Path

import tomllib  # Python 3.11+ stdlib

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    BlobResourceContents,
    EmbeddedResource,
    ImageContent,
)


logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[mcp-srv] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("mvp-mcp-server")

# Quiet uvicorn's per-request access log so it doesn't bleed into the
# seller's interactive `Reply (blank to skip):` prompt in seller.py serve.
# Tool-call activity is still logged via our own `log.info` calls below.
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)


HERE = Path(__file__).resolve().parent
PHOTOS_DIR = HERE / "sample_photos"
INSPECTION_PATH = HERE / "sample_inspection.txt"
COVER_PATH = PHOTOS_DIR / "cover.png"


# Minimal valid 1×1 red PNG, used as a default fixture if the user
# hasn't dropped a real cover.png into sample_photos/. Reused from
# spike/seller_mcp.py — known-good bytes.
_FALLBACK_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000"
    "00907753de0000000c49444154789c63f8cfc0000000020001e22165"
    "850000000049454e44ae426082"
)


def _ensure_fixtures() -> None:
    """Materialize the fallback fixtures on first run if missing.

    Avoids forcing the user to manually create files just to demo the
    photo flow. Runs once at module import; idempotent.
    """
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    if not COVER_PATH.exists():
        COVER_PATH.write_bytes(_FALLBACK_PNG)
        log.info("seeded fallback cover.png at %s", COVER_PATH)
    if not INSPECTION_PATH.exists():
        # Don't overwrite — sample_inspection.txt is checked into the
        # repo. Only seed if truly missing.
        INSPECTION_PATH.write_text(
            "INSPECTION REPORT (auto-generated MVP fixture)\n"
            "No real inspection on file. Drop your PDF or text report\n"
            "at this path and the seller's MCP server will return it.\n"
        )


_ensure_fixtures()


# Item identity. ITEM_ID_DEFAULT is the hardcoded id used when the
# caller omits `item_id` (single-listing demo). LISTING_TITLE / SUMMARY
# are the global fallback used for any unknown item_id.
ITEM_ID_DEFAULT = os.environ.get("MVP_ITEM_ID", "8f4a2b1e")
LISTING_TITLE = os.environ.get("MVP_LISTING_TITLE", "2018 Mazda 6 hatchback")
LISTING_SUMMARY = os.environ.get(
    "MVP_LISTING_SUMMARY",
    "65k mi, 1 owner, full Mazda service history. No accidents. 15,000 EUR. Prague.",
)

HOST = os.environ.get("MVP_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MVP_MCP_PORT", "8765"))


# In-memory catalog: item_id → {title, summary, photos_dir, inspection_path}.
# Empty until _load_catalog() runs (called from module init below if
# MVP_LISTINGS_DIR is set). Single-listing path leaves it empty and
# every call falls through to the global defaults.
CATALOG: dict[str, dict] = {}


def _detect_mime(path: Path) -> str:
    """Map a file extension to a MIME type. Falls back to
    application/octet-stream so unknown extensions still serialize
    correctly through MCP EmbeddedResource."""
    suffix = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md":  "text/markdown",
    }.get(suffix, "application/octet-stream")


def _per_item_inspection(item_id: str) -> Path | None:
    """Locate sample_inspection_<item_id>.{pdf,txt,md} or return None."""
    for ext in (".pdf", ".txt", ".md"):
        candidate = HERE / f"sample_inspection_{item_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def _per_item_photos_dir(item_id: str) -> Path | None:
    """Return sample_photos/<item_id>/ if it exists and contains
    *.png, else None."""
    candidate = PHOTOS_DIR / item_id
    if candidate.is_dir() and any(candidate.glob("*.png")):
        return candidate
    return None


def _load_catalog() -> None:
    """Read every *.toml in MVP_LISTINGS_DIR and populate CATALOG.

    Each listing's photos directory is sample_photos/<item_id>/
    and inspection report is sample_inspection_<item_id>.{pdf,txt,md}
    (auto-detected). Falls back to the global cover.png +
    sample_inspection.txt for items without per-item assets.
    """
    listings_dir = os.environ.get("MVP_LISTINGS_DIR", "").strip()
    if not listings_dir:
        return
    p = Path(listings_dir)
    if not p.is_dir():
        log.warning("MVP_LISTINGS_DIR=%s is not a directory; skipping catalog", p)
        return
    for toml_path in sorted(p.glob("*.toml")):
        try:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:  # noqa: BLE001
            log.warning("skipping %s: %s", toml_path.name, e)
            continue
        item_id = data.get("item_id")
        if not item_id:
            log.warning("skipping %s: no item_id", toml_path.name)
            continue
        photos_dir = _per_item_photos_dir(item_id) or PHOTOS_DIR
        inspection_path = _per_item_inspection(item_id) or INSPECTION_PATH
        CATALOG[item_id] = {
            "title": data.get("title", LISTING_TITLE),
            "summary": data.get("summary", LISTING_SUMMARY),
            "photos_dir": photos_dir,
            "inspection_path": inspection_path,
        }
        log.info(
            "catalog +%s: photos=%s inspection=%s",
            item_id, photos_dir, inspection_path.name,
        )
    log.info("catalog loaded: %d listing(s)", len(CATALOG))


_load_catalog()


def _resolve(item_id: str) -> dict:
    """Resolve item_id → {title, summary, photos_dir, inspection_path}.

    Falls back to the global single-listing defaults if item_id is
    unknown. Logs the resolution path so you can tell from server
    logs whether per-item or fallback assets were used.
    """
    if item_id in CATALOG:
        return CATALOG[item_id]
    return {
        "title": LISTING_TITLE,
        "summary": LISTING_SUMMARY,
        "photos_dir": PHOTOS_DIR,
        "inspection_path": INSPECTION_PATH,
    }


mcp = FastMCP("mvp-cars-seller", host=HOST, port=PORT)


@mcp.tool()
def view_listing(item_id: str = ITEM_ID_DEFAULT) -> str:
    """Return a short textual summary of the item.

    The first call a buyer's agent makes after `tools/list`. Confirms
    the item exists and grabs the human-readable description before
    asking for binary content.
    """
    entry = _resolve(item_id)
    via = "catalog" if item_id in CATALOG else "fallback"
    log.info("view_listing(item_id=%s) via=%s", item_id, via)
    return f"{entry['title']}\n{entry['summary']}"


@mcp.tool()
def request_photos(
    item_id: str = ITEM_ID_DEFAULT,
    kinds: list[str] | None = None,
) -> list[ImageContent]:
    """Return photos for `item_id` as inline ImageContent blocks.

    Resolution: if sample_photos/<item_id>/ exists with *.png inside,
    return all of them. Otherwise return the global fallback
    sample_photos/cover.png as a single image.

    MVP scope: ignores `kinds`. Production cars-pack@1 sellers apply
    the per-kind grant policy (auto for cover/exterior/interior/
    engine_bay; user-confirm for license_plate/interior_with_documents).
    """
    entry = _resolve(item_id)
    via = "catalog" if item_id in CATALOG else "fallback"
    log.info(
        "request_photos(item_id=%s, kinds=%s) via=%s photos_dir=%s",
        item_id, kinds, via, entry["photos_dir"],
    )

    photos_dir: Path = entry["photos_dir"]
    if photos_dir != PHOTOS_DIR:
        # Per-item directory: return every PNG inside.
        png_paths = sorted(photos_dir.glob("*.png"))
    else:
        # Global fallback: just the single cover.png.
        png_paths = [COVER_PATH]

    out: list[ImageContent] = []
    for path in png_paths:
        img_bytes = path.read_bytes()
        sha = hashlib.sha256(img_bytes).hexdigest()
        log.info("  → photo %s bytes=%d sha=%s…", path.name, len(img_bytes), sha[:12])
        out.append(
            ImageContent(
                type="image",
                data=base64.b64encode(img_bytes).decode("ascii"),
                mimeType="image/png",
            )
        )
    return out


@mcp.tool()
def request_inspection_report(item_id: str = ITEM_ID_DEFAULT) -> EmbeddedResource:
    """Return the inspection report as an embedded binary resource.

    Resolution: if sample_inspection_<item_id>.{pdf,txt,md} exists,
    return it (with the matching MIME type). Otherwise fall back to
    the global sample_inspection.txt fixture.

    MIME type is auto-detected from the file extension via
    `_detect_mime` — drop a real `.pdf` next to the `.toml` and the
    server will return it as application/pdf.

    Production sellers return the actual PDF from a real
    pre-purchase inspection, attached with a signed attestation
    referencing the inspection event.
    """
    entry = _resolve(item_id)
    via = "catalog" if item_id in CATALOG else "fallback"
    inspection_path: Path = entry["inspection_path"]
    log.info(
        "request_inspection_report(item_id=%s) via=%s file=%s",
        item_id, via, inspection_path.name,
    )

    blob_bytes = inspection_path.read_bytes()
    sha = hashlib.sha256(blob_bytes).hexdigest()
    mime = _detect_mime(inspection_path)
    log.info(
        "  → report bytes=%d sha=%s… mime=%s",
        len(blob_bytes), sha[:12], mime,
    )
    return EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri=f"local://inspection/{item_id}",
            mimeType=mime,
            blob=base64.b64encode(blob_bytes).decode("ascii"),
        ),
    )


@mcp.tool()
def request_vin(item_id: str = ITEM_ID_DEFAULT) -> str:
    """Always user-confirm: return a denial in the MVP.

    Production wires this to `mcp_grant_decision(...)` which prompts
    the seller's user before disclosing the full VIN. MVP cuts the
    interactive step and returns a stable denial so buyer agents
    can exercise the negative branch.
    """
    via = "catalog" if item_id in CATALOG else "fallback"
    log.info("request_vin(item_id=%s) via=%s → DENY (MVP default policy)", item_id, via)
    return (
        "DENIED: full VIN requires explicit user confirmation. "
        "MVP server returns deny by default. Production wiring "
        "will prompt the seller's user via mcp_grant_decision."
    )


@mcp.tool()
def submit_offer(
    item_id: str = ITEM_ID_DEFAULT,
    price_cents: int = 0,
    conditions: str = "",
) -> str:
    """Stub — returns a polite refusal in the MVP.

    Production wires this to the negotiation state machine in
    `seller/src/chaos_seller/negotiation.py` (≤ 5 rounds,
    ≤ 1000 chars per offer). MVP doesn't simulate negotiation.
    """
    log.info(
        "submit_offer(item_id=%s, price_cents=%d, conditions=%s)",
        item_id, price_cents, conditions[:80],
    )
    return (
        "STUB: MVP server does not simulate offers. "
        "Production cars-pack@1 negotiation flow ships in "
        "seller/ + buyer/ components."
    )


@mcp.tool()
def cancel_inquiry(conversation_id: str = "") -> str:
    """Acknowledge an inquiry-cancel from the buyer."""
    log.info("cancel_inquiry(conversation_id=%s)", conversation_id)
    return "ACK: inquiry cancelled."


def serve_blocking() -> None:
    """Start the FastMCP HTTP+SSE server. Blocks the current thread."""
    log.info("MVP MCP server starting on http://%s:%d/sse", HOST, PORT)
    mcp.run(transport="sse")


if __name__ == "__main__":
    serve_blocking()
