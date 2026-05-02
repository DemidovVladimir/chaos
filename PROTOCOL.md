# PROTOCOL — on-the-wire design

The complete protocol. Two main mechanisms:

- **Nostr** for discovery, identity, and structured 1-to-1 inquiries
- **ACP** (Agent Client Protocol) for rich agent-to-agent dialogue
  including binary content (photos, PDFs)

If you want the product narrative, read `OVERVIEW.md`. If you want
the precise requirements, read `PRD.md`. This document is what goes
on the wire.

## Identity

Each agent owns a **secp256k1 keypair**. The pubkey (32-byte
x-only, BIP-340) is the agent's identity, encoded as `npub1…`
(NIP-19 bech32) for display. Keys are stored at
`~/.neuro_spati/keys/{seller|buyer}.key` mode 0600.

There is no recovery mechanism. Sovereignty has costs.

In v2 we may add NIP-46 remote-signer support so users can hold the
key on a hardware device.

## Discovery — NIP-99 classified listings

Listings are **NIP-99** events (`kind: 30402`, addressable +
replaceable). The cars-pack tag schema (see `cars-pack/tag_schema.md`)
defines the canonical tags. Minimum required tags:

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
    ["acp", "<https url to seller's ACP endpoint>"],
    ["photos_via", "acp"]
  ],
  "content": "<short description, ≤ 4000 chars; full one stays local>"
}
```

`d` makes the event addressable: republishing with the same `d`
replaces the previous version on cooperative relays. Combined with a
NIP-09 deletion request, this gives item updates and removals.

Public listings carry **no `image` tag and no public photo URLs.**
Photos arrive via ACP (see below) only after the seller's agent
explicitly grants the inquiry.

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

Buyers' agents subscribe to the configured relays with REQ filters
shaped against the cars-pack tag schema:

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

Buyer-to-seller and seller-to-buyer messages are **NIP-17 sealed
gift-wraps**. Three layers:

1. **Rumor** (`kind: 14`) — the structured payload (asks, replies,
   counter-offers), signed by the sender.
2. **Seal** (`kind: 13`) — the rumor encrypted with NIP-44 to the
   recipient's pubkey, signed by the sender.
3. **Gift wrap** (`kind: 1059`) — the seal encrypted with NIP-44
   from a fresh ephemeral keypair, signed by that ephemeral key,
   tagged `["p", "<recipient_pubkey>"]`.

Relays carry the gift-wrap. They cannot read the content (NIP-44
encrypted). They cannot prove who sent it (ephemeral key signature).
They can see *that* a gift-wrap was delivered to a recipient pubkey
and the timing.

Inquiry payload shape (inside the rumor):

```json
{
  "type": "item_inquiry",
  "item_id": "<seller's d tag value>",
  "buyer_acp_url": "<https url to buyer's ACP endpoint>",
  "asks": [
    "full_description",
    "service_history",
    "accident_history",
    "photos:exterior",
    "photos:interior",
    "photos:engine_bay",
    "inspection_at_shop",
    "vin_full",
    "delivery_options"
  ]
}
```

Reply payload:

```json
{
  "type": "item_inquiry_reply",
  "item_id": "<same>",
  "granted": ["full_description", "service_history", "photos:exterior", "photos:interior"],
  "denied":  ["vin_full"],
  "denial_reason": "user_declined",
  "inline": {
    "full_description": "<text>",
    "service_history": "<text>"
  },
  "acp_session_offer": {
    "session_id": "<uuid>",
    "endpoint": "<seller's acp_url>",
    "expires_at": 1714780000
  }
}
```

Photos and large documents are NOT inline in the rumor. The reply
includes an `acp_session_offer` that the buyer's agent uses to open
an ACP session with the seller's agent.

## Rich content — ACP `ImageContentBlock` + `EmbeddedResourceContentBlock`

When the buyer's agent receives an `acp_session_offer`, it opens an
ACP session against the seller's `acp_url`:

```
buyer.acp_client.NewSession(
  endpoint=seller.acp_url,
  auth_token=hmac(buyer_sk, session_id_nonce + buyer_pubkey),
  prompt="Item inquiry follow-up; serve the granted asks."
)
```

The seller's ACP server (the `marketplace-seller` skill running in
the seller's Hermes) authenticates the session via the HMAC, looks
up the session_id, and streams back content blocks:

```python
# inside the seller-cars skill, on ACP prompt:
yield TextContentBlock(text="Photos for item " + item_id + ":")
for photo_path in granted_photos:
    yield ImageContentBlock(
        mimeType="image/jpeg",
        data=base64(photo_path.read_bytes()),
    )
yield TextContentBlock(text="Inspection report attached.")
yield EmbeddedResourceContentBlock(
    name="inspection-2024-q4.pdf",
    mimeType="application/pdf",
    data=base64(inspection_pdf.read_bytes()),
)
yield TextContentBlock(text="Asking 14,500 EUR. Pickup in Prague any weekend.")
```

The buyer's ACP client receives the blocks and stores them locally.
**The bytes never touch a third party — not the relay, not us, not
any HTTP file host.**

ACP transport: stdio for local agent-to-agent (Hermes' default), or
HTTP+SSE for cross-network (which is what we use here). Hermes ships
both via `acp_adapter/`.

## File / photo handling — NEVER via HTTP

Restating because it's the architecture's hardest rule:

- **No HTTP file server we operate**
- **No signed URLs to seller's local file server**
- **No third-party file host** (Imgur, Dropbox, S3, ngrok-tunneled,
  Blossom, anything)
- **No image tag in public listings**
- **All binary content moves agent-to-agent over ACP content blocks**

Photos exist on two disks — seller's machine and (after a granted
inquiry) buyer's machine. Nothing in between holds them.

## Negotiation rounds

After photos and details are shared, negotiation continues as more
NIP-17 DMs between buyer and seller (or as additional ACP messages
within the same session, if it stays open). Limits:

- Max 5 rounds per (item, counterparty)
- Max 1000 chars per offer message
- Max 50,000 chars total per match

Both ends enforce these. Acceptance always requires explicit user
confirmation in the same session.

When both sides accept, each agent stores a small "agreement" event
locally signed by both parties. There is **no central agreement
registry**. The off-platform handover (payment + key/title transfer)
is the users' responsibility.

## Item updates and removal

- **Update**: republish a new kind-30402 event with the same `d` tag.
  Cooperative relays replace the previous version.
- **Status change** (e.g. `status: reserved` while a deal is in
  progress, `status: sold` when closed): same as update with the
  changed tag.
- **Hard delete**: publish a NIP-09 deletion request (`kind: 5`)
  referencing the event id and the `addressable` form
  `30402:<pubkey>:<d-value>`. Cooperative relays drop it; non-
  cooperative relays may not. **Do not rely on deletion as a privacy
  primitive.**

When a seller archives or sells an item, their agent publishes both
a `status: archived/sold` update and the deletion request. Local
files remain on the seller's disk; their agent stops responding to
ACP photo grants for that item id.

## Trust — three-layer overlay

No single trust signal is decisive.

### NIP-58 verified-seller badges

Operator agent (registry side) issues badges after lightweight
verification:

- **Verified Identity** — email + domain confirmed
- **Verified Payment** — payment-method confirmation (no money
  handled)
- **Verified Dealer** — domain ownership + business registration
- **Long-Standing Member** — auto-issued after N months of clean
  activity

Badges are kind-30009 (definition) + kind-8 (award) events. Buyers'
filters can require badges. Sellers reference their awarded badges
in their NIP-99 listings via `["badge", "30009:<issuer>:<badge-id>"]`.

### NIP-51 mute lists

Operator publishes a NIP-51 mute list under the operator pubkey
naming pubkeys we've blocked. Buyers' agents subscribe via the
default trust graph and apply the list as a hard suppression.

### Reputation and follow graph

Each pubkey accumulates history: how many listings, how many closed
cleanly, presence of complaints in the user's trust-graph mute lists.
Buyer-cars rubric weights this in evaluation.

## Bootstrap

Every agent ships with a default config pointing to:

```yaml
relays:
  - "wss://relay.<your-domain>"        # Mode A operator relay
  - "wss://relay.damus.io"             # community
  - "wss://nos.lol"                    # community
  - "wss://nostr.mom"                  # community
default_trust_root_pubkey: "<operator pubkey hex>"
```

The user can edit these freely. The architecture works in **Mode C**
(community relays only, no operator relay) without code changes —
just remove the operator-specific entries.

## Failure modes

| Failure | Detection | Mitigation |
|---|---|---|
| Operator relay down | Buyer agent's REQ subscription drops | Buyer keeps subscribing to remaining relays; new listings still arrive via community relays |
| All relays down | Both sides notice subscription drops | Ongoing buyer↔seller deals continue (bytes already exchanged via ACP); new discovery pauses until at least one relay returns |
| Seller's ACP endpoint down mid-session | Buyer's ACP client errors | Buyer retries; if persistent, the session fails and the buyer can re-attempt later. Future state: ACP session resume on reconnect |
| Buyer's ACP endpoint down | Seller's ACP send blocks | Same — retry; the inquiry itself is still in the seller's queue |
| Spam attack on relays | Relay rejection rate spikes | Relay rate-limit + PoW raise spam cost; operator may add temporary allowlist mode |
| Deleted event still served by some relay | Buyer sees stale listing | Buyer-cars rubric checks `created_at` and `status` tags; soft-suppress stale events; the buyer may also DM the seller to confirm |

## What this protocol intentionally does NOT support

- Public file URLs in listings (everything binary moves over ACP)
- Plaintext (kind 4 NIP-04) DMs in production (NIP-04 is MVP-only)
- Multi-recipient broadcasts beyond NIP-99 listings (no group DMs)
- Streaming media (real-time voice/video) — out of scope
- Smart-contract escrow / on-chain settlement — out of scope
- Cross-relay sync we operate (relays sync via clients publishing to
  multiple, not via relay-to-relay protocols)

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
- **ACP** — Agent Client Protocol; agent-to-agent JSON-RPC 2.0 with
  content blocks
- **strfry** — high-performance C++ Nostr relay implementation
- **secp256k1** — elliptic curve used by Nostr (and Bitcoin) for
  identity
- **BIP-340** — Schnorr signatures over secp256k1
