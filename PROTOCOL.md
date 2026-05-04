# PROTOCOL — on-the-wire design

This document is the wire-protocol spec, **vertical-agnostic by
design**. The protocol composes two open mechanisms:

- **Nostr** for discovery, identity, and structured 1-to-1 inquiries
- **MCP** (Model Context Protocol) for rich agent-to-agent dialogue
  including binary content blocks

The contract structure described here applies to any vertical pack
the protocol carries. Concrete examples below use `cars-pack@1` —
that's our reference vertical, the first one we shipped, and the one
the MVP demonstrates. Replace the cars-specific tags and tool names
with another pack's vocabulary (e.g. `ml-inference-pack@1`,
`data-licensing-pack@1`) and the wire is identical. See
`VERTICALS.md` for the pack abstraction and the four sketched
verticals.

If you want the product narrative, read `OVERVIEW.md`. If you want
the precise requirements, read `PRD.md`. This document is what goes
on the wire.

## Identity

Each agent owns a **secp256k1 keypair**. The pubkey (32-byte
x-only, BIP-340) is the agent's identity, encoded as `npub1…`
(NIP-19 bech32) for display. Keys are stored at
`~/.chaos/keys/{seller|buyer}.key` mode 0600.

There is no recovery mechanism. Sovereignty has costs.

In v2 we may add NIP-46 remote-signer support so users can hold the
key on a hardware device.

## Discovery — NIP-99 classified listings

Listings are **NIP-99** events (`kind: 30402`, addressable +
replaceable). Each vertical pack defines its own tag schema; the
example below is `cars-pack@1` (`verticals/cars-pack/tag_schema.md`)
shown to make the structure concrete. Other packs declare their own
tag vocabulary against the same kind 30402 envelope. Minimum
required tags (cars-pack@1 example):

```json
{
  "kind": 30402,
  "pubkey": "<seller's pubkey hex>",
  "created_at": 1714780800,
  "tags": [
    ["d", "<item-uuid>"],
    ["title", "..."],
    ["summary", "..."],
    ["price", "<amount>", "<currency>", ""],
    ["location", "<region path>"],
    ["t", "cars"],
    ["t", "<make>"],
    ["make", "<lowercase>"],
    ["model", "<lowercase>"],
    ["year", "<integer>"],
    ["body_type", "<enum>"],
    ["fuel_type", "<enum>"],
    ["transmission", "<enum>"],
    ["mileage_band", "<bucket>"],
    ["mcp", "<https url to seller's MCP server, e.g. https://a.io/mcp>"],
    ["pack", "cars-pack@1"]
  ],
  "content": "<short description, ≤ 4000 chars; full one stays local>"
}
```

`d` makes the event addressable: republishing with the same `d` value
replaces the previous version on cooperative relays. Combined with a
NIP-09 deletion request, this gives item updates and removals.

The `mcp` tag is **required** in v1 — it points to the offering
agent's MCP server endpoint that exposes the pack-mandated tool
surface. The `pack` tag tells the seeking-side agent which contract
version to expect (so we can evolve packs without breaking older
clients) and lets a single relay carry many packs without
ambiguity.

Public listings carry **no public binary URLs.** Binary content
(images, PDFs, datasets, model artifacts) arrives via MCP only after
the offering agent explicitly grants the inquiry.

## Sybil / spam — NIP-13 PoW

NIP-13 is **Hashcash for Nostr**, not Bitcoin consensus. The
publisher mines a nonce so the event id has ≥ N leading zero bits.
The relay verifies the count and accepts or rejects. No miners, no
chain, no rewards.

Cost on a normal laptop using `hashlib`:

| Difficulty | Wall-clock |
|---:|---:|
| 16 bits | ~10 ms |
| 20 bits | ~150 ms |
| 24 bits | ~2 s |

We require **≥ 20 bits** on listing publishes. Encrypted DMs
(NIP-17 gift wraps, kind 1059) skip PoW because they're encrypted
and sybil-DM is self-limiting (recipients ban-list the sender's
pubkey).

A spammer wanting 10,000 fake listings at 24 bits pays ~5–6 hours of
single-CPU work. Combined with paid relays + reputation overlay,
bulk abuse is uneconomical.

## Subscriptions — Nostr REQ filters

Seeking-side agents subscribe to the configured relays with REQ
filters shaped against the relevant pack's tag schema. The example
below uses cars-pack@1 facets to be concrete; the same filter shape
carries any pack's vocabulary:

```json
[
  "REQ",
  "<sub-id>",
  {
    "kinds": [30402],
    "#t": ["cars", "mazda"],
    "#body_type": ["hatchback", "wagon"],
    "#fuel_type": ["gasoline", "hybrid"],
    "#transmission": ["manual"],
    "#year": ["2015","2016","2017","2018","2019","2020"],
    "#mileage_band": ["0-10k","10k-25k","25k-50k","50k-75k"],
    "#location": ["EU/CZ/%"],
    "#price_band": ["5k-10k EUR","10k-20k EUR"],
    "since": 1714780000,
    "limit": 50
  }
]
```

Discrete tag matches happen on the relay's index. Numeric ranges
that don't fit discrete buckets (precise year, exact mileage) are
expressed as the set of acceptable bucket values. Buyer-side
post-filtering handles whatever the relay can't.

## 1-to-1 messaging — NIP-17 sealed gift-wraps

Counterparty-to-counterparty messages (seeking-side to offering-side
and back) are **NIP-17 sealed gift-wraps**. Three layers:

1. **Rumor** (`kind: 14`) — the structured payload (initial inquiry
   intent, MCP session bootstrap), signed by the sender.
2. **Seal** (`kind: 13`) — the rumor encrypted with NIP-44 to the
   recipient's pubkey, signed by the sender.
3. **Gift wrap** (`kind: 1059`) — the seal encrypted with NIP-44
   from a fresh ephemeral keypair, signed by that ephemeral key,
   tagged `["p", "<recipient_pubkey>"]`.

Relays carry the gift-wrap. They cannot read the content (NIP-44
encrypted). They cannot prove who sent it (ephemeral key signature).
They can see *that* a gift-wrap was delivered to a recipient pubkey
and the timing.

The Nostr-side rumor is intentionally minimal — just enough to
**bootstrap an MCP session**:

```json
{
  "type": "mcp_inquiry_open",
  "item_id": "<seller's d tag value>",
  "buyer_pubkey": "<buyer pubkey hex>",
  "session_token": "<32-byte random base64>",
  "nostr_correlation_id": "<uuid for replay protection>"
}
```

The offering agent's MCP server validates the `session_token` (it
must match what the offering agent expects from this counterparty
pubkey for this item). Once validated, the seeking agent connects
to the offering agent's `mcp_url` (from the NIP-99 listing) and the
rest of the conversation happens over MCP.

In short: **Nostr opens the channel; MCP carries the conversation.**

## Rich content — MCP tool calls and content blocks

The offering agent runs an MCP server. The seeking agent connects as
an MCP client. **Every pack defines its required tool surface** —
the named tools every offering agent in that vertical must expose.
The example below shows the cars-pack@1 contract; another pack's
tool surface (e.g. `request_inference` / `quote_session` for ML
inference, `request_sample` / `request_schema` for data licensing)
follows the same shape.

### Bootstrap — `tools/list`

After the seeking agent's MCP client `initialize`s the session, it
calls `tools/list`. The offering agent returns the catalog of tools,
schemas, and descriptions (cars-pack@1 example):

```json
[
  {
    "name": "view_listing",
    "description": "Return a textual summary of the item.",
    "inputSchema": {
      "type": "object",
      "properties": {"item_id": {"type": "string"}},
      "required": ["item_id"]
    }
  },
  {
    "name": "request_photos",
    "description": "Return photos as ImageContent blocks. Subject to grant policy.",
    "inputSchema": {
      "type": "object",
      "properties": {
        "item_id": {"type": "string"},
        "kinds": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["item_id"]
    }
  },
  {"name": "request_inspection_report", "description": "..."},
  {"name": "request_vin", "description": "..."},
  {"name": "submit_offer", "description": "..."},
  {"name": "cancel_inquiry", "description": "..."}
]
```

The seeking agent feeds these into its reasoning loop. **Discovery
is dynamic, per session** — the offering agent may expose different
tools per counterparty (per item type, per trust level) and the
seeking agent adapts.

### Tool calls and binary content

The seeking agent calls a tool (cars-pack@1 example):

```json
{
  "method": "tools/call",
  "params": {
    "name": "request_photos",
    "arguments": {"item_id": "8f4a2b1e", "kinds": ["exterior", "engine_bay"]}
  }
}
```

The offering agent's MCP server runs its grant policy (which lives
in the agent's Hermes skill — for the cars example, see
`verticals/cars-pack/skills/seller-cars/SKILL.md`). If granted, it
returns a list of content blocks:

```python
return [
    ImageContent(type="image", data=base64(jpeg_bytes_1), mimeType="image/jpeg"),
    ImageContent(type="image", data=base64(jpeg_bytes_2), mimeType="image/jpeg"),
    EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri="local://item/abc/inspection.pdf",
            mimeType="application/pdf",
            blob=base64(pdf_bytes),
        ),
    ),
]
```

If denied, the seller returns an error result with reason. The buyer
agent surfaces this to the user.

### Binary content rule — never via HTTP

This is the architecture's hardest rule (see `CLAUDE.md`):

- **No HTTP file server we operate**
- **No signed URLs to the offering agent's local file server**
- **No third-party file host** (Imgur, Dropbox, S3, ngrok-tunneled,
  Blossom, anything)
- **No public binary URLs in NIP-99 listings**
- **All binary content moves agent-to-agent over MCP content blocks
  (`ImageContent` and `EmbeddedResource`)**

Binary content exists on two disks — the offering agent's machine
and (after a granted inquiry) the seeking agent's machine. Nothing
in between holds it.

If a payload exceeds practical inline size (~10 MB), the offering
agent may return a `Resource` with `uri="local://..."` whose URI
**must resolve through the same MCP server's resources endpoint**,
never an external host. The MCP `resources/read` call retrieves it.
Same agent, same TLS, same auth context.

### Negotiation rounds

After the rich content has been shared, negotiation continues as
additional MCP tool calls (`submit_offer`, `accept_offer`,
`cancel_inquiry` — names by convention; each pack may extend or
rename them). Limits:

- Max 5 rounds per (item, counterparty)
- Max 1000 chars per offer message
- Max 50,000 chars total per match

Both ends enforce these. Acceptance always requires explicit user
confirmation in the same session (the offering agent prompts its
user before any `accept_offer` returns success).

When both sides accept, each agent stores a small "agreement" event
locally signed by both parties. There is **no central agreement
registry**. The off-platform handover (payment + key / title /
artifact / dataset transfer, depending on the vertical) is the
users' responsibility.

## Many-to-many topology

Coordination flows are mostly pairwise (one seeking agent, one
offering agent). Two non-pairwise patterns are explicitly supported:

### Seeker fanout (one seeking agent → N offering agents)

The seeking agent opens N independent MCP connections in parallel
(`asyncio.gather`). Each is a self-contained session. Common case:
comparison shopping — fetch quotes from 5 offering agents and rank
them. The MCP spike validated this with two parallel offering
agents (`spike/MCP_SPIKE_REPORT.md`). This requires no
protocol-level multicast — it's just multiple MCP client
connections on the seeking side.

### Aggregator (one identity-of-record → N underlying offerings)

An institutional offering — a dealership representing 50 cars, an
ML provider exposing 20 model variants, a data lab with 30 dataset
slices — runs one Hermes process, one MCP server, one Nostr
identity. The MCP server's tool implementations take `item_id` and
route internally. From the seeking agent's perspective it looks
like any other offering.

A higher-level aggregator (an aggregator of aggregators) runs an
MCP server whose tools internally **call other MCP servers**. This
is composition: the aggregator is both a server (to clients) and a
client (to underlying providers). It's a regular pattern in
production MCP and requires no architectural changes.

### What we do NOT support natively

True multi-party consensus (a "swarm" of agents collaboratively
making a decision) is not in scope for v1–v3. If we ever need it,
that's a separate layer above MCP using libp2p / gossipsub. The
current design doesn't preclude this — it just doesn't ship it.

## Item updates and removal

- **Update**: republish a new kind-30402 event with the same `d` tag.
  Cooperative relays replace the previous version.
- **Status change** (e.g. `status: reserved` while a deal is in
  progress, `status: sold` when closed): same as update with the
  changed tag.
- **Hard delete**: publish a NIP-09 deletion request (`kind: 5`)
  referencing the event id and the addressable form
  `30402:<pubkey>:<d-value>`. Cooperative relays drop it; non-
  cooperative relays may not. **Do not rely on deletion as a
  privacy primitive.**

When an offering is archived or fulfilled, the agent publishes both
a `status: archived/sold` update and the deletion request. Local
files remain on the offering agent's disk; the MCP server stops
serving content for that item id (the grant policy returns "denied:
archived").

## Trust — five-layer overlay

No single trust signal is decisive. The full reputation model lives
in `reputation/README.md`; the on-the-wire pieces:

### NIP-58 verified-issuer badges

A vertical's operator (or anyone the user trusts) issues badges
after lightweight verification:

- **Verified Identity** — email + domain confirmed
- **Verified Payment** — payment-method confirmation (no money
  handled)
- **Verified Institution** — domain ownership + business
  registration (vertical-specific name; e.g. Verified Dealer for
  cars, Verified Provider for ML inference, Verified Lab for data
  licensing)
- **Long-Standing Member** — auto-issued after N months of clean
  activity

Badges are kind-30009 (definition) + kind-8 (award) events.
Seeking-side filters can require badges. Offering agents reference
their awarded badges in their NIP-99 listings via
`["badge", "30009:<issuer>:<badge-id>"]`.

### Bilateral peer attestations

After a deal, either side may publish a counterparty attestation as
kind 30410 (positive) / 30411 (negative). Unilateral observations
ride on kind 30412. Schema in `reputation/attestation_schema.md`;
weights in `reputation/scoring.md`.

### NIP-51 mute lists

A vertical's operator publishes a NIP-51 mute list under the
operator pubkey naming blocked counterparties. Agents subscribe via
the default trust graph and apply the list as a hard suppression.
Users may also subscribe to their own mute lists or those of any
pubkey they trust.

### NIP-02 web of trust

The follow graph traversed from the user's own pubkey. Each agent
weights counterparties by trust-graph distance, with depth gated by
plugin tier (1 hop free, up to 3 hops on `chaos-pro`).

### Admin-agent decisions (opt-in)

Kind 30430 (decisions) + kind 30431 (appeals). Opt-in per CLAUDE.md
Rule 16; users may install plugins without trusting any
admin-pubkey. Admin's verdicts are signals, never gates.

## Bootstrap (where to start when you're a new agent)

Every agent ships with a default config pointing to:

```yaml
relays:
  - "wss://relay.<your-domain>"        # Mode A operator relay
  - "wss://relay.damus.io"             # community
  - "wss://nos.lol"                    # community
  - "wss://nostr.mom"                  # community
default_trust_root_pubkey: "<operator pubkey hex>"
default_packs:
  - "cars-pack@1"
```

The user can edit these freely. The architecture works in **Mode C**
(community relays only, no operator relay) without code changes —
just remove the operator-specific entries.

## Failure modes

| Failure | Detection | Mitigation |
|---|---|---|
| Operator relay down | Seeking agent's REQ subscription drops | Agent keeps subscribing to remaining relays; new listings still arrive via community relays |
| All relays down | Both sides notice subscription drops | Ongoing pairwise sessions continue (MCP is direct, doesn't depend on relays); new discovery pauses until at least one relay returns |
| Offering agent's MCP endpoint down mid-session | Seeking agent's MCP client errors | Agent retries; if persistent, the session fails and the seeking agent can re-attempt later |
| Offering agent refuses inquiry (Nostr `mcp_inquiry_open` returns no MCP session_token) | Seeking agent surfaces denial reason | Try again later or look elsewhere |
| Spam attack on relays | Relay rejection rate spikes | Relay rate-limit + PoW raise spam cost; operator may add temporary allowlist mode |
| Deleted event still served by some relay | Seeking agent sees stale listing | Pack's evaluation rubric checks `created_at` and `status` tags; soft-suppress stale events; agent may also confirm via `view_listing` MCP call |

## What this protocol intentionally does NOT support

- Public file URLs in listings (everything binary moves over MCP)
- Plaintext (kind 4 NIP-04) DMs in production (NIP-04 is MVP-only)
- Multi-recipient broadcasts beyond NIP-99 listings (no group DMs)
- Streaming media (real-time voice/video) — out of scope
- Smart-contract escrow / on-chain settlement — out of scope
- Cross-relay sync we operate (relays sync via clients publishing to
  multiple, not via relay-to-relay protocols)
- Multi-party consensus / swarm agreement — not v1–v3

## Glossary

- **NIP** — Nostr Implementation Possibility, the IETF-RFC-shaped
  spec series for the protocol
- **NIP-99** — classified listings (the listing event shape)
- **NIP-17** — sealed gift-wrapped DMs (the message format)
- **NIP-13** — proof-of-work
- **NIP-44** — encryption (XChaCha20-Poly1305 + ECDH)
- **NIP-58** — badges
- **NIP-51** — categorized lists (follow / mute)
- **NIP-09** — deletion requests
- **NIP-19** — bech32 encoding (npub, nsec, etc.)
- **MCP** — Model Context Protocol; agent ↔ tool-server with
  HTTP+SSE / WebSocket / stdio transport, JSON-RPC envelope,
  `tools/list` introspection, and `ImageContent` /
  `EmbeddedResource` blocks for binary
- **strfry** — high-performance C++ Nostr relay implementation
- **secp256k1** — elliptic curve used by Nostr (and Bitcoin) for
  identity
- **BIP-340** — Schnorr signatures over secp256k1
- **FastMCP** — high-level Python helper class in the `mcp` SDK
  that wraps a server with `@mcp.tool()` decorators

## Why MCP, not ACP or A2A

Three transport spikes in `spike/`. Headlines:

| | ACP | A2A | **MCP** (canonical) |
|---|---|---|---|
| Transport in shipping SDK | stdio only | HTTP+JSON-RPC | **HTTP+SSE / WebSocket / stdio** |
| Bootstrap discovery | none | static agent card | **dynamic `tools/list`** |
| Hermes integration | exists, stdio only | write own (3-5 days) | **built in (`tools/mcp_tool.py`)** |
| Spike attempts to pass | 2 | 7 | **1** |
| Multi-agent fanout demonstrated | no | no | **yes** |

See `spike/MCP_SPIKE_REPORT.md` for the full comparison.
