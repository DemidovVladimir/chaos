# seller — IMPLEMENTATION_PLAN.md

Week-1-shaped plan for the seller-side production agent. This is the
plan one engineer follows to convert the scaffold under
`src/chaos_seller/` into a working Hermes plugin that
participates end-to-end in the protocol described in `../PROTOCOL.md`.

This is *Week 1* of the seller plugin work-stream (overall
`LAUNCH_PLAN.md` milestone is "Weeks 3-4 — Hermes plugin baseline").
Four engineering days; the rest of the milestone slips to Week 2.

> Source-of-truth references this plan touches:
>
> - `../CLAUDE.md` — non-negotiable rules
> - `../PROTOCOL.md` — wire format
> - `../mvp/seller.py`, `../mvp/shared.py` — runnable starter
> - `../verticals/cars-pack/skills/seller-cars/SKILL.md` — grant policy + flow
> - `../spike/seller_mcp.py` — the proven FastMCP HTTP+SSE seller
>   spike (cars-pack@1 tool surface), which `mcp_server.py` is
>   based on
> - Hermes upstream:
>   - `hermes-agent/website/docs/guides/build-a-hermes-plugin.md` —
>     plugin contract
>   - `hermes-agent/plugins/memory/honcho/__init__.py` — clean
>     `register(ctx)` reference
>   - `hermes-agent/hermes_cli/plugins.py` — concrete `PluginContext`
>     surface
>   - `hermes-agent/tools/mcp_tool.py`,
>     `hermes-agent/tools/mcp_serve.py` — Hermes already speaks MCP
>     (client + server side); no second peer transport is added by
>     this plugin

## Phase 1 — plumbing + Nostr publish path + inquiry decode

### Goal

A minimal Hermes plugin that loads, holds the seller identity,
publishes a NIP-99 listing with PoW, and decodes incoming NIP-04
inquiries (NIP-17 follows in Phase 3). No FastMCP server yet — this
phase is wire-format-only on the Nostr side.

### Steps

1. Write `pyproject.toml`. Declare the entry point:

   ```toml
   [project.entry-points."hermes_agent.plugins"]
   chaos-seller = "chaos_seller"
   ```

   Reference: `../seller/README.md` § "Hermes plugin shape" + the
   plugin guide §"Distribute via pip". Plugin discovery uses the
   `hermes_agent.plugins` entry-point group. Pin `mcp==1.27.0` —
   matches the version proven in `spike/seller_mcp.py`.

2. Write `plugin.yaml` per `seller/README.md` § "Hermes plugin shape".

3. Implement `config.py` — `SellerConfig` frozen dataclass.
   Loads `~/.chaos/seller.yaml`. Fail loud if `relays:` is
   empty. Validates `mcp_url` is `https://`. The `pack` field
   defaults to `cars-pack@1`.

4. Implement `identity.py` — port the keypair load/save logic from
   `mvp/shared.py::Identity` to `~/.chaos/keys/seller.key` mode
   0600. Add a `sign_event(ev: Event) -> Event` helper that calls
   `pynostr`'s `Event.sign(sk_hex)` so callers don't touch the secret
   key directly.

5. Implement `input_safety.py` — copy the Layer-1 sanitizer pattern
   per `../CLAUDE.md` § "Input safety". Functions:

   - `sanitize(text: str, *, source: str, key: str = "") -> str` —
     NFKC normalize, strip invisible, strip reserved tags, length
     cap, phrase-scan, wrap in `<untrusted source="..." key="...">`.
   - `is_suspicious(text: str) -> bool` — pure detector (no wrap).

6. Implement `catalog.py` — local item store. Items live at
   `~/.chaos/items/<uuid>/`. One method:

   - `load(item_id: str) -> Item`
   - `save(item: Item) -> None`
   - `iter_items() -> Iterator[Item]`
   - `photos_for(item_id: str, *, category) -> list[Path]`

7. Implement `publish.py`:

   - `build_event(item: Item, *, pubkey_hex: str, mcp_url: str,
     pack: str = "cars-pack@1") -> dict` — same as
     `mvp/shared.py::build_nip99_listing` but takes our typed `Item`
     and emits `["mcp", mcp_url]` and `["pack", pack]` tags.
   - `mine_pow(raw_event: dict, *, bits: int = 20) -> dict` — adds /
     replaces a `["nonce", "<n>", "<bits>"]` tag and bumps the nonce
     until the event id has `bits` leading zero bits. NIP-13.
   - `publish(rm: RelayManager, sk: PrivateKey, raw: dict) -> Event`
     — sign + publish + return Event.

8. Implement `tools_publish.py` — three Hermes tools wrapping the
   functions above:

   - `publish_item({"item_id": "..."})`
   - `archive_item({"item_id": "...", "reason": "..."})`
   - `update_item({"item_id": "...", "patch": {...}})`

   Each handler returns a JSON string (per the plugin guide rule).

9. Implement the Phase-1 form of `inquiry_listener.py`:

   - NIP-04 path **only**, copied from `mvp/seller.py`.
     Add a `# TODO(phase-3): replace with NIP-17 gift-wrap` comment so
     the ratchet is visible. (CLAUDE.md rule 7 — NIP-04 is MVP-only;
     this scaffold is week-1 of seller plugin, NIP-17 lands in
     Phase 3.)
   - The rumor's structured payload type is `mcp_inquiry_open` and
     carries `{ "type": "mcp_inquiry_open", "session_token": "...",
     "item_id": "...", "free_text": "..." }`.
   - Routes each inquiry's `free_text` through
     `input_safety.sanitize` BEFORE the LLM-facing surface ever sees
     it.
   - Binds `session_token → buyer_pubkey` in
     `mcp_server.SessionRegistry` so the upcoming MCP handshake can
     validate the token.

10. Wire `__init__.py::register(ctx)`:

    ```python
    from . import schemas, tools_publish, tools_inquire, tools_negotiate

    def register(ctx) -> None:
        ctx.register_tool(
            name="publish_item",
            toolset="chaos-seller",
            schema=schemas.PUBLISH_ITEM,
            handler=tools_publish.publish_item,
        )
        # ... archive_item, update_item, handle_inquiry, ...
        ctx.register_cli_command(
            name="chaos-seller",
            help="chaos seller agent",
            setup_fn=main.setup_argparse,
            handler_fn=main.dispatch,
        )
    ```

11. Smoke-test on Mode A relay: `hermes chaos-seller publish
    items/foo.toml`. Confirm the event lands on
    `wss://relay.<domain>` (use a third-party Nostr client to read it
    back) and the PoW count is ≥ 20. Confirm the `mcp` and `pack`
    tags are present and no `image` tag exists.

### Phase-1 exit criteria

- `hermes` starts cleanly with the plugin loaded; `/plugins` shows it.
- `publish_item` lands a kind-30402 event with cars-pack tags
  (`mcp`, `pack=cars-pack@1`) + PoW.
- No `image` tag and no public photo URL anywhere on the event.
- `inquiry_listener` decodes a NIP-04 DM, validates the
  `mcp_inquiry_open` rumor type, and binds the session token to the
  buyer's pubkey.

## Phase 2 — FastMCP server with cars-pack@1 tool surface

### Goal

Stand up `mcp_server.py` as a FastMCP HTTP+SSE server exposing the
cars-pack@1 tool surface. When a buyer's agent opens an MCP session
against the seller's public URL with a valid `session_token`, the
server resolves the bound buyer pubkey, runs each `tools/call`
through the per-tool grant policy, and returns photos as MCP
`ImageContent` blocks and inspection PDFs as `EmbeddedResource`
blocks.

This phase replaces the previously-planned ACP server. The proven
shape is in `../spike/seller_mcp.py`; `mcp_server.py` is the
production-shaped scaffold of that spike.

### Steps

1. Implement `grant_policy.py` — per-tool decision table from
   `verticals/cars-pack/skills/seller-cars/SKILL.md` § "Inquiry-handling
   policy". One entry per cars-pack@1 tool:

   ```python
   class Decision(Enum):
       GRANT     = "grant"     # execute the tool call
       ASK_USER  = "ask_user"  # blocks until user confirms
       DENY      = "deny"
   ```

   Default decisions per tool name (e.g. `request_vin → ASK_USER`,
   `request_photos → GRANT`, `request_phone_number → DENY`), plus a
   `PER_ARG_OVERRIDES` table that escalates specific argument values
   (e.g. `request_photos(kinds=["license_plate"]) → ASK_USER`), plus
   an `ALWAYS_USER_CONFIRM` set that always routes through `ASK_USER`
   regardless of defaults.

2. Implement `mcp_server.py`. This is the single hardest piece;
   read `spike/seller_mcp.py` end-to-end first — it's the proven
   reference.

   The server is a `FastMCP` instance:

   ```python
   from mcp.server.fastmcp import FastMCP
   from mcp.types import (
       BlobResourceContents,
       EmbeddedResource,
       ImageContent,
       TextContent,
   )

   mcp = FastMCP(name, host=host, port=port)

   @mcp.tool()
   def view_listing(item_id: str) -> str:
       ...

   @mcp.tool()
   def request_photos(
       item_id: str,
       kinds: list[str] | None = None,
   ) -> list[ImageContent]:
       ...

   @mcp.tool()
   def request_inspection_report(item_id: str) -> EmbeddedResource:
       ...
   ```

   Photos come back as inline `ImageContent` blocks with
   base64-encoded bytes (`data=base64.b64encode(buf).decode("ascii")`,
   `mimeType="image/jpeg"`). Inspection PDFs come back as
   `EmbeddedResource(resource=BlobResourceContents(uri="local://...",
   mimeType="application/pdf", blob=base64.b64encode(buf).decode()))`.

3. Per-tool grant gate. Each `@mcp.tool()` body is shaped:

   ```python
   @mcp.tool()
   def request_photos(item_id, kinds=None):
       binding = registry.take(_current_session_token())
       if binding is None:
           raise PermissionError("session_not_bound")
       outcome = grant_policy.decide(
           "request_photos", {"kinds": kinds}, catalog.load(item_id),
       )
       if outcome.decision is Decision.DENY:
           raise PermissionError(outcome.reason)
       if outcome.decision is Decision.ASK_USER:
           raise PermissionError("pending_user_confirm")
       return _build_image_blocks(item_id, kinds, catalog)
   ```

   When the buyer's MCP client receives the `PermissionError`, it
   surfaces the reason back to the buyer's LLM. For
   `pending_user_confirm`, the seller's `tools_inquire.grant_asks`
   tool path is the human-in-the-loop unblocker.

4. Authentication: the buyer's MCP client connects with the
   `session_token` in the `Authorization` header on the SSE
   handshake. The session token was emitted by the buyer in the
   NIP-17 `mcp_inquiry_open` rumor; `inquiry_listener` bound it to
   the buyer's pubkey before the handshake arrives. The FastMCP
   server's auth hook resolves the token via
   `SessionRegistry.take(token)`; if the binding is missing or
   expired the handshake is refused.

5. Wire the FastMCP boot into `main.py serve` so a single process
   runs both the relay listener and the FastMCP server. The serve
   loop hosts both as asyncio tasks.

6. End-to-end test on a single laptop:

   - Seller publishes a listing with a local item folder containing
     three test photos.
   - Buyer (using `mvp/buyer.py` patched to dial MCP) sends a NIP-04
     inquiry asking for photos.
   - Seller's `inquiry_listener` binds the session token.
   - Buyer's MCP client opens `https://localhost:7501/sse` with the
     token and calls `request_photos(item_id, kinds=["exterior"])`.
   - Seller's `mcp_server` returns three `ImageContent` blocks.
   - Bytes never touch a third-party host.

### Phase-2 exit criteria

- `pytest seller/tests/test_mcp_server.py` passes for the inline
  fake-buyer in-process test.
- A two-laptop manual run (seller laptop + buyer laptop) completes
  the photo-stream successfully.
- Per-tool grant policy correctly blocks `request_vin` (ASK_USER) and
  refuses `request_photos(kinds=["license_plate"])` without user
  confirmation.

## Phase 3 — NIP-17 + attestations + negotiation

### Goal

Replace the Phase-1 NIP-04 inquiry path with full NIP-17 gift-wrap
plumbing. Wire the negotiation and attestation modules.

### Steps

1. Replace the NIP-04 path in `inquiry_listener.py` with NIP-17:

   - Subscribe to kind-1059 events tagged `["p", <our_pubkey>]`.
   - Decrypt gift wrap → seal → rumor (kind 14, sender-signed).
   - Validate `rumor.content.type == "mcp_inquiry_open"`.
   - Bind `(session_token, sender_pubkey)` in `SessionRegistry`.

2. Replace the NIP-04 path in `send_reply` with NIP-17 gift-wrapped
   `mcp_inquiry_ack` rumors. Used when we need to deliver a
   human-readable note outside the MCP session itself (e.g. an
   explicit denial when no MCP session will be opened).

3. Implement `attestation.py` — sign / verify Nostr `kind: 30078`
   (NIP-78) attestation events bound to a specific listing.

4. Implement `negotiation.py` and `tools_negotiate.py`:

   - Round tracking, `bid_min_cents` floor, user-confirm gates.
   - Hermes tools: `counter_offer`, `accept_offer`, `reject_offer`.
   - `submit_offer` on the FastMCP side feeds into the same state
     machine (every offer round counts whether it came over MCP or
     over a Hermes tool).

### Phase-3 exit criteria

- Buyer's plugin can open an inquiry over NIP-17 and the seller's
  plugin can reply with a gift-wrapped `mcp_inquiry_ack`.
- A signed attestation event verifies against the seller's pubkey.
- A 5-round negotiation completes and the 6th counter is rejected.

## Phase 4 — reverse_image_check + vin_decode + market_comp + polish

### Goal

Wire the supporting MCPs and polish the CLI.

### Steps

1. `reverse_image_check` pre-share gate: any photo flagged by
   `tier=fast` is held back from `request_photos` and surfaced to the
   user. The actual MCP comes online in Weeks 5-6; Phase-4 ships
   with a stub that always returns `clean` plus a `WARN` log,
   marked for replacement.

2. `vin_decode` MCP — free, structural decode using the public WMI
   registry (CLAUDE.md rule 6 forbids third-party data resellers).
   `request_vin` calls into this for any returned VIN to add a small
   inline summary.

3. `market_comp` MCP — aggregates already-on-network NIP-99 listings
   to produce a comparable-cars summary. Pure aggregation over the
   relay — no third-party data.

4. CLI polish: `hermes chaos-seller status` shows configured
   relays, identity (npub), MCP public URL, recent publish counts,
   and recent inquiry counts.

### Phase-4 exit criteria

- A live demo: `hermes chaos-seller serve item.toml` boots,
  publishes a listing, accepts a buyer's NIP-17 inquiry, opens the
  MCP session on the buyer's connect, returns three real photos and
  one inspection PDF, and the `reverse_image_check` gate is wired
  (stubbed but reachable).

## Files to create

In `seller/src/chaos_seller/`:

| File | One-line description |
|---|---|
| `__init__.py` | Hermes entry point: `register(ctx)` wires tools, hooks, CLI |
| `config.py` | `SellerConfig` frozen dataclass loaded from `~/.chaos/seller.yaml` |
| `identity.py` | Keypair load/save (mode 0600), Schnorr sign helper |
| `input_safety.py` | Layer-1 sanitizer: NFKC, strip invisible/tags, length cap, wrap in `<untrusted>` |
| `catalog.py` | Local item store at `~/.chaos/items/<uuid>/` |
| `publish.py` | NIP-99 build, NIP-13 PoW mine, sign, publish |
| `inquiry_listener.py` | NIP-17 / (MVP NIP-04) gift-wrap listener, decrypt, route, bind session_token |
| `grant_policy.py` | Per-tool policy decision table (cars-pack@1 tool surface) |
| `mcp_server.py` | FastMCP HTTP+SSE server: cars-pack@1 tools (`view_listing`, `request_photos`, `request_inspection_report`, `request_vin`, `submit_offer`, `cancel_inquiry`, …) returning `ImageContent` / `EmbeddedResource` |
| `negotiation.py` | Round tracking, `bid_min_cents`, user-confirm gates |
| `attestation.py` | Sign / verify Nostr `kind: 30078` (NIP-78) attestation events |
| `tools_publish.py` | Tool handlers: `publish_item`, `archive_item`, `update_item` |
| `tools_inquire.py` | Tool handlers: `handle_inquiry`, `grant_asks`, `deny_ask` |
| `tools_negotiate.py` | Tool handlers: `counter_offer`, `accept_offer`, `reject_offer` |
| `schemas.py` | JSON-schema dicts for every tool above (LLM-facing) |
| `main.py` | CLI: `chaos-seller {publish, listen, serve, status}` |

## Hermes plugin entry-point shape

Based on `hermes-agent/website/docs/guides/build-a-hermes-plugin.md`
and the concrete `PluginContext` in
`hermes-agent/hermes_cli/plugins.py`:

```python
# seller/src/chaos_seller/__init__.py
"""Hermes plugin entry point for the chaos seller agent."""
from __future__ import annotations

import logging

from . import schemas, tools_publish, tools_inquire, tools_negotiate, main

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Wire schemas to handlers and register hooks.

    Called exactly once at Hermes startup. ``ctx`` is a
    ``PluginContext`` instance (see hermes_cli/plugins.py).
    If this function raises, the plugin is disabled but Hermes
    continues fine.
    """
    # publish toolset
    ctx.register_tool(
        name="publish_item",
        toolset="chaos-seller",
        schema=schemas.PUBLISH_ITEM,
        handler=tools_publish.publish_item,
    )
    ctx.register_tool(
        name="archive_item",
        toolset="chaos-seller",
        schema=schemas.ARCHIVE_ITEM,
        handler=tools_publish.archive_item,
    )
    ctx.register_tool(
        name="update_item",
        toolset="chaos-seller",
        schema=schemas.UPDATE_ITEM,
        handler=tools_publish.update_item,
    )

    # inquire toolset
    ctx.register_tool(
        name="handle_inquiry",
        toolset="chaos-seller",
        schema=schemas.HANDLE_INQUIRY,
        handler=tools_inquire.handle_inquiry,
    )
    ctx.register_tool(
        name="grant_asks",
        toolset="chaos-seller",
        schema=schemas.GRANT_ASKS,
        handler=tools_inquire.grant_asks,
    )
    ctx.register_tool(
        name="deny_ask",
        toolset="chaos-seller",
        schema=schemas.DENY_ASK,
        handler=tools_inquire.deny_ask,
    )

    # negotiate toolset
    ctx.register_tool(
        name="counter_offer",
        toolset="chaos-seller",
        schema=schemas.COUNTER_OFFER,
        handler=tools_negotiate.counter_offer,
    )
    ctx.register_tool(
        name="accept_offer",
        toolset="chaos-seller",
        schema=schemas.ACCEPT_OFFER,
        handler=tools_negotiate.accept_offer,
    )
    ctx.register_tool(
        name="reject_offer",
        toolset="chaos-seller",
        schema=schemas.REJECT_OFFER,
        handler=tools_negotiate.reject_offer,
    )

    # ship the seller-cars skill out of the plugin so it loads
    # under the "chaos-seller:seller-cars" namespace
    from pathlib import Path
    skill_md = Path(__file__).parent.parent.parent / "skills" / "seller-cars" / "SKILL.md"
    if skill_md.exists():
        ctx.register_skill("seller-cars", skill_md)

    # CLI subcommand: hermes chaos-seller {publish, listen, serve, status}
    ctx.register_cli_command(
        name="chaos-seller",
        help="Manage the chaos seller agent",
        setup_fn=main.setup_argparse,
        handler_fn=main.dispatch,
    )

    logger.info("chaos-seller plugin registered")
```

## Worked example — buyer DMs, seller streams photos

```text
# 0. Setup (offline, before any wire activity)
seller_config = load("~/.chaos/seller.yaml")
me = identity.load("seller")
catalog.save(item_id="abc-123", photos=[exterior_1.jpg, ..., engine.jpg])

# 1. Seller publishes — Phase 1 of plan
raw = publish.build_event(
    item="abc-123", pubkey_hex=me.pk_hex,
    mcp_url=seller_config.mcp.public_url, pack=seller_config.pack,
)
raw = publish.mine_pow(raw, bits=20)
ev  = publish.publish(rm, sk, raw)              # kind-30402, addressable

# 2. Buyer (out-of-process) sends a NIP-17 gift wrap
#    rumor.kind = 14, rumor.content = JSON inquiry payload:
#       {"type":"mcp_inquiry_open","item_id":"abc-123",
#        "session_token":"<random-32-bytes-hex>",
#        "free_text":"interested, can I see photos?"}

# 3. Seller's inquiry_listener wakes up
ev = recv()                                      # kind-1059 gift wrap
sender_pk, rumor_json = inquiry_listener.unwrap_gift(ev, my_sk=me.sk_hex)
inquiry = json.loads(rumor_json)
inquiry_text_for_llm = input_safety.sanitize(
    inquiry.get("free_text", ""),
    source="buyer_inquiry",
    key=ev.id,
)

# 4. Seller binds session_token → buyer pubkey for the upcoming MCP session
session_registry.bind(SessionBinding(
    session_token=inquiry["session_token"],
    buyer_pubkey=sender_pk,
    item_id=inquiry["item_id"],
    expires_at=now + 600,
))

# 5. (Optional) Send a NIP-17 mcp_inquiry_ack with any human-readable text.
#    The acks are kept terse — the real conversation is over MCP.

# 6. Buyer dials MCP. The buyer's MCP client opens
#    https://seller.example.com/sse with Authorization: Bearer <session_token>.
#    The FastMCP auth hook resolves the token via SessionRegistry.take(token);
#    if missing or expired, the handshake is refused.

# 7. Buyer calls cars-pack@1 tools:
#    tools/call view_listing(item_id="abc-123")
#       → text summary
#    tools/call request_photos(item_id="abc-123", kinds=["exterior", "engine_bay"])
#       → list[ImageContent] (base64 inline, mimeType="image/jpeg")
#    tools/call request_inspection_report(item_id="abc-123")
#       → EmbeddedResource (PDF blob)
#
#    Each tool body runs grant_policy.decide(tool, args, item) before
#    doing the work. ASK_USER decisions raise a PermissionError with
#    reason "pending_user_confirm" until tools_inquire.grant_asks
#    flips the bit.

# 8. Buyer's MCP client receives the blocks, writes them into its
#    inbox under ~/.chaos/buyer/inbox/abc-123.jsonl, runs
#    reverse_image_check tier=thorough on the bytes, then surfaces
#    them to the buyer-side LLM.
```

The only network hops are (a) the relay carrying NIP-99 + NIP-17
events and (b) the direct MCP HTTP+SSE between buyer and seller.
**No third party touches the photo bytes.**

## Tests to write first (TDD-shaped)

Under `seller/tests/`:

| Test | What it validates |
|---|---|
| `test_publish.py::test_publish_signs_correctly` | A built kind-30402 event has a valid Schnorr signature against the seller's pubkey, all required cars-pack tags present, and no `image` tag |
| `test_publish.py::test_pow_mine_meets_difficulty` | After `mine_pow(raw, bits=20)`, the event id has ≥ 20 leading zero bits and the `nonce` tag is present |
| `test_publish.py::test_publish_no_image_tag_ever` | Property test: across 100 random `Item` fixtures, no resulting event includes an `image` tag |
| `test_publish.py::test_publish_mcp_and_pack_tags_present` | Every event includes `["mcp", <https url>]` and `["pack", "cars-pack@1"]` |
| `test_grant_policy.py::test_default_grants_match_skill_md` | The decision table matches the rows of seller-cars SKILL.md § "Inquiry-handling policy" |
| `test_grant_policy.py::test_request_vin_always_asks_user` | `decide("request_vin", {}, item)` returns `ASK_USER`; never auto-grants |
| `test_grant_policy.py::test_request_pickup_address_requires_user_confirm` | Same shape |
| `test_grant_policy.py::test_request_phone_number_always_denied` | `decide("request_phone_number", {}, item)` returns `DENY` regardless of item |
| `test_grant_policy.py::test_request_photos_license_plate_kind_escalates` | Per-arg override fires for `request_photos(kinds=["license_plate"])` |
| `test_input_safety.py::test_strips_reserved_tags` | An incoming inquiry containing `<system>...</system>` has it stripped before the LLM-facing surface |
| `test_input_safety.py::test_wraps_in_untrusted` | Sanitized output starts with `<untrusted source="buyer_inquiry"` |
| `test_mcp_server.py::test_mcp_server_view_listing_returns_summary` | `view_listing(item_id)` returns text |
| `test_mcp_server.py::test_mcp_server_request_photos_returns_image_content_blocks` | An in-process fake MCP client connects, calls `request_photos`, and observes 3 `ImageContent` blocks |
| `test_mcp_server.py::test_mcp_server_request_inspection_report_returns_embedded_resource` | An `inspection_report` request emits an `EmbeddedResource` (PDF blob) |
| `test_mcp_server.py::test_mcp_server_rejects_unknown_session_token` | A handshake with an unbound session_token is refused |
| `test_mcp_server.py::test_mcp_server_rejects_after_session_expiry` | A bound session past expiry is rejected |
| `test_mcp_server.py::test_mcp_server_request_vin_blocks_until_user_confirm` | `request_vin` always raises pending-user-confirm |
| `test_negotiation.py::test_round_cap_at_5` | Sixth counter is rejected |
| `test_negotiation.py::test_offer_chars_capped_at_1000` | Long offer text is truncated/rejected |
| `test_attestation.py::test_attestation_signature_round_trip` | A signed attestation event verifies against the seller's pubkey |

Run target: `pytest seller/tests/ -q`.

## Open questions for the engineer

1. **`pynostr` reconnect behaviour.** Does
   `RelayManager.run_sync()` automatically resubscribe on
   reconnect after a relay drop? Audited briefly in the MVP but not
   under sustained churn. Answer this before going to production.

2. **NIP-17 maturity in `pynostr` 0.6.2.** The MVP uses NIP-04 because
   `pynostr`'s NIP-44 / NIP-59 helpers are partial. Confirm by
   reading `pynostr/encrypted_dm.py` and the NIP-44 module. If
   missing, write a thin NIP-44 encrypt + gift-wrap helper inline
   under `inquiry_listener.py`. Acceptance: round-trip a kind-1059
   gift-wrap with a third-party Nostr client (Damus, nak).

3. **FastMCP auth hook for session tokens.** The spike at
   `spike/seller_mcp.py` runs without auth; the production server
   needs to validate the `Authorization` header on the SSE
   handshake against `SessionRegistry`. Verify the
   `mcp.server.fastmcp` API for hooking auth — either via a
   middleware on the underlying ASGI app or via a `FastMCP` lifecycle
   hook. Worst case, host the FastMCP ASGI app inside our own
   `uvicorn.Server` with a shim middleware.

4. **MCP transport — SSE vs streamable-http.** The spike uses
   `transport="sse"`. The MCP SDK 1.27.0 also supports
   `streamable-http`; confirm which the buyer's
   `tools/mcp_tool.py` in Hermes prefers. Default to SSE for v1 to
   match the spike.

5. **Where `~/.chaos/items/` lives in shared deployments.**
   If the user runs Hermes in Docker, the path needs to be a
   bind-mount. Document this in the seller README before the first
   pilot user.

6. **Reverse-image MCP availability on Phase 4.** The MCP itself is
   Weeks 5-6 deliverable. If it's not online when we wire the
   pre-share gate, we ship with a stub that always returns `clean`
   plus a `WARN` log. Mark the stub for replacement.

7. **`register_skill(name, path)` signature precision.** The plugin
   guide shows the call shape but `hermes_cli/plugins.py` line 544
   is the source of truth — read its full signature before wiring.

## Definition of done for Week 1

- All 16 files in `src/chaos_seller/` compile under
  `python -m compileall`.
- `ruff check seller/` passes.
- `mypy seller/src` (or `ty`) passes with no public-API errors.
- All test files run (most asserting `assert False` — that's Week 2's
  job to fill in).
- A live demo: `hermes chaos-seller serve item.toml` boots,
  publishes a listing on the Mode A relay, accepts an MVP buyer's
  NIP-04 DM, binds the session_token → buyer pubkey, and the buyer's
  MCP client successfully calls `view_listing`, `request_photos` and
  `request_inspection_report` against the FastMCP server. Photos
  come back as `ImageContent` blocks, the inspection report as an
  `EmbeddedResource`. Production-quality two-machine run is Week 2.
