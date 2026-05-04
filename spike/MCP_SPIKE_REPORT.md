<!-- (Historical -- written under the project's previous name "neuro-spati", now called "chaos".) -->

# MCP spike report — final verdict

**Date**: 2026-05-02
**SDK**: `mcp==1.27.0`
**Result**: PASS on first attempt
**Verdict**: **MCP is the canonical peer-to-peer transport for neuro-spati.**

This is the third and final transport spike. Read the previous two
(`README.md` for ACP, `A2A_SPIKE_REPORT.md`) for context. This one
closes the question.

## What was tested

Two seller MCP servers and one buyer MCP client, all in distinct
processes:

- `seller_mcp.py` × 2 — two `FastMCP` servers running on
  `127.0.0.1:7501` (alice) and `127.0.0.1:7502` (bob), each
  exposing the same tool surface (`view_listing`, `request_photos`,
  `request_inspection_report`) but with **different bytes**
  (different PNGs per seller, so SHAs distinguish them).
- `buyer_mcp.py` — spawns both, in parallel via `asyncio.gather`:
  1. opens an MCP HTTP+SSE session to each
  2. calls `tools/list` (bootstrap)
  3. calls `request_photos(...)` (binary)
  4. calls `request_inspection_report(...)` (resource binary)
  5. SHA-256-verifies the bytes against expected for each seller

## What this proved, in one shot

| Property | Status |
|---|---|
| Cross-network transport (HTTP + SSE) | ✅ |
| Binary content via `ImageContent` (image_block analog) | ✅ |
| Binary content via `EmbeddedResource` (file analog) | ✅ |
| Bootstrap capability discovery via `tools/list` | ✅ |
| Multi-seller parallel fanout (one buyer → two sellers, asyncio.gather) | ✅ |
| Per-session session_id management | ✅ — handled by SDK |
| Hermes integration | ✅ — Hermes already ships an MCP client (`tools/mcp_tool.py`) and server (`mcp_serve.py`); zero glue code needed |

## Result log

```
[buyer]   [bob]   tools/list → ['view_listing', 'request_photos', 'request_inspection_report']
[buyer]   [alice] tools/list → ['view_listing', 'request_photos', 'request_inspection_report']
[seller-bob]   request_photos(item_id=8f4a2b1e, kinds=['exterior']) called
[seller-bob]     → 1 photo bytes=70 sha=d12112152221…
[seller-alice] request_photos(item_id=8f4a2b1e, kinds=['exterior']) called
[seller-alice]   → 1 photo bytes=69 sha=c19c64e14541…
[buyer]   [bob]   image bytes=70 mime=image/png sha=d12112152221…
[buyer]   [alice] image bytes=69 mime=image/png sha=c19c64e14541…
[buyer]   [alice] PASS image sha matches (69 bytes)
[buyer]   [alice] PASS report received (132 bytes)
[buyer]   [bob]   PASS image sha matches (70 bytes)
[buyer]   [bob]   PASS report received (130 bytes)
=== MCP SPIKE PASS ===
```

Both sellers were queried in parallel. Each returned distinct binary
content. Both verified.

## Side-by-side comparison of all three spikes

| Property | ACP | A2A | **MCP** |
|---|---|---|---|
| Designed for | IDE ↔ agent | Agent ↔ agent across orgs | Agent ↔ tool servers |
| Transport in shipping SDK | stdio only | HTTP + JSON-RPC | **HTTP + SSE + WebSocket + stdio** |
| Cross-network ready | requires bridge | yes | **yes** |
| Binary content shape | `image_block(base64_str)` | `Part(raw=bytes)` | `ImageContent(data=base64_str)` + `EmbeddedResource(blob)` |
| Bootstrap discovery | none | static `agent-card.json` | **dynamic `tools/list` per session** |
| Hermes integration | exists (acp_adapter/) but stdio | write own adapter (~3-5 days) | **built in (`tools/mcp_tool.py` + `mcp_serve.py`)** |
| Open governance | newer, in flux | Linux Foundation (Google donated) | **Anthropic-led, broad community spec process** |
| Production ecosystem | Hermes, Zed | Google ADK, LangGraph, CrewAI | **all of the above + Claude Desktop, Cursor, Zed, JetBrains, hundreds of OSS servers** |
| Spike attempts to pass | 2 | 7 | **1** |
| API gotchas hit | 1 | 10 | **0** |
| Spike code lines | ~250 | ~340 | ~280 |
| Multi-agent fanout demonstrated | no | no | **yes** |
| Tool-shaped semantic fit for marketplace | medium | high | **high** |

## Why MCP wins for our specific case

1. **Hermes integration is structurally free.** The buyer side
   doesn't need a single line of glue code — Hermes' built-in MCP
   client (`tools/mcp_tool.py`) connects to any MCP server and
   surfaces its tools to the agent's reasoning loop as if they were
   native. Seller side similarly: Hermes ships `mcp_serve.py` which
   we extend / mirror, ~100 lines.

2. **`tools/list` is real bootstrap, not static metadata.** The buyer
   doesn't need to know in advance what the seller exposes. The
   seller can change its tool surface dynamically (per buyer, per
   item, per time of day). This matches the actual semantics of
   peer-to-peer commerce — sellers' offerings change.

3. **Vertical packs become MCP tool surface contracts.**
   `cars-pack` defines: every cars seller MUST expose
   `view_listing`, `request_photos`, `request_inspection_report`,
   `submit_offer`, `cancel_inquiry`. Future packs (real-estate,
   watches, services) define their own tool sets. The protocol
   (MCP) is universal; the pack is the marketplace contract.

4. **Composability matches the architecture.** A seller-aggregator
   is just an MCP server that internally calls other MCP servers —
   same pattern, recursively. Hierarchies, multi-seller fanout,
   reputation overlay agents — all naturally fit "open another MCP
   session" without protocol-level changes.

5. **MCP is the realest "open standard" of the three.** Multiple
   independent SDKs (Python, TS, Go, Rust, Java), no single-vendor
   contributor dominance, hundreds of production OSS MCP servers
   already exist, all major IDEs adopting. We're not betting on
   nascent protocol momentum — it's already there.

## Architectural commitments locked in by this spike

These become non-negotiable rules in `CLAUDE.md`:

1. **MCP is the canonical peer-to-peer transport.** All
   buyer↔seller dialogue, photo/file exchange, negotiation, and
   structured queries flow over MCP HTTP+SSE.

2. **Each agent runs its own MCP server.** Sellers expose the
   pack-defined tool surface; buyers can also run servers if they
   need other agents to call them (e.g., aggregator buyer agents).

3. **Discovery stays on Nostr.** NIP-99 listings carry the seller's
   MCP endpoint URL in a `["mcp", "https://a.io/mcp"]` tag. Identity
   stays on Nostr pubkeys + NIP-58 badges.

4. **Vertical packs define MCP tool contracts.** A pack is
   `(Nostr tag schema, MCP tool surface spec, buyer skill, seller
   skill, default grant policy)`. Adding a new vertical = adding a
   new pack, never a new protocol.

5. **Binary content travels in `ImageContent` and `EmbeddedResource`
   blocks**, never as a public URL or third-party-host link. If a
   payload is too large to base64 inline (~10MB+ practical limit),
   the MCP server may return a `Resource(uri="local://...")` whose
   URI must point at the **same MCP server's resource endpoint** —
   never an external host.

6. **No protocol-level multi-cast.** Many-to-many topology is
   handled client-side (parallel MCP connections) or via
   composed MCP servers (aggregator pattern). Real swarm consensus
   would require a separate layer, out of scope for v1-v3.

## Architecture: what changes vs. what stays

| Layer | Was (after A2A spike) | Now (after MCP spike) |
|---|---|---|
| L1 — Discovery | Nostr NIP-99 + relays | **unchanged** |
| L2 — Identity | Nostr pubkeys + NIP-58 badges | **unchanged** |
| L3 — Wire transport | A2A HTTP + JSON-RPC (planned) | **MCP HTTP + SSE** |
| L4 — Capability discovery | A2A static agent card | **MCP `tools/list` per-session** |
| L5 — Vertical pack | "v1 protocol" — was vague | **MCP tool surface spec** — concrete |
| L6 — Hermes integration | "write A2A adapter (3-5 days)" | **none — already built** |

The Nostr layer is untouched. The pack layer becomes meaningfully
sharper (tool names + schemas, not just tags). The Hermes plugin
work shrinks because the wire is already plumbed.

## Files this spike produced

```
spike/
├── seller_mcp.py            FastMCP server with view_listing, request_photos, request_inspection_report
├── buyer_mcp.py             MCP client with parallel fanout to two sellers + SHA verification
├── received_mcp/
│   ├── alice_image.png      verified bytes from alice
│   ├── alice_report.txt     verified bytes from alice
│   ├── bob_image.png        verified bytes from bob (different)
│   └── bob_report.txt       verified bytes from bob (different)
└── MCP_SPIKE_REPORT.md      this file (the verdict)
```

The earlier ACP and A2A spike files remain in `spike/` as historical
record. They're marked superseded.

## What this changes in the repo (the sweep that follows)

- `PROTOCOL.md`: rewritten — MCP as the L3/L4 transport, with the
  cars-pack tool surface specified in full
- `CLAUDE.md`: updated — Rule 2 changes from "ACP only" to "MCP only"
  for binary content; new commitments above are codified
- `cars-pack/tag_schema.md`: `["mcp", url]` replaces the older
  `["acp", url]` / `["a2a", url]` tag
- `cars-pack/example_listing.json`: same change
- `cars-pack/skills/seller-cars/SKILL.md`: tool surface aligned to
  MCP tool names
- `cars-pack/skills/buyer-cars/SKILL.md`: same on buyer side
- `seller/IMPLEMENTATION_PLAN.md` and `buyer/IMPLEMENTATION_PLAN.md`:
  shortened (no adapter to write) and re-targeted at MCP
- `seller/README.md` and `buyer/README.md`: terminology + dependency
  list updated (`mcp[cli]` instead of `agent-client-protocol`)
- `OVERVIEW.md`, `LAUNCH_PLAN.md`, `BUSINESS_MODEL.md`, root
  `README.md`: search-replace ACP → MCP where it appears
- `architecture.svg`: diagram label updates
- `spike/seller_acp.py`, `spike/buyer_acp.py`, `spike/README.md`,
  `spike/seller_a2a.py`, `spike/buyer_a2a.py`, `spike/A2A_SPIKE_REPORT.md`:
  preserved as-is, headers note they're superseded by this spike
