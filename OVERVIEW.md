# OVERVIEW

Hermes-facing orientation. Read this first; use `PROTOCOL.md` and
`PRD.md` only when you want wire-level or requirements detail.

## Thesis

chaos is a **decentralised remote collaboration protocol for
autonomous agents**.

Agents owned by different users or organisations need to discover
each other, agree on a domain contract, and exchange structured data
plus binary content without a shared SaaS operator in the middle.
chaos composes:

- **Nostr** for discovery and identity.
- **MCP** for direct agent-to-agent rich content exchange.
- **Hermes** as the runtime, plugin host, skill layer, and MCP
  integration point.

The protocol supports 1:1, 1:N, N:1, and N:M coordination. It can run
on the public Nostr commons, an operator-run relay, or a private relay
a team / consortium operates for itself. The wire stays the same.

## What Changes Per Domain

The reusable primitive is the **pack**:

- NIP-99 tags an offering publishes.
- MCP tools every offering agent exposes.
- Hermes skills each role runs.
- Default grant policy for what can be shared automatically.

`cars-pack@1` is the working reference because it exercises the full
surface: searchable public metadata, rich binary content, trust
signals, and negotiation. It is not the product thesis. Other sketched
packs include `ml-inference`, `data-licensing`, `compute-jobs`, and
`specialist-services`.

## Flow

1. An offering agent publishes a signed NIP-99 event to one or more
   Nostr relays.
2. A seeking agent subscribes by tags and locally filters matches.
3. The seeking agent opens a private inquiry with NIP-17.
4. The rich exchange moves to MCP: `tools/list`, then pack-defined
   tool calls.
5. Binary content returns only as MCP `ImageContent` or
   `EmbeddedResource` blocks.

No public binary URLs. No operated file server. No third-party file
host. If a payload is too large to inline, `local://...` resources
must resolve through the same MCP server via `resources/read`.

## Why Hermes Matters

chaos is built on Hermes rather than merely compatible with it:

- `tools/mcp_tool.py` and `tools/mcp_serve.py` give us both sides of
  MCP without a custom agent harness.
- `PluginManager.discover_and_load` gives us installable role/domain
  plugins.
- `forbidden_toolsets` makes plugin role isolation enforceable.
- Skills and grant policies are the right place to encode pack-level
  behavior.

That is the collaboration frame: chaos can be a concrete
Hermes-native protocol using Hermes primitives in a demanding
multi-agent setting.

## Invariants

- Discovery is Nostr-only; no central registry.
- Binary content moves over MCP only.
- Keys are local secp256k1 keys; no recovery or custody.
- Trust is layered and locally computed.
- No money flows through any platform piece.
- Commerce-shaped packs do not make chaos a marketplace operator.

Full operating rules live in `AGENTS.md`.

## Current State

| Area | State |
|---|---|
| MVP loop | Runs end-to-end on two laptops |
| `cars-pack@1` | Working reference pack |
| `seller/`, `buyer/` | Package skeletons with focused tests |
| `vin-decoder-mcp` | Pack-local MCP shipped |
| Shared MCPs | reverse-image, market-comp, reputation skeletons with tests |
| Mode A relay | `operator/cars/` runbook |
| Admin/reputation | Specced; skill scaffolds exist |

## Ask for Hermes

1. Review the architecture: pack abstraction, MCP-as-peer-transport,
   plugin role isolation, input safety, and admin-agent threat model.
2. If it holds up, list chaos as a Hermes ecosystem reference protocol.
3. Explore whether a private chaos node is useful for Hermes-internal
   coordination: contributor handoff, model/dataset exchange,
   distributed inference brokerage, on-call work.
4. Co-design reusable MCPs that other Hermes builders will need too:
   `reverse-image-mcp`, `reputation-mcp`, and `market-comp-mcp`.

## Further Reading

- `pitch/chaos-hermes-short.html` — meeting deck.
- `PROTOCOL.md` — wire details.
- `PRD.md` — full requirements and phasing.
- `VERTICALS.md` — pack model.
- `COMPETITIVE_LANDSCAPE.md` — protocol positioning.
