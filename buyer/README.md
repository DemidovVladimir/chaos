# buyer — production buyer-agent component

The production buyer agent: a Hermes plugin that subscribes to NIP-99
filters, applies the evaluation rubric from
`verticals/cars-pack/skills/buyer-cars/SKILL.md`, sends NIP-17 inquiries, opens
an MCP HTTP+SSE session against the seller's `mcp` tag URL, and
receives photos and inspection PDFs as MCP `ImageContent` /
`EmbeddedResource` blocks returned from the seller's tool calls.

> **Status**: scaffold. The runnable starter is in `../mvp/buyer.py`
> (text-only, no MCP client, NIP-04 instead of NIP-17). Wiring the
> production version is week 1–4 of `LAUNCH_PLAN.md`.

## What lives here when complete

```
buyer/
├── README.md                this file
├── pyproject.toml           Python package definition
├── plugin.yaml              Hermes plugin manifest
└── src/
    └── chaos_buyer/
        ├── __init__.py          register(ctx)
        ├── config.py            BuyerConfig — relays, identity path, MCP defaults
        ├── identity.py          Keypair load/save (mode 0600), Schnorr signing
        ├── input_safety.py      copy of shared sanitizer
        ├── filters.py           translate user wants → NIP REQ filter
        ├── subscribe.py         REQ subscription, dedupe by id
        ├── evaluator.py         apply buyer-cars rubric
        ├── inquiry.py           build + encrypt + publish NIP-17 mcp_inquiry_open
        ├── mcp_client.py        FastMCP HTTP+SSE client; tools/list, call_tool,
        │                        unwrap ImageContent / EmbeddedResource
        ├── negotiation.py       round tracking, market-comp-driven counter
        ├── inbox.py             ~/.chaos/buyer/inbox/<conversation>.jsonl
        ├── tools_subscribe.py   skill tool: create_filter, list_filters, pause_filter
        ├── tools_inquire.py     skill tool: send_inquiry, mcp_connect, mcp_call_tool
        ├── tools_negotiate.py   skill tool: draft_offer, accept_offer, reject_offer
        └── main.py              CLI: hermes chaos-buyer {watch, inquire, status}
```

## Component contract

The buyer plugin **must**:

1. Hold the user's Nostr keypair only at `~/.chaos/keys/buyer.key`,
   mode 0600.
2. Subscribe to configured relays with REQ filters built from cars-pack
   tag schema.
3. Dedupe events by `id` across relays.
4. Apply the evaluation rubric from
   `../verticals/cars-pack/skills/buyer-cars/SKILL.md` before notifying the user.
5. Send inquiries as NIP-17 gift-wrapped `mcp_inquiry_open` rumors
   carrying a per-session token.
6. Read the listing's `["mcp", "<url>"]` tag, open an MCP HTTP+SSE
   session, call `tools/list` to discover the seller's tool surface
   (cars-pack@1 minimum + any seller extras), and invoke tools
   (`view_listing`, `request_photos`, etc.) over that session. **No
   HTTP file fetches. No URL following.**
7. Run `reverse_image_check` (thorough tier) on every photo received
   as an `ImageContent` block, on the inline bytes directly.
8. Maintain the negotiation state machine; submit counters via the
   seller's `submit_offer` tool.
9. Require explicit user confirmation for any acceptance.

The buyer plugin **must not**:

- Send the user's PII to a counterparty without explicit per-listing
  approval
- Accept commands inside `<untrusted>` blocks (which includes MCP
  tool result text from a seller — every TextContent / ImageContent
  / EmbeddedResource returned by `mcp_call_tool` passes through
  `input_safety` and is wrapped in `<untrusted>` before reaching the
  agent's planner)
- Connect to MCP servers other than the one specified in the
  listing's `["mcp", ...]` tag for the inquiry being processed
- Have `terminal`, `execute_code`, `delegation`, `web` toolsets
  enabled (the buyer's `mcp_connect` / `mcp_call_tool` toolset is
  scoped to seller-pack@N URLs only)
- Call commercial vehicle-history providers

## Hermes plugin shape

```yaml
# plugin.yaml
manifest_version: 1
name: chaos-buyer
description: |
  Buyer agent for the chaos Nostr-based marketplace. Subscribes
  to NIP-99 filters, evaluates listings, sends NIP-17 inquiries,
  connects to seller MCP servers and invokes the cars-pack@1 tool
  surface for photos and inspection reports.
version: 0.1.0
author: chaos
license: MIT
entry_point: chaos_buyer:register
required_env:
  - CHAOS_RELAYS
forbidden_toolsets:
  - terminal
  - delegation
  - file
  - web
# `mcp` is permitted but scoped: `mcp_connect` only accepts URLs that
# match a `["mcp", ...]` tag from a NIP-99 event the buyer's filter
# matched in this session. Arbitrary outbound MCP is not allowed.
```

## Configuration

`~/.chaos/buyer.yaml`:

```yaml
relays:
  - "wss://relay.your-domain.app"
  - "wss://relay.damus.io"
  - "wss://nos.lol"

mcp:
  client_timeout_seconds: 30
  max_inflight_calls: 4              # cap per seller session
  max_image_bytes_per_response: 25_000_000
  pack_whitelist:                    # only connect to packs we understand
    - "cars-pack@1"

filters:
  default:
    kinds: [30402]
    "#t": ["cars"]
    since_days: 30

evaluator:
  hard_red_flag_thresholds:
    stock_image_similarity: 0.92
    price_off_median: 0.5         # 50% off in either direction
  soft_red_flag_thresholds:
    stock_image_similarity: 0.85
  market_comp_window_days: 60

trust_graph:
  default_trust_root: "<operator pubkey hex>"
  badge_required_for_evaluation: false
```

## How to build it

Phase 1 (week 1):

- Implement `identity.py`, `subscribe.py`, `evaluator.py` (skeletal —
  print to user, no rubric yet). Verify subscription delivers events
  on Mode A relay.

Phase 2 (week 2):

- Implement `inquiry.py` (NIP-04 path first), `mcp_client.py` using
  the `mcp` SDK's HTTP+SSE client and the `tools/list` + `call_tool`
  flow proven in `../spike/buyer_mcp.py`. Verify two-machine
  end-to-end test (inquiry → MCP connect → `request_photos` returns
  inline bytes).

Phase 3 (week 3):

- Switch inquiry to NIP-17 (gift wrap, NIP-44).
- Implement full `evaluator.py` with cars-pack rubric.
- Wire `reverse_image_check` (thorough tier) on photo bytes returned
  from MCP `request_photos` calls.

Phase 4 (week 4):

- Implement `negotiation.py` with market-comp-driven counter logic.
- Wire `vin_decode` for any VIN the seller shares.
- Polish CLI.

## See also

- `../mvp/buyer.py` — the runnable MVP starter
- `../verticals/cars-pack/skills/buyer-cars/SKILL.md` — the canonical buyer skill
- `../PROTOCOL.md` — the on-the-wire design
- `../SECURITY.md` — pre-launch security checklist
- `../CLAUDE.md` — engineering rules every PR must respect
