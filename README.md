# neuro-spati

A peer-to-peer marketplace where buyers and sellers run autonomous
agents that discover each other through Nostr and trade directly. The
platform owns no data. Sellers own their content. Buyers own their
keys. The registry is a Nostr relay; binary content moves
agent-to-agent over ACP. Cars first; other verticals follow.

## What's in this repo

```
neuro-spati/
├── README.md                this file
├── CLAUDE.md                operating rules for any Claude session in this repo
├── PRD.md                   product requirements document
├── OVERVIEW.md              what the product is, in plain prose
├── PROTOCOL.md              the on-the-wire design (Nostr + ACP)
├── SECURITY.md              threat model, defense in depth, pre-launch checklist
├── BUSINESS_MODEL.md        how this becomes a sustainable business
├── LAUNCH_PLAN.md           90-day plan with weekly milestones and exit criteria
├── MVP_WEEKEND.md           smallest thing that proves the loop, in one weekend
├── LICENSE                  MIT
│
├── architecture.svg         top-level system diagram
├── nostr_federation.svg     how relays + agents fan in / out
├── injection_defense_layers.html   interactive defense-in-depth onion
│
├── seller/                  seller-agent component (Hermes plugin scaffold)
├── buyer/                   buyer-agent component (Hermes plugin scaffold)
├── registry/                Mode A Nostr relay deployment (strfry + Caddy + monitoring)
├── cars-pack/               cars-vertical pack (skills, tag schema, MCP specs)
└── mvp/                     weekend MVP — runnable seller.py + buyer.py
```

## Where to start

| If you want to… | Open |
|---|---|
| Understand the product in 5 minutes | `OVERVIEW.md` |
| Know the rules before writing code | `CLAUDE.md` |
| Know what we're building, exactly | `PRD.md` |
| See the protocol on the wire | `PROTOCOL.md` |
| Ship the smallest thing that works | `MVP_WEEKEND.md` then `mvp/` |
| Deploy the relay | `registry/README.md` |
| Build the seller agent | `seller/README.md` |
| Build the buyer agent | `buyer/README.md` |
| Plan the next 90 days | `LAUNCH_PLAN.md` |
| Plan how to monetize | `BUSINESS_MODEL.md` |
| Threat-model and harden | `SECURITY.md` |

## What this is not

- Not a marketplace operator (no funds, no inventory, no PII)
- Not a Carfax-style data reseller (no third-party VIN-history lookups)
- Not a custodial chat platform (DMs are end-to-end encrypted at the protocol layer)
- Not a file-hosting service (binary content moves agent-to-agent over ACP)
- Not a tracker for off-platform deals — once buyer and seller agree, the platform is out

## Status

- **MVP**: runnable code in `mvp/` — see `MVP_WEEKEND.md`
- **Mode A registry**: deployment runbook ready in `registry/`
- **Cars pack**: skills + tag schema + MCP specs in `cars-pack/`
- **Production seller / buyer Hermes plugins**: scaffolds in `seller/` and `buyer/`; full implementation is the post-MVP sprint

## Quick start — weekend MVP, no infrastructure on your side

```bash
cd mvp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seller.py keygen
python buyer.py keygen

# Terminal 1
python seller.py publish sample_car.toml
python seller.py listen

# Terminal 2
python buyer.py watch
```

Two laptops, two free public Nostr relays, no infrastructure of your
own. Text-only inquiry round-trip. See `mvp/README.md` for the demo
flow.

## License

MIT. See `LICENSE`.
