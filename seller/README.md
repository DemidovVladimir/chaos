# seller — production seller-agent component

The production seller agent: a Hermes plugin that publishes NIP-99
listings, listens for NIP-17 inquiries, exposes a cars-pack@1 MCP
server that buyers connect to for photos and inspection reports, and
applies the per-tool grant policy from
`verticals/cars-pack/skills/seller-cars/SKILL.md`.

> **Status**: scaffold. The runnable starter is in `../mvp/seller.py`
> (text-only, no MCP server, NIP-04 instead of NIP-17, no PoW).
> Wiring the production version is week 1–4 of `LAUNCH_PLAN.md`. This
> folder exists so the contract is clear and so future Claude sessions
> know where to put the production code.

## What lives here when complete

```
seller/
├── README.md                this file
├── pyproject.toml           Python package definition
├── plugin.yaml              Hermes plugin manifest
└── src/
    └── chaos_seller/
        ├── __init__.py          register(ctx)
        ├── config.py            SellerConfig — relays, identity path, MCP url
        ├── identity.py          Keypair load/save (mode 0600), Schnorr signing
        ├── input_safety.py      copy of shared sanitizer; layer-1 defense
        ├── catalog.py           local item store at ~/.chaos/items/
        ├── publish.py           NIP-99 build + PoW mine + sign + publish
        ├── inquiry_listener.py  NIP-17 gift-wrap listener, decrypt, session_token routing
        ├── grant_policy.py      per-tool policy (from seller-cars skill)
        ├── mcp_server.py        FastMCP server; exposes cars-pack@1 tool surface
        │                        (view_listing, request_photos,
        │                         request_inspection_report, request_vin,
        │                         submit_offer, cancel_inquiry)
        ├── negotiation.py       round tracking, bid floor, user-confirm
        ├── attestation.py       sign / verify Nostr attestation events
        ├── tools_publish.py     skill tool: publish_item, archive_item, update_item
        ├── tools_inquire.py     skill tool: handle_inquiry, grant_asks, deny_ask
        ├── tools_negotiate.py   skill tool: counter_offer, accept_offer, reject_offer
        └── main.py              CLI: hermes chaos-seller {publish, listen, status}
```

## Component contract

The seller plugin **must**:

1. Hold the user's Nostr keypair only at `~/.chaos/keys/seller.key`,
   mode 0600.
2. Publish NIP-99 events with cars-pack tag schema; never include an
   `image` tag; always include `["mcp", "<url>"]` and
   `["pack", "cars-pack@1"]` tags.
3. Mine NIP-13 PoW ≥ 20 bits before signing.
4. Run `reverse_image_check` (fast tier, local) on every photo in the
   item folder before any `request_photos` MCP tool call can return
   the bytes.
5. Listen for NIP-17 gift-wrapped `mcp_inquiry_open` rumors on
   configured relays; bind the `session_token` to the calling buyer
   pubkey.
6. Run a FastMCP server exposing the cars-pack@1 tool surface
   (`view_listing`, `request_photos`, `request_inspection_report`,
   `request_vin`, `submit_offer`, `cancel_inquiry`). Apply the
   per-tool grant policy from
   `../verticals/cars-pack/skills/seller-cars/SKILL.md` § "MCP tool surface".
7. Return photos and PDFs to the buyer's agent only as MCP
   `ImageContent` and `EmbeddedResource` blocks from tool calls.
   **Never via HTTP file servers, never as URLs.**
8. Maintain the negotiation state machine (≤ 5 rounds, ≤ 1000 chars
   per offer, ≤ 50,000 chars total).
9. Require explicit user confirmation for any acceptance, sensitive
   tool grant (`request_vin`, `request_photos` for license-plate
   kinds), or PII-adjacent action.

The seller plugin **must not**:

- Hold any third-party file URLs to user photos (no Imgur, Dropbox,
  etc.)
- Return URLs from MCP tool calls instead of inline content blocks
- Store buyer PII received during inquiries beyond the
  conversation log
- Accept commands inside `<untrusted>` blocks
- Have `terminal`, `execute_code`, `delegation`, `web`, or general
  outbound `mcp` toolsets enabled (the seller's own MCP server is
  inbound-only — it serves tools to buyers; the seller agent does
  not call arbitrary outside MCPs) (per `CLAUDE.md` § Architecture
  rules)

## Hermes plugin shape

```yaml
# plugin.yaml
manifest_version: 1
name: chaos-seller
description: |
  Seller agent for the chaos Nostr-based marketplace. Publishes
  NIP-99 listings, handles NIP-17 inquiries, exposes a cars-pack@1
  MCP server for photo and inspection-report delivery.
version: 0.1.0
author: chaos
license: MIT
entry_point: chaos_seller:register
required_env:
  - CHAOS_RELAYS              # comma-separated wss:// urls
  - CHAOS_MCP_URL             # https url where this seller's MCP server is reachable
forbidden_toolsets:
  - terminal
  - delegation
  - file
  - web
```

## Configuration

`~/.chaos/seller.yaml`:

```yaml
relays:
  - "wss://relay.your-domain.app"
  - "wss://relay.damus.io"
  - "wss://nos.lol"

mcp:
  bind: "0.0.0.0:8645"
  public_url: "https://a.io/mcp"        # ngrok or other tunnel; the public face
  transport: "http+sse"                 # FastMCP HTTP+SSE; stdio for local dev only
  pack: "cars-pack@1"                   # vertical-pack contract this server speaks

publish:
  pow_min_bits: 20
  default_currency: "EUR"
  default_region: "EU/CZ/Prague"

grant_policy:
  defaults_from: "verticals/cars-pack/skills/seller-cars/SKILL.md"
  always_user_confirm:
    - vin_full
    - pickup_address
    - phone_number

negotiation:
  max_rounds: 5
  max_chars_per_offer: 1000
  max_chars_per_match: 50000
```

## How to build it

Phase 1 (week 1 of `LAUNCH_PLAN.md`):

- Implement `identity.py`, `publish.py`, `inquiry_listener.py` —
  enough to publish a listing and decrypt an inquiry. Reuses
  `pynostr` like the MVP does.
- Wire as a Hermes plugin (entry point, register hook).
- Verify text-only round-trip on Mode A relay.

Phase 2 (week 2):

- Implement `mcp_server.py` using FastMCP from Hermes'
  `tools/mcp_serve.py`. Expose the cars-pack@1 tool surface.
  Return a test photo as `ImageContent` from `request_photos`.
- Wire `grant_policy.py` from the seller-cars skill into per-tool
  hooks.
- Verify two-machine end-to-end test passes unattended (buyer's
  `mcp_connect` reaches the seller's public MCP url, `tools/list`
  works, `request_photos` returns inline bytes).

Phase 3 (week 3):

- Replace NIP-04 with NIP-17 gift-wrap path (NIP-44 encryption).
- Implement attestation signing (`attestation.py`).
- Implement negotiation rounds (`negotiation.py`).

Phase 4 (week 4+):

- Wire `reverse_image_check` integration as a pre-share gate.
- Wire `vin_decode` and `market_comp` references.
- Polish CLI.

## See also

- `../mvp/seller.py` — the runnable MVP starter
- `../verticals/cars-pack/skills/seller-cars/SKILL.md` — the canonical seller
  skill
- `../PROTOCOL.md` — the on-the-wire design
- `../SECURITY.md` — pre-launch security checklist
- `../CLAUDE.md` — engineering rules every PR must respect
