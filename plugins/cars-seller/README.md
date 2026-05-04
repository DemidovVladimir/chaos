# `chaos-cars-seller`

Sell cars on the chaos Nostr-based marketplace.

## What it bundles

- The **universal seller engine** (`chaos-seller`) — Hermes
  plugin that knows how to publish NIP-99 listings, accept NIP-17
  inquiries, and run a per-seller MCP server that returns photos
  and inspection PDFs as `ImageContent` / `EmbeddedResource`
  blocks.
- The **cars-pack contract** (`cars-pack@1`) — NIP-99 tag schema,
  required MCP tool surface (`view_listing`, `request_photos`,
  `request_inspection_report`).
- The **seller-cars skill** — drives the agent's behavior when the
  user says "list my Mazda 6". Lives in
  `verticals/cars-pack/skills/seller-cars/SKILL.md`.

## Who installs this

Anyone who wants to sell a car. One install per Hermes profile;
keys live at `~/.chaos/seller.key` (mode 0600). The platform
never holds your keys.

## Install (stub)

```sh
hermes plugin install chaos-cars-seller
```

The first run prompts you to set `CHAOS_RELAYS` (default:
the operator's strfry instance plus a couple of community relays)
and `CHAOS_MCP_URL` (the public address your seller MCP
server will bind to).

## What it does NOT include

- No capability MCPs. The seller side doesn't need
  `reverse-image-mcp` or `vin-decoder-mcp` locally; those are
  buyer-side checks. (We do flag stock images on the seller side
  proactively — that runs through the buyer-side MCP when the
  seller is also a buyer.)
- No payment processing. Money flows off-platform; the platform
  never custodies funds (see `CLAUDE.md` rule 8).
