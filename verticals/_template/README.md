# `<vertical>-pack` — copy-and-fill skeleton

> This folder is a skeleton. Copy it to `verticals/<vertical>-pack/`,
> rename `<vertical>` to your vertical (e.g. `realestate`,
> `lawyers`, `watches`), then fill in the placeholders. Pack names
> are versioned: the first release is `<vertical>-pack@1`.

## What you are filling in

A vertical pack is the contract every offering agent and seeking agent in this
category agrees to. The wire (Nostr discovery + MCP peer transport)
is universal; only the contents of this folder change. To define a
new vertical, you write:

1. `tag_schema.md` — which NIP-99 tags are required / recommended /
   optional / forbidden-on-public-listing for this vertical, plus
   the MCP tool surface contract every offering agent in this vertical must
   expose.
2. `example_listing.json` — a complete NIP-99 event a offering agent could
   publish today, with every required tag filled in.
3. `skills/<vertical>-offering/SKILL.md` — Hermes offering agent skill: hard
   rules, listing flow, MCP tool handlers, grant policy, negotiation
   flow, verification checklist.
4. `skills/<vertical>-seeking/SKILL.md` — Hermes seeking agent skill: filter
   construction, evaluation rubric (red / soft / green flags), MCP
   inquiry flow, negotiation drafting, escalation rules,
   verification checklist.
5. `mcp/` (optional) — vertical-specific local capability MCPs. See
   `mcp/README.md` for the rules these must follow.

## Files in this skeleton

```
_template/
├── README.md                 this file
├── tag_schema.md             fill in: tags, MCP tool surface, "what is NEVER public"
├── example_listing.json      fill in: a full NIP-99 event
├── skills/
│   ├── <vertical>-offering/SKILL.md   fill in: hard rules + listing/MCP/negotiation flow
│   └── <vertical>-seeking/SKILL.md    fill in: filter + rubric + inquiry flow
└── mcp/
    └── README.md             rules for any local capability MCPs you add here
```

## Rename checklist

Search-and-replace these markers across the copy:

- `<vertical>` → your vertical name (e.g. `realestate`)
- `<VERTICAL>` → uppercase or human-readable form
- `<DOMAIN_NOUN>` → what's being listed (e.g. "property", "watch",
  "legal-services engagement")
- `<DOMAIN_PHOTO_OR_DOC>` → the binary content kind your seeking agent's ask
  for (e.g. "request_floorplan", "request_provenance_photo")
- `<DOMAIN_DETAIL>` → a vertical-specific text detail
- `<DOMAIN_PII_GATED>` → a sensitive ask that always requires user
  confirmation (analogue of cars' `request_vin`)

Also rename the two folders inside `skills/` from `<vertical>-offering`
and `<vertical>-seeking` to your concrete names.

## Rules every pack must respect

These come from `AGENTS.md` and apply uniformly:

- No tag introduced without a `schema_version` policy. Within a
  major version, changes are additive only; breaking changes require
  a new major (e.g. `<vertical>-pack@2`) and a written migration
  plan.
- Photos and binary documents NEVER ride a public URL. They flow as
  MCP `ImageContent` / `EmbeddedResource` blocks returned from a
  tool call on the offering agent's own MCP server. If a payload exceeds
  ~10 MB, it may be returned as a `Resource(uri="local://...")`
  whose URI resolves through the same MCP server's `resources/read`
  endpoint — never an external host.
- No tag carries PII (full name, full address, phone, government
  IDs, payment instruments). Such fields stay on the offering agent's
  machine and travel only over an authenticated MCP session, behind
  an explicit user-confirm grant.
- Local capability MCPs in `mcp/` may compute over data the user
  already has, query free authoritative sources, or aggregate data
  already on the network. They MAY NOT resell commercial data
  brokers' feeds.
- Offering agents MAY expose more tools than the contract requires; seeking agents'
  skills surface unknown tools to the user as "this offering agent offers
  also: …".

## After you have filled it in

1. Bump the pack version in your new `README.md` to `<vertical>-pack@1`.
2. Add a one-line entry in `verticals/README.md`'s example tree.
3. Add an entry in the top-level `README.md` "What's in this repo"
   tree.
4. If your pack ships any local capability MCPs, document each one
   in its own file under `mcp/<mcp-name>.md` with the rationale
   that satisfies `AGENTS.md` rule 6.
