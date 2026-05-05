# PRD — chaos

This is the long requirements document. For a Hermes first pass, read
`OVERVIEW.md` and the short deck; use this file for diligence on
scope, constraints, and phasing.

A precise product-requirements document. Read alongside `OVERVIEW.md`
(plain-English narrative), `PROTOCOL.md` (on-the-wire design),
`VERTICALS.md` (the pack abstraction), and `AGENTS.md` (engineering
rules).

## 1. Problem statement

Autonomous agents, owned by different users and running on
different machines, need to coordinate. The cardinality is
not fixed: sometimes one offering agent and one seeking agent
pair up; often **one offering agent serves many seekers** at the
same time (1:N fan-out); often **many offerings are converged
by one seeker** (N:1 aggregation); and **many-to-many** concurrent
sessions are the norm at scale. An offering agent has something
— an item, a service, a model, a dataset, a block of inference
cycles — and wants the right counterparties (one or many) to
find it. A seeking agent has a need and wants to evaluate
offers (one or many) without revealing its identity to a custodial
intermediary. Today every shape of this handshake routes through
a platform that holds the data, mediates the messaging, takes a
percentage of the deal, and operates as a regulated data controller
on both sides. `cars-pack@1` is the working reference because
peer-to-peer vehicle discovery exercises the full surface — public
metadata, rich binary inspection content, negotiation, trust signals —
but the protocol contract is not cars-specific.

That platform is structurally unnecessary. The discovery problem
(signed events on a federated relay) and the rich-content problem
(JSON-RPC tool calls returning binary content blocks) both have
mature open-protocol answers. What's been missing is the contract
layer that says, **for a given domain**, which tags publishers must
emit and which tools every offering agent must expose. Without that
contract, agents on different machines can't actually find or
evaluate each other.

chaos is the contract layer plus the wiring to make two
agents on different machines coordinate end-to-end without a
platform sitting in the data path.

## 2. Solution in one sentence

Each user runs a Hermes-based agent that publishes signed offerings
as Nostr events tagged according to a pack, subscribes for
matching offers, and connects directly to counterparties over MCP
for the rich-content exchange — no custodial platform anywhere in
the data path.

## 3. Goals

The protocol succeeds if it delivers all of the following:

- **Sovereign identity.** Each agent owns a secp256k1 keypair stored
  locally. The platform never custodies, escrows, or recovers user
  keys. Identity is portable across any Nostr-based application.
- **Federated discovery.** No central registry. Listings are NIP-99
  events on a Nostr relay; the relay set is configurable per agent.
  Mode A (one operator-run relay + community relays) is the v1
  default; Mode B (federation) and Mode C (community-only) are
  migration paths the architecture already supports.
- **Peer transport for everything after pairing.** Once a match
  occurs (and a seeking agent may be matched with several offering
  agents concurrently, or vice versa), the conversation moves to
  MCP for each pair. No platform in the data path. Binary content (images, PDFs, datasets, model artifacts) is
  delivered exclusively as MCP `ImageContent` and `EmbeddedResource`
  blocks returned from `tools/call` results on the offering agent's
  own MCP server.
- **Layered trust.** Five independent trust signals (NIP-58 badges,
  peer attestations, NIP-51 mute lists, NIP-02 web of trust, opt-in
  admin-agent decisions). No single signal is a gatekeeper. Each
  agent computes its own score locally.
- **Vertical composability.** Adding a domain is writing a pack
  (`verticals/<vertical>-pack/`), not re-engineering the protocol.
  The wire is universal; the per-pack contract pins which tags and
  which tools.
- **Security against prompt injection.** Every untrusted input
  passes through a sanitizer and is wrapped in source-tagged
  `<untrusted>` blocks. Agents are explicitly trained to never
  execute instructions found inside untrusted blocks.

## 4. Non-goals

These are explicitly out of scope. A request to build any of them
requires explicit user override per AGENTS.md.

- **Marketplace operator features.** No escrow, no refunds, no
  platform-mediated dispute arbitration with binding outcomes, no
  KYC, no AML.
- **Payment processing of any kind.** Even token-pegged stablecoins.
  Future onchain integrations are non-custodial multi-sig only
  (AGENTS.md Rule 14).
- **Custodial photo or file hosting.** Binary content moves over MCP
  only. No HTTP file servers we operate, no signed URLs to
  third-party hosts.
- **A second peer transport.** MCP is the canonical wire for
  agent↔agent dialogue. No parallel gRPC, custom WebSocket, or other
  peer transport without explicit override.
- **Third-party data brokering.** Custom MCPs may compute over data
  the user already has, query free authoritative sources, or
  aggregate data already on the network. They may not resell
  commercial data we'd need to license, store, or re-distribute.
- **Mobile-first UI.** Desktop / CLI / Hermes-driven first; mobile
  is v2+.
- **Browser extension.** Out of scope.
- **Crypto / web3 token mechanics.** Nostr is a federated relay
  protocol — not a chain, not a token. Phase-1 onchain staking is a
  separate non-custodial roadmap layer, not a token launch.
- **In-app social features** beyond NIP-51 mute lists and NIP-58
  badges.
- **Real-time voice or video.**
- **Per-vertical paid plugins.** The cross-domain pro tier
  (`plugins/chaos-pro/`) is the only paid plugin shape;
  per-domain paid bundles like `cars-buyer-pro` are explicitly
  forbidden.

## 5. Personas

The personas are written domain-agnostically. `cars-pack@1` is one
concrete instantiation; the same shape applies
to ML inference, data licensing, compute jobs, specialist services,
and any future pack.

### 5.1 Offering-side user (single-item)

A person or organization with a specific thing to advertise — one
car, one apartment, one dataset, one consultancy slot, one fine-tuned
model. Mid-30s, professional, has a few hours per week to spend on
the listing. Wants their offering visible to the right
counterparties without uploading content to a custodial platform
that may reuse it. Wants spam filtered out before it reaches them.

**Goals**: list once, get qualified inquiries, share the rich
content (photos, samples, schemas) only with counterparties they've
explicitly approved, finalize off-platform.

### 5.2 Offering-side user (institutional / bulk)

A dealership, a model provider, a compute provider, a law firm —
anyone running multiple offerings under one identity. Wants
efficient bulk listing, brand visibility, and a clean inquiry inbox.
Often has an existing CRM or pipeline they don't want to replace.

**Goals**: list inventory in bulk, route inquiries internally, track
conversion. Will pay for tools that integrate with what they
already run.

### 5.3 Seeking-side user

Looking for a specific kind of offering. Wants to be notified when
matches appear, wants to evaluate without scrolling, wants to talk
to offerors without giving up identifying details up front.

**Goals**: define a filter once, receive matches, evaluate, contact
the offering party, finalize.

### 5.4 Vertical operator

Operates one or more vertical support services: the Mode A relay,
optional NIP-58 badge issuance, and optional admin-agent trust signals.
These are separate responsibilities and may be run independently.

**Goals**: a clean low-spam relay; sustainable revenue from premium
tools, badge issuance, and admin-tier subscriptions; minimal
operational and regulatory burden.

Boundary: the relay operator runs strfry/Caddy and relay policy; the
badge issuer performs manual due diligence and signs NIP-58 badges; the
admin-agent is a separate Hermes process that publishes opt-in kind
30430/30431 trust signals. The admin-agent does not operate the relay,
issue badges, revoke badges, or call buyer/seller MCP servers.

## 6. User stories

Written for any vertical. **Agent A** is the offering side; **Agent
B** is the seeking side. `cars-pack@1` is one instantiation; the
shape is identical for any pack.

- **US-1 — Offering published.** Agent A's user describes their
  offering. Agent A constructs a NIP-99 event tagged according to
  the relevant pack, mines NIP-13 PoW (≥ 20 bits), signs with the
  user's secp256k1 key, and publishes to the configured relay set.
- **US-2 — Filter subscription.** Agent B's user defines a filter in
  the pack's tag vocabulary. Agent B opens a Nostr REQ subscription
  matching that filter across configured relays, dedupes incoming
  events by `id`.
- **US-3 — Evaluation.** When a matching event arrives, Agent B runs
  the pack's evaluation rubric (cross-domain capability MCPs plus
  pack-specific checks) and classifies the listing as `surface`,
  `watchlist`, or `suppress`.
- **US-4 — Inquiry initiation.** Agent B's user taps "ask for more
  details". Agent B composes a structured `asks` payload, encrypts
  via NIP-17 sealed gift-wrap addressed to Agent A's pubkey,
  publishes the gift-wrap event with a `session_token`.
- **US-5 — MCP session open.** Agent A receives the gift-wrap,
  decrypts, applies the per-ask grant policy (auto-grant routine
  asks; user-prompt for sensitive asks). Agent B's MCP client
  connects to Agent A's `mcp_url` carrying the `session_token` from
  the rumor, runs `tools/list` to discover the pack's tool surface.
- **US-6 — Rich-content exchange.** Agent B calls the pack-defined
  tools (e.g. `request_photos`, `request_inspection_report`,
  `request_sample`, `request_benchmark`). Agent A returns text
  blocks for descriptions, `ImageContent` blocks for images, and
  `EmbeddedResource` blocks for arbitrary binary payloads.
- **US-7 — Negotiation rounds.** Buyer and seller exchange offers
  via `submit_offer` MCP tool calls (or NIP-17 DMs if the MCP
  session has closed). Bounded: max 5 rounds per (item,
  counterparty), max 1000 chars per offer, max 50,000 chars per
  match.
- **US-8 — Acceptance.** Each side requires explicit user
  confirmation before any `accept_offer` returns success. When both
  accept, each agent stores a small signed agreement event locally.
  The actual transfer of value happens off-platform.
- **US-9 — Status update / removal.** Agent A republishes with
  `status: sold` and (optionally) issues a NIP-09 deletion request.
- **US-10 — Reputation lookup.** At any point during US-3 through
  US-8, either agent calls `shared-mcp/reputation-mcp` to compute a
  local `score_aggregate` for the counterparty pubkey, weighting
  the five trust signals according to the user's policy.

## 7. Functional requirements

### 7.1 Offering-side agent (FR-O)

- **FR-O1**: Generate a secp256k1 keypair on first run; store at
  `~/.chaos/keys/seller.key` mode 0600.
- **FR-O2**: Accept a TOML or interactive description; construct a
  NIP-99 (kind 30402) event using the pack's tag schema.
- **FR-O3**: Mine NIP-13 PoW (≥ 20 bits) before signing.
- **FR-O4**: Publish to the configured relay set (default: operator
  relay + 2–3 community relays).
- **FR-O5**: Support update by republishing with the same `d` tag;
  support archive via status update + NIP-09 deletion.
- **FR-O6**: Maintain a local catalog at
  `~/.chaos/items/<item-id>/`.
- **FR-O7**: Receive NIP-17 gift-wraps (NIP-04 only in MVP),
  decrypt locally.
- **FR-O8**: Apply the per-ask grant policy from the pack's
  `seller-<vertical>` skill.
- **FR-O9**: Expose the pack-mandated MCP tool surface via FastMCP
  HTTP+SSE. Tools return content blocks (`text` / `ImageContent` /
  `EmbeddedResource`). **No HTTP file delivery, ever.**
- **FR-O10**: Run pack-relevant pre-share checks before any tool
  call returns binary content (e.g. `reverse-image-mcp` on photos
  for cars and real estate; integrity checks on dataset samples for
  data-licensing).
- **FR-O11**: Support negotiation rounds with bounded state
  (max 5 rounds, 1000 chars per message, 50k total).
- **FR-O12**: Never accept a final offer without explicit user
  confirmation in the same session.

### 7.2 Seeking-side agent (FR-S)

- **FR-S1**: Generate a secp256k1 keypair, stored as in FR-O1.
- **FR-S2**: Accept a filter spec in the pack's tag vocabulary;
  subscribe via Nostr REQ across the configured relay set.
- **FR-S3**: Dedupe events by `id` across relays.
- **FR-S4**: Run the pack's evaluation rubric; classify each
  matching event as `surface`, `watchlist`, or `suppress`.
- **FR-S5**: Surface to the user via Hermes' configured gateway
  (Telegram, Discord, CLI, …).
- **FR-S6**: Compose structured `asks` payload, encrypt via NIP-17,
  publish gift-wrap.
- **FR-S7**: Open MCP HTTP+SSE session against the offering agent's
  `mcp_url` carrying the `session_token`. Run `tools/list`. Call
  pack-defined tools as needed. Run cross-domain capability MCPs
  (e.g. `reverse-image-mcp` thorough tier) on returned content.
- **FR-S8**: Maintain a local inbox at `~/.chaos/inbox/` —
  one JSONL per inquiry conversation.
- **FR-S9**: Same negotiation bounds as FR-O11.
- **FR-S10**: Never commit without explicit user confirmation.

### 7.3 Relay (FR-R)

- **FR-R1**: A strfry-based Nostr relay reachable at
  `wss://relay.<operator-domain>` (per-domain or unified).
- **FR-R2**: Accept kinds 0, 5, 13, 14, 1059, 1985, 8, 30000–30099,
  30009, 30402, 30403, plus reputation kinds (30410–30431).
- **FR-R3**: Enforce NIP-13 PoW ≥ 20 bits on kind-30402 events.
  Skip PoW on kinds 13/14/1059 (encrypted DM family).
- **FR-R4**: Max event size 16 KB, max content 8 KB; reject events
  > 1 year old or > 15 minutes future-dated.
- **FR-R5**: Per-pubkey rate limit: 10 events/min, 100 events/hour
  default; configurable allowlist override.
- **FR-R6**: Pubkey blocklist at the writePolicy layer.
- **FR-R7**: NIP-11 relay-info doc at the root via Caddy.
- **FR-R8**: TLS via Caddy + Let's Encrypt.
- **FR-R9**: Daily LMDB snapshot, off-site retention 90 days.
- **FR-R10**: Prometheus metrics on a private port.
- **FR-R11**: External canary publish/subscribe round-trip every 5
  minutes from a separate host.
- **FR-R12**: Append-only moderation log at
  `/var/lib/moderation/log.jsonl` with actor + reason for every
  blocklist action.

### 7.4 Pack contract (FR-P)

For any pack `<vertical>-pack@<major>`:

- **FR-P1**: A NIP-99 tag schema in
  `verticals/<vertical>-pack/tag_schema.md` defining required and
  optional tags. Backwards-additive only within a major version.
- **FR-P2**: A `seller-<vertical>` skill in
  `verticals/<vertical>-pack/skills/seller-<vertical>/SKILL.md`.
- **FR-P3**: A `buyer-<vertical>` skill in
  `verticals/<vertical>-pack/skills/buyer-<vertical>/SKILL.md`.
- **FR-P4**: An optional `admin-<vertical>` skill if the operator
  runs an admin-agent for the vertical.
- **FR-P5**: A documented MCP tool surface — the named tools every
  offering agent in this vertical must expose, with input schemas
  and content-block return types.
- **FR-P6**: An `example_listing.json` showing a fully-tagged event.
- **FR-P7**: A default grant policy declaring per-ask defaults and
  which asks require explicit user approval.

The reference vertical (cars-pack@1) implements all of FR-P1
through FR-P7 today. Sketched verticals fill these in as scaffolds
land.

### 7.5 Trust signals (FR-T)

The 5-layer reputation model is documented in
`reputation/README.md`. NIP-58 badges (FR-T1) are layer 1;
admin-agent decisions (kind 30430, see AGENTS.md Rules 15–16) are
layer 5 and opt-in.

- **FR-T1**: NIP-58 badge issuer workflow operated by the vertical's
  operator (documented under `operator/<vertical>/`), capable of
  issuing domain-appropriate badges. This is separate from the
  admin-agent.
- **FR-T2**: Verification flow combines email confirmation,
  payment-method confirmation (no money handled — just
  attestation), and (for institutional offerings) domain-ownership
  check.
- **FR-T3**: Badges are NIP-58 events; seeking-side agents read them
  and weight them in the evaluation rubric.
- **FR-T4**: Operator publishes a NIP-51 mute list of pubkeys
  blocklisted at the relay; agents subscribe by default.
- **FR-T5**: Bilateral peer attestations as kinds 30410 / 30411
  (and unilateral 30412). Schema in
  `reputation/attestation_schema.md`; weights in
  `reputation/scoring.md`.
- **FR-T6**: Admin-agent (opt-in, operator-deployed) publishes
  structured decisions as kind 30430. Affected parties may publish
  appeals as kind 30431. It does not issue/revoke NIP-58 badges or
  operate the relay. See `reputation/dispute_protocol.md`.
- **FR-T7**: All reputation reads route through
  `shared-mcp/reputation-mcp`. Each agent computes its own
  `score_aggregate` locally — no central rep store, no published
  official rankings.

### 7.6 Plugins and pro tier (FR-PL)

- **FR-PL1**: Each plugin under `plugins/<vertical>-<role>/`
  declares its toolset in `plugin.yaml` and respects AGENTS.md
  Rule 11 (role isolation). CI lint rejects violations.
- **FR-PL2**: `plugins/chaos-pro/` is the **single
  cross-domain paid upgrade** — applies to every installed buyer
  plugin. No per-domain paid plugins exist.
- **FR-PL3**: Admin plugins (`plugins/<vertical>-admin/`) are
  operator-deployed only. Admin invariants per AGENTS.md Rule 16;
  threat model per Rule 15.

## 8. Non-functional requirements

### 8.1 Privacy / data protection

- **NFR-P1**: The platform never receives or stores user PII.
- **NFR-P2**: The platform never receives or stores binary content.
  Binary moves exclusively as MCP content blocks from `tools/call`
  results on the offering agent's own MCP server.
- **NFR-P3**: 1-to-1 messaging is end-to-end encrypted at the
  protocol layer (NIP-17 in production; NIP-04 only in MVP).
- **NFR-P4**: Audit logs at the relay carry only event metadata
  (counts, kinds, status codes) — never decrypted content.
- **NFR-P5**: Right to erasure: deleting an issuer-side record is
  one operation; local data deletion is the user's responsibility
  on their own machine.

### 8.2 Performance

- **NFR-PERF1**: Listing publish round-trip ≤ 5s end-to-end.
- **NFR-PERF2**: Subscription receives matching event within 10s
  of publish (subject to relay propagation).
- **NFR-PERF3**: Relay query p99 ≤ 100 ms at v1 scale.
- **NFR-PERF4**: MCP HTTP+SSE session opens within 3s of
  initiation; per-content-block throughput limited only by network.

### 8.3 Availability

- **NFR-AVAIL1**: Mode A relay target uptime 99.5%.
- **NFR-AVAIL2**: When the operator's relay is down, agents
  continue via community relays. Live peer↔peer sessions continue
  uninterrupted (MCP is direct, doesn't depend on relays).

### 8.4 Security

- **NFR-SEC1**: All inbound webhook routes (if any) verify HMAC.
- **NFR-SEC2**: All untrusted text passes through the input
  sanitizer before any LLM context render.
- **NFR-SEC3**: Agent toolsets are narrowed: no `terminal`,
  `execute_code`, `delegation`, unconstrained `web`, or unrelated
  MCP toolsets enabled.
- **NFR-SEC4**: Container isolation — read-only root, tmpfs `/tmp`,
  egress allowlist limited to relays + LLM endpoint + gateway.

### 8.5 Operational

- **NFR-OPS1**: Mode A relay deploys in ≤ 30 min from a clean VPS
  using `operator/<vertical>/docker-compose.yml` + DNS + TLS.
- **NFR-OPS2**: Backup RPO ≤ 24h; RTO ≤ 30 min.
- **NFR-OPS3**: Monitoring with alerting for: relay unreachable,
  cert expiry, disk free, rejection-rate anomalies, latency
  anomalies.

## 9. Constraints

- **C1**: Discovery layer must be Nostr; no central database we
  operate.
- **C2**: Binary content must move agent-to-agent over MCP as
  `ImageContent` / `EmbeddedResource` blocks. No HTTP file servers,
  no third-party file hosts. No second peer transport.
- **C3**: Identity is a secp256k1 keypair owned by the user; no
  recovery path through us.
- **C4**: Custom MCPs may not aggregate or resell commercial
  third-party data.
- **C5**: Compatible with Hermes Agent (Nous Research) v0.11+ as
  the runtime. Plugin shape per Hermes' plugin contract.

## 10. Success criteria

- **SC-1 — Composability.** A new pack is implementable in
  ≤ 5 person-days end-to-end (tag schema + tool surface + skills +
  example listing). Measured by shipping a second pack alongside
  cars.
- **SC-2 — Trust.** All 5 trust signal types are implemented and
  composable into a per-agent local score. Measured by
  `reputation-mcp` returning each layer's contribution
  independently.
- **SC-3 — Security.** All 16 architectural rules in AGENTS.md are
  enforced (Rule 11 by CI lint; Rules 15–16 by admin-skill review
  before each release; Rules 1–10 by code review).
- **SC-4 — Demonstrable working demo.** End-to-end run on two
  laptops, two free public relays, no infrastructure on the
  developer's side (`mvp/` ships this today).
- **SC-5 — Multi-pack user.** A single Hermes instance running 2+
  installed buyer plugins side-by-side, evaluating offers from 2
  different verticals concurrently. Measured at end of the launch
  plan.
- **SC-6 — Federated topology.** At least 3 independently operated
  relays carrying chaos listings, with cross-relay propagation
  verified by canary.

## 11. Phasing

| Phase | Window | Goal | Exit criterion |
|---|---|---|---|
| **P0 — MVP** | Weekend | Two laptops, encrypted text inquiry round-trip over public relays | Demo screen-capture works |
| **P1 — Universal engines** | Week 1 | `seller/` + `buyer/` scaffolds wired into Hermes plugin loaders | A vacuous pack loads end-to-end |
| **P2 — First pack** | Week 2 | cars-pack@1 end-to-end via Hermes plugin (FastMCP server + client, `ImageContent` photo delivery) | Two-machine end-to-end test passes unattended |
| **P3 — Second pack** | Week 3 | One sketched vertical (e.g. data-licensing) implemented to prove generality + reputation-mcp wiring | Same Hermes instance runs both packs concurrently |
| **P4 — Admin-agent trust signals** | Week 4 | admin-cars live; opt-in dispute signal flow wired; Phase-1 staking remains research-only | First public dispute signal → decision → appeal cycle completes on relay |
| **Beyond** | — | Multi-vertical user, federated relay topology, cross-domain reputation | 100+ active agents across 2+ verticals on 3+ relays |



## 12. Decisions log (high-stakes)

- **D1**: Discovery = Nostr. Rejected: Supabase, libp2p, custom
  gossip.
- **D2**: Binary content = MCP `ImageContent` / `EmbeddedResource`
  blocks only, returned from `tools/call`. Rejected: HTTP file
  server, signed URLs, Imgur, Dropbox, S3, Blossom.
- **D3**: First paid MCP = `reverse-image-mcp`. Rejected:
  `vin-lookup-mcp` Carfax-style aggregation.
- **D4**: Production DM = NIP-17 sealed gift-wraps. NIP-04 only as
  MVP shortcut.
- **D5**: Mode A (operator-run relay + community) is v1 default.
- **D6**: cars-pack@1 ships first as the reference vertical.
  Rejected: leading the launch with multiple verticals
  simultaneously.
- **D7**: Hermes Agent as host runtime. Rejected: writing our own
  agent harness.

## 13. Open questions

- **OQ1**: Which payment-method confirmation pattern for verified-
  individual badges? Stripe SetupIntent? Open-banking attestation?
  Manual review?
- **OQ2**: Which community relays in the default relay list? Need
  2–3 stable, low-spam ones beyond ours.
- **OQ3**: Sequencing of the second pack — data-licensing
  vs. ml-inference vs. specialist-services. Driven by which
  community has the most pull.
- **OQ4**: Pricing of `reverse-image-mcp` Pro tier — confirm $9/mo
  bundle vs. $0.10/call metered after first 100 free.
- **OQ5**: Phase-1 staking jurisdiction sequencing — which target
  jurisdiction for the first legal review.

## 14. Competitive landscape

A brief pointer: there are three meaningfully different design
points in the agent-coordination protocol space as of May 2026.
Full analysis lives in `COMPETITIVE_LANDSCAPE.md`.

- **Centralized agentic checkout** — custodial, KYC'd,
  conventional money rails.
  Optimized for retail-style purchases by AI shopping
  assistants. **A single shape: AI buys from a regulated
  merchant.**
- **Agent-services vending on open rails** — **Elisym**
  (elisym.network, elisymprotocol/elisym-core) is the
  closest-adjacent project: Nostr discovery + NIP-90 Data
  Vending Machines + self-custodial Lightning. **A single
  shape: agent sells a service for sats.**
- **Decentralised remote agentic collaboration substrate** —
  chaos. NIP-99 classifieds + MCP rich-content delivery + no
  money flow and no custodial platform in the data path +
  public-OR-private deployment topology. **The general substrate**
  any of the specific shapes above can ride on. `cars-pack@1` is
  the working reference; `ml-inference`, `data-licensing`,
  `compute-jobs`, and `specialist-services` are sketched.

These are not substitutes. chaos and Elisym can coexist on the
same Nostr fabric — same identity, different event kinds. See
`COMPETITIVE_LANDSCAPE.md` for the head-to-head table and the
six-point argument that chaos is the substrate Hermes-built
applications most naturally compose against.

## 15. Hermes collaboration framing

chaos is **built on Hermes**, not merely compatible with it. The
critical Hermes surfaces are MCP client/server tools, plugin loading,
`forbidden_toolsets`, skills, and grant policy.

The ask is partnership-shaped:

1. Review the architecture and security model.
2. If it holds up, list chaos as a Hermes ecosystem reference
   protocol.
3. Explore a private chaos node for Hermes-internal coordination.
4. Co-design reusable MCPs: `reverse-image-mcp`, `market-comp-mcp`,
   and `reputation-mcp`.

Use `pitch/chaos-hermes-short.html` for the first conversation.
`pitch/chaos-deck.html`, this PRD, and `COMPETITIVE_LANDSCAPE.md` are
follow-up material.
