# BUSINESS MODEL

How neuro-spati becomes a sustainable business while staying a
discovery layer. The protocol stays free; revenue comes from layers
above.

## What this product is, in legal terms

A discovery / classifieds layer, not a custodial marketplace.

| Custodial marketplace (Etsy, Vinted, Carvana) | This (neuro-spati) |
|---|---|
| Hosts product images on platform servers | Photos stay on seller's machine |
| Holds payments in escrow | No money flows through any platform piece |
| Settles disputes, processes refunds | Two people transact directly, off-platform |
| Takes a cut of each sale | No transactions on the platform |
| Knows seller PII for tax / compliance | Seller is a Nostr pubkey; PII never leaves their machine |
| Is a *platform* in the EU DSA / US consumer-protection sense | Is a classifieds notice / search index |

Closest analogues: BitTorrent trackers, RSS aggregators, search
engines, Craigslist's pre-personals classifieds. Regulatory burden
sits at the **web host / software vendor** tier, not the
**marketplace operator** tier.

## Decentralization scorecard (for marketing claims)

| Layer | Status | Notes |
|---|---|---|
| Discovery / registry | **Fully decentralized** | Relays are commodity, anyone can run one, protocol is open spec |
| Identity | **Fully decentralized** | secp256k1 keypair owned by user; portable to any Nostr client |
| Content / photos / files | **Fully decentralized** | Lives on seller's machine; delivered to buyers agent-to-agent over ACP; never replicated to platform or any third-party host |
| 1-to-1 messaging | **End-to-end encrypted** | NIP-17 sealed gift-wraps — relays cannot see content |
| Reputation | **Decentralized + portable** | NIP-51 lists / NIP-58 badges; usable across any Nostr app |
| Network layer | **Centralized by default** | DNS, TLS, relay IPs are visible. Tor / `.onion` is opt-in |
| LLM dependency | **Per-agent** | Each Hermes uses its own LLM provider — independent, not platform-controlled |

You can honestly say: **"a fully decentralized discovery layer for
peer-to-peer commerce, with end-to-end encrypted negotiation and
sovereign identity."** What you cannot honestly say: "anonymous" or
"unsurveillable" — those require Tor on top.

## What you ARE / ARE NOT

| | What you ARE | What you are NOT |
|---|---|---|
| Custodian of funds | ❌ | ✓ |
| Custodian of inventory | ❌ | ✓ |
| Custodian of PII | ❌ | ✓ |
| Custodian of photos / files | ❌ | ✓ |
| Transaction processor | ❌ | ✓ |
| Discovery / classifieds layer | ✓ | |
| Software vendor | ✓ | |
| Reputation issuer (optional) | ✓ | |
| Relay operator (optional, Modes A/B) | ✓ | |

## Six clean revenue streams

### 1. Plugin license — freemium

Open-source the protocol code, paid premium tier with the
differentiated capabilities:

- AI-assisted negotiation drafting (cheap-LLM assist for buyer / seller turns)
- Multi-modal item search (text + photo similarity via local CLIP)
- Photo grading / authenticity assist (pre-flag stock photos vs. seller's own)
- CRM features (deal pipeline, follow-up reminders, comparison sheets)
- Export / import (CSV, JSON, integration with personal accounting)
- Multi-account orchestration (manage 100 listings across personas)

**Pricing**: $5–20 per agent per month. Volume pricing for businesses.

**Distribution**: PyPI for the open-source baseline; license server gates
the premium features (per-pubkey license token, validated locally).

### 2. Managed/curated relay — subscription

You operate one or more private relays with better SLA than community
ones:

- Tight anti-spam policy (require ≥ 24-bit PoW, paid-only writes,
  manual pubkey approval for new sellers in regulated categories)
- Faster propagation (geo-distributed, lower per-event latency)
- Better availability (99.9% SLA vs. community-relay best-effort)
- Optional content moderation (illegal-listing scrubbing)

**Pricing**: $5/month per `npub` for personal use. $50–500/month for
business plans. Free tier with rate limits seeds the network.

**Cost**: ~$50/month all-in to operate one `strfry` instance with
backup. Margin scales linearly.

### 3. NIP-58 badge issuer — verification fees

Become a trusted issuer of seller-quality badges:

- "Verified Identity" — email + domain confirmed
- "Verified Payment" — payment-method confirmation (no money handled)
- "Verified Inventory" — photo + serial-number check for high-value
  items (cars, watches)
- "Long-Standing Member" — auto-issued after N months of clean activity
- Vertical-specific: "Verified Dealer" for cars, "Verified Breeder"
  for animals, etc.

Buyers' filters can require badges. Sellers pay for the trust signal.

**Pricing**: $5–50 one-time per badge. Re-verification at intervals.

**Risk profile**: you're certifying, not custodying. Public issuance
policy. Revoke on abuse. Substantially lower regulatory burden than
custodial KYC.

### 4. Vertical packs — pre-built bundles

Each pack is `(skills + tag schema + relay list + custom MCPs +
moderation policy)` shipped as a single installable for a specific
vertical:

- **Cars pack** — VIN structural decode, market comp from network,
  reverse-image, year/make/model/trim/mileage tag schema, region-aware
  pricing, test-drive scheduling assist
- **Real estate pack** — property tag schema, MLS-style search, photo
  walkthrough assist, mortgage-calculator MCP
- **Watches pack** — brand/model/serial schema, authenticity check
  MCP, condition grading assist
- **Livestock pack** — breed tag schema, registration-paper handling,
  vet-record skill
- **Services pack** — hourly/fixed/recurring schemas, scheduling MCP,
  proposal templates

**Pricing**: $50–500/month per pack. Targeted at dealerships, brokers,
vertical communities. Customizable for white-label use.

### 5. Custom MCP servers — protocol-universal capability

Highest-leverage stream because **MCP is universal** — your servers
work in Hermes, Claude Desktop, Cursor, future MCP-compatible
clients. The TAM is "MCP users" not "your marketplace users".

**Strict rule for every paid MCP we ship: no third-party data
custody.** MCPs may compute over data the user already has, query
public free authoritative sources, or aggregate data already on the
network. They may not aggregate commercial data we'd then need to
license, store, or resell. This keeps GDPR clean and avoids vendor
lock-in to data providers.

Examples worth building (all local-only or network-derived):

- **`reverse-image-mcp`** — perceptual-hash photo-fraud detection.
  Stores only hashes, not images. Cross-vertical (cars / real estate
  / watches / livestock / services). **The first paid MCP we ship.**
  $0.10/call thorough tier; $9/mo Pro for 200 calls.
- **`vin-decoder-mcp`** — pure ISO-3779 VIN structure decode using
  public WMI registry. **Free.** Ships bundled with the cars pack.
- **`market-comp-mcp`** — pricing comps from NIP-99 listings on the
  user's configured relays. No external data. **Free.**
- **`scam-pattern-mcp`** — NLP against known scam-text patterns
  (urgency cues, payment-redirect phrases, language-mismatch flags).
  Local. $5–9/mo.
- **`exif-mcp`** — photo EXIF analysis for date / GPS / camera
  consistency checks. Local. $3–5/mo.
- **`logistics-mcp`** — shipping-rate lookup against public carrier
  APIs. Per-call. Sellers and buyers use it during handover planning.
- **`tax-doc-mcp`** — generates seller-side tax docs from the seller's
  *own* per-item history (locally stored). No data leaves the seller.
  $5/mo.

**Things we deliberately do NOT build**:

- ~~`vehicle-history-mcp`~~ — would aggregate Carfax-style commercial
  data. Vendor lock-in, data custody, GDPR surface. Rejected.
- Any MCP that requires us to store user data centrally.
- Any MCP that resells third-party data we don't own.

**Pricing**: $0.10/call metered or $5–25 per server per month per
pubkey for subscription tiers. Generous free tiers on the loss-
leaders (`vin-decoder-mcp`, `market-comp-mcp`).

**Distribution**: catalog on your website + npm/PyPI. License keys
gate metered use. Hosted endpoints for convenience; container images
for users who want full local-only operation.

### 6. Skills marketplace, meta

Once you have audience (~1k active users), run a curated catalog of
paid skills authored by third parties. You take a 20–30% cut. Built
natively on Nostr — skill listings are themselves NIP-99 events. The
system eats its own cooking.

This works once you have ~1,000 active sellers/buyers. Premature
otherwise.

## What to avoid (drags you back to custodial platform)

| Avoid | Why |
|---|---|
| Hosting seller keypairs / photo storage | You become a data controller; back to GDPR + breach liability |
| Processing payments | Money-services regulation |
| Holding escrow | Custodial; same risk |
| Taking a cut of off-platform sales | Platform-operator semantics regardless of where trade happens |
| Mediating disputes with binding outcomes | Looks like a marketplace operator to regulators |
| Issuing identity that's tied to government IDs | KYC obligations attach |

## Napkin model

| Stream | Unit | Volume | MRR |
|---|---|---:|---:|
| Premium plugin | $10/agent/mo | 1,000 | $10k |
| Managed relay | $5/npub/mo | 800 | $4k |
| Verification badges | $20 one-time | 200/mo | $4k |
| Vertical packs (3 launched) | $50/pack/mo | 50 each | $7.5k |
| `reverse-image-mcp` Pro | $9/mo | 400 | $3.6k |
| `reverse-image-mcp` metered overage | $0.10/call | 50k calls/mo | $5k |
| Other paid MCPs (3 launched at $5/mo avg) | $5/mcp/mo | 200 each | $3k |
| **Total** | | | **~$37k MRR** |

Conservative — at $440k ARR with no platform-operator regulatory
overhead and a small operator team. Achievable inside 12 months if
the protocol implementation is good and the first vertical pack
finds product-market fit.

## Sequencing

1. **Months 1–2**: Open-source baseline plugin. Free. Goal: real users
   on community relays.
2. **Months 2–3**: Add managed relay. First paid stream. Bundle with
   the plugin.
3. **Months 3–4**: Premium plugin tier with negotiation drafting +
   multi-modal search.
4. **Months 4–6**: First vertical pack (cars). Launch verification
   badges.
5. **Months 6–9**: Additional custom MCPs (`scam-pattern-mcp`,
   `logistics-mcp`, `exif-mcp`).
6. **Months 9–12**: Skills marketplace meta-layer once active community
   exists.

## What stays free, forever

The protocol implementation, the basic seller/buyer skills, the
connection logic, the input safety helpers, the bootstrap relay list.
**Free forever, openly licensed.** That's the keel. Premium is the
sail.

If you ever pivot to a custodial marketplace (Mode A relay + custom
payments + escrow), every revenue stream above still works — but you
take on regulatory load. The free protocol stays free; the custodial
layer would be its own business decision.
