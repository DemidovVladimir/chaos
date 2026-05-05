# verticals — vertical packs live here

A **vertical pack** is what makes the chaos protocol composable. Each
pack defines, for one domain of offerings, the small set of
conventions every offering-side and seeking-side agent in that domain
agrees to. The wire is universal; the pack is the contract.

A pack is, in concrete terms, five things:

1. A **NIP-99 tag schema** — which tags every listing in this
   vertical must carry, which are recommended, which are optional,
   and which categories of data must NEVER appear on the public
   listing (PII, exact addresses, anything that should travel only
   over an authenticated MCP session).
2. An **MCP tool surface contract** — the named tools every offering agent
   in this vertical must expose on their FastMCP HTTP+SSE server,
   with their argument schemas and response semantics. Seeking agents'
   agents discover these via `tools/list` against the offering agent's
   `["mcp", "<url>"]` tag and call them via `tools/call`. Photos and
   documents come back as `ImageContent` and `EmbeddedResource`
   blocks.
3. A **offering agent/offering skill** — a Hermes skill (`skills/<vertical>-offering/SKILL.md`)
   that knows how to publish a well-formed listing, run the MCP
   server, and apply the per-tool grant policy.
4. A **seeking agent/seeking skill** — a Hermes skill
   (`skills/<vertical>-seeking/SKILL.md`) that knows how to translate
   user wants into REQ filters, evaluate listings against a rubric
   of red and green flags, and call the offering agent's tools in the right
   order.
5. **Optional vertical-specific local capability MCPs** — small
   utility MCPs an offering or seeking agent calls under the hood
   (e.g. cars-pack ships `reverse-image-mcp`, `vin-decoder-mcp`,
   `market-comp-mcp`). These run on the user's own machine. They
   never resell commercial data; see `AGENTS.md` rule 6.

## Why one folder per pack

Each pack is independently installable and independently versioned.
Putting them as siblings under `verticals/` keeps the protocol-level
docs (`PROTOCOL.md`) clean and lets a deployment ship just the packs
it needs. The cars-only operator installs `cars-pack`; the multi-
vertical operator installs several.

`cars-pack/` is the working reference pack. Other packs slot in as
siblings:

```
verticals/
├── README.md
├── _template/                 copy-and-fill skeleton
├── cars-pack/                 cars-pack@1   (working reference)
├── ml-inference-pack/         sketched
├── data-licensing-pack/       sketched
├── compute-jobs-pack/         sketched
└── specialist-services-pack/  sketched
```

Same shape, different tags + tool surface.

## What every pack must include

Five files, regardless of vertical:

- `README.md` — what this pack is, which version is current, where
  to read first.
- `tag_schema.md` — required / recommended / optional NIP-99 tags;
  what is NEVER on the public listing; the MCP tool surface; rules
  of thumb.
- `example_listing.json` — a complete NIP-99 event a offering agent could
  publish today, with every required tag filled in.
- `skills/<vertical>-offering/SKILL.md` and
  `skills/<vertical>-seeking/SKILL.md` — the two Hermes skills.
- `mcp/` (optional) — vertical-specific local capability MCPs.

## The wire stays universal

The protocol (`PROTOCOL.md`) does not change between verticals.
Discovery is NIP-99 (`kind: 30402`) plus NIP-13 PoW; identity is
secp256k1; trust signals are NIP-58 badges, NIP-51 mute lists, and
offering agent pubkey reputation; DMs are NIP-17. The peer transport is MCP
HTTP+SSE. Hermes is the runtime. Only the *contents* of the pack
change between verticals.

## Compatibility note

Pack names are versioned: `cars-pack@1`, `realestate-pack@1`. The
version appears as a NIP-99 `["pack", "<name>@<version>"]` tag on
every listing. Within a major version, changes are **additive only**
— new optional tags, new optional MCP tools, new recommended fields.
A breaking change (renamed required tag, changed tool semantics,
removed required field) requires a major version bump and a written
migration plan documented in the pack's `README.md`.

## Adding a vertical

To add a vertical, copy `_template/` to `verticals/<name>-pack/` and
fill in the placeholders. Every file in `_template/` carries
`<PLACEHOLDER>` markers and inline notes explaining what each
section means.
