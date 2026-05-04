# Vertical-specific local capability MCPs

Drop vertical-specific local capability MCP specs here, one per
file (`<mcp-name>.md`). These are MCPs the seller or buyer agent
calls **under the hood** while preparing a listing or evaluating
one — not the seller's marketplace MCP server (which exposes the
vertical's tool surface to buyers).

Examples from `cars-pack`: `reverse-image-mcp` (paid, perceptual-
hash photo-fraud detection), `vin-decoder-mcp` (free, ISO-3779
structural decode), `market-comp-mcp` (free, pricing comps from
listings already on the relay).

## Rules these must follow

(All of these come from `CLAUDE.md`; restating here so a vertical
author can sanity-check their proposal in one place.)

1. **Free, or one-shot paid (per-call, x402-style).** Subscriptions
   are out of scope. A user pays per call, runs the MCP locally,
   and owns the result.
2. **No commercial data brokers.** Custom MCPs may compute over
   data the user already has, query free authoritative sources
   (e.g. a public WMI registry, a national stolen-vehicle
   database), or aggregate data already on the network. They MAY
   NOT resell commercial vehicle-history data, address-verification
   data, person-lookup data, or anything that would require us to
   operate as a data processor.
3. **No third-party file hosts.** No Imgur, Dropbox, S3, Blossom,
   or signed URLs to outside hosts. Binary inputs come from the
   user's local files or from MCP `ImageContent` /
   `EmbeddedResource` blocks the agent already received from
   another MCP server.
4. **No commercial PII reseller.** Don't wrap a paid people-search
   API.
5. **Run locally by default.** The MCP is a binary the user
   installs and runs; the protocol is MCP HTTP+SSE on localhost
   (or stdio for tighter integrations).

## Spec template

Each file `mcp/<mcp-name>.md` should describe:

- **Purpose** — one sentence
- **Pricing** — free, or per-call price + denomination
- **Tool surface** — `tools/list` output: tool name, args, return
  type. Use MCP content types (`TextContent`, `ImageContent`,
  `EmbeddedResource`) where appropriate
- **Inputs** — what data the MCP expects (raw bytes received from
  the agent, never URLs)
- **Data sources** — free / local / public; explicitly state that
  no commercial broker is queried
- **Rationale** — why this MCP belongs at the pack level and why
  it satisfies `CLAUDE.md` rule 6

## Adding a new MCP

When you add an MCP here, also add a one-line bullet under the
pack's `README.md` `## What this pack adds` section so users
discover it.
