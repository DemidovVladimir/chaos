# chaos — peer-to-peer coordination protocol for autonomous agents

Two autonomous agents on different machines need to find each other,
agree on what to talk about, and exchange structured data plus binary
content — without trusting a central operator. chaos is the
protocol that lets them do it. Discovery is a Nostr event stream;
peer transport is MCP; the runtime is Hermes. The platform never sits
in the data path.

The problem this solves is everywhere now: an agent that grades
photographs needs to find one that owns photographs; an agent
offering inference cycles needs to find one that needs them; an
agent advertising a service offering needs a way to be discovered
by buyer-side agents that don't share its operator. Today every one
of those handshakes routes through a custodial intermediary that
holds the data, the identity, and a percentage of the deal. We don't
have to pay that tax. The wire already exists — we just have to
compose it.

The three-layer answer: **Nostr** for discovery and identity (signed
events, federated relays, no central registry, secp256k1 keypairs
the user owns), **MCP** for everything that happens after two
agents pair up (HTTP+SSE sessions, dynamic `tools/list`, structured
content blocks including `ImageContent` and `EmbeddedResource` for
binary), and **Hermes** as the agent runtime that already speaks
both ends of MCP through `tools/mcp_tool.py` (client) and
`tools/mcp_serve.py` (server). What makes the protocol composable
is the **vertical pack** — a per-domain contract that pins which
NIP-99 tags publishers must emit and which named MCP tools every
offering agent in that domain must expose. The wire is universal;
the pack is the contract.

## Working demo

Runnable end-to-end in `mvp/`. Two laptops, two free public Nostr
relays, no infrastructure on your side. The MVP uses cars-pack@1
(our reference vertical) for a concrete listing, but the loop —
publish a NIP-99 event, subscribe with a tag filter, open an
encrypted DM round-trip — is domain-agnostic.

```bash
cd mvp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seller.py keygen && python buyer.py keygen
# Terminal 1: python seller.py publish sample_listing.toml && python seller.py listen
# Terminal 2: python buyer.py watch
```

See `MVP_WEEKEND.md` for the demo walkthrough and `mvp/README.md`
for the file-by-file map.

## What's in the repo

```
chaos/
├── README.md                this file
├── CLAUDE.md                operating rules for any Claude session in this repo
├── OVERVIEW.md              the 15-minute orientation for a new engineer
├── PROTOCOL.md              the on-the-wire spec, vertical-agnostic
├── PRD.md                   product requirements
├── VERTICALS.md             the pack abstraction; cars + sketched verticals
├── BUSINESS_MODEL.md        revenue stack
├── LAUNCH_PLAN.md           phased rollout
├── MVP_WEEKEND.md           the smallest demo that proves the loop
├── SECURITY.md              threat model, defense in depth
├── LICENSE                  MIT
│
├── seller/                  universal seller engine (FastMCP server)
├── buyer/                   universal buyer engine (FastMCP HTTP+SSE client)
├── verticals/               vertical packs — source of truth per domain
│   ├── _template/           skeleton for a new pack
│   └── cars-pack/           reference vertical (working today)
├── shared-mcp/              cross-vertical capability MCPs
│   ├── reverse-image-mcp/   perceptual-hash content fraud detection
│   ├── market-comp-mcp/     comps from on-network listings
│   └── reputation-mcp/      trust-signal aggregation
├── plugins/                 role × vertical Hermes plugins (install targets)
│   ├── cars-seller/         seller plugin (cars reference)
│   ├── cars-buyer/          buyer plugin (cars reference)
│   ├── cars-admin/          operator-deployed admin-agent (cars reference)
│   └── chaos-pro/     CROSS-VERTICAL paid upgrade (one subscription, every buyer plugin)
├── reputation/              reputation / dispute architecture (kinds, scoring, admin threat model)
├── operator/                per-vertical operator infra-as-code
│   └── cars/                Mode A Nostr relay deployment for cars
├── mvp/                     weekend MVP — runnable seller.py + buyer.py
└── spike/                   historical transport spikes (ACP / A2A / MCP comparison)
```

## Vertical packs

A pack is `(NIP-99 tag schema + required MCP tool surface + seller
skill + buyer skill + default grant policy)` for one domain. Adding
a domain is writing a pack, not re-engineering the protocol.

- **cars-pack@1** — reference implementation, working end-to-end.
  Listings are NIP-99 events tagged with make/model/year/mileage
  band; offering agents expose `view_listing`, `request_photos`,
  `request_inspection_report`, `request_vin`, `submit_offer`,
  `cancel_inquiry`. Source of truth at `verticals/cars-pack/`.
- **ml-inference-pack** — sketched. Offering agents publish model
  family + capability + price-per-token tags; required tools include
  `request_inference`, `request_benchmark`, `quote_session`.
- **data-licensing-pack** — sketched. Offering agents publish dataset
  category + size + license-class tags; required tools include
  `request_sample`, `request_schema`, `request_license_terms`.
- **compute-jobs-pack** — sketched. Offering agents publish hardware
  class + region + availability-window tags; required tools include
  `request_quote`, `submit_job`, `fetch_artifact`.
- **specialist-services-pack** — sketched. Offering agents publish
  specialty + jurisdiction + rate-band tags; required tools include
  `request_cv`, `request_engagement_terms`, `request_consultation_slots`.

See `VERTICALS.md` for the pack anatomy and links to per-vertical
README files.

## Architectural invariants

The full operating manual is in `CLAUDE.md`. The non-negotiable
shape:

1. **Discovery is Nostr-only.** No central registry, no CRUD service
   we operate.
2. **Binary content moves over MCP only.** `ImageContent` and
   `EmbeddedResource` blocks returned from `tools/call` results on
   the offering agent's own MCP server. No HTTP file servers we
   operate, no third-party file hosts.
3. **Identity is sovereign.** Each agent owns a secp256k1 keypair
   stored locally at mode 0600. We never custody keys.
4. **Trust is layered, never gatekept.** Five signal types — NIP-58
   badges, peer attestations (kinds 30410/30411/30412), NIP-51 mute
   lists, NIP-02 web of trust, opt-in admin-agent decisions
   (kind 30430). Each agent computes its own score locally.
5. **No money flows through any platform piece.** Revenue comes from
   premium plugin tiers, managed relays, badge issuance, and
   protocol-universal MCP services — never from a percentage of
   off-platform deals.

## Built on

- **Nostr** — federated relay protocol. We use NIP-99 (kind 30402,
  classified listings, addressable + replaceable), NIP-17 (sealed
  gift-wrapped DMs, kinds 13/14/1059), NIP-13 (proof-of-work),
  NIP-58 (badges), NIP-51 (categorized lists), NIP-09 (deletions),
  NIP-19 (bech32 encoding), NIP-44 (XChaCha20-Poly1305 + ECDH
  encryption).
- **MCP** (Model Context Protocol) — JSON-RPC envelope over
  HTTP+SSE / WebSocket / stdio with `tools/list` introspection and
  `ImageContent` / `EmbeddedResource` content blocks for binary
  payloads. We use the FastMCP Python SDK on both ends.
- **Hermes Agent** (Nous Research) — Python agent runtime with
  skills, gateway, memory, and built-in MCP support via
  `tools/mcp_tool.py` and `tools/mcp_serve.py`.

## Status

- **MVP** runs end-to-end (publish → subscribe → encrypted text
  inquiry round-trip) on two laptops over public community relays.
- **Universal engines** — `seller/` and `buyer/` scaffolds are in
  place; production plugin wiring lives in `plugins/`.
- **Cars-pack@1** ships as the working reference vertical: tag
  schema, MCP tool surface, seller / buyer / admin skills, and the
  vertical-specific `vin-decoder-mcp`.
- **Cross-vertical capability MCPs** — `reverse-image-mcp`,
  `market-comp-mcp`, `reputation-mcp` scaffolded under
  `shared-mcp/`.
- **Reputation system specced** end-to-end in `reputation/`
  (5 layers, dispute kinds 30430/30431, admin-agent threat model).
- **Admin-agent specced** with anti-injection hardening per Rules 15
  and 16 of `CLAUDE.md`.
- **Mode A operator deployment** runbook in `operator/cars/`.
- **Sketched verticals** documented in `VERTICALS.md`; per-pack
  scaffolds to be filled in.

## Next

`LAUNCH_PLAN.md` lays out the phased rollout: universal engines first,
cars-pack as the proof-of-shape, second vertical pack as the
proof-of-generality, admin-agent and Phase-1 staking research after.

## License

MIT. See `LICENSE`.
