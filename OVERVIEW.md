# OVERVIEW

A 5-minute read. For the precise requirements see `PRD.md`; for the
on-the-wire design see `PROTOCOL.md`.

## What it is

neuro-spati is a peer-to-peer marketplace where buyers and sellers
are represented by autonomous agents. Each agent runs on the user's
own machine. The agents discover each other through a Nostr relay,
talk directly (encrypted), and exchange photos and documents
agent-to-agent over ACP. The platform never holds the data.

The product launches with a **cars** vertical. The same shape works
for real estate, watches, livestock, services — anything where
description + photos + region + price are the discovery facets.

## How it actually works, end to end

### A seller listing a car

1. The seller tells their Hermes-based agent: "I want to sell my
   2018 Mazda 3, 65k miles, 15,000 EUR, located in Prague, accept
   offers down to 13,800."
2. The agent generates (or reuses) a secp256k1 keypair as the
   seller's identity. The pubkey is the seller's portable account.
3. The agent helps the user organize photos and a description into
   a local catalog at `~/.neuro_spati/items/<item-id>/`. Nothing
   uploaded.
4. The agent constructs a NIP-99 classified-listing event (`kind:
   30402`) with the cars-pack tag schema (make, model, year,
   mileage band, body type, price band, region, etc.). It mines a
   small proof-of-work (~150ms on a laptop) and signs the event.
5. The agent publishes to the configured Nostr relays — typically
   our own (`wss://relay.<our-domain>`) plus 2–3 community relays
   like `wss://relay.damus.io`. The listing is now visible to anyone
   subscribed to those relays.

### A buyer finding it

1. The buyer's agent has a saved filter ("Mazda 3 hatchback, 2015–
   2020, EU/CZ, 10–20k EUR, ≤ 75k miles").
2. The agent maintains a Nostr REQ subscription matching that filter.
3. When the seller publishes, the agent receives the event within
   seconds, dedupes by id, and runs an evaluation rubric:
   - perceptual-hash check on the listing photos (once they arrive
     via ACP — not on the public listing, which carries no photos)
   - structural VIN decode (if a VIN was shared in the inquiry
     channel)
   - market comp from other on-network listings
   - reputation from NIP-58 badges and NIP-51 mute lists
4. If it passes, the buyer's agent surfaces the listing to the user
   on whatever channel they prefer (Telegram, Discord, CLI).
5. The user taps "ask seller for more details".

### The 1-to-1 inquiry

1. The buyer's agent composes a structured `asks` payload (full
   description, photos:exterior, photos:interior, service history,
   delivery options, etc.).
2. The agent encrypts the payload as a NIP-17 sealed gift-wrap event,
   addressed to the seller's pubkey, and publishes it. Relays propagate
   it but cannot read it.
3. The seller's agent receives the gift-wrap, decrypts it, and
   applies the seller's per-ask grant policy. Routine asks (full
   description, public photos) are auto-granted; sensitive asks
   (full VIN, last-4 of plate, pickup address) require explicit user
   approval in the same session.
4. The seller's agent opens an **ACP session** against the buyer's
   `acp_url` and streams the response: text content blocks for the
   description, image content blocks for the photos, embedded
   resources for the inspection PDF. **The bytes flow seller-disk →
   ACP session → buyer-disk. No HTTP file server. No third-party
   host.**
5. The buyer's agent receives the content blocks, runs reverse-image
   checks on the photos (locally, on bytes it just received), verifies
   any signed attestations, and presents everything to the user.

### Negotiation and close

1. Buyer and seller exchange counter-offers as additional NIP-17 DMs
   (or as ACP messages within the same session, if it stays open).
2. Maximum 5 rounds; user must explicitly approve any acceptance.
3. When both sides accept, the agents create a small signed
   "agreement" event each side stores locally. The actual transfer
   of money happens **off-platform**, between two humans, however
   they want.
4. Either side can update their listing to `status: sold` and issue
   a NIP-09 deletion request for the original event.

## What's distinctive about this design

### Sovereign identity

Every agent owns a secp256k1 keypair. That keypair is the user's
portable identity across any Nostr-based application. It works in
Damus, Plebeian Market, future Nostr clients — not just ours. We
can't deplatform; we can refuse to relay (one operator's slice of
the network), but the user moves to other relays freely.

### Federated discovery, no platform database

The Nostr relay we operate is one of many. Sellers publish to ours
plus community relays; buyers subscribe to a similar set. The
"registry" is the union of those relays. We can run our own with
tighter spam policy and verified-seller badges; users who don't
trust us route around us.

### Content stays with the seller

Photos, full descriptions, inspection PDFs, contact info — all live
on the seller's machine. A buyer fetches them only after the seller
explicitly grants access in a 1-to-1 ACP session. The platform
processes nothing. GDPR posture is structural: we have no data to
delete because we never had it.

### End-to-end encrypted negotiation

NIP-17 sealed gift-wraps mean relays carry the inquiry traffic but
cannot read it. The platform — even the relay we operate — cannot
mediate, surveil, or moderate negotiation content. We can moderate
listings (which are public and signed) and we can blocklist abusive
pubkeys, but we cannot read DMs.

### Trust as a stack, not a gatekeeper

Trust signals are layered. None alone is decisive:

- NIP-13 PoW raises the per-event spam cost
- Paid relays raise the per-pubkey spam cost
- NIP-58 verified-seller badges issued by us (lightweight verification:
  email, payment method, dealer domain)
- NIP-51 mute lists (ours, others, the user's own)
- Seller pubkey reputation (age, prior-listing closures, follow graph)

A buyer composes a trust posture from this stack. There's no single
"approved seller" gate.

## How we make money

The protocol stays free. Revenue comes from layers above:

1. **Premium plugin tier** — AI-assisted negotiation drafting, photo
   grading, multi-account orchestration. ~$10/agent/month.
2. **Managed relay subscription** — better SLA, tighter spam policy
   on our relay. ~$5/npub/month.
3. **NIP-58 verified-seller badges** — $20 one-time for private
   sellers, $50/year for dealers.
4. **Vertical packs** — pre-built skill + tag schema + custom MCP
   bundles for cars (first), real estate, watches, services. Sold
   as installable packages, $50–500/month for business plans.
5. **Custom MCP servers** — `reverse-image-mcp` (paid), and a
   pipeline of cross-vertical MCPs that work in any MCP-compatible
   client (Claude Desktop, Cursor, Hermes, future tools). Pricing
   per-call or subscription.

Notably absent: no escrow, no payments, no transaction fees. Every
sale happens off-platform, peer-to-peer.

## What it's not

- Not a marketplace operator. We don't custody money, inventory, or
  PII.
- Not a Carfax-style data reseller. The MCPs we sell are local-only
  (perceptual hashes, VIN structure decode, on-network price comps).
- Not a custodial chat platform. We can't read DMs.
- Not a file-hosting service. Photos move agent-to-agent over ACP.
- Not crypto-adjacent. Nostr is a federated relay protocol; there's
  no token, no chain, no consensus, no smart contracts.

## Why now

Three things converged:

1. **Hermes Agent** (Nous Research, MIT) ships as a real, running
   agent runtime with skills, memory, gateway, and MCP support.
   We don't have to build the agent harness.
2. **Nostr** matured to the point where there are mature relays
   (`strfry`), good clients in every language, and a standardized
   classified-listing event shape (NIP-99). The protocol stack we'd
   need to invent is already done.
3. **ACP** (Agent Client Protocol) gives us standardized
   agent-to-agent rich communication including binary content blocks
   — the missing piece for "photos move peer-to-peer". Hermes ships
   the adapter.

The product is composing those three things with a tight skill /
tag-schema / MCP layer specific to commerce.

## Where to go from here

- `PRD.md` for the precise requirements
- `PROTOCOL.md` for the on-the-wire design
- `MVP_WEEKEND.md` for the smallest demo
- `LAUNCH_PLAN.md` for the 90-day shipping plan
- `SECURITY.md` for the threat model and pre-launch checklist
- `BUSINESS_MODEL.md` for the revenue stack
- `CLAUDE.md` for the rules every code change must respect
