# Weekend MVP — the smallest thing that proves the loop

The MVP is the working three-layer demo: **Nostr discovery →
encrypted DM round-trip → MCP HTTP+SSE rich-content delivery with
SHA-256 verification**, on two laptops, over public community
relays, with no infrastructure on your side and no third-party file
host anywhere in the data path.

The reference vertical we ship the demo against is `cars-pack@1` —
a fictional used-car listing — but the loop is the protocol's
loop, not cars-specific. The same publish / subscribe / MCP-fetch
shape carries any vertical pack: a model offering, a dataset
sample, a service quote, a compute job. The MVP is the protocol's
proof, not the domain's.

## What this MVP proves

1. Two agents on different machines find each other via a Nostr
   relay neither of them operates.
2. They open an end-to-end encrypted DM channel using the user's
   own secp256k1 keys — the relay can carry the ciphertext but
   cannot read it.
3. They open an MCP HTTP+SSE session and exchange binary content
   (images + an inspection PDF) as `ImageContent` and
   `EmbeddedResource` blocks returned from `tools/call` results,
   verified by SHA-256 hash.
4. **No third-party file host anywhere in the path.** Bytes flow
   seller-disk → MCP tool result → buyer-disk.

That's the whole protocol in miniature. Everything in `seller/`,
`buyer/`, and `plugins/` is a more production-shaped version of the
same loop — full grant policy, NIP-17 instead of NIP-04, full PoW,
the cross-vertical capability MCPs wired in.

## What's IN, what's OUT

| In (weekend MVP) | Out (production scaffolds) |
|---|---|
| One offering script: `seller.py` | Hermes plugin integration (`plugins/`) |
| One seeking script: `buyer.py` | Mode A relay (your own strfry) |
| Public community relays only (`wss://relay.damus.io`, `wss://nos.lol`) | Premium plugin tier, billing |
| `pynostr` library — keypair + sig + WebSocket | Hand-rolled NIP-44 / Schnorr |
| **NIP-04 legacy DMs** (kind 4) — encrypted but simpler than NIP-17 | NIP-17 sealed gift-wrap (production) |
| One TOML file as the offering's local catalog | Full per-item catalog, manifests, attestations |
| FastMCP server / client wired against the cars-pack tool surface | Full grant policy from `seller-cars` skill |
| ~11 essential cars-pack tags | Full cars-pack tag schema |
| Hardcoded buyer filter | Filter authoring UI |
| No PoW (relays we use don't require it for MVP) | NIP-13 mining ≥ 20 bits |
| No verified-issuer badges | NIP-58 issuer agent |
| No reverse-image check | `reverse-image-mcp` |
| No market comps | `market-comp-mcp` |
| No reputation aggregation | `reputation-mcp` |
| No moderation tooling | `abuse@` inbox + appeal flow |

## Stack

- Python 3.11+
- `pynostr` — `pip install pynostr` (handles keypair, signing,
  WebSocket relay client, NIP-04 encrypt/decrypt)
- `mcp` — the FastMCP Python SDK for the HTTP+SSE server / client
- `httpx`, `websockets` (transitive)

That's it. Two Python scripts plus two relay URLs.

## Setup

```bash
git clone <repo> chaos && cd chaos/mvp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Generate sovereign keypairs locally (mode 0600)
python seller.py keygen
python buyer.py keygen
```

That writes `~/.chaos/keys/seller.key` and
`~/.chaos/keys/buyer.key` at mode 0600. There is no key
recovery path — sovereignty has costs. Lose this file, you lose
the identity.

## Run the demo

```bash
# Terminal 1 — offering side
python seller.py publish sample_listing.toml   # NIP-99 publish to relay set
python seller.py serve                          # FastMCP HTTP+SSE server + DM listener

# Terminal 2 — seeking side
python buyer.py watch                           # subscribe + DM round-trip + MCP fetch
```

The reference `sample_listing.toml` describes a fictional used car —
it's the cars-pack@1 example we shipped first. To experiment with
another shape, write a new TOML against a different pack's tag
schema; the publish flow is identical.

## What you should see

1. **Within ~5 seconds**, the `buyer.py watch` terminal prints:
   `Match: <listing title>, <price>, <region>. DM seller? [y/N]`
2. Press `y`, type a question. The seeking-side agent encrypts via
   NIP-04, publishes the kind-4 event addressed to the offering
   pubkey.
3. The `seller.py serve` terminal prints:
   `Inquiry from <buyer-pubkey>: <text>. Reply? [y/N]`
4. Press `y`, type a reply (which includes a `mcp_url` and a
   `session_token`). The buyer reads the reply and **opens an MCP
   HTTP+SSE session** against the seller's URL.
5. The buyer runs `tools/list`, then calls `request_photos` and
   `request_inspection_report`. The seller's FastMCP server returns
   `ImageContent` blocks for the photos and an `EmbeddedResource`
   block for the PDF. The buyer verifies each block by SHA-256
   against a hash the seller included in the previous DM.
6. The buyer prints the photo count, the PDF size, and `OK — bytes
   never touched a third-party host.`

## What it doesn't do

- **NIP-04, not NIP-17.** Production wires sealed gift-wraps; the
  MVP keeps the simpler legacy DM format because `pynostr` ships an
  `EncryptedDirectMessage` helper for it. NIP-17 wiring lives in
  `seller/` and `buyer/`.
- **No PoW.** Public relays we use don't require it; the production
  publish flow mines ≥ 20 bits.
- **No grant policy.** The MVP `seller.py` returns whatever the
  buyer asks for. The full per-ask grant policy (auto-grant routine
  asks; user-prompt for sensitive asks) lives in
  `verticals/cars-pack/skills/seller-cars/SKILL.md` and is wired
  into the production seller scaffold.
- **No capability MCPs.** Reverse-image, market-comp, reputation,
  and pack-local capability MCPs (e.g. `vin-decoder-mcp` for cars)
  are not wired into the MVP loop. They are wired into the buyer
  plugin scaffold under `plugins/cars-buyer/`.
- **No NIP-58 badges, no NIP-51 mute lists, no admin-agent.** All
  five trust layers are scaffolded under `reputation/` but not
  active in the MVP loop.

The production wiring lives in:

- `seller/` and `buyer/` — universal engines, pack-driven
- `plugins/cars-seller/`, `plugins/cars-buyer/`,
  `plugins/cars-admin/` — Hermes install targets for the reference
  vertical
- `plugins/chaos-pro/` — cross-vertical paid upgrade
- `shared-mcp/` — capability MCPs reused by every vertical
- `reputation/` — kinds, scoring, dispute protocol

## Files in `mvp/`

```
mvp/
├── README.md                  detailed run notes
├── requirements.txt           pynostr + mcp + httpx
├── seller.py                  publish + DM listener + FastMCP server
├── buyer.py                   subscribe + DM round-trip + FastMCP client
├── shared.py                  helpers (keypair, event builders, hash verify)
├── sample_listing.toml        the demo offering (cars reference)
└── sample_photos/             local content the seller serves over MCP
```

## After the weekend

When the demo works, work continues in `LAUNCH_PLAN.md`. The
sequence:

- **Phase 1 (week 1)** — universal engines (`seller/` + `buyer/`)
  wired into Hermes plugin loaders.
- **Phase 2 (week 2)** — first vertical pack (cars) end-to-end
  via Hermes plugin, full grant policy, NIP-17 instead of NIP-04,
  PoW on publish.
- **Phase 3 (week 3)** — second vertical pack as proof-of-generality
  (one of the sketched verticals — see `VERTICALS.md`) +
  `reputation-mcp` wiring.
- **Phase 4 (week 4)** — admin-agent live, community arbitration,
  Phase-1 staking research kicked off.

## Reality check

If by Sunday evening the loop doesn't work, do not "scope creep"
through Monday. Stop, identify the one failure point (almost
certainly: relay choice, library install issue, MCP transport
auth, or NIP-04 encryption), and unblock it. The MVP either works
in a weekend or there's something about the stack we didn't
understand. That's information; act on it.
