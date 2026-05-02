# PRD — neuro-spati

A precise product-requirements document. Read alongside `OVERVIEW.md`
(plain-English narrative), `PROTOCOL.md` (on-the-wire design), and
`CLAUDE.md` (engineering rules).

## 1. Problem statement

Selling and buying high-value items peer-to-peer (cars, real estate,
watches, etc.) today happens on **custodial classifieds platforms**
(Craigslist, Facebook Marketplace, AutoTrader, Carvana). Those
platforms:

- Hold seller inventory data and photos
- Hold buyer search history and identity
- Take a cut on transactions or insert advertising
- Operate as data controllers under GDPR
- Can deplatform users for any reason
- Mediate communication, often blocking off-platform contact

Sellers and buyers want to find each other; they don't want a
custodial intermediary.

## 2. Solution in one sentence

Each user runs an agent that publishes wants/offers as signed Nostr
events and connects directly to counterparties for inquiry and file
exchange — no custodial platform in the data path.

## 3. Users and personas

### 3.1 Seller (private individual)

A person selling one car. Mid-30s, professional, has 2–3 hours per
week to spend on the sale. Wants their car visible to qualified
buyers, doesn't want their phone number in public, doesn't want to
upload photos to a corporate platform that may reuse them.

**Goals**: list the car once, get qualified inquiries, share photos
to buyers I trust, finalize off-platform.

**Frustrations** with status quo: spam from non-serious buyers,
identity exposure on public boards, repetitive responses to the same
basic questions.

### 3.2 Seller (small dealer)

A dealership with 5–50 vehicles in inventory. Wants efficient bulk
listing, brand visibility, and a clean inquiry inbox.

**Goals**: list inventory in bulk, route inquiries to the right
salesperson, track conversion.

**Constraints**: existing CRM/DMS systems they don't want to replace.
Will pay for tools that integrate.

### 3.3 Buyer

Looking for a specific kind of vehicle. Wants to be notified when
matches appear, wants to evaluate quickly without scrolling, wants
to talk to sellers without giving up their phone number first.

**Goals**: define a filter once, receive matches, evaluate, contact
seller, finalize.

### 3.4 Registry operator (you, eventually a small team)

Operates the Mode A Nostr relay, issues NIP-58 verified-seller
badges, runs the moderation policy, ships and supports the cars-pack.

**Goals**: a clean, low-spam relay; a sustainable revenue model from
premium tools; minimal operational and regulatory burden.

## 4. Functional requirements

Numbered for traceability.

### 4.1 Seller agent (FR-S)

- **FR-S1**: The agent generates a secp256k1 keypair on first run and
  stores it locally at `~/.neuro_spati/keys/seller.key` mode 0600.
- **FR-S2**: The agent accepts a TOML or interactive description of a
  car and constructs a NIP-99 (kind 30402) classified-listing event
  using the cars-pack tag schema.
- **FR-S3**: The agent mines NIP-13 PoW (≥ 20 bits) before signing
  and publishing the event.
- **FR-S4**: The agent publishes to the configured relay set
  (default: `wss://relay.<operator-domain>`,
  `wss://relay.damus.io`, `wss://nos.lol`).
- **FR-S5**: The agent supports updating an item by republishing a
  new event with the same `d` tag.
- **FR-S6**: The agent supports archiving an item by publishing a
  status update (`status=archived`) and a NIP-09 deletion request.
- **FR-S7**: The agent supports deregistering itself by stopping
  publication and (optionally) issuing NIP-09 deletions for past
  events.
- **FR-S8**: The agent maintains a local catalog at
  `~/.neuro_spati/items/<item-id>/` with `manifest.json`,
  `description.md`, `photos/`, `private.md`.
- **FR-S9**: The agent receives encrypted DM inquiries (NIP-17 in
  production, NIP-04 in MVP) and decrypts them locally.
- **FR-S10**: The agent applies a per-ask grant policy (defaults in
  `cars-pack/skills/seller-cars/SKILL.md`); user-prompt for asks the
  policy marks as "ask user".
- **FR-S11**: When a buyer requests photos/files, the agent opens
  an ACP session and streams photos as `ImageContentBlock`s and
  documents as `EmbeddedResourceContentBlock`s. **No HTTP file
  delivery, ever.**
- **FR-S12**: The agent runs `reverse-image-mcp` (fast tier, local)
  on every photo before any ACP session can deliver it.
- **FR-S13**: The agent supports negotiation rounds with bounded
  state: max 5 rounds per (item, counterparty), max 1000 chars per
  offer message, hard cap on total chars per match.
- **FR-S14**: The agent never sends final-offer acceptance without
  explicit user confirmation in the same session.

### 4.2 Buyer agent (FR-B)

- **FR-B1**: The agent generates a secp256k1 keypair, stored as in
  FR-S1.
- **FR-B2**: The agent accepts a filter specification (cars-pack
  tag-shape) and subscribes via Nostr REQ across the configured
  relay set.
- **FR-B3**: The agent dedupes incoming events by `id` across relays.
- **FR-B4**: For each matching event, the agent runs the evaluation
  rubric in `cars-pack/skills/buyer-cars/SKILL.md` and classifies
  the listing as `surface`, `watchlist`, or `suppress`.
- **FR-B5**: For `surface` listings, the agent notifies the user
  (via Hermes' configured gateway: Telegram, Discord, CLI, …).
- **FR-B6**: When the user wants to inquire, the agent composes a
  structured `asks` payload, encrypts via NIP-17, and publishes the
  gift-wrap event.
- **FR-B7**: When the seller's agent opens an ACP session in
  response, the buyer's agent receives content blocks, runs
  `reverse-image-mcp` (thorough tier) on each `ImageContentBlock`,
  verifies signed attestations, and surfaces results to the user.
- **FR-B8**: The agent maintains a local inbox at
  `~/.neuro_spati/inbox/` with one JSONL per inquiry conversation.
- **FR-B9**: The agent supports negotiation rounds with the same
  bounds as the seller side.
- **FR-B10**: The agent never commits to a purchase without explicit
  user confirmation.

### 4.3 Registry (FR-R)

- **FR-R1**: A strfry-based Nostr relay reachable at
  `wss://relay.<operator-domain>`.
- **FR-R2**: Accepts kinds: 0, 5, 13, 14, 1059, 1985, 8, 30000–30099,
  30009, 30402, 30403. Rejects all other kinds.
- **FR-R3**: Enforces NIP-13 PoW ≥ 20 bits on kind-30402 events.
  Skips PoW on kinds 13/14/1059 (encrypted DM family).
- **FR-R4**: Enforces max event size 16 KB, max content length 8 KB,
  rejects events older than 1 year or > 15 minutes future-dated.
- **FR-R5**: Per-pubkey rate limit: default 10 events/min,
  100 events/hour. Configurable allowlist override for verified
  dealers.
- **FR-R6**: Pubkey blocklist enforced at the writePolicy layer.
- **FR-R7**: NIP-11 relay-info document served at the relay root via
  Caddy.
- **FR-R8**: TLS via Caddy + Let's Encrypt.
- **FR-R9**: Daily LMDB snapshot, off-site backup retained 90 days.
- **FR-R10**: Prometheus-scrapeable metrics exposed on a private
  port.
- **FR-R11**: External canary publish/subscribe round-trip every 5
  minutes from a separate host.
- **FR-R12**: Moderation log at `/var/lib/moderation/log.jsonl`,
  append-only, includes actor + reason for every blocklist action.

### 4.4 Cars pack (FR-C)

- **FR-C1**: A NIP-99 tag schema (`cars-pack/tag_schema.md`) defining
  required and optional tags for car listings; backwards-
  additive only.
- **FR-C2**: A `seller-cars` skill installable into Hermes
  (`cars-pack/skills/seller-cars/SKILL.md`).
- **FR-C3**: A `buyer-cars` skill installable into Hermes.
- **FR-C4**: Three custom MCPs:
  - `reverse-image-mcp` (paid, perceptual-hash photo-fraud detection,
    cross-vertical)
  - `vin-decoder-mcp` (free, ISO-3779 structural decode)
  - `market-comp-mcp` (free, derives from listings on the relay)
- **FR-C5**: An `example_listing.json` showing a fully-tagged real
  car listing.

### 4.5 Trust signals (FR-T)

- **FR-T1**: NIP-58 badge issuer agent operated by the registry
  operator, capable of issuing `verified-private-seller` and
  `verified-dealer` badges.
- **FR-T2**: Verification flow combines email confirmation, payment-
  method confirmation (no money handled — just attestation), and (for
  dealers) domain-ownership check.
- **FR-T3**: Badges are NIP-58 events; buyer's agent reads them and
  weights them in the evaluation rubric.
- **FR-T4**: Operator publishes a NIP-51 mute list of pubkeys
  blocklisted at the relay; buyer's agents can subscribe to the mute
  list as a default trust-graph input.

## 5. Non-functional requirements

### 5.1 Privacy / data protection

- **NFR-P1**: The platform never receives or stores user PII (names,
  addresses, payment details, phone numbers).
- **NFR-P2**: The platform never receives or stores binary content
  (photos, PDFs).
- **NFR-P3**: 1-to-1 messaging is end-to-end encrypted at the
  protocol level (NIP-17 in production).
- **NFR-P4**: Audit logs at the relay carry only event metadata
  (counts, kinds, status codes), never decrypted content.
- **NFR-P5**: Right to erasure: deleting an `agents` row at the
  registry (or the operator's badge issuer) is one operation. Local
  data deletion is the user's responsibility on their own machine.

### 5.2 Performance

- **NFR-PERF1**: Listing publish round-trip ≤ 5 seconds end-to-end
  (PoW mining + relay write + propagation to other relays).
- **NFR-PERF2**: Buyer subscription receives a matching event within
  10 seconds of seller publish (subject to relay propagation).
- **NFR-PERF3**: Relay query p99 latency ≤ 100 ms at v1 scale.
- **NFR-PERF4**: ACP photo session opens within 3 seconds of
  initiation; per-photo throughput limited only by network.

### 5.3 Availability

- **NFR-AVAIL1**: Mode A relay target uptime: 99.5% (allows ~3.6
  hours/month of unplanned downtime).
- **NFR-AVAIL2**: When the operator's relay is down, agents continue
  to operate via community relays (degraded discovery, but live
  buyer↔seller deals continue uninterrupted because they're peer-to-
  peer once paired).

### 5.4 Security

- **NFR-SEC1**: All inbound webhook routes (if any) verify HMAC.
- **NFR-SEC2**: All untrusted text passes through the input
  sanitizer before any LLM context render.
- **NFR-SEC3**: Agent toolsets are narrowed: marketplace agents do
  not have `terminal`, `execute_code`, `delegation`, `web`, or `mcp`
  toolsets enabled.
- **NFR-SEC4**: Container isolation: all marketplace agents run in
  Docker (or Modal/Daytona) with read-only root, tmpfs `/tmp`, and
  egress allowlist limited to relays + LLM endpoint + gateway
  platform.

### 5.5 Operational

- **NFR-OPS1**: Mode A relay deploys in ≤ 30 minutes from a clean VPS
  using `registry/strfry-compose.yml` + DNS + TLS.
- **NFR-OPS2**: Backup RPO ≤ 24 hours; RTO ≤ 30 minutes.
- **NFR-OPS3**: Monitoring with alerting for: relay unreachable, cert
  expiry, disk free, rejection-rate anomalies, query-latency
  anomalies.

## 6. Constraints

- **C1**: Discovery layer must be Nostr; no central database we
  operate.
- **C2**: Binary content must move agent-to-agent over ACP; no HTTP
  file servers, no third-party file hosts.
- **C3**: Identity is a secp256k1 keypair owned by the user; no
  recovery path through us.
- **C4**: Custom MCPs may not aggregate / resell commercial third-
  party data.
- **C5**: Compatible with Hermes Agent (Nous Research) v0.11+ as the
  agent runtime. Plugin shape per Hermes' plugin contract.

## 7. Phasing

| Phase | Window | Goal | Exit criterion |
|---|---|---|---|
| **P0 — MVP** | One weekend | Two laptops, text inquiry round-trip over public relays | Demo screen-capture works |
| **P1 — Mode A relay** | Week 1–2 | Operator's strfry deployed, monitored, backed up | Canary round-trips for 24h, third-party Nostr client connects cleanly |
| **P2 — Hermes plugin baseline** | Week 3–4 | Seller / buyer plugins installable into Hermes; ACP photo sharing wired | Two-machine end-to-end test passes unattended |
| **P3 — MCPs + cars pack** | Week 5–6 | `reverse-image-mcp`, `vin-decoder-mcp`, `market-comp-mcp` ship; cars-pack skills ship | Pre-publish stock-image check catches a planted test; buyer-cars rubric flags a synthetic stock-photo listing |
| **P4 — Closed beta** | Week 7–8 | 5–10 invited sellers, 10–20 buyers | ≥ 3 sellers publish a second car unprompted |
| **P5 — Verification + polish** | Week 9–10 | NIP-58 badge issuer live, docs site live, public install path | New user goes from install to listing in < 30 min |
| **P6 — Public launch** | Week 11–12 | Open to public; first revenue from premium tiers | 50 active sellers, 200 active buyers within 30 days |

Detail for each phase is in `LAUNCH_PLAN.md`.

## 8. Out of scope (explicit)

- Marketplace operator features (escrow, refunds, dispute
  arbitration, KYC, AML)
- Payment processing of any kind
- Custodial photo / file hosting
- VIN-history reselling (no Carfax-style aggregation)
- Custodial DM history
- Mobile-first UI (desktop / Hermes-driven first)
- Browser extension
- Internationalization beyond English + one EU language for v1
- Real-time voice or video
- Crypto / web3 token mechanics
- In-app social features beyond NIP-51 mute lists and NIP-58 badges

## 9. Success metrics

### 9.1 Activity (every phase)

- Active sellers per week (publishing or replying to inquiries)
- Active buyers per week (subscribing or sending inquiries)
- Items published per week
- Inquiries per item (median)
- Successful negotiation rounds per match (median)

### 9.2 Quality (P3 onwards)

- % of listings flagged as red by the buyer-cars rubric
- % of inquiries that lead to a buyer↔seller agreement
  (self-reported by users via a one-tap "did this lead to a deal?"
  prompt)
- Time-to-match (publish → first qualifying buyer inquiry)

### 9.3 Revenue (P5 onwards)

- Premium plugin paying users
- Managed-relay paying npubs
- Verified-seller badges issued
- `reverse-image-mcp` Pro tier conversion rate from buyer cohort

## 10. Decisions log (high-stakes)

Track every reversed decision so future Claude sessions don't
relitigate them.

- **D1**: Discovery layer = Nostr (rejected: Supabase, libp2p, custom
  gossip)
- **D2**: Binary content = ACP only (rejected: HTTP file server,
  signed URLs, Imgur, Dropbox, S3, Blossom)
- **D3**: First paid MCP = `reverse-image-mcp` (rejected:
  `vin-lookup-mcp` Carfax-style aggregation)
- **D4**: Production DM = NIP-17 sealed gift-wraps (NIP-04 only as MVP
  shortcut)
- **D5**: Mode A (one operator-run relay + community) is the v1
  deployment posture (Mode B/C are migration paths, not v1)
- **D6**: Cars vertical first (rejected: real estate, watches as
  first vertical for v1)
- **D7**: Hermes Agent as the host runtime (rejected: writing our own
  agent harness)

## 11. Open questions

Things to decide before P3 closes:

- **OQ1**: Which payment-method confirmation pattern for verified-
  private-seller badge? Stripe SetupIntent? Open-banking attestation?
  Manual review + photo of card?
- **OQ2**: Bootstrap-auth on the registry's `agent-register` route
  (when we add one beyond pure Nostr publish)? Invite-code? PoW?
  Manual approval?
- **OQ3**: Federation with which community relays in the default
  relay list? We need 2–3 stable, low-spam ones beyond ours.
- **OQ4**: Pricing of the `reverse-image-mcp` Pro tier — confirm
  $9/mo bundle vs. $0.10/call metered after first 100 free.
- **OQ5**: Which jurisdictions for v1? Czech Republic + Germany
  default; EN-language fallback for everyone else? Or open from day 1?
