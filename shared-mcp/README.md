# shared-mcp/ — capability MCPs that work across verticals

This folder holds **capability MCPs** that are useful in more than
one vertical (cars, real-estate, watches, …). Vertical-specific
MCPs live in `verticals/<vertical>-pack/mcp/`.

Each subfolder here is a **standalone Python package** with a
FastMCP server inside. Any vertical role-plugin (e.g.
`plugins/cars-buyer`) can list one or more of these as a
`capability_mcps` dependency in its `plugin.yaml`.

## What lives here

- `reverse-image-mcp/` — perceptual-hash photo fraud detection
  (universal — applies to any vertical that exchanges photos).
- `market-comp-mcp/` — pricing comparables computed from NIP-99
  listings already on the relay (universal — works for any vertical
  whose listings carry a numeric price tag).
- `reputation-mcp/` — layered trust-signal aggregation: badges,
  attestations, admin decisions, web-of-trust depth, optional
  on-chain stake (universal — every vertical needs it).
- `_template/` — copy-and-fill skeleton for adding a new shared MCP.

## Rules (from `AGENTS.md` rules 2 and 6)

1. **Free, or one-shot paid (per-call x402-style).** No
   subscriptions inside the MCP itself; subscriptions live at the
   plugin layer (`chaos-pro`).
2. **No third-party data brokers.** Compute over data the user
   already has, query free authoritative sources, or aggregate data
   already on the network. Do NOT resell commercial vehicle-
   history, address-verification, person-lookup, or any data that
   would force us to operate as a data processor.
3. **No third-party file hosts.** No Imgur, Dropbox, S3, Blossom,
   or signed URLs to outside hosts. Binary inputs come from the
   user's local files or from MCP `ImageContent` /
   `EmbeddedResource` blocks the agent already received.
4. **Run locally by default.** The MCP is a binary the user
   installs and runs; the protocol is MCP HTTP+SSE on localhost
   (or stdio for tighter integrations). The hosted variant (if
   any) MUST be no-retention TLS-in-only.
5. **Pack-level vs protocol-level.** If the MCP is useful only for
   one vertical, it belongs in `verticals/<vertical>-pack/mcp/`,
   not here.

## Adding a new shared MCP

1. Copy `_template/` to `shared-mcp/<your-mcp>/`.
2. Fill in `README.md`, `manifest.yaml`, and the `server.py` stub.
3. List it in this README under "What lives here".
4. Add it to the relevant role-plugin's `plugin.yaml` under
   `includes.capability_mcps`.
