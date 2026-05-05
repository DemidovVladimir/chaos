# cars-pack — vertical pack for car listings

The cars-pack is a self-contained installable bundle: tag schema +
**MCP tool surface contract** + offering agent skill + seeking agent skill +
custom-MCP specs + an example listing. It is the working reference
pack because it exercises the full protocol surface.

The pack defines what every cars-pack@1 offering agent's MCP server must
expose: `view_listing`, `request_photos`,
`request_inspection_report`, `request_vin`, `submit_offer`,
`cancel_inquiry`. The wire (MCP) is universal; the pack is the
contract.

## Files

```
cars-pack/
├── README.md                   this file
├── tag_schema.md               NIP-99 tag conventions for cars (canonical)
├── example_listing.json        a fully-tagged real-world car listing
├── skills/
│   ├── offering-cars/SKILL.md    offering agent skill — listing, MCP server tools, grant policy
│   └── seeking-cars/SKILL.md     seeking agent skill — filter, evaluate, MCP-call offering agent, negotiate
└── mcp/
    ├── reverse-image-mcp.md    PAID — perceptual-hash photo-fraud detection
    ├── vin-decoder-mcp.md      free — ISO-3779 structural decode (no third party)
    └── market-comp-mcp.md      free — pricing comps from on-network listings
```

## Why cars-pack is the reference

- **High average transaction value** — a $15k car justifies $50–$500
  in publisher-side tooling spend
- **Standardized facets** — make / model / year / mileage / VIN are
  universal and machine-readable
- **Real fraud signals available locally** — photo reuse and stock-
  image patterns are detectable without third-party data

## What this pack adds on top of the bare protocol

- A **tag schema** — fixed conventions for which NIP-99 tags carry
  which car facets. Without this, two implementations would tag
  inconsistently and filters wouldn't match.
- **MCP tool surface contract** — the named tools every cars offering agent
  must expose, with schemas and semantics. This is the real
  pack protocol; the wire layer (MCP) is universal.
- **Offering agent and seeking agent skills** — Hermes skills tuned for car-specific
  flows: photo coverage checklist, per-tool grant policy, financing
  conversation patterns, history-report etiquette.
- **Three custom MCP utility servers** (different from the offering agent's
  peer MCP server — these are local capability MCPs the
  agents use under the hood):
  - `reverse-image-mcp` (paid, photo-fraud detection across all verticals)
  - `vin-decoder-mcp` (free, pure structural decode)
  - `market-comp-mcp` (free, pricing comps from listings already on the relay)

## Operational shape

- Offering agents run cars-pack on their own Hermes (with the offering agent plugin)
- Seeking agents run it on theirs
- Both publish to the **Mode A relay you operate** plus 2–3 community
  Nostr relays
- Verification badges (NIP-58) issued by you for "Verified Dealer"
  / "Verified Private Offering agent" — not required, improves search ranking
- Photos and inspection PDFs move agent-to-agent through MCP
  `ImageContent` and `EmbeddedResource` blocks (returned from
  `request_photos` / `request_inspection_report` tool calls) — never
  through a third-party file host
- The reverse-image-mcp is sold as a paid add-on, runs on the
  seeking agent's own machine on bytes the seeking agent's agent received from the
  offering agent's MCP server

## Pack lifecycle

The pack is a versioned bundle (semver). Updates ship as a new
release; users opt in. The protocol contract (NIP-99 tag names) stays
stable — additive changes only, never breaking.

## Read order

1. `tag_schema.md` — the canonical car-listing shape
2. `example_listing.json` — concrete event you can publish today
3. `skills/offering-cars/SKILL.md` — what the offering agent does
4. `skills/seeking-cars/SKILL.md` — what the seeking agent does
5. `mcp/reverse-image-mcp.md` — the first paid capability
