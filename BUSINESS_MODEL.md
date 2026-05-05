# BUSINESS MODEL

How chaos becomes a sustainable business while staying a
discovery layer rather than a custodial intermediary. The protocol
itself is open and free; revenue comes from optional layers above.

## What this product is, in legal terms

A discovery / classifieds layer for autonomous agent coordination —
not a custodial marketplace. Closest legal analogues: BitTorrent
trackers, RSS aggregators, search engines, federated relays.
Regulatory burden sits at the **software vendor / relay operator**
tier, not the **marketplace operator** tier. We never custody
funds, inventory, PII, or files.

## What we ARE / ARE NOT

| Status | Role |
|---|---|
| ARE | Discovery / classifieds layer |
| ARE | Software vendor (open-source protocol + paid plugins) |
| ARE | Reputation issuer (optional, per-domain) |
| ARE | Relay operator (optional, Modes A/B) |
| ARE NOT | Custodian of funds |
| ARE NOT | Custodian of inventory |
| ARE NOT | Custodian of PII |
| ARE NOT | Custodian of binary content (photos, PDFs, datasets, model artifacts) |
| ARE NOT | Transaction processor |
| ARE NOT | Off-platform deal cut taker |

## Revenue streams

The model is per-domain pluralizable: each new pack extends the
addressable market without re-engineering the wire. The discovery
layer (Nostr) and the peer transport (MCP) are the same; only the
per-domain contract changes. That's leverage — packs compound, the
protocol does not.

### 1. Premium plugin tiers

`plugins/chaos-pro/` is the **single cross-domain paid
upgrade**, applied to every installed seeking-side plugin the user
runs. There is no `cars-buyer-pro`, no `realestate-buyer-pro`, no
per-domain paid bundle (AGENTS.md cut list — the pack is the
contract; the upgrade is universal).

**What pro adds across every installed buyer plugin**:

- **Thorough-tier `reverse-image-mcp`** — deeper reference library,
  perceptual-hash + visual-similarity backbone (free tier is
  fast-hash-only)
- **Wider `market-comp-mcp` window** — pulls comps from a longer
  history and more relays, with confidence intervals (free tier is
  current-listing median only)
- **Deeper `nip02_wot` traversal** — 3 hops vs. free-tier 1 hop,
  with stronger weighting against muted edges
- **Optional Phase-1 onchain stake reading** — surfaces the
  `onchain_stake` field from `reputation-mcp` (default off; opt-in
  per AGENTS.md Rule 14)
- **AI-assisted negotiation drafting** — cheap-LLM assist for buyer
  / seller turns
- **Multi-modal item search** (text + content similarity via local
  CLIP)
- **CRM features** — deal pipeline, follow-up reminders, comparison
  sheets
- **Multi-account orchestration** — manage many listings or many
  watchlists across personas

**Pricing**: $15/mo subscription, or x402 micropayment per session.
Both metered against the same per-pubkey license. Volume pricing for
businesses.

**Distribution**: shipped as `plugins/chaos-pro/` — installed
alongside whichever buyer plugins the user already has. License
token validated locally.

### 2. Managed relay subscriptions

We operate one or more curated relays per vertical with better SLA
than the public commons:

- Tight anti-spam policy (≥ 24-bit PoW on listings, paid-only writes
  for institutional offerings, manual pubkey approval for regulated
  categories)
- Faster propagation (geo-distributed, lower per-event latency)
- Better availability (99.9% SLA vs. community-relay best-effort)
- Optional content moderation (pack-level enforcement of the
  vertical's tag schema + illegal-listing scrubbing)

**Pricing**: $5/month per `npub` for personal use. $50–500/month for
business plans. Free tier with rate limits seeds the network.

**Cost**: ~$50/month all-in to operate one `strfry` instance with
backup. Margin scales linearly.

The relay tier is also where the multi-vertical strategy plays out
on the deployment side. We can run one strfry per vertical
(e.g. `relay-cars.<domain>`, `relay-mlinference.<domain>`,
`relay-datalicensing.<domain>`) — each with its own moderation
policy, PoW floor, and pack-aware kinds allowlist — or one unified
relay carrying many `["pack", "..."]` tags. Operators choose. Either
way the wire stays MCP and discovery stays Nostr.

### 3. NIP-58 badge issuance fees

Operators of a vertical may become the trusted badge issuer for that
vertical:

- **Verified Identity** — email + domain confirmed
- **Verified Payment** — payment-method confirmation (no money
  handled — just attestation)
- **Verified Institution** — domain ownership + business
  registration (vertical-specific name; e.g. Verified Dealer for
  cars, Verified Provider for ML inference, Verified Lab for data
  licensing)
- **Long-Standing Member** — auto-issued after N months of clean
  activity

Buyers' filters can require badges. Sellers pay for the trust signal.

**Pricing**: $5–50 one-time per badge. Re-verification at intervals
the operator sets.

**Risk profile**: certifying, not custodying. Public issuance
policy. Revoke on abuse. Substantially lower regulatory burden than
custodial KYC.

### 4. Packs as paid templates

A pack is `(skills + tag schema + relay list + capability MCPs +
moderation policy)` shipped as a single installable for a domain.
The reference pack (cars-pack@1) is open-source and free. Specialty
packs targeted at institutional use are sold:

- **cars-pack@1** — free reference, ships with `vin-decoder-mcp`
- **realestate-pack** (planned) — paid template with
  property-specific skills, MLS-style search, mortgage-calculator
  MCP
- **watches-pack** (planned) — authenticity-check MCP, condition
  grading assist
- **livestock-pack** (planned) — registration-paper handling,
  vet-record skill
- **ml-inference-pack** — paid template targeted at model providers
- **data-licensing-pack** — paid template targeted at data labs and
  vendors
- **compute-jobs-pack** — paid template targeted at compute
  providers
- **specialist-services-pack** — paid template targeted at firms

**Pricing**: $50–500/month per pack for institutional users.
Customizable for white-label deployments.

### 5. Protocol-universal MCP services

The highest-leverage stream because **MCP is universal** — these
servers work in Hermes, Claude Desktop, Cursor, future MCP-compatible
clients. The TAM is "MCP users" not "chaos users".

Strict rule for every paid MCP we ship: **no third-party data
custody.** MCPs may compute over data the user already has, query
public free authoritative sources, or aggregate data already on the
network. They may not aggregate commercial data we'd then need to
license, store, or resell.

- **`reverse-image-mcp`** — perceptual-hash content fraud detection.
  Stores only hashes, not content. Cross-vertical (any pack that
  uses images). $0.10/call thorough tier; $9/mo Pro for 200 calls.
- **`market-comp-mcp`** — comps derived from on-network listings on
  the user's configured relays. No external data. **Free.**
- **`reputation-mcp`** — trust-signal aggregation across the 5
  layers. **Free** (free-tier traversal depth; pro tier deeper).
- **`scam-pattern-mcp`** — NLP against known prompt-injection and
  scam-text patterns. Local. $5–9/mo.
- **`exif-mcp`** — photo EXIF analysis for date / GPS / camera
  consistency checks. Local. $3–5/mo.
- **`logistics-mcp`** — shipping-rate lookup against public carrier
  APIs. Per-call. Used during off-platform handover planning.
- **`tax-doc-mcp`** — generates seller-side tax docs from the
  seller's *own* per-item history (locally stored). No data leaves
  the seller. $5/mo.

**Things we deliberately do NOT build**:

- Carfax-style commercial-data aggregation. Vendor lock-in, data
  custody, GDPR surface. Rejected at protocol level.
- Any MCP that requires us to store user data centrally.
- Any MCP that resells third-party data we don't own.

**Pricing**: $0.10/call metered or $5–25 per server per month per
pubkey for subscription tiers. Generous free tiers on
loss-leaders (`market-comp-mcp`, `reputation-mcp`,
`vin-decoder-mcp`).

**Distribution**: catalog on our website + npm/PyPI. License keys
gate metered use. Hosted endpoints for convenience; container images
for users who want full local-only operation.

### 6. Admin-agent operator subscriptions

Operators that run an admin-agent for their vertical pay the
chaos platform fee for the admin plugin
(`plugins/cars-admin/`, future `plugins/<vertical>-admin/`). The
admin-agent runs only on the operator's infrastructure; the plugin
install is gated behind the operator-tier subscription.

**What the operator-tier plugin gives them**:

- Admin-agent skill (`verticals/<vertical>-pack/skills/
  admin-<vertical>/SKILL.md`) hardened against prompt injection per
  AGENTS.md Rule 15
- Anti-injection hardening updates (signed, version-pinned skill
  releases)
- Escalation queue tooling — dispute inbox, decision-publishing
  helper, hash-retention 90-day-forgetting cron
- Decision-event templates (kind 30430 / 30431) and the
  `submit_dispute` MCP tool surface

**Adjacent revenue the same operator may earn** (independent of the
admin-agent plugin fee):

- NIP-58 badge issuance fees for their vertical (separate operator
  workflow, not performed by the admin-agent)
- Paid-relay subscriptions on the operator's strfry deployment
- Dispute-resolution-pool yield (Phase 1, opt-in;
  see AGENTS.md Rule 14 — non-custodial multi-sig only, no platform
  cut of off-platform deals)

**Pricing**: $200–500/mo per vertical the operator runs admin-agent
for. Higher tiers for operators running admin-agent across multiple
verticals.

**Risk profile (AGENTS.md Rule 16)**: an operator's admin-agent
cannot unilaterally take destructive action — only `clear` /
`warning` / `flag` / `escalated` decisions. Anything stronger
requires multi-sig with affected parties + a community arbitrator.
All decisions are publicly auditable. Users opt-in to trust each
admin-pubkey individually.

### 7. Future: Phase-1 staking treasury yield

Roadmap, not MVP. Per AGENTS.md Rule 14, any money / value flows
through open-source, audited, on-chain programs where chaos is
at most one of N multi-sig signers — never custodian. Reference
`reputation/STAKE.md` for the full Phase-1 design.

**Mechanics** (Phase 1, Solana-based, opt-in per user):

- Offering-side users may post a small stake bond (USDC / SOL)
  against their pubkey. Stake amount surfaces via `reputation-mcp`
  as `onchain_stake.amount_usd`.
- Stake is held in an open-source Solana program where chaos
  is one of N multi-sig signers. We can never unilaterally seize or
  move user funds.
- A buyer's reputation lookup weights `onchain_stake.amount_usd` as
  an additional positive signal — bigger stake, more skin in the
  game.
- On a confirmed `flag` decision from a community arbitrator (NOT
  unilaterally from the operator's admin-agent — Rule 16),
  multi-sig participants may release a portion of the stake to the
  affected counterparty.

**Where chaos earns** (none of which is a cut of off-platform
deals):

- **0.5% annual yield on the opt-in arbitration pool** — treasury
  revenue from idle staked funds parked in audited DeFi rails;
  fully non-custodial, fully opt-in, fully transparent.
- **Optional pro-arbitrator NFT issuance fee** — community
  arbitrators stake to be discoverable; one-time mint fee.
- **Cross-vertical pro tier may bundle "Phase-1 stake bond
  reduction" perk** — pro subscribers post a smaller required bond
  for the same trust signal weight.

**Strict invariants** (AGENTS.md Rule 14):

- Money never flows through any platform piece.
- We never %-of-deal.
- We never custody user keys.
- Phase 1 ships only after legal review for the target jurisdiction
  and an external smart-contract audit.

## Anti-revenue

Things we explicitly do not take a cut of:

- **Off-platform deal value.** Once counterparties agree (whether a
  single pair, a fan-out, or many-to-many), they handle payment and
  exchange themselves. We see nothing.
- **Peer DM volume.** NIP-17 sealed gift-wraps are end-to-end
  encrypted. Relays carry the bytes; nobody but the recipient reads
  them.
- **Binary content transferred over MCP.** Bytes flow agent-to-agent.
  No relay, no platform piece, sees them. We could not bill on
  volume even if we wanted to.
- **Reputation lookups, capability-MCP results, listing match
  notifications.** All happen on the agent's machine. We don't see
  them.

## What stays free, forever

The protocol implementation, the universal seller / buyer engines,
the cross-domain capability MCPs at their free tier, the
input-safety helpers, the bootstrap relay list, and the reference
pack (cars-pack@1). **Free forever, openly licensed.**
That's the keel. Premium is the sail.

## Napkin model

| Stream | Unit | Volume | MRR |
|---|---|---:|---:|
| Cross-vertical pro tier | $15/agent/mo | 1,000 | $15k |
| Managed relay | $5/npub/mo | 800 | $4k |
| Verification badges | $20 one-time | 200/mo | $4k |
| Vertical paid packs (3 launched) | $200/pack/mo | 30 each | $18k |
| `reverse-image-mcp` Pro | $9/mo | 400 | $3.6k |
| `reverse-image-mcp` metered overage | $0.10/call | 50k calls/mo | $5k |
| Other paid MCPs (3 launched at $5/mo avg) | $5/mcp/mo | 200 each | $3k |
| Admin-agent operator tier (1 vertical) | $300/mo | 5 | $1.5k |
| **Total** | | | **~$54k MRR** |

Conservative — at ~$650k ARR with no platform-operator regulatory
overhead and a small operator team. Achievable inside 12 months
with one shipped reference pack, two paid packs, and the cross-
vertical pro tier converted at modest rates.
