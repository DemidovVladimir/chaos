# `chaos-cars-buyer`

Buy cars on the chaos Nostr-based marketplace. **Free tier.**

## What it bundles

- The **universal buyer engine** (`chaos-buyer`) — Hermes
  plugin that subscribes to NIP-99 cars listings, opens MCP
  sessions against seller MCP servers, and orchestrates the buyer
  rubric.
- The **cars-pack contract** (`cars-pack@1`) — NIP-99 tag schema +
  the seller-side MCP tool surface this buyer expects.
- The **buyer-cars skill** — runs the rubric (price sanity, photo
  fraud check, VIN cross-check, reputation lookup, …).
- **Capability MCPs** in fast-tier mode:
  - `reverse-image-mcp@1` (shared) — perceptual-hash photo fraud
    detection.
  - `market-comp-mcp@1` (shared) — pricing comps from on-network
    listings.
  - `vin-decoder-mcp@1` (cars-pack) — ISO-3779 structural VIN
    decode.
  - `reputation-mcp@1` (shared) — layered trust signals.

## Free tier vs pro

The free tier ships every capability MCP in **fast** mode (config
flag `pro_mode: false`). Install **`chaos-pro`** alongside
this plugin to flip the same MCPs into **thorough** mode (deeper
WoT depth, wider comp window, EXIF + federated registry checks on
images, optional on-chain stake reads).

`chaos-pro` is **cross-vertical**: one subscription covers
every buyer plugin you have installed. We do not ship a per-
vertical `cars-buyer-pro`.

## Install (stub)

```sh
hermes plugin install chaos-cars-buyer
```

## Required env

- `CHAOS_RELAYS` — comma-separated wss URLs.
