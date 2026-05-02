# seller — production seller-agent component

The production seller agent: a Hermes plugin that publishes NIP-99
listings, listens for NIP-17 inquiries, applies the per-ask grant
policy from `cars-pack/skills/seller-cars/SKILL.md`, and streams
photos to buyers via ACP.

> **Status**: scaffold. The runnable starter is in `../mvp/seller.py`
> (text-only, no ACP, NIP-04 instead of NIP-17, no PoW). Wiring the
> production version is week 1–4 of `LAUNCH_PLAN.md`. This folder
> exists so the contract is clear and so future Claude sessions know
> where to put the production code.

## What lives here when complete

```
seller/
├── README.md                this file
├── pyproject.toml           Python package definition
├── plugin.yaml              Hermes plugin manifest
└── src/
    └── neuro_spati_seller/
        ├── __init__.py          register(ctx)
        ├── config.py            SellerConfig — relays, identity path, ACP url
        ├── identity.py          Keypair load/save (mode 0600), Schnorr signing
        ├── input_safety.py      copy of shared sanitizer; layer-1 defense
        ├── catalog.py           local item store at ~/.neuro_spati/items/
        ├── publish.py           NIP-99 build + PoW mine + sign + publish
        ├── inquiry_listener.py  NIP-17 gift-wrap listener, decrypt, route
        ├── grant_policy.py      per-ask policy (from seller-cars skill)
        ├── acp_session.py       ACP server endpoint; streams ImageContentBlocks
        ├── negotiation.py       round tracking, bid floor, user-confirm
        ├── attestation.py       sign / verify Nostr attestation events
        ├── tools_publish.py     skill tool: publish_item, archive_item, update_item
        ├── tools_inquire.py     skill tool: handle_inquiry, grant_asks, deny_ask
        ├── tools_negotiate.py   skill tool: counter_offer, accept_offer, reject_offer
        └── main.py              CLI: hermes neuro-spati-seller {publish, listen, status}
```

## Component contract

The seller plugin **must**:

1. Hold the user's Nostr keypair only at `~/.neuro_spati/keys/seller.key`,
   mode 0600.
2. Publish NIP-99 events with cars-pack tag schema; never include an
   `image` tag; always include `acp` and `photos_via=acp` tags.
3. Mine NIP-13 PoW ≥ 20 bits before signing.
4. Run `reverse_image_check` (fast tier, local) on every photo in the
   item folder before any ACP session can deliver it.
5. Listen for NIP-17 gift-wrapped inquiries on configured relays.
6. Apply the per-ask grant policy from
   `../cars-pack/skills/seller-cars/SKILL.md` § "Inquiry-handling
   policy".
7. Stream photos and PDFs to the buyer via ACP `ImageContentBlock` /
   `EmbeddedResourceContentBlock`. **Never via HTTP.**
8. Maintain the negotiation state machine (≤ 5 rounds, ≤ 1000 chars
   per offer, ≤ 50,000 chars total).
9. Require explicit user confirmation for any acceptance, sensitive
   ask grant, or PII-adjacent action.

The seller plugin **must not**:

- Hold any third-party file URLs to user photos (no Imgur, Dropbox,
  etc.)
- Store buyer PII received during inquiries beyond the
  conversation log
- Accept commands inside `<untrusted>` blocks
- Have `terminal`, `execute_code`, `delegation`, `web`, `mcp`
  toolsets enabled (per `CLAUDE.md` § Architecture rules)

## Hermes plugin shape

```yaml
# plugin.yaml
manifest_version: 1
name: neuro-spati-seller
description: |
  Seller agent for the neuro-spati Nostr-based marketplace. Publishes
  NIP-99 listings, handles NIP-17 inquiries, streams photos via ACP.
version: 0.1.0
author: neuro-spati
license: MIT
entry_point: neuro_spati_seller:register
required_env:
  - NEURO_SPATI_RELAYS              # comma-separated wss:// urls
  - NEURO_SPATI_ACP_URL             # https url where this seller's ACP server runs
forbidden_toolsets:
  - terminal
  - delegation
  - file
  - web
  - mcp
```

## Configuration

`~/.neuro_spati/seller.yaml`:

```yaml
relays:
  - "wss://relay.your-domain.app"
  - "wss://relay.damus.io"
  - "wss://nos.lol"

acp:
  bind: "0.0.0.0:8645"
  public_url: "https://a.io/acp"        # ngrok or other tunnel; the public face

publish:
  pow_min_bits: 20
  default_currency: "EUR"
  default_region: "EU/CZ/Prague"

grant_policy:
  defaults_from: "cars-pack/skills/seller-cars/SKILL.md"
  always_user_confirm:
    - vin_full
    - pickup_address
    - phone_number

negotiation:
  max_rounds: 5
  max_chars_per_offer: 1000
  max_chars_per_match: 50000
```

## How to build it

Phase 1 (week 1 of `LAUNCH_PLAN.md`):

- Implement `identity.py`, `publish.py`, `inquiry_listener.py` —
  enough to publish a listing and decrypt an inquiry. Reuses
  `pynostr` like the MVP does.
- Wire as a Hermes plugin (entry point, register hook).
- Verify text-only round-trip on Mode A relay.

Phase 2 (week 2):

- Implement `acp_session.py` using Hermes' `acp_adapter/`. Stream
  test photo on demand.
- Wire `grant_policy.py` from the seller-cars skill.
- Verify two-machine end-to-end test passes unattended.

Phase 3 (week 3):

- Replace NIP-04 with NIP-17 gift-wrap path (NIP-44 encryption).
- Implement attestation signing (`attestation.py`).
- Implement negotiation rounds (`negotiation.py`).

Phase 4 (week 4+):

- Wire `reverse_image_check` integration as a pre-share gate.
- Wire `vin_decode` and `market_comp` references.
- Polish CLI.

## See also

- `../mvp/seller.py` — the runnable MVP starter
- `../cars-pack/skills/seller-cars/SKILL.md` — the canonical seller
  skill
- `../PROTOCOL.md` — the on-the-wire design
- `../SECURITY.md` — pre-launch security checklist
- `../CLAUDE.md` — engineering rules every PR must respect
