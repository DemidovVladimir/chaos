# buyer — IMPLEMENTATION_PLAN.md

Phased plan for the buyer-side production agent. Mirrors
`../seller/IMPLEMENTATION_PLAN.md` but focused on the four buyer-side
deltas:

- Filter authoring (translating user wants into REQ filters)
- The evaluation rubric from
  `../verticals/verticals/cars-pack/skills/buyer-cars/SKILL.md`
- MCP **CLIENT** side (HTTP+SSE FastMCP client dialing the seller's
  `["mcp", url]` tag, calling `tools/list`, then `tools/call` per ask)
- Local inbox at `~/.chaos/buyer/inbox/<conversation>.jsonl`

> Source-of-truth references this plan touches:
>
> - `../AGENTS.md`, `../PROTOCOL.md`
> - `../mvp/buyer.py`, `../mvp/shared.py`
> - `../verticals/verticals/cars-pack/skills/buyer-cars/SKILL.md`
> - `../spike/buyer_mcp.py` — the proven MCP HTTP+SSE client spike
>   (bootstrap via `tools/list`, binary content via `ImageContent` /
>   `EmbeddedResource`, multi-seller fanout)
> - Hermes upstream:
>   - `hermes-agent/website/docs/guides/build-a-hermes-plugin.md`
>   - `hermes-agent/hermes_cli/plugins.py` for the `PluginContext`
>     surface
>   - `hermes-agent/tools/mcp_tool.py` — Hermes already speaks MCP;
>     the same `mcp` Python SDK is reused on the buyer side
>   - `hermes-agent/plugins/memory/honcho/__init__.py` as a clean
>     `register(ctx)` reference

## Phase 1 — plumbing + REQ subscription

### Goal

Plugin loads, holds the buyer identity, subscribes to Mode A relay
with a cars-tag filter, dedupes events, prints matches.

### Steps

1. `pyproject.toml` — entry point
   `[project.entry-points."hermes_agent.plugins"]
    chaos-buyer = "chaos_buyer"`.
2. `plugin.yaml` per `buyer/README.md`.
3. `config.py` — `BuyerConfig` frozen dataclass loaded from
   `~/.chaos/buyer.yaml`.
4. `identity.py` — keypair load/save mode 0600. Same shape as the
   seller side; the file is at
   `~/.chaos/keys/buyer.key`.
5. `input_safety.py` — copy of the layer-1 sanitizer.
6. `filters.py` — translate user wants into a NIP REQ filter.

   - `from_user_want(want: dict) -> dict` returning the filter shape
     in `PROTOCOL.md` § "Subscriptions". Accepts make/model lists,
     year ranges (translated to bucket sets), price bands, location
     prefixes (`"EU/CZ/%"`), `since_days`.
   - `to_filter_list(filters: list[dict]) -> FiltersList` —
     `pynostr` adapter.

7. `subscribe.py`:

   - `start(rm, sub_id, filters)` — wraps
     `rm.add_subscription_on_all_relays`.
   - `iter_events(rm, sub_id) -> Iterator[Event]` — drains
     `rm.message_pool` and dedupes by `event.id` against an LRU.
   - `cache_seen(item_id) -> None` — persistent dedup at
     `~/.chaos/buyer/seen.jsonl` so we don't notify the user
     twice for the same listing across restarts.

8. `tools_subscribe.py`:

   - `create_filter({"name": "...", "want": {...}})`
   - `list_filters({})`
   - `pause_filter({"name": "..."})`
   - `delete_filter({"name": "..."})`

9. Wire `__init__.py::register(ctx)`. Same shape as the seller
   plugin; tools registered under the
   `"chaos-buyer"` toolset.

10. `evaluator.py` skeleton — accept an event, print to user, do not
    yet apply the rubric. Day-2-equivalent rubric work moves into
    Phase 3 once the photo path is live.

### Phase-1 exit criteria

- `hermes chaos-buyer watch` runs, subscribes to the relay
  set, and prints any matching kind-30402 event with the cover
  facets — including the `["mcp", url]` and `["pack", "cars-pack@1"]`
  tags it carries.
- `seen.jsonl` survives a process restart.

## Phase 2 — inquiry sender (NIP-17) + MCP client round-trip

### Goal

Apply hard-red-flag heuristics that don't need photo bytes. Send an
inquiry over NIP-17. Open an MCP HTTP+SSE
session to the seller's MCP URL, run the bootstrap (`tools/list`),
and complete one `request_photos` round-trip — exactly the shape the
spike at `spike/buyer_mcp.py` proved.

### Steps

1. `evaluator.py`. Take just the *hard red flags* from
   `verticals/cars-pack/skills/buyer-cars/SKILL.md` § "Evaluation rubric"
   that we can compute without the photo bytes (which only arrive
   later via MCP). Phase-2 scope:

   - Asking price > 1.5× market median (stub the
     `market_comp` integration; return `None` if no comp data).
   - Asking price < 0.6× market median (same stub).
   - `accident_history: none_known` but description contains
     `"crash" | "collision" | "repair"`.
   - Seller pubkey age < 7 days AND prior listings < 1 (computed
     from local cache of seen events).

   Soft red flags + green flags + photo-based hard flags wait for
   Phase 3 when the photo path is wired and `market_comp` is live.

2. `inquiry.py`:

   - `build_payload(item_id, asks: list[str], session_token: str) ->
      dict` — builds the rumor content per `PROTOCOL.md` §
     "1-to-1 messaging". Rumor type is `mcp_inquiry_open`; payload
     carries `{type, item_id, buyer_pubkey, session_token, asks}`.
     The buyer gets the seller's MCP HTTP URL from the matched
     listing's `["mcp", url]` tag — it is NOT inside the rumor.
   - `send(rm, sk, recipient_pk, payload)` — Phase-2 NIP-17
     (`# TODO(phase-3): replace with NIP-17 gift wrap`); Phase-3
     swaps to NIP-17.
   - `await_reply(rm, sk, sub_id, *, timeout: float)` — pulls the
     seller's reply from the inbox subscription.

3. `inbox.py` — append-only JSONL at
   `~/.chaos/buyer/inbox/<conversation_id>.jsonl`. One line per
   event we send or receive, plus one line per MCP tool call /
   response. No decrypted content for stored DMs is kept beyond a
   7-day window unless the user opts in (AGENTS.md rule 5 — minimize
   custody).

4. `mcp_client.py`. Based on `spike/buyer_mcp.py`. Thin wrapper
   around the `mcp` Python SDK's `ClientSession` + `sse_client`:

   ```python
   from mcp import ClientSession
   from mcp.client.sse import sse_client

   async def connect(url: str) -> tuple[ClientSession, ...]:
       async with sse_client(url) as (read, write):
           async with ClientSession(read, write) as session:
               await session.initialize()
               yield session
   ```

   Exposed surface: `connect(url) -> ClientSession`,
   `list_tools(session)`, `call_tool(session, name, arguments) ->
   list[ContentBlock]`, plus a helper that unwraps `ImageContent` /
   `EmbeddedResource` / `TextContent` blocks, applies the per-block
   size cap from `BuyerConfig.mcp.max_image_bytes_per_response`, and
   writes bytes onto disk.

5. `tools_inquire.py`:

   - `send_inquiry({"item_id": "...", "asks": [...]})`
   - `mcp_connect({"item_id": "..."})` — opens the MCP HTTP+SSE
     session to the seller's `["mcp", url]` tag and calls
     `tools/list`. Returns the tool surface the seller advertises.
   - `mcp_call_tool({"item_id": "...", "tool_name": "...",
     "arguments": {...}})` — dispatches a single `tools/call` and
     returns the unwrapped content blocks (with byte paths for any
     `ImageContent` / `EmbeddedResource`).
   - `list_inquiries({})`

### Phase-2 exit criteria

- A staged listing whose description contains "front collision
  repair" but whose tags include `accident_history=none_known` is
  flagged as a hard red flag and never surfaces to the user.
- An inquiry round-trip via NIP-17 against an MVP `mvp/seller.py`
  works and lands an entry in the inbox JSONL.
- `mcp_connect` against the spike seller exposes the cars-pack@1
  tool surface; `mcp_call_tool("request_photos", ...)` returns at
  least one `ImageContent` block whose decoded bytes land on disk.

## Phase 3 — NIP-17 + full evaluator + photo-based flags

### Goal

Production-shaped DM path (NIP-17 sealed gift wraps over NIP-44).
Full buyer-cars rubric, including the soft/green flags and
photo-derived flags computed from MCP-delivered inline bytes.

### Steps

1. Swap `inquiry.send` to NIP-17: rumor (kind 14) → seal (kind 13,
   NIP-44 to recipient) → gift wrap (kind 1059, NIP-44 from
   ephemeral keypair). The rumor type stays `mcp_inquiry_open` with
   a `session_token`. Drop the NIP-17 path from the production
   path; keep it only inside `mvp/` for the legacy CLI shortcut.

2. Full `evaluator.py`:

   - All flag families from
     `verticals/cars-pack/skills/buyer-cars/SKILL.md` § "Evaluation rubric".
   - Photo-based flags run on the inline bytes returned from
     `request_photos` — never on a URL, never on a remote fetch.
   - `reverse_image_check` is invoked via the local capability
     MCP (Weeks 5-6) on the same bytes. For Phase 3, the call is
     stubbed with a `WARN` log if no MCP is configured.
   - EXIF / perceptual-hash checks run on the decoded
     `ImageContent.data` bytes the seller sent through MCP.

3. `attestation.py` — verify any seller-signed attestation events
   referenced by the listing.

4. End-to-end on a single laptop with the seller plugin:

   - Seller publishes a listing with
     `["mcp", "https://<seller>/sse"]` and
     `["pack", "cars-pack@1"]`.
   - Buyer's filter matches it; evaluator does not flag it on the
     metadata-only checks.
   - Buyer sends an NIP-17 inquiry carrying a `session_token`.
   - Seller replies with which asks it grants.
   - Buyer's `mcp_client` dials the listing's `["mcp", url]`, calls
     `tools/list`, then `mcp_call_tool("request_photos", ...)` and
     `mcp_call_tool("request_inspection_report", ...)`.
   - All inline `ImageContent` / `EmbeddedResource` bytes land
     under `~/.chaos/buyer/inbox/<convo>/photos/` and
     `documents/`.
   - `reverse_image_check` runs over the same bytes; soft/green
     flags surface to the user.

### Phase-3 exit criteria

- `pytest buyer/tests/test_mcp_client.py` — fake-server in-process
  test passes (an in-process FastMCP server emits 3 ImageContent
  + 1 EmbeddedResource; client decodes and writes 4 files).
- Two-machine manual run completes with a 4-photo + 1-PDF stream.
- No HTTP request observed leaving the buyer's machine to anything
  other than (a) the relay, (b) the seller's `["mcp", url]`
  endpoint. (Verify with `tcpdump` or `mitmproxy` once.)

## Phase 4 — negotiation, vin_decode, CLI polish

### Goal

Buyer can submit offers, decode VINs locally, and the
`hermes chaos-buyer {watch, inquire, status}` UX is polished
enough for a public demo.

### Steps

1. `negotiation.py` — round tracking (≤ 5 rounds), market-comp-driven
   counter draft, idempotent `submit_offer` calls through the MCP
   tool surface (`mcp_call_tool("submit_offer", ...)`).

2. `tools_negotiate.py`:

   - `draft_offer({"item_id": "...", "stance": "fair|low|high"})`
   - `accept_offer({"item_id": "...", "terms": {...}})` — always
     blocks on explicit user confirmation via `notify_user`.
   - `reject_offer({"item_id": "...", "reason": "..."})`
   - `counter_offer(...)` — wraps `mcp_call_tool("submit_offer",
     ...)`.

3. `vin_decode` MCP integration — local-only, public WMI registry,
   no third-party broker.

4. CLI polish: rich-format the `status` output, persist
   `pending_inquiries`, surface tool-call traces in `hermes`
   verbose mode.

5. Final: every binary content path uses MCP `ImageContent` /
   `EmbeddedResource` blocks returned from a tool call on the
   seller's MCP server. No HTTP file URLs anywhere in the buyer
   tree.

## Files to create

In `buyer/src/chaos_buyer/`:

| File | One-line description |
|---|---|
| `__init__.py` | Hermes entry point: `register(ctx)` |
| `config.py` | `BuyerConfig` frozen dataclass loaded from `~/.chaos/buyer.yaml` |
| `identity.py` | Keypair load/save mode 0600 |
| `input_safety.py` | Layer-1 sanitizer (copy of seller's) |
| `filters.py` | Translate user wants to NIP REQ filters |
| `subscribe.py` | REQ subscription, dedupe, persistent seen-cache |
| `evaluator.py` | Apply buyer-cars rubric (hard / soft / green flags) |
| `inquiry.py` | Build + encrypt + publish NIP-17 inquiry; await reply |
| `mcp_client.py` | MCP HTTP+SSE client (FastMCP); receive `ImageContent` blocks |
| `negotiation.py` | Round tracking, market-comp-driven counter draft |
| `inbox.py` | Append-only JSONL conversation log + photos folder |
| `attestation.py` | Verify seller-signed attestation events |
| `tools_subscribe.py` | Tool handlers: `create_filter`, `list_filters`, `pause_filter` |
| `tools_inquire.py` | Tool handlers: `send_inquiry`, `mcp_connect`, `mcp_call_tool`, `list_inquiries` |
| `tools_negotiate.py` | Tool handlers: `draft_offer`, `accept_offer`, `reject_offer` |
| `schemas.py` | JSON-schema dicts for every tool above |
| `main.py` | CLI: `chaos-buyer {watch, inquire, status}` |

## Hermes plugin entry-point shape

```python
# buyer/src/chaos_buyer/__init__.py
"""Hermes plugin entry point for the chaos buyer agent."""
from __future__ import annotations

import logging

from . import (
    schemas,
    tools_subscribe,
    tools_inquire,
    tools_negotiate,
    main,
)

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Wire schemas to handlers and register hooks.

    Called exactly once at Hermes startup. ``ctx`` is a
    ``PluginContext`` instance (see hermes_cli/plugins.py).
    If this function raises, the plugin is disabled but Hermes
    continues fine.
    """
    # subscribe toolset
    ctx.register_tool(
        name="create_filter",
        toolset="chaos-buyer",
        schema=schemas.CREATE_FILTER,
        handler=tools_subscribe.create_filter,
    )
    ctx.register_tool(
        name="list_filters",
        toolset="chaos-buyer",
        schema=schemas.LIST_FILTERS,
        handler=tools_subscribe.list_filters,
    )
    ctx.register_tool(
        name="pause_filter",
        toolset="chaos-buyer",
        schema=schemas.PAUSE_FILTER,
        handler=tools_subscribe.pause_filter,
    )

    # inquire toolset
    ctx.register_tool(
        name="send_inquiry",
        toolset="chaos-buyer",
        schema=schemas.SEND_INQUIRY,
        handler=tools_inquire.send_inquiry,
    )
    ctx.register_tool(
        name="mcp_connect",
        toolset="chaos-buyer",
        schema=schemas.MCP_CONNECT,
        handler=tools_inquire.mcp_connect,
    )
    ctx.register_tool(
        name="mcp_call_tool",
        toolset="chaos-buyer",
        schema=schemas.MCP_CALL_TOOL,
        handler=tools_inquire.mcp_call_tool,
    )

    # negotiate toolset
    ctx.register_tool(
        name="draft_offer",
        toolset="chaos-buyer",
        schema=schemas.DRAFT_OFFER,
        handler=tools_negotiate.draft_offer,
    )
    ctx.register_tool(
        name="accept_offer",
        toolset="chaos-buyer",
        schema=schemas.ACCEPT_OFFER,
        handler=tools_negotiate.accept_offer,
    )
    ctx.register_tool(
        name="reject_offer",
        toolset="chaos-buyer",
        schema=schemas.REJECT_OFFER,
        handler=tools_negotiate.reject_offer,
    )

    # ship the buyer-cars skill
    from pathlib import Path
    skill_md = Path(__file__).parent.parent.parent / "skills" / "buyer-cars" / "SKILL.md"
    if skill_md.exists():
        ctx.register_skill("buyer-cars", skill_md)

    ctx.register_cli_command(
        name="chaos-buyer",
        help="Manage the chaos buyer agent",
        setup_fn=main.setup_argparse,
        handler_fn=main.dispatch,
    )

    logger.info("chaos-buyer plugin registered")
```

## MCP exact shapes used (quoted from upstream + spike)

`mcp` Python SDK (pinned to `mcp==1.27.0`, the version that the
spike at `spike/buyer_mcp.py` proved):

```python
from mcp import ClientSession
from mcp.client.sse import sse_client
# Content block types come back from session.call_tool().content:
# - mcp.types.TextContent      (type="text", text=str)
# - mcp.types.ImageContent     (type="image", data=base64, mimeType=str)
# - mcp.types.EmbeddedResource (type="resource", resource.blob/uri/mimeType)
```

Buyer-side use of these: `session.call_tool(name, arguments)` returns
a `CallToolResult` whose `.content` is a list of those three block
types. We unwrap each block:

```python
for block in result.content:
    if block.type == "image":
        img_bytes = base64.b64decode(block.data)
        out = inbox_dir / "photos" / f"{idx:03d}.{ext_for(block.mimeType)}"
        out.write_bytes(img_bytes)
    elif block.type == "resource":
        blob_bytes = base64.b64decode(block.resource.blob)
        out = inbox_dir / "documents" / safe_name(block.resource.uri)
        out.write_bytes(blob_bytes)
    elif block.type == "text":
        text_blocks.append(block.text)
```

## Worked example — inquiry through to inbox

```text
# 0. Subscription (Phase 1)
flt = filters.from_user_want({
    "make": ["mazda"],
    "year_range": (2015, 2020),
    "transmission": ["manual"],
    "location_prefix": ["EU/CZ/%"],
    "price_band": ["10k-20k EUR"],
})
subscribe.start(rm, "cars-watch", [flt])

# 1. Listing arrives
for ev in subscribe.iter_events(rm, "cars-watch"):
    item = parse_listing(ev)              # picks up ["mcp", url] + ["pack", "cars-pack@1"]
    sanitized_summary = input_safety.sanitize(item.summary, source="seller_listing", key=ev.id)
    flags = evaluator.evaluate(item, ev)
    if flags.has_hard_red_flag():
        continue                          # auto-suppress
    notify_user(item, flags)              # via Hermes notify_user

# 2. User says "ask about this one"
asks = ["full_description", "service_history", "photos:exterior",
        "photos:engine_bay", "inspection_at_shop", "delivery_options"]
session_token = secrets.token_urlsafe(24)
payload = inquiry.build_payload(item.id, asks, session_token=session_token)
inquiry.send(rm, my_sk, item.seller_pubkey, payload)
inbox.append(item.id, role="me", payload=payload)

# 3. Seller's NIP-17 reply (granted asks)
reply = inquiry.await_reply(rm, my_sk, "inbox-sub", timeout=120)
inbox.append(item.id, role="seller", payload=reply)

# 4. MCP HTTP+SSE session for granted asks
async with mcp_client.connect(item.mcp_tag) as session:
    tools = await mcp_client.list_tools(session)
    inbox.append(item.id, role="me", kind="mcp_tools_list", payload={"tools": [t.name for t in tools]})

    for ask in reply.granted:
        if ask.startswith("photos:"):
            blocks = await mcp_client.call_tool(
                session,
                "request_photos",
                {"item_id": item.id, "kinds": [ask.split(":", 1)[1]], "session_token": session_token},
            )
        elif ask == "inspection_at_shop":
            blocks = await mcp_client.call_tool(
                session,
                "request_inspection_report",
                {"item_id": item.id, "session_token": session_token},
            )
        # writes ImageContent / EmbeddedResource bytes to disk:
        # ~/.chaos/buyer/inbox/<item_id>/photos/
        # ~/.chaos/buyer/inbox/<item_id>/documents/
        inbox_entry = mcp_client.persist_blocks(blocks, inbox_dir=BUYER_INBOX / item.id)

# 5. Run reverse_image_check on the inline bytes (no URLs)
for photo in inbox_entry.photos:
    result = reverse_image_check(photo.read_bytes(), tier="thorough")
    if result.is_stock and result.similarity >= 0.92:
        flags.add_hard_red_flag(f"stock photo similarity {result.similarity}")

# 6. Surface to user with rubric verdict + photo paths
notify_user_with_evaluation(item, flags, inbox_entry)
```

## Tests to write first (TDD-shaped)

Under `buyer/tests/`:

| Test | What it validates |
|---|---|
| `test_filters.py::test_year_range_to_buckets` | A `(2015, 2020)` range expands to the 6 discrete year tag values |
| `test_filters.py::test_price_band_inclusion` | `5k-10k EUR` is in the canonical band set |
| `test_filters.py::test_no_filter_emits_full_relay_query` | A user with empty wants still emits a valid `kinds=[30402]` filter |
| `test_subscribe.py::test_dedupes_by_event_id_across_relays` | Two relays delivering the same event id surface only once |
| `test_subscribe.py::test_seen_cache_survives_restart` | After restart, a previously-notified id is suppressed |
| `test_evaluator.py::test_hard_red_flag_overpriced` | `price > 1.5×median` is auto-suppressed |
| `test_evaluator.py::test_hard_red_flag_accident_contradiction` | tag `accident_history=none_known` + description "collision repair" → hard flag |
| `test_evaluator.py::test_inquiry_grant_policy_denies_vin_full_without_user` | (Mirror of seller test) — buyer never auto-shares the user's VIN-equivalent PII |
| `test_evaluator.py::test_buyer_pii_never_in_outgoing_inquiry` | A buyer's name, phone, address never end up in the rumor content |
| `test_input_safety.py::test_listing_description_wrapped` | Seller's description is sanitized before any LLM-facing surface sees it |
| `test_inquiry.py::test_inquiry_payload_shape_matches_protocol` | Payload matches `PROTOCOL.md` § "1-to-1 messaging" exactly (`mcp_inquiry_open` + session_token) |
| `test_inquiry.py::test_inquiry_pow_skipped` | DM is *not* PoW-mined (per PROTOCOL.md) |
| `test_mcp_client.py::test_mcp_session_streams_image_blocks` | In-process FastMCP server returns 3 `ImageContent` blocks; client writes 3 files into the inbox |
| `test_mcp_client.py::test_mcp_session_streams_embedded_resource` | An `EmbeddedResource` is decoded and saved to `documents/` |
| `test_mcp_client.py::test_mcp_session_rejects_oversized_block` | A 50 MB inline image is refused (cap to e.g. 10 MB per block) |
| `test_inbox.py::test_inbox_jsonl_append_only` | Appending entries keeps prior entries unchanged |
| `test_inbox.py::test_inbox_no_decrypted_content_after_7_days` | The retention sweeper drops the `cleartext` field of older entries |
| `test_negotiation.py::test_round_cap_at_5` | Sixth counter is rejected |

Run target: `pytest buyer/tests/ -q`.

## Open questions for the engineer

1. **`pynostr`'s NIP-17 helpers.** Does
   `pynostr` 0.6.2 expose any helper for kind-1059 gift wraps? If
   not, write the seal/wrap manually using NIP-44 + an ephemeral
   keypair. Verify by sending a gift wrap to your own pubkey from
   a known-good third-party tool (e.g. `nak`).

2. **MCP SDK version pin.** The spike at `spike/buyer_mcp.py` proved
   `mcp==1.27.0`. Pin the buyer's `pyproject.toml` to the same
   version so the buyer and seller speak the same wire shapes.

3. **Inbox retention default.** What's the right window for
   keeping cleartext DM bodies? Buyer-cars SKILL.md doesn't say.
   Suggest 7 days; confirm with the user before shipping.

4. **What tools are *not* in the buyer plugin's allowlist.**
   `terminal`, `delegation`, `web`, `file` are forbidden per
   `buyer/README.md`. Verify the plugin's `forbidden_toolsets:`
   list in `plugin.yaml` actually disables them when Hermes loads
   the plugin.

5. **`market_comp` bootstrap.** It needs a recent corpus of
   on-network listings to compute medians. Until Mode A relay has
   ≥ 200 listings of the same make/model/year/mileage band,
   medians will be noisy. Soft-degrade: return `None` and skip
   that branch of the rubric.

6. **Reverse-image MCP bytes-in vs. URL-in.** Confirm the MCP
   accepts raw bytes (per `verticals/cars-pack/skills/buyer-cars/SKILL.md`
   note) — it MUST accept bytes; we must never upload a photo to
   any URL.

7. **Concurrent inquiries.** A user can have N open conversations.
   Make sure `mcp_client` `ClientSession`s are reusable (or cleanly
   disposed via `async with` per ask) and `inbox.jsonl` writes are
   flock'd.

## Definition of done for the buyer scaffold

- All 17 files in `src/chaos_buyer/` compile under
  `python -m compileall`.
- `ruff check buyer/` passes.
- `mypy buyer/src` (or `ty`) passes with no public-API errors.
- Test files run; most assert `assert False` (later phases fill
  them in).
- Live demo: `hermes chaos-buyer watch` runs against the
  Mode A relay, sees seller MVP listings, and prints them.
  `hermes chaos-buyer inquire <item_id>` round-trips an
  NIP-17 inquiry to the seller MVP. The MCP path is wired up to
  the point of receiving 3 test photos in a controlled localhost
  run; the production-quality two-machine NIP-17 + MCP run is
  Phase 3.
