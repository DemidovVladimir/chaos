# `<vertical>` NIP-99 tag schema

> Skeleton for a vertical pack's tag schema. Fill in the
> `<PLACEHOLDER>` rows with the required tags for your vertical;
> keep the structure and the rules-of-thumb sections.

Conventions for tagging a `<DOMAIN_NOUN>` listing as a NIP-99 event
(`kind: 30402`). Stable contract; additive changes only within a
major version.

## Required tags

Every listing in this vertical MUST carry these.

| Tag | Cardinality | Purpose | Example |
|---|---|---|---|
| `d` | 1 | Addressable item id (uuid v4) | `["d", "<UUID>"]` |
| `title` | 1 | Human-readable title (≤ 200 chars) | `["title", "<TITLE>"]` |
| `summary` | 1 | One-line summary (≤ 280 chars) | `["summary", "<SUMMARY>"]` |
| `t` | ≥ 2 | Discovery tags. Always include `t=<vertical>` and one or more category facets | `["t","<vertical>"], ["t","<FACET>"]` |
| `price` | 1 | NIP-99 price in `[amount, currency, frequency]`. Use the empty-string frequency unless the listing is recurring (e.g. rent). | `["price","<AMOUNT>","<CCY>",""]` |
| `location` | 1 | Hierarchical region (continent/country/city) or a coarse geohash. Never an exact street address. | `["location","<REGION_PATH>"]` |
| `<REQUIRED_FACET_1>` | 1 | <Describe what this facet is and why every listing needs it.> | `["<REQUIRED_FACET_1>","<VALUE>"]` |
| `<REQUIRED_FACET_2>` | 1 | <Describe.> | `["<REQUIRED_FACET_2>","<VALUE>"]` |
| `<REQUIRED_FACET_3>` | 1 | <Describe.> | `["<REQUIRED_FACET_3>","<VALUE>"]` |
| `mcp` | 1 | MCP server endpoint where binary content is delivered agent-to-agent | `["mcp","https://a.io/mcp"]` |
| `pack` | 1 | Vertical-pack contract version this listing speaks. | `["pack","<vertical>-pack@1"]` |
| `status` | 1 | One of: `available, reserved, sold, archived`. Default `available`. | `["status","available"]` |
| `language` | 1 | ISO code of the listing language | `["language","en"]` |
| `schema_version` | 1 | Pack schema version (current: `"1"`) | `["schema_version","1"]` |

## Recommended tags

Strongly suggested but not required. Improves filterability and
buyer signal.

| Tag | Cardinality | Purpose |
|---|---|---|
| `<RECOMMENDED_FACET_1>` | 0 or 1 | <Describe.> |
| `<RECOMMENDED_FACET_2>` | 0 or 1 | <Describe.> |
| `expires_at` | 0 or 1 | Unix timestamp; defaults to publish + 30 days |
| `accepts_offer` | 0 or 1 | `yes` / `no` — seller is open to counter-offers |
| `bid_min_cents` | 0 or 1 | If `accepts_offer=yes`, minimum acceptable bid |
| `badge` | 0+ | NIP-58 badge references the seller has been issued |

## Optional / advanced

| Tag | Purpose |
|---|---|
| `<OPTIONAL_FACET_1>` | <Describe.> |
| `region_geohash` | 5-char geohash for fine-grained region search without leaking exact location |
| `currency_alt` | Alternative currency the seller accepts |
| `comparable_listings` | One or more `e` tags pointing to comparable NIP-99 events |

## Bucketing rules of thumb

For numeric facets (price, size, age, …), use **discrete buckets**
so filters work as cheap tag matches on the relay:

- Pick 6–10 contiguous bands that cover the realistic range for
  this vertical.
- Always use the same units (e.g. metric).
- Buyers' filters compose by listing acceptable bands as
  `["#<facet>_band", ["<band-a>","<band-b>"]]`.

## Region pattern

Hierarchical with `/` separators:

```
EU/CZ/Prague
NA/US/CA/SF
```

Buyer filters use prefix matching (`EU/CZ/%`).

## What is NEVER on the public listing

These fields stay on the seller's machine and are shared only on
explicit grant during 1-to-1 inquiry, **delivered as MCP content
blocks** (`ImageContent`, `EmbeddedResource`) returned from a tool
call on the seller's MCP server, direct to the requesting buyer's
agent:

- Owner / counterparty name, contact info, full address
- Government-issued IDs, registration numbers, license plates,
  serial numbers when those uniquely identify the item
- All photos — including the cover photo. Listings carry no
  `image` tag. Photos arrive in the buyer's agent via MCP
  (`request_<DOMAIN_PHOTO_OR_DOC>` tool returning `ImageContent`
  blocks) after the seller's agent grants the inquiry.
- Inspection reports, provenance documents, contracts, signed
  certificates
- Exact GPS or street-level location

## Example: minimal valid listing

```json
{
  "kind": 30402,
  "tags": [
    ["d", "<UUID>"],
    ["title", "<TITLE>"],
    ["summary", "<SUMMARY>"],
    ["t", "<vertical>"],
    ["t", "<FACET>"],
    ["price", "<AMOUNT>", "<CCY>", ""],
    ["location", "<REGION_PATH>"],
    ["<REQUIRED_FACET_1>", "<VALUE>"],
    ["<REQUIRED_FACET_2>", "<VALUE>"],
    ["<REQUIRED_FACET_3>", "<VALUE>"],
    ["mcp", "https://a.io/mcp"],
    ["pack", "<vertical>-pack@1"],
    ["status", "available"],
    ["language", "en"],
    ["schema_version", "1"]
  ],
  "content": "<PUBLIC_DESCRIPTION_NO_PII>"
}
```

See `example_listing.json` for the fully-tagged version.

## MCP tool surface (the `<vertical>-pack` contract)

Every seller in this vertical MUST expose these tools on their
MCP server. The buyer's `<vertical>-pack@1` skill knows them by
name.

| Tool | Args | Returns | Subject to grant policy |
|---|---|---|---|
| `view_listing(item_id)` | item_id: str | TextContent — short summary | always granted |
| `request_<DOMAIN_PHOTO_OR_DOC>(item_id, kinds)` | item_id: str, kinds: list[str] | list[ImageContent] or list[EmbeddedResource] | per-kind grant policy |
| `request_<DOMAIN_DETAIL>(item_id)` | item_id: str | TextContent or EmbeddedResource | grant if exists |
| `request_<DOMAIN_PII_GATED>(item_id)` | item_id: str | TextContent — gated value, or denied | always user-confirm |
| `submit_offer(item_id, price_cents, conditions)` | as named | TextContent — counter / accept / reject | rate-limited 5 rounds/match |
| `cancel_inquiry(conversation_id)` | as named | TextContent — ack | always granted |

Sellers MAY expose additional tools beyond this minimum (e.g.
`request_<DOMAIN_EXTRA>`); buyers' skills read `tools/list` and
surface unknown tools to the user as "this seller offers also: …".

## Compatibility

- Forward-compatible with broader Nostr marketplace clients: they
  read `title`, `summary`, `price`, `location`, `t`. They ignore
  tags they don't recognize.
- The vertical-specific tags should be neither prefixed with
  `<vertical>-` nor with `t=` so they're cheap one-shot filter
  queries on relay indexes.

## Versioning

This schema is **v1**. Within v1, future updates add tags only,
never rename or remove. The pack ships with `schema_version: "1"`
so clients warn on unknown major bumps.

A breaking change (renamed required tag, changed tool semantics,
removed required field) requires a major version bump
(`<vertical>-pack@2`) AND a written migration plan documented in
this pack's `README.md` describing how `<vertical>-pack@1`
listings are translated to or coexist with v2.
