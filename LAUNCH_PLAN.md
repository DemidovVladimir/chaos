# 90-day launch plan — cars vertical, Mode A relay

Bias: ship over polish. Each milestone has explicit deliverables and
exit criteria. If a milestone slips a week, it slips — don't compress
later milestones to catch up.

## Pre-conditions (week 0)

Before week 1 starts:

- [ ] Domain registered (e.g. `neuro-spati.app` and a subdomain plan)
- [ ] VPS account funded (Hetzner / DigitalOcean / Modal)
- [ ] Off-site backup target chosen (Backblaze B2, S3, or Storj)
- [ ] Email infrastructure for `abuse@…` and operator addresses
- [ ] LLM provider chosen (Claude or OpenRouter — confirm budget for
      pilot users; ~$0.50–$2 per active hour at typical use)
- [ ] Stock-image hash starter database obtained (~500k pHashes from
      public stock-photo thumbnails, ~5 MB compressed). One engineer-
      week to assemble.

If any of these slip past week 0, slip the whole plan. Don't start
without infrastructure.

## Weeks 1–2 — Mode A relay live

**Goal**: a working `wss://relay.<your-domain>` with the moderation
runbook in place.

Deliverables:

- [ ] VPS provisioned, DNS resolves, firewall configured
- [ ] `docker compose up -d` runs `registry/strfry-compose.yml`
- [ ] Caddy issues a valid Let's Encrypt cert
- [ ] strfry NIP-11 doc returns 200 with your operator pubkey + name
- [ ] PoW enforcement verified (publish without PoW → rejected)
- [ ] Rate limit verified (12 events in a minute → 11th rejected)
- [ ] Backup cron running, first off-site snapshot completed
- [ ] External canary publish/subscribe round-trip succeeds every
      5 minutes for 24h straight
- [ ] Moderation policy live at `https://moderation.<domain>`
- [ ] `abuse@<domain>` mailbox monitored daily

**Exit criteria**: a third-party Nostr client (Damus, nostr-cli) can
publish and subscribe round-trip successfully against your relay over
TLS. Alerts go to the channel you actually monitor.

If you slip: extend by one week, do not compress later phases.

## Weeks 3–4 — Hermes plugin baseline

**Goal**: a working Hermes plugin that publishes a NIP-99 listing and
subscribes for matching listings, against your relay (Mode A) plus
2–3 community relays. Photos move agent-to-agent over ACP.

Deliverables:

- [ ] `neuro-spati-seller` and `neuro-spati-buyer` packages on PyPI
      (private feed or GitHub release for now; public PyPI later)
- [ ] Keypair generation + secure local storage (mode 0600)
- [ ] NIP-99 publishing flow with PoW (≥ 20 bits)
- [ ] REQ subscription with cars-tag filters
- [ ] NIP-17 gift-wrap encrypt + decrypt for inquiry messages
- [ ] ACP transport between agents (Hermes already ships
      `acp_adapter/`); seller agent can stream `ImageContentBlock`s
      to a buyer agent over a session
- [ ] Webhook adapter route `/webhooks/item-inquiry` configured (for
      structured inquiry pre-ACP-session)
- [ ] Seller-cars and buyer-cars skills installable
- [ ] Configuration: relay list, npub, recovery key
- [ ] One end-to-end test: seller publishes, buyer subscribes, buyer
      sends inquiry over NIP-17, buyer's agent opens an ACP session
      against the seller's `acp_url`, seller's agent streams photos
      as `ImageContentBlock`s. **No third-party file host.** All
      discovery on real relays.

**Exit criteria**: the test scenario runs unattended on two separate
machines with no manual intervention. Zero centralized state outside
the relay (which is your Mode A) and the user's own machines.

If you slip: extend by 1 week. Cut the photo-grant policy down to
"grant all" temporarily if needed; tighten in Phase 2.

## Weeks 5–6 — Three local-only MCPs ship

**Goal**: paid `reverse-image-mcp` + free `vin-decoder-mcp` + free
`market-comp-mcp` all installable. First revenue stream live.

Deliverables:

- [ ] `reverse-image-mcp` v1.0:
  - [ ] pHash + dHash hashing primitives (NumPy, ~50 lines each)
  - [ ] Bundled stock-image hash database (~500k entries, ~5 MB)
  - [ ] `tier=fast` free-tier endpoint (loss-leader: 100/day per pubkey)
  - [ ] `tier=thorough` paid-tier endpoint with EXIF + optional CLIP
  - [ ] Per-pubkey API key + metering with signed receipts
  - [ ] Stripe / BTCpay billing integration for the Pro tier
        ($9/mo, 200 thorough calls)
  - [ ] Hosted endpoint at `https://photos.<domain>/mcp`
  - [ ] Container image for self-host customers
- [ ] `vin-decoder-mcp` v1.0 (free, local):
  - [ ] WMI registry data file (~10k entries, ~500 KB)
  - [ ] Year-code mapping (30-year cycle)
  - [ ] Mod-11 check digit validator
  - [ ] Cross-check vs. listing tags
  - [ ] Bundled with the cars-pack as a default-on free MCP
- [ ] `market-comp-mcp` v1.0 (free, derives from on-network listings):
  - [ ] Relay-query helper
  - [ ] Percentile + recency-weighted aggregation
  - [ ] ECB FX-rate snapshot for cross-currency normalization
  - [ ] 5-minute in-memory result cache
- [ ] Cars-pack skills wired up
- [ ] Pricing page live; terms of service published

**Exit criteria**:
- The pre-share stock-image check on seller-cars catches a planted
  test stock photo and refuses to deliver it via ACP.
- The buyer-cars rubric flags a synthetic listing built from stock
  photos as a hard red flag and auto-suppresses it.
- A real $0.10 `thorough` reverse-image call is charged and delivered.

If you slip: ship `vin-decoder-mcp` and `market-comp-mcp` first (both
free, both core to the buyer rubric). Defer `reverse-image-mcp` paid
tier by 1 week — the free `fast` tier is enough for beta.

## Weeks 7–8 — Closed beta with 5–10 sellers

**Goal**: real listings on the relay from real sellers, with the
buyer-cars skill receiving real notifications.

Deliverables:

- [ ] 5–10 invited beta sellers
- [ ] Each provides at least 1 real car listing
- [ ] 10–20 invited buyer accounts subscribed
- [ ] Daily check-ins
- [ ] Bug-tracking issue list with severity tags
- [ ] At least 1 real successful negotiation round-trip
- [ ] Per-user feedback survey

**Exit criteria**: ≥ 3 of the beta sellers publish a second car
unprompted. That's the meaningful signal.

If fewer come back: do not launch publicly. Talk to those 3, find out
why they didn't, and adjust.

## Weeks 9–10 — Verification badges + first vertical pack polish

**Goal**: NIP-58 verified-seller badge live; the cars-pack feels
"done enough" for public launch.

Deliverables:

- [ ] Badge-issuer agent running (Hermes instance with badge-issuer
      skill, your operator pubkey)
- [ ] Verification flow: seller submits email + payment-method
      confirmation → admin agent issues NIP-58 badge → badge appears
      in NIP-99 listings as `["badge", "..."]`
- [ ] Pricing for badges live ($20 one-time private, $50/yr dealer)
- [ ] Buyer-cars skill prefers badge-holders in evaluation rubric
- [ ] Cars-pack documentation site live with: tag schema, skill
      docs, "how to be a verified seller", "how to install the
      plugin", FAQ
- [ ] Pricing page covers: free plugin, paid premium, paid relay,
      verified-seller badge, reverse-image-mcp tiers
- [ ] Telemetry minimal — track active sellers/week, active
      buyers/week, successful inquiries/week, badges issued, MCP
      calls. No PII.

**Exit criteria**: from a clean machine, a new user installs the
plugin, registers, publishes a real car, gets a badge, receives an
inquiry, responds — all in under 30 minutes following the docs. Test
this with someone who hasn't seen the code.

## Weeks 11–12 — Public launch

**Goal**: marketplace is live. Word-of-mouth growth begins.

Deliverables:

- [ ] Public website launch announcement
- [ ] `neuro-spati-seller` and `neuro-spati-buyer` on public PyPI
- [ ] Relay listed on common Nostr relay directories (`nostr.watch`,
      `relay.exchange`)
- [ ] Forum / Discord / Telegram for users — pick one
- [ ] Initial content marketing: 1 blog post explaining the model,
      1 tutorial ("sell your first car in 30 minutes")
- [ ] Outreach to 50 small-dealer contacts
- [ ] Pricing finalized

**Exit criteria**: 50 active sellers, 200 active buyers within 30
days of public launch. If you don't hit it, treat it as data: which
acquisition channel worked, which didn't, what does the next 30 days
need to look like.

## What's deliberately NOT in 90 days

- Real estate vertical pack — wait until cars proves out
- Skills marketplace meta-layer — needs ≥ 1k users first
- Mode B / Mode C migration — not until users ask for federation
- Mobile clients — desktop-first; mobile in v2
- Payment integration — explicitly off-platform
- Escrow — explicitly off-platform
- Internationalization beyond English + one EU language

## Post-launch quarterly cadence

- **Q2**: Real estate or watches vertical pack (whichever has user pull)
- **Q3**: First custom MCP beyond the cars-pack three —
  likely `scam-pattern-mcp`
- **Q4**: Mode B (federate with paid relays)

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Relay performance under load | low at this scale | Capacity plan + canary alerts |
| Spam attack on launch day | medium | PoW + paid relays + invite-only first 2 weeks |
| Stock-image database becomes stale | medium | Federated NIP-31000 scam-hash registry from v1.1; quarterly bundled-DB refresh |
| False positives on reverse-image check | medium | Auto-suppress only on ≥ 0.92 similarity; soft-flag in 0.85–0.92 band |
| Sellers don't see value vs. existing classifieds | high | Buyer-cars filtering quality is the killer feature; lean on it in marketing |
| Regulatory grey area in some EU country | low-medium | Mode A with curated allowlist; geo-block sanctioned regions; lawyer review pre-launch |
| Hermes upstream breaking change | medium | Pin Hermes version; quarterly upgrade cadence |
| Single-host relay outage during launch week | medium | RTO 30 min; canary + alerts; tested redeploy script |

## What good looks like at day 90

- Mode A relay: < 1 hour of unplanned downtime in 30 days
- ~200 active sellers, ~1,000 active buyers
- 50+ verified-seller badges issued
- `reverse-image-mcp` Pro tier doing $0.5–2k MRR
- Premium plugin at $25/mo with ~50 conversions
- 5+ unsolicited "love this" reviews / posts in the user community
- Two pieces of negative feedback that are actually instructive

If you have all of those, scale. If you have most, iterate. If you
have few, regroup.
