# LAUNCH PLAN — phased rollout

This is the shipping plan for chaos as a coordination protocol
for autonomous agents. The phases are bias-toward-shipping; each
phase has explicit deliverables and exit criteria. If a phase slips
a week, it slips — don't compress later phases to catch up.

## Approach

The phasing is deliberately not "ship cars first then add other
verticals". The phasing is:

1. **Universal engines first.** Prove that `seller/` and `buyer/`
   can load any pack and round-trip the protocol end-to-end.
2. **First vertical pack as the proof-of-shape.** Implement
   cars-pack@1 fully end-to-end via Hermes plugins. This is the
   reference vertical; everything else extends the same shape.
3. **Second vertical pack as the proof-of-generality.** Implement
   one sketched vertical (likely data-licensing, ml-inference, or
   specialist-services — driven by which community has pull).
   Successful exit means the same Hermes runtime serves both
   verticals concurrently.
4. **Admin-agent + community arbitration.** Activate dispute kinds
   30430 / 30431, the admin-agent's hardened skill, and the
   community-arbitrator multi-sig hooks for Phase-1 staking
   readiness.
5. **Beyond.** Multi-vertical user, federated relay topology,
   cross-vertical reputation. Scale.

## Pre-conditions (week 0)

Before week 1 starts:

- [ ] Domain registered (e.g. `chaos.app` and a per-vertical
      subdomain plan)
- [ ] VPS account funded (Hetzner / DigitalOcean / Modal)
- [ ] Off-site backup target chosen (Backblaze B2, S3, or Storj)
- [ ] Email infrastructure for `abuse@…` and operator addresses
- [ ] LLM provider chosen (Claude or OpenRouter — confirm budget)
- [ ] Stock-image hash starter database obtained (for
      `reverse-image-mcp` — relevant to any pack that handles
      photos: cars, real-estate, watches, livestock). Roughly 500k
      pHashes from public stock-photo thumbnails, ~5 MB compressed.

If any of these slip past week 0, slip the whole plan. Don't start
without infrastructure.

## Phase 1 (week 1) — Universal engines

**Goal**: `seller/` and `buyer/` scaffolds wired into Hermes plugin
loaders. A vacuous pack — minimal tag schema, single
`echo` MCP tool — loads end-to-end.

Deliverables:

- [ ] `seller/` engine loads a pack from
      `verticals/<pack>/pack.yaml` and exposes the pack's tool
      surface via FastMCP HTTP+SSE
- [ ] `buyer/` engine loads a pack and runs the pack's evaluation
      rubric
- [ ] Plugin loader contract verified: `plugin.yaml` declares
      toolset; CI lint enforces role isolation per CLAUDE.md Rule 11
- [ ] Hermes plugin install path documented and tested with
      `plugins/_template/`
- [ ] Keypair generation + secure local storage (mode 0600)
- [ ] Configuration: relay list, npub, MCP server URL + TLS,
      MCP-allowlist (buyer side)

**Exit criteria**: `plugins/_template/` installs cleanly into
Hermes, the universal engines run a vacuous pack end-to-end, and
the role-isolation lint catches a deliberately broken
configuration.

If you slip: extend by one week. Do not compress phase 2.

## Phase 2 (week 2) — First vertical pack (cars), seamless from MVP

**Goal**: cars-pack@1 ships end-to-end as a Hermes plugin pair
(`plugins/cars-seller/` + `plugins/cars-buyer/`), against your
operator relay (Mode A) plus 2–3 community relays. Photos flow
agent-to-agent over MCP.

Deliverables:

- [ ] `plugins/cars-seller/` and `plugins/cars-buyer/` install into
      Hermes
- [ ] NIP-99 publish flow with PoW (≥ 20 bits), tags include
      `["mcp", "<https-url>"]` and `["pack", "cars-pack@1"]`
- [ ] REQ subscription with cars-pack tag filters
- [ ] NIP-17 gift-wrap encrypt + decrypt for the inquiry channel
      (rumor type `mcp_inquiry_open` carries the `session_token`)
- [ ] FastMCP HTTP+SSE server on the offering agent exposing the
      cars-pack@1 tool surface: `view_listing`, `request_photos`,
      `request_inspection_report`, `request_vin`, `submit_offer`,
      `cancel_inquiry`
- [ ] FastMCP HTTP+SSE client on the seeking agent that runs
      `tools/list` then `mcp_call_tool` for each ask
- [ ] `seller-cars` and `buyer-cars` skills installable from
      `verticals/cars-pack/skills/`
- [ ] One end-to-end test on two separate machines: seller
      publishes; buyer subscribes; buyer sends `mcp_inquiry_open`
      rumor over NIP-17; buyer connects to seller's `mcp_url`
      carrying `session_token`; runs `tools/list`; calls
      `request_photos`; receives photos as `ImageContent` blocks;
      receives the inspection report as an `EmbeddedResource`.
      **No third-party file host anywhere in the loop.**
- [ ] Mode A relay deployed via `operator/cars/docker-compose.yml`,
      backups + canary running
- [ ] Three local-only capability MCPs ship: `reverse-image-mcp`,
      `vin-decoder-mcp`, `market-comp-mcp`. First metered revenue
      from the `reverse-image-mcp` Pro tier is wired but not yet
      depended on for the demo

**Exit criteria**: the test scenario runs unattended on two separate
machines with no manual intervention, no platform piece in the data
path. Zero centralized state outside the relay (Mode A) and the
user's own machines.

If you slip: extend by 1 week. Cut the photo-grant policy down to
"grant all" temporarily if needed; tighten in phase 3.

## Phase 3 (week 3) — Second vertical pack, proof-of-generality

**Goal**: one sketched vertical implemented end-to-end, demonstrating
that the protocol contract works for a non-cars domain. Same Hermes
runtime serves both packs concurrently. `reputation-mcp` wired up.

Likely candidate: **`data-licensing-pack`** (clean tag schema,
clean tool surface, pre-existing demand from the data-broker
displacement story) or **`ml-inference-pack`** (closest to the
Hermes audience). Decided at start of phase 3 based on community
pull.

Deliverables:

- [ ] Pack source of truth at `verticals/<vertical>-pack/`:
      `tag_schema.md`, `example_listing.json`, MCP tool-surface
      spec, seller skill, buyer skill, default grant policy
- [ ] Plugin pair: `plugins/<vertical>-seller/` and
      `plugins/<vertical>-buyer/` installable into Hermes
- [ ] If the pack needs a vertical-specific capability MCP (most
      packs reuse the cross-vertical ones, but some — e.g. ML
      inference — need one), it lives in
      `verticals/<vertical>-pack/mcp/<mcp-name>/`
- [ ] One end-to-end demo on two machines, same shape as the cars
      demo
- [ ] `shared-mcp/reputation-mcp` wired into both buyer plugins;
      score_aggregate computed locally per agent across all 5
      reputation layers (NIP-58, peer attestations, NIP-51, NIP-02
      WoT, opt-in admin decisions)
- [ ] Multi-vertical user demo: one Hermes instance with both
      `cars-buyer` and `<new>-buyer` plugins installed,
      simultaneously evaluating offers from both verticals

**Exit criteria**: the second vertical's end-to-end demo runs on
the same Hermes instance as the cars demo, against the same relay
infrastructure, with no protocol-level changes. The wire is
unchanged; only the per-pack contract differs.

If you slip: keep the second vertical scaffolded but skip the
end-to-end demo until phase 4.

## Phase 4 (week 4) — Admin-agent + community arbitration

**Goal**: the admin-agent runs live for cars (extensible to any
vertical), the community-arbitration multi-sig hooks are wired,
and the Phase-1 staking research is kicked off.

Deliverables:

- [ ] `admin-cars` skill from
      `verticals/cars-pack/skills/admin-cars/SKILL.md` deployed via
      `plugins/cars-admin/` on the operator's infrastructure
- [ ] Admin-agent invariants from CLAUDE.md Rule 16 enforced:
      decisions limited to `clear` / `warning` / `flag` /
      `escalated`; no destructive unilateral action
- [ ] Anti-injection hardening per CLAUDE.md Rule 15 verified:
      input sanitizer + source-tagged `<untrusted>` blocks, refusal
      to act on instructions found inside untrusted blocks
- [ ] Dispute kinds 30430 (decisions) + 30431 (appeals) live on
      relay
- [ ] Multi-sig hook for community-arbitrator decisions: at least
      one full cycle of submit-dispute → admin-agent decision →
      affected-party appeal completes on relay
- [ ] First public dispute → decision → appeal cycle audited on
      relay
- [ ] Phase-1 staking research initiated: legal review for target
      jurisdiction begun, smart-contract auditor identified, kinds
      30420–30422 schema reviewed

**Exit criteria**: at least one dispute / decision / appeal
sequence runs to completion on relay, fully publicly auditable.
The admin-agent does not custody money or PII (CLAUDE.md Rule 16);
hashes-only retention after decision verified.

## Beyond — multi-vertical scale, federation, cross-vertical reputation

Quarterly cadence after phase 4:

- **Q2** — Third vertical pack (whichever has user pull); first
  cross-vertical reputation signal sharing (opt-in)
- **Q3** — Mode B (federate with paid relays) operationalized; new
  `scam-pattern-mcp` shipped as the next paid capability MCP
- **Q4** — Fourth vertical pack; Phase-1 staking goes live for the
  first jurisdiction (only after legal review and external smart-
  contract audit, per CLAUDE.md Rule 14)
- **Year 2** — Skills marketplace meta-layer once active community
  exists across multiple verticals (~1k active users threshold)

## Success metrics

By the end of phase 4 (week 4):

- **Multi-pack** — at least one user is running 2+ buyer plugins
  side-by-side with their score_aggregate computed across both
  verticals
- **Federated** — at least 3 independently operated relays carry
  chaos listings, with cross-relay propagation verified by
  canary
- **Active agents** — 100+ active agents across 2+ verticals on 3+
  relays
- **Demonstrable** — the admin-agent has handled at least one full
  dispute cycle publicly auditable on relay

By month 12 (post-launch):

- 200+ active offering-side users across 3+ verticals
- 1,000+ active seeking-side users
- 50+ NIP-58 verified-issuer badges issued across the network
- `reverse-image-mcp` Pro tier at $0.5–2k MRR (across all packs
  that use images)
- `chaos-pro` cross-vertical subscription at ~50 conversions

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Relay performance under load | low at this scale | Capacity plan + canary alerts |
| Spam attack on launch day | medium | PoW + paid relays + invite-only first 2 weeks |
| Stock-image database becomes stale | medium | Federated NIP-31000 scam-hash registry from v1.1; quarterly bundled-DB refresh |
| False positives on cross-vertical capability MCPs | medium | Auto-suppress only on high-confidence thresholds; soft-flag below |
| First vertical doesn't find product-market fit | medium | Cars chosen because it has clean tag vocabulary + photo-fraud problem the protocol uniquely solves; second vertical (phase 3) provides backup |
| Hermes upstream breaking change | medium | Pin Hermes version; quarterly upgrade cadence |
| Single-host relay outage during launch week | medium | RTO 30 min; canary + alerts; tested redeploy script |
| Plugin role-isolation rule (Rule 11) violated by contributor | low | CI lint rejects; review checklist enforces |
| Admin-agent prompt injection succeeds | low (Rule 15 hardened) | Mandatory skill review before each release; soft-negative reputation for issuing pubkey |
| Phase-1 staking jurisdictional risk | medium | Phase-1 ships only after legal review + external audit (CLAUDE.md Rule 14) |

## What good looks like at end of phase 4

- Mode A relay: < 1 hour of unplanned downtime in 30 days
- Two vertical packs running end-to-end on the same Hermes runtime
- ~100 active agents across both verticals
- At least 5 NIP-58 verified-issuer badges issued
- At least one full dispute cycle (submit / decision / appeal)
  on relay, publicly auditable
- `reverse-image-mcp` Pro tier wired as a payable service
- `chaos-pro` cross-vertical subscription wired with first
  conversions

If you have all of those, scale into Q2. If you have most, iterate.
If you have few, regroup before adding a third vertical.
