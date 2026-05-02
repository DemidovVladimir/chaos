# buyer — production buyer-agent component

The production buyer agent: a Hermes plugin that subscribes to NIP-99
filters, applies the evaluation rubric from
`cars-pack/skills/buyer-cars/SKILL.md`, sends NIP-17 inquiries, and
receives photos via ACP.

> **Status**: scaffold. The runnable starter is in `../mvp/buyer.py`
> (text-only, no ACP, NIP-04 instead of NIP-17). Wiring the production
> version is week 1–4 of `LAUNCH_PLAN.md`.

## What lives here when complete

```
buyer/
├── README.md                this file
├── pyproject.toml           Python package definition
├── plugin.yaml              Hermes plugin manifest
└── src/
    └── neuro_spati_buyer/
        ├── __init__.py          register(ctx)
        ├── config.py            BuyerConfig — relays, identity path, ACP url
        ├── identity.py          Keypair load/save (mode 0600), Schnorr signing
        ├── input_safety.py      copy of shared sanitizer
        ├── filters.py           translate user wants → NIP REQ filter
        ├── subscribe.py         REQ subscription, dedupe by id
        ├── evaluator.py         apply buyer-cars rubric
        ├── inquiry.py           build + encrypt + publish NIP-17 inquiry
        ├── acp_client.py        ACP client; receives ImageContentBlocks from seller
        ├── negotiation.py       round tracking, market-comp-driven counter
        ├── inbox.py             ~/.neuro_spati/buyer/inbox/<conversation>.jsonl
        ├── tools_subscribe.py   skill tool: create_filter, list_filters, pause_filter
        ├── tools_inquire.py     skill tool: send_inquiry, await_response
        ├── tools_negotiate.py   skill tool: draft_offer, accept_offer, reject_offer
        └── main.py              CLI: hermes neuro-spati-buyer {watch, inquire, status}
```

## Component contract

The buyer plugin **must**:

1. Hold the user's Nostr keypair only at `~/.neuro_spati/keys/buyer.key`,
   mode 0600.
2. Subscribe to configured relays with REQ filters built from cars-pack
   tag schema.
3. Dedupe events by `id` across relays.
4. Apply the evaluation rubric from
   `../cars-pack/skills/buyer-cars/SKILL.md` before notifying the user.
5. Send inquiries as NIP-17 gift-wrapped events.
6. Open ACP sessions against `seller.acp_url` to receive photos and
   documents. **Never fetch via HTTP.**
7. Run `reverse_image_check` (thorough tier) on every photo received
   via ACP, on the bytes directly.
8. Maintain the negotiation state machine.
9. Require explicit user confirmation for any acceptance.

The buyer plugin **must not**:

- Send the user's PII to a counterparty without explicit per-listing
  approval
- Accept commands inside `<untrusted>` blocks
- Have `terminal`, `execute_code`, `delegation`, `web`, `mcp` toolsets
  enabled
- Call commercial vehicle-history providers

## Hermes plugin shape

```yaml
# plugin.yaml
manifest_version: 1
name: neuro-spati-buyer
description: |
  Buyer agent for the neuro-spati Nostr-based marketplace. Subscribes
  to NIP-99 filters, evaluates listings, sends NIP-17 inquiries,
  receives photos via ACP.
version: 0.1.0
author: neuro-spati
license: MIT
entry_point: neuro_spati_buyer:register
required_env:
  - NEURO_SPATI_RELAYS
  - NEURO_SPATI_ACP_URL
forbidden_toolsets:
  - terminal
  - delegation
  - file
  - web
  - mcp
```

## Configuration

`~/.neuro_spati/buyer.yaml`:

```yaml
relays:
  - "wss://relay.your-domain.app"
  - "wss://relay.damus.io"
  - "wss://nos.lol"

acp:
  bind: "0.0.0.0:8645"
  public_url: "https://x.io/acp"

filters:
  default:
    kinds: [30402]
    "#t": ["cars"]
    since_days: 30

evaluator:
  hard_red_flag_thresholds:
    stock_image_similarity: 0.92
    price_off_median: 0.5         # 50% off in either direction
  soft_red_flag_thresholds:
    stock_image_similarity: 0.85
  market_comp_window_days: 60

trust_graph:
  default_trust_root: "<operator pubkey hex>"
  badge_required_for_evaluation: false
```

## How to build it

Phase 1 (week 1):

- Implement `identity.py`, `subscribe.py`, `evaluator.py` (skeletal —
  print to user, no rubric yet). Verify subscription delivers events
  on Mode A relay.

Phase 2 (week 2):

- Implement `inquiry.py` (NIP-04 path first), `acp_client.py`. Verify
  two-machine end-to-end test.

Phase 3 (week 3):

- Switch inquiry to NIP-17 (gift wrap, NIP-44).
- Implement full `evaluator.py` with cars-pack rubric.
- Wire `reverse_image_check` (thorough tier) on photos received via
  ACP.

Phase 4 (week 4):

- Implement `negotiation.py` with market-comp-driven counter logic.
- Wire `vin_decode` for any VIN the seller shares.
- Polish CLI.

## See also

- `../mvp/buyer.py` — the runnable MVP starter
- `../cars-pack/skills/buyer-cars/SKILL.md` — the canonical buyer skill
- `../PROTOCOL.md` — the on-the-wire design
- `../SECURITY.md` — pre-launch security checklist
- `../CLAUDE.md` — engineering rules every PR must respect
