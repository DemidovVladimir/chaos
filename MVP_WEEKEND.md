# Weekend MVP — the smallest thing that proves the loop

**Goal:** by Sunday night, two laptops can do this:

- Laptop A publishes a NIP-99 listing for a fictional car
- Laptop B's filter matches it and surfaces it
- Laptop B sends Laptop A a DM: "tell me more"
- Laptop A replies with a longer description
- The whole thing runs over **a public community Nostr relay** with
  **no infrastructure on your side** and **no Hermes integration yet**

Everything beyond that is out of scope until this works.

## What's IN, what's OUT

| In (weekend) | Out (later) |
|---|---|
| One seller script: `seller.py` | Hermes plugin integration |
| One buyer script: `buyer.py` | Mode A relay (your own strfry) |
| Public community relays only (`wss://relay.damus.io`, `wss://nos.lol`) | Premium plugin tier, billing |
| `pynostr` library — handles keypair + sig + WebSocket | Schnorr / NIP-44 hand-rolled |
| **NIP-04 legacy DMs** (kind 4) — encrypted but simpler than NIP-17 | NIP-17 gift-wrap |
| One JSON file as the seller's local "catalog" | Per-item catalogs, manifests, attestations |
| **No photos in the MVP at all** — text inquiry / text reply only | ACP `ImageContentBlock` streamed agent-to-agent (no third-party host, no HTTP file server, ever) |
| ~11 essential cars-pack tags | Full cars-pack tag schema |
| Hardcoded buyer filter | Filter authoring UI |
| No PoW (relays we use don't require it) | NIP-13 mining |
| No verified-seller badges | NIP-58 issuer |
| No reverse-image check | reverse-image-mcp |
| No market comps | market-comp-mcp |
| No moderation tooling | abuse@ inbox + appeal flow |

The full cars-pack schema, the operations runbook, the launch plan,
the business model — all stay as documents, none ship as code this
weekend.

## On photos — they don't exist in this MVP

Photos move agent-to-agent via ACP content blocks
(`ImageContentBlock`, `EmbeddedResourceContentBlock`). No HTTP file
server, no signed URLs, no third-party host. **That layer ships in
the post-weekend sprint when we wire ACP transport.** For the
weekend, the entire demo is text. The seller can reference photos in
the listing description as a sentence ("interior is gray cloth,
clean") but no image bytes leave their machine until ACP is up.

This is a deliberate scope cut, not a missing feature. The protocol
does not require third-party file hosting; we don't need to fake
one for the MVP.

## Stack

- Python 3.11+ (you have it)
- `pynostr` — `pip install pynostr` (handles keypair, signing,
  WebSocket relay client, NIP-04 encrypt/decrypt). Mature.
- `websockets` (transitive dep of pynostr)

That's it. Two Python scripts and two relay URLs.

## Time budget

| Task | Time |
|---|---|
| Saturday morning — env setup, keypairs, hello-world publish | 2h |
| Saturday afternoon — `seller.py`: publish a NIP-99 listing | 2h |
| Saturday evening — `buyer.py`: subscribe, decode, render | 2h |
| Sunday morning — DM round-trip (NIP-04) | 3h |
| Sunday afternoon — pull it together: 30-second demo | 2h |
| Sunday evening — slack | 2h |

**13 hours of focused work.**

## Files in this MVP

```
mvp/
├── README.md                  how to run it
├── requirements.txt           pynostr only
├── seller.py                  publish + listen for DMs + reply
├── buyer.py                   subscribe + render matches + send DM
├── shared.py                  helpers (keypair load/save, event builders)
└── sample_car.toml            the demo car
```

## The whole protocol, weekend-edition

```
seller.py                       relay.damus.io                         buyer.py
   │                                  │                                     │
   │ publish kind:30402 ─────────────▶│                                     │
   │  tags: d, title, summary,        │                                     │
   │        price, location, t=cars,  │                                     │
   │        t=mazda, make, model,     │                                     │
   │        year, mileage_band        │                                     │
   │  content: full description       │                                     │
   │                                  │                                     │
   │                                  │◀─── REQ {kinds:[30402], #t:["cars"], │
   │                                  │       #make:["mazda"]}              │
   │                                  │                                     │
   │                                  │─── EVENT (the listing) ────────────▶│
   │                                  │                              prints:│
   │                                  │                              "match │
   │                                  │                              found, │
   │                                  │                              DM y/n?"│
   │                                  │                                     │
   │                                  │◀──── publish kind:4 (NIP-04 DM)─────│
   │                                  │  encrypted to seller's pubkey       │
   │                                  │  content: "tell me more"            │
   │                                  │                                     │
   │◀── EVENT (the DM) ───────────────│                                     │
   │                                  │                                     │
   │ decrypt, print, reply            │                                     │
   │ publish kind:4 to buyer ────────▶│                                     │
   │  content: "<longer description>" │                                     │
   │                                  │─── EVENT (reply DM) ───────────────▶│
   │                                  │                              prints:│
   │                                  │                              reply  │
```

Six round-trips with the relay. No infrastructure on your side.

## DMs — NIP-04 not NIP-17

For the weekend we use **NIP-04 legacy encrypted DMs** (kind 4), not
NIP-17 gift wraps. Reasons:

- `pynostr` ships an `EncryptedDirectMessage` helper for NIP-04
- AES-256-CBC with shared ECDH secret. Encrypted. Works.
- NIP-04 is "deprecated in favor of NIP-17" but every relay still
  supports it
- NIP-17 would add ~half a day on its own (gift-wrap + ephemeral
  keypairs + NIP-44 encryption). Not weekend-shaped.

**We migrate to NIP-17 in week 3 of the launch plan.**

## Relay choice

Two free, public, low-friction relays:

- `wss://relay.damus.io` — popular, reliable, no PoW
- `wss://nos.lol` — secondary

That's it. Your own strfry comes in week 1 of the launch plan.

## Demo script for Sunday evening

The deliverable is a 30-second screen capture showing:

1. Run `python seller.py publish sample_car.toml` on Laptop A.
2. Run `python buyer.py watch` on Laptop B.
3. Within ~5 seconds, Laptop B prints: "Match: 2018 Mazda 3
   hatchback, 15,000 EUR, EU/CZ/Prague. DM seller? [y/N]".
4. Press `y`. Type "tell me more about service history".
5. Laptop A's `seller.py` listener prints: "Inquiry from
   <buyer-pubkey>: tell me more about service history. Reply? [y/N]".
6. Press `y`. Type "Full Mazda dealer service history. Recently
   passed STK. New tires. Happy to share photos and inspection
   report once we open an ACP session — book one when you're ready."
7. Laptop B prints: "Reply from seller: <text>".

The "open an ACP session" line is a placeholder for the next sprint;
it makes explicit to the buyer that photos exist and are shared
peer-to-peer, not via an external link.

That's the whole MVP. ~150 lines of Python total, two free public
relays, zero infrastructure. If it works by Sunday evening, you've
validated the architecture and the launch plan sequences cleanly.

## After the weekend

When the demo works, week-by-week:

- **Week 1**: Replace the hardcoded filter with a Hermes skill that
  the agent invokes. Wire ACP transport between agents (Hermes ships
  `acp_adapter/`) so the seller can stream `ImageContentBlock`s to
  the buyer when asked. **Photos arrive in the buyer's ACP session,
  never via HTTP.**
- **Week 2**: Stand up your own strfry relay (the operations runbook
  in `registry/` applies — a few hours of deployment work).
- **Week 3**: Move from NIP-04 to NIP-17 sealed DMs.
- **Week 4**: Add the cars-pack tag schema in full + the
  reverse-image-mcp.

## Reality check

If by Sunday evening the loop doesn't work, do not "scope creep"
your way through Monday. Stop, identify the one failure point
(almost certainly: relay choice, library issue, or NIP-04 encryption),
and unblock it. The MVP either works in a weekend or there's something
about the stack you didn't understand. That's information; act on it.
