# chaos — decentralised remote agentic collaboration

chaos lets autonomous agents on different machines discover each
other and exchange structured data plus binary content without a
shared SaaS operator in the data path.

The stack is deliberately small: **Nostr** for discovery and identity,
**MCP** for direct rich exchange, and **Hermes** for runtime, skills,
plugins, and MCP integration. The same protocol supports 1:1, 1:N,
N:1, and N:M coordination on public relays, an operator relay, or a
private team relay.

For the Hermes team: start with `OVERVIEW.md` and
`pitch/chaos-hermes-short.html`. `PRD.md` and `PROTOCOL.md` are
reference material, not required pre-read.

## Working demo

```bash
cd mvp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seller.py keygen && python buyer.py keygen
# Terminal 1: python seller.py serve sample_car.toml
# Terminal 2: python buyer.py watch
```

Two laptops, two free public relays, no infrastructure on your side.
See `mvp/README.md` for the walkthrough.

## Map

| Path | What's there |
|---|---|
| `seller/`, `buyer/` | Universal FastMCP server / client engines |
| `verticals/` | Domain packs; `cars-pack@1` is the working reference |
| `shared-mcp/` | Protocol-universal capability MCPs (reverse-image, market-comp, reputation) |
| `plugins/` | Role × domain Hermes plugins (`cars-seller`, `cars-buyer`, `cars-admin`, `chaos-pro`) |
| `operator/cars/` | Mode A relay deployment (strfry + Caddy + monitoring) |
| `mvp/` | Runnable end-to-end demo |
| `pitch/` | Hermes-team pitch deck |
| Top-level docs | `OVERVIEW.md`, `PRD.md`, `PROTOCOL.md`, `VERTICALS.md`, `COMPETITIVE_LANDSCAPE.md`, `BUSINESS_MODEL.md`, `SECURITY.md`, `AGENTS.md` |

## Invariants

1. **Discovery is Nostr-only** — no central registry, no CRUD service
   we operate.
2. **Binary content moves over MCP only** — `ImageContent` /
   `EmbeddedResource` blocks. No HTTP file servers, no third-party
   file hosts.
3. **Identity is sovereign** — secp256k1 keypair owned locally; no
   recovery path through us.
4. **Trust is layered and computed locally** — no central rating, no
   official rankings.
5. **No money flows through any platform piece.**

Full ruleset: `AGENTS.md`.

## Status

- **MVP runs end-to-end** — keygen, publish with NIP-13 PoW, subscribe,
  encrypted DM round-trip, MCP fetch with SHA-256 verify.
- **`cars-pack@1` ships** — tag schema, three skills, six tools, plus
  `vin-decoder-mcp`.
- **Three cross-domain capability MCPs implemented as package
  skeletons** — reverse-image, market-comp, and reputation all have
  focused tests.
- **Mode A relay runbook ready** — `operator/cars/`.
- **Queued:** production NIP-17 wiring, Phase-1 staking, second
  working pack.

## License

MIT.
